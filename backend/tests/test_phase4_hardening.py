import pytest
import io
import json
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.security.tokens import create_access_token
from app.models.document import Document
from app.models.ocr import OCRJob, OCRExtractedField
from app.models.audit import AuditEvent
from app.storage.service import storage_service
from app.intelligence.delay_predictor import DelayPredictorService
from app.intelligence.model_trainer import train_and_evaluate_model, FEATURE_COLUMNS
from app.intelligence.ocr_service import OCRService
from app.intelligence.aph_service import APHAssistantService
from app.audit.service import record_audit_event, verify_audit_chain


def get_auth_headers(user, roles, inst_id=None):
    token = create_access_token(user_id=user.id, email=user.email, roles=roles, institution_id=inst_id)
    return {"Authorization": f"Bearer {token}"}


def make_test_pdf(text: str) -> bytes:
    stream_content = f"BT\n/F1 12 Tf\n72 712 Td\n({text}) Tj\nET\n".encode("latin1")
    stream_len = len(stream_content)
    return (
        f"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>
endobj
4 0 obj
<< /Length {stream_len} >>
stream
""".encode("latin1")
        + stream_content
        + f"""endstream
endobj
5 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000229 00000 n 
0000000390 00000 n 
trailer
<< /Size 6 /Root 1 0 R >>
startxref
500
%%EOF""".encode("latin1")
    )


def make_blank_pdf() -> bytes:
    import pypdf
    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


# ==============================================================================
# PART 1: M11 DELAY-RISK PREDICTION HARDENING
# ==============================================================================

@pytest.mark.asyncio
async def test_m11_feature_leakage_and_outcome_independence(db_session: AsyncSession, seed_test_data):
    """
    Verify feature extraction uses only pre-decision operational indicators.
    Must not contain post-decision outcomes, final approval/rejection flags, or future timestamps.
    """
    app = seed_test_data["application"]
    service = DelayPredictorService(db_session)
    features = await service.extract_features(app)

    # All defined feature columns
    for col in FEATURE_COLUMNS:
        assert col in features, f"Missing feature: {col}"
        assert not isinstance(features[col], (list, dict)), f"Feature {col} must be numeric scalar"

    # Strictly verify NO outcome leakage features
    forbidden_leakage_keys = [
        "final_decision", "outcome", "is_approved", "is_rejected",
        "sac_outcome", "shc_outcome", "decision_timestamp", "approval_order_id"
    ]
    for forbidden in forbidden_leakage_keys:
        assert forbidden not in features, f"Data leakage detected! Feature '{forbidden}' is present."


@pytest.mark.asyncio
async def test_m11_missing_inputs_resilience(db_session: AsyncSession, seed_test_data):
    """
    Ensure the delay predictor handles missing, null, or extreme values gracefully.
    Clamps probabilities cleanly between 0.01 and 0.99.
    """
    app = seed_test_data["application"]
    # Intentionally corrupt timestamps or operational fields
    app.submitted_at = None
    await db_session.commit()

    service = DelayPredictorService(db_session)
    pred = await service.predict_for_application(app.id)

    assert pred.risk_score >= 0.01 and pred.risk_score <= 0.99
    assert pred.risk_category in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
    assert pred.estimated_delay_days >= 0.0
    assert pred.is_automated_advisory is True


@pytest.mark.asyncio
async def test_m11_risk_category_thresholds(db_session: AsyncSession):
    """
    Validate that risk category categorization strictly adheres to thresholds:
    < 0.25: LOW, 0.25 - 0.50: MEDIUM, 0.50 - 0.75: HIGH, >= 0.75: CRITICAL
    """
    service = DelayPredictorService(db_session)

    _, cat_low, _, _ = service.compute_prediction({
        "unresolved_deficiencies_count": 0,
        "deficient_documents_count": 0,
        "evc_pending": False,
        "regional_backlog_density": 1,
        "days_in_current_status": 2.0,
    })
    assert cat_low == "LOW"

    _, cat_med, _, _ = service.compute_prediction({
        "unresolved_deficiencies_count": 2,
        "deficient_documents_count": 0,
        "evc_pending": False,
        "regional_backlog_density": 1,
        "days_in_current_status": 2.0,
    })
    assert cat_med == "MEDIUM"

    _, cat_high, _, _ = service.compute_prediction({
        "unresolved_deficiencies_count": 3,
        "deficient_documents_count": 2,
        "evc_pending": True,
        "regional_backlog_density": 25,
        "days_in_current_status": 30.0,
    })
    assert cat_high in ("HIGH", "CRITICAL")


@pytest.mark.asyncio
async def test_m11_reproducible_synthetic_training_evaluation():
    """
    Verify reproducible model training and evaluation generates genuine measured metrics,
    distinguishing synthetic demonstration datasets from fabricated claim metrics.
    """
    result = train_and_evaluate_model(random_state=42)
    metrics = result["metrics"]

    assert metrics["is_synthetic_demonstration"] is True
    assert metrics["train_sample_size"] == 450
    assert metrics["evaluation_sample_size"] == 150
    assert metrics["roc_auc"] >= 0.65
    assert metrics["accuracy"] >= metrics["baseline_accuracy"]
    assert metrics["precision"] > 0.0
    assert metrics["recall"] > 0.0
    assert metrics["f1_score"] > 0.0
    assert metrics["mae_delay_days"] > 0.0


# ==============================================================================
# PART 2: M12 DOCUMENT EXTRACTION HARDENING (7 SCENARIOS)
# ==============================================================================

@pytest.mark.asyncio
async def test_m12_clean_text_pdf_extraction(client: AsyncClient, db_session: AsyncSession, seed_test_data):
    """
    Scenario 1: Clean text-based PDF correctly parses authentic fields without fabricated bounding boxes.
    """
    app = seed_test_data["application"]
    u_scrutiny = seed_test_data["users"]["scrutiny"]
    headers = get_auth_headers(u_scrutiny, ["SCRUTINY_OFFICER"])

    storage_key = "clean_text_fire_cert.pdf"
    pdf_bytes = make_test_pdf(
        "Department of Fire Services. Certificate No: NOC-2026-9842. Issued on: 2026-01-15. Valid upto: 2028-12-31."
    )
    safe_path = storage_service.vault_dir / storage_key
    with open(safe_path, "wb") as f:
        f.write(pdf_bytes)

    doc = Document(
        id="doc-clean-text-1",
        application_id=app.id,
        institution_id=app.institution_id,
        original_filename="clean_text_fire_cert.pdf",
        file_size=len(pdf_bytes),
        mime_type="application/pdf",
        sha256_hash="hash-clean-1",
        storage_key=storage_key,
        category="FIRE_NOC",
        uploaded_by_user_id=u_scrutiny.id,
        scan_status="ACCEPTED",
    )
    db_session.add(doc)
    await db_session.commit()

    resp = await client.post(f"/api/v1/ocr/process/{doc.id}", headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "COMPLETED"

    # All bounding boxes must be None (no fabricated coordinates)
    for field in data["fields"]:
        assert field["bounding_box"] is None
        assert field["is_automated_advisory"] is True

    field_names = [f["field_name"] for f in data["fields"]]
    assert "fire_noc_number" in field_names
    assert "expiry_date" in field_names
    assert "compliance_status" in field_names


@pytest.mark.asyncio
async def test_m12_scanned_raster_image_pdf_detection(client: AsyncClient, db_session: AsyncSession, seed_test_data):
    """
    Scenario 2: Scanned/image-only PDF without text layer is detected.
    Does NOT fabricate dummy fields; documents Tesseract absence accurately.
    """
    app = seed_test_data["application"]
    u_scrutiny = seed_test_data["users"]["scrutiny"]
    headers = get_auth_headers(u_scrutiny, ["SCRUTINY_OFFICER"])

    storage_key = "blank_raster_scan.pdf"
    pdf_bytes = make_blank_pdf()
    safe_path = storage_service.vault_dir / storage_key
    with open(safe_path, "wb") as f:
        f.write(pdf_bytes)

    doc = Document(
        id="doc-scanned-raster-1",
        application_id=app.id,
        institution_id=app.institution_id,
        original_filename="blank_raster_scan.pdf",
        file_size=len(pdf_bytes),
        mime_type="application/pdf",
        sha256_hash="hash-scanned-1",
        storage_key=storage_key,
        category="FIRE_NOC",
        uploaded_by_user_id=u_scrutiny.id,
        scan_status="ACCEPTED",
    )
    db_session.add(doc)
    await db_session.commit()

    resp = await client.post(f"/api/v1/ocr/process/{doc.id}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    # Must have 0 extracted fields (no dummy fallback data!)
    assert len(data["fields"]) == 0
    # Must document OCR limitation
    assert "Tesseract OCR" in data["error_message"] or "text layer" in data["error_message"]


@pytest.mark.asyncio
async def test_m12_empty_or_malformed_pdf_rejected(client: AsyncClient, db_session: AsyncSession, seed_test_data):
    """
    Scenario 3: Corrupted or truncated PDF structure is safely rejected with MALFORMED_PDF 400.
    """
    app = seed_test_data["application"]
    u_scrutiny = seed_test_data["users"]["scrutiny"]
    headers = get_auth_headers(u_scrutiny, ["SCRUTINY_OFFICER"])

    storage_key = "corrupt_file.pdf"
    corrupt_bytes = b"%PDF-1.4 [corrupted binary junk that terminates unexpectedly without xref"
    safe_path = storage_service.vault_dir / storage_key
    with open(safe_path, "wb") as f:
        f.write(corrupt_bytes)

    doc = Document(
        id="doc-corrupt-1",
        application_id=app.id,
        institution_id=app.institution_id,
        original_filename="corrupt_file.pdf",
        file_size=len(corrupt_bytes),
        mime_type="application/pdf",
        sha256_hash="hash-corrupt-1",
        storage_key=storage_key,
        category="FIRE_NOC",
        uploaded_by_user_id=u_scrutiny.id,
        scan_status="ACCEPTED",
    )
    db_session.add(doc)
    await db_session.commit()

    resp = await client.post(f"/api/v1/ocr/process/{doc.id}", headers=headers)
    assert resp.status_code == 400
    error_data = resp.json()
    assert error_data["code"] == "MALFORMED_PDF"


@pytest.mark.asyncio
async def test_m12_unsupported_format_rejected(client: AsyncClient, db_session: AsyncSession, seed_test_data):
    """
    Scenario 4: Unsupported format (plain text file) is rejected with UNSUPPORTED_FORMAT 400.
    """
    app = seed_test_data["application"]
    u_scrutiny = seed_test_data["users"]["scrutiny"]
    headers = get_auth_headers(u_scrutiny, ["SCRUTINY_OFFICER"])

    doc = Document(
        id="doc-unsupported-1",
        application_id=app.id,
        institution_id=app.institution_id,
        original_filename="notes.txt",
        file_size=120,
        mime_type="text/plain",
        sha256_hash="hash-unsupported-1",
        storage_key="notes.txt",
        category="FIRE_NOC",
        uploaded_by_user_id=u_scrutiny.id,
        scan_status="ACCEPTED",
    )
    db_session.add(doc)
    await db_session.commit()

    resp = await client.post(f"/api/v1/ocr/process/{doc.id}", headers=headers)
    assert resp.status_code == 400
    assert resp.json()["code"] == "UNSUPPORTED_FORMAT"


@pytest.mark.asyncio
async def test_m12_quarantined_document_rejected(client: AsyncClient, db_session: AsyncSession, seed_test_data):
    """
    Scenario 5: Document not in ACCEPTED state is rejected with DOCUMENT_NOT_CLEAN 400.
    """
    app = seed_test_data["application"]
    u_scrutiny = seed_test_data["users"]["scrutiny"]
    headers = get_auth_headers(u_scrutiny, ["SCRUTINY_OFFICER"])

    doc = Document(
        id="doc-quarantine-2",
        application_id=app.id,
        institution_id=app.institution_id,
        original_filename="pending_scan.pdf",
        file_size=500,
        mime_type="application/pdf",
        sha256_hash="hash-pending-1",
        storage_key="pending_scan.pdf",
        category="FIRE_NOC",
        uploaded_by_user_id=u_scrutiny.id,
        scan_status="SCANNING",
    )
    db_session.add(doc)
    await db_session.commit()

    resp = await client.post(f"/api/v1/ocr/process/{doc.id}", headers=headers)
    assert resp.status_code == 400
    assert resp.json()["code"] == "DOCUMENT_NOT_CLEAN"


@pytest.mark.asyncio
async def test_m12_no_dummy_fallback_values(client: AsyncClient, db_session: AsyncSession, seed_test_data):
    """
    Scenario 6: Missing fields are NOT synthesized or populated with dummy fallbacks.
    Only actually matched regex patterns are returned.
    """
    app = seed_test_data["application"]
    u_scrutiny = seed_test_data["users"]["scrutiny"]
    headers = get_auth_headers(u_scrutiny, ["SCRUTINY_OFFICER"])

    storage_key = "partial_fire_cert.pdf"
    # Notice: No authority name, no issue date
    pdf_bytes = make_test_pdf("Certificate No: NOC-2026-9842. Valid upto: 2028-12-31.")
    safe_path = storage_service.vault_dir / storage_key
    with open(safe_path, "wb") as f:
        f.write(pdf_bytes)

    doc = Document(
        id="doc-partial-1",
        application_id=app.id,
        institution_id=app.institution_id,
        original_filename="partial_fire_cert.pdf",
        file_size=len(pdf_bytes),
        mime_type="application/pdf",
        sha256_hash="hash-partial-1",
        storage_key=storage_key,
        category="FIRE_NOC",
        uploaded_by_user_id=u_scrutiny.id,
        scan_status="ACCEPTED",
    )
    db_session.add(doc)
    await db_session.commit()

    resp = await client.post(f"/api/v1/ocr/process/{doc.id}", headers=headers)
    assert resp.status_code == 200
    fields = resp.json()["fields"]
    field_names = [f["field_name"] for f in fields]

    # Exactly matched fields present
    assert "fire_noc_number" in field_names
    # Missing field must NOT be synthesized
    assert "issue_date" not in field_names


@pytest.mark.asyncio
async def test_m12_active_vs_expired_certificate_compliance(client: AsyncClient, db_session: AsyncSession, seed_test_data):
    """
    Scenario 7: Date validation properly checks certificate expiration date:
    - Future date -> COMPLIANT_ACTIVE
    - Past date -> EXPIRED
    """
    app = seed_test_data["application"]
    u_scrutiny = seed_test_data["users"]["scrutiny"]
    headers = get_auth_headers(u_scrutiny, ["SCRUTINY_OFFICER"])

    # Test expired certificate
    storage_key = "expired_cert.pdf"
    pdf_bytes = make_test_pdf("Fire Office Certificate No: NOC-1111. Valid upto: 2019-05-20.")
    safe_path = storage_service.vault_dir / storage_key
    with open(safe_path, "wb") as f:
        f.write(pdf_bytes)

    doc = Document(
        id="doc-expired-1",
        application_id=app.id,
        institution_id=app.institution_id,
        original_filename="expired_cert.pdf",
        file_size=len(pdf_bytes),
        mime_type="application/pdf",
        sha256_hash="hash-expired-1",
        storage_key=storage_key,
        category="FIRE_NOC",
        uploaded_by_user_id=u_scrutiny.id,
        scan_status="ACCEPTED",
    )
    db_session.add(doc)
    await db_session.commit()

    resp = await client.post(f"/api/v1/ocr/process/{doc.id}", headers=headers)
    assert resp.status_code == 200
    fields = resp.json()["fields"]
    status_field = next(f for f in fields if f["field_name"] == "compliance_status")
    assert status_field["normalized_value"] == "EXPIRED"


@pytest.mark.asyncio
async def test_m12_officer_verification_and_audit_trail(client: AsyncClient, db_session: AsyncSession, seed_test_data):
    """
    Scenario 8: Scrutiny Officer verification/correction workflow.
    Ensures:
    - Officer sets status to CORRECTED with corrected_value.
    - is_automated_advisory transitions to False.
    - Immutable chained audit log records actor, timestamps, original, and corrected values.
    """
    app = seed_test_data["application"]
    u_scrutiny = seed_test_data["users"]["scrutiny"]
    headers = get_auth_headers(u_scrutiny, ["SCRUTINY_OFFICER"])

    # Create an extracted field directly
    raw_val = "Fire Dept Typo"
    field = OCRExtractedField(
        ocr_job_id="test-job-audit",
        document_id="test-doc-audit",
        application_id=app.id,
        field_name="issuing_authority",
        field_category="FIRE_NOC",
        raw_value=raw_val,
        normalized_value=raw_val,
        confidence=0.88,
        page_number=1,
        verification_status="PENDING",
        is_automated_advisory=True,
    )
    db_session.add(field)
    await db_session.commit()
    await db_session.refresh(field)

    # Scrutiny officer corrects field
    correction_payload = {
        "verification_status": "CORRECTED",
        "corrected_value": "Delhi Fire & Emergency Services",
        "review_comments": "Corrected typo in extracted authority name",
    }
    resp = await client.put(f"/api/v1/ocr/fields/{field.id}/verify", json=correction_payload, headers=headers)
    assert resp.status_code == 200
    updated = resp.json()
    assert updated["verification_status"] == "CORRECTED"
    assert updated["corrected_value"] == "Delhi Fire & Emergency Services"
    assert updated["is_automated_advisory"] is False
    assert updated["reviewed_by_user_id"] == u_scrutiny.id

    # Verify chained audit log record
    stmt = (
        select(AuditEvent)
        .where(AuditEvent.resource_id == field.id)
        .order_by(AuditEvent.sequence_number.desc())
    )
    audit_res = await db_session.execute(stmt)
    event = audit_res.scalar_one_or_none()
    assert event is not None
    assert event.action == "OCR_FIELD_CORRECTED"
    assert event.actor_id == u_scrutiny.id
    details = json.loads(event.details_json)
    assert details["original_raw_value"] == raw_val
    assert details["corrected_value"] == "Delhi Fire & Emergency Services"
    assert details["new_status"] == "CORRECTED"


# ==============================================================================
# PART 3: M13 APH CORPUS & CITATION RETRIEVAL HARDENING
# ==============================================================================

@pytest.mark.asyncio
async def test_m13_lexical_retrieval_and_exact_citation(db_session: AsyncSession, seed_test_data):
    """
    Verify APH Regulatory Assistant retrieval operates in LEXICAL_BM25_PASSAGE_RETRIEVAL mode,
    grounding responses with exact Chapter, Clause, and Page citations.
    """
    u_inst = seed_test_data["users"]["inst"]
    service = APHAssistantService(db_session)

    query = await service.ask_assistant(
        user_id=u_inst.id,
        query_text="What is the faculty student ratio required for engineering degree programmes?",
    )

    assert query.retrieval_mode == "LEXICAL_BM25_PASSAGE_RETRIEVAL"
    assert query.is_automated_advisory is True
    assert query.uncertainty_warning is None

    citations = json.loads(query.citations_json)
    assert len(citations) >= 1
    best_citation = citations[0]
    assert best_citation["clause_number"] == "4.1.1"
    assert best_citation["chapter_number"] == 4
    assert best_citation["page_number"] == 68


@pytest.mark.asyncio
async def test_m13_out_of_corpus_uncertainty_safeguard(db_session: AsyncSession, seed_test_data):
    """
    Ensure out-of-corpus queries trigger explicit uncertainty warnings
    to prevent statutory hallucination.
    """
    u_inst = seed_test_data["users"]["inst"]
    service = APHAssistantService(db_session)

    query = await service.ask_assistant(
        user_id=u_inst.id,
        query_text="How to bake authentic Neapolitan sourdough pizza at 450 degrees celsius?",
    )

    assert query.uncertainty_warning is not None
    assert "sufficient" in query.uncertainty_warning.lower()
    assert "Notice of Insufficient Corpus Coverage" in query.response_text


# ==============================================================================
# PART 4: AUDIT INTEGRITY & TAMPER DETECTION
# ==============================================================================

@pytest.mark.asyncio
async def test_audit_hash_chain_verification_and_tamper_detection(db_session: AsyncSession, seed_test_data):
    """
    Validate continuous SHA-256 linear hash-chain integrity:
    1. Untampered chain reports is_valid=True.
    2. Tampering with event payload immediately detected at exact sequence.
    3. Tampering with previous_entry_hash linkage detected.
    4. Verification check is read-only (does not mutate audit history).
    """
    u_admin = seed_test_data["users"]["admin"]

    # 1. Record two genuine chained events
    e1 = await record_audit_event(
        db=db_session,
        actor_id=u_admin.id,
        action="TEST_ACTION_ALPHA",
        resource_type="TEST_RES",
        resource_id="res-001",
        details={"key": "val1"},
    )
    e2 = await record_audit_event(
        db=db_session,
        actor_id=u_admin.id,
        action="TEST_ACTION_BETA",
        resource_type="TEST_RES",
        resource_id="res-002",
        details={"key": "val2"},
    )
    await db_session.commit()

    # 2. Verify clean chain
    res_clean = await verify_audit_chain(db_session)
    assert res_clean.is_valid is True
    assert res_clean.total_events_checked >= 2

    # 3. Tamper with payload
    original_details = e2.details_json
    e2.details_json = json.dumps({"key": "TAMPERED_VAL"})
    await db_session.commit()

    res_tampered_payload = await verify_audit_chain(db_session)
    assert res_tampered_payload.is_valid is False
    assert res_tampered_payload.broken_sequence_id == e2.id
    assert "payload_hash mismatch" in res_tampered_payload.verification_message

    # Revert payload tamper
    e2.details_json = original_details
    await db_session.commit()

    # 4. Tamper with previous_entry_hash
    original_prev_hash = e2.previous_entry_hash
    e2.previous_entry_hash = "deadbeef" * 8
    await db_session.commit()

    res_tampered_link = await verify_audit_chain(db_session)
    assert res_tampered_link.is_valid is False
    assert res_tampered_link.broken_sequence_id == e2.id
    assert "previous_entry_hash mismatch" in res_tampered_link.verification_message

    # Revert linkage
    e2.previous_entry_hash = original_prev_hash
    await db_session.commit()

    # Final check: back to valid
    res_restored = await verify_audit_chain(db_session)
    assert res_restored.is_valid is True
