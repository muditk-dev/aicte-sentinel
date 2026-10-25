import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.security.tokens import create_access_token
from app.models.document import Document
from app.storage.service import storage_service


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


@pytest.mark.asyncio
async def test_delay_risk_prediction_features_and_attributions(client: AsyncClient, seed_test_data):
    data = seed_test_data
    u_scrutiny = data["users"]["scrutiny"]
    app = data["application"]
    headers = get_auth_headers(u_scrutiny, ["SCRUTINY_OFFICER"])

    # 1. Fetch risk prediction
    response = await client.get(f"/api/v1/intelligence/risk/{app.id}", headers=headers)
    assert response.status_code == 200, response.text
    res_data = response.json()

    assert "risk_score" in res_data
    assert 0.0 <= res_data["risk_score"] <= 1.0
    assert res_data["risk_category"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
    assert res_data["is_automated_advisory"] is True
    assert "factor_attributions" in res_data
    assert len(res_data["factor_attributions"]) > 0

    # Verify SHAP-style attribution structure
    factor = res_data["factor_attributions"][0]
    assert "factor" in factor
    assert "display_name" in factor
    assert "impact" in factor
    assert "weight" in factor
    assert "description" in factor


@pytest.mark.asyncio
async def test_delay_risk_overview_and_recompute(client: AsyncClient, seed_test_data):
    data = seed_test_data
    u_ro = data["users"]["ro"]
    app = data["application"]
    headers = get_auth_headers(u_ro, ["REGIONAL_OFFICER"])

    # Recompute risk
    recompute_resp = await client.post(f"/api/v1/intelligence/risk/{app.id}/recompute", headers=headers)
    assert recompute_resp.status_code == 200
    recomp_data = recompute_resp.json()
    assert recomp_data["is_automated_advisory"] is True

    # Risk overview
    overview_resp = await client.get("/api/v1/intelligence/overview", headers=headers)
    assert overview_resp.status_code == 200
    overview_data = overview_resp.json()
    assert len(overview_data) >= 1
    assert any(item["application_id"] == app.id for item in overview_data)


@pytest.mark.asyncio
async def test_model_versions_transparency(client: AsyncClient, seed_test_data):
    data = seed_test_data
    u_admin = data["users"]["admin"]
    headers = get_auth_headers(u_admin, ["SUPER_ADMIN"])

    resp = await client.get("/api/v1/intelligence/models", headers=headers)
    assert resp.status_code == 200
    models = resp.json()
    assert len(models) >= 1
    model = models[0]
    assert "algorithm" in model
    assert "metrics" in model
    assert "training_dataset_summary" in model
    assert model["is_active"] is True


@pytest.mark.asyncio
async def test_ocr_clean_vault_quarantine_enforcement(client: AsyncClient, db_session: AsyncSession, seed_test_data):
    data = seed_test_data
    u_scrutiny = data["users"]["scrutiny"]
    app = data["application"]
    headers = get_auth_headers(u_scrutiny, ["SCRUTINY_OFFICER"])

    # Create a quarantined document
    quarantined_doc = Document(
        id="doc-quarantine-test",
        application_id=app.id,
        institution_id=app.institution_id,
        original_filename="fire_safety_cert.pdf",
        file_size=1024,
        mime_type="application/pdf",
        sha256_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        storage_key="quarantine/fire_safety_cert.pdf",
        category="FIRE_NOC",
        uploaded_by_user_id=u_scrutiny.id,
        scan_status="QUARANTINED",  # Not accepted!
    )
    db_session.add(quarantined_doc)
    await db_session.commit()

    # Attempt OCR on quarantined doc -> must be rejected
    resp = await client.post(f"/api/v1/ocr/process/{quarantined_doc.id}", headers=headers)
    assert resp.status_code == 400
    error_payload = resp.json()
    assert "DOCUMENT_NOT_CLEAN" in error_payload.get("code", "") or "quarantine" in error_payload.get("message", "").lower()


@pytest.mark.asyncio
async def test_ocr_processing_and_field_verification(client: AsyncClient, db_session: AsyncSession, seed_test_data):
    data = seed_test_data
    u_scrutiny = data["users"]["scrutiny"]
    app = data["application"]
    headers = get_auth_headers(u_scrutiny, ["SCRUTINY_OFFICER"])

    # Create an ACCEPTED clean vault document
    storage_key = "test_fire_noc_clean.pdf"
    sample_pdf_content = make_test_pdf(
        "Issuing Authority: Directorate of Fire Services. Certificate No: NOC-2026-9842. Issued on: 2026-01-15. Valid upto: 2027-12-31."
    )
    # Write to vault
    safe_path = storage_service.vault_dir / storage_key
    with open(safe_path, "wb") as f:
        f.write(sample_pdf_content)

    clean_doc = Document(
        id="doc-clean-vault-test",
        application_id=app.id,
        institution_id=app.institution_id,
        original_filename="fire_noc_clean.pdf",
        file_size=len(sample_pdf_content),
        mime_type="application/pdf",
        sha256_hash="abc123clean",
        storage_key=storage_key,
        category="FIRE_NOC",
        uploaded_by_user_id=u_scrutiny.id,
        scan_status="ACCEPTED",
    )
    db_session.add(clean_doc)
    await db_session.commit()

    # Trigger OCR
    resp = await client.post(f"/api/v1/ocr/process/{clean_doc.id}", headers=headers)
    assert resp.status_code == 200, resp.text
    job_data = resp.json()
    assert job_data["status"] == "COMPLETED"
    assert len(job_data["fields"]) >= 3

    # Check extracted fields
    field_to_verify = job_data["fields"][0]
    assert field_to_verify["verification_status"] == "PENDING"
    assert field_to_verify["is_automated_advisory"] is True

    # Scrutiny Officer verifies field
    v_resp = await client.put(
        f"/api/v1/ocr/fields/{field_to_verify['id']}/verify",
        json={"verification_status": "VERIFIED", "review_comments": "Verified against state fire registry"},
        headers=headers,
    )
    assert v_resp.status_code == 200
    v_data = v_resp.json()
    assert v_data["verification_status"] == "VERIFIED"
    assert v_data["is_automated_advisory"] is False
    assert v_data["reviewed_by_user_id"] == u_scrutiny.id

    # Correct another field
    field_to_correct = job_data["fields"][1]
    c_resp = await client.put(
        f"/api/v1/ocr/fields/{field_to_correct['id']}/verify",
        json={
            "verification_status": "CORRECTED",
            "corrected_value": "Delhi Fire & Emergency Services",
            "review_comments": "Corrected minor spelling omission in raw OCR",
        },
        headers=headers,
    )
    assert c_resp.status_code == 200
    c_data = c_resp.json()
    assert c_data["verification_status"] == "CORRECTED"
    assert c_data["corrected_value"] == "Delhi Fire & Emergency Services"


@pytest.mark.asyncio
async def test_aph_regulatory_assistant_grounded_citations(client: AsyncClient, seed_test_data):
    data = seed_test_data
    u_inst = data["users"]["inst"]
    headers = get_auth_headers(u_inst, ["INSTITUTION_ADMIN"], inst_id=data["institution"].id)

    # 1. Ask about fire safety requirements
    fire_resp = await client.post(
        "/api/v1/aph/ask",
        json={"query_text": "What are the fire safety and sprinkler requirements for buildings above 15 meters?"},
        headers=headers,
    )
    assert fire_resp.status_code == 200, fire_resp.text
    fire_data = fire_resp.json()
    assert fire_data["is_automated_advisory"] is True
    assert len(fire_data["citations"]) > 0
    # Must cite clause 1.7.3 or Chapter 1
    assert any("1.7.3" in c["clause_number"] or "Fire" in c["clause_title"] for c in fire_data["citations"])

    # 2. Ask about land requirements
    land_resp = await client.post(
        "/api/v1/aph/ask",
        json={"query_text": "What is the minimum land requirement in mega and metro cities for engineering colleges?"},
        headers=headers,
    )
    assert land_resp.status_code == 200
    land_data = land_resp.json()
    assert any("1.4.1" in c["clause_number"] or "Land" in c["clause_title"] for c in land_data["citations"])

    # 3. Ask out-of-corpus query -> should trigger uncertainty safeguard
    out_resp = await client.post(
        "/api/v1/aph/ask",
        json={"query_text": "Explain quantum entanglement in astrophysical neutron stars and black holes"},
        headers=headers,
    )
    assert out_resp.status_code == 200
    out_data = out_resp.json()
    assert out_data["uncertainty_warning"] is not None
    assert "sufficient" in out_data["uncertainty_warning"].lower()

    # 4. Submit feedback
    fb_resp = await client.post(
        f"/api/v1/aph/feedback/{fire_data['id']}",
        json={"rating": 1},
        headers=headers,
    )
    assert fb_resp.status_code == 200
    assert fb_resp.json()["feedback_rating"] == 1


@pytest.mark.asyncio
async def test_aph_sources_and_clauses_listing(client: AsyncClient, seed_test_data):
    data = seed_test_data
    u_admin = data["users"]["admin"]
    headers = get_auth_headers(u_admin, ["SUPER_ADMIN"])

    sources_resp = await client.get("/api/v1/aph/sources", headers=headers)
    assert sources_resp.status_code == 200
    sources = sources_resp.json()
    assert len(sources) >= 1
    assert sources[0]["edition"] == "2026-27"
    assert len(sources[0]["sha256_hash"]) == 64

    clauses_resp = await client.get("/api/v1/aph/clauses?category=FACULTY_RATIO", headers=headers)
    assert clauses_resp.status_code == 200
    clauses = clauses_resp.json()
    assert len(clauses) >= 1
    assert clauses[0]["clause_number"] == "4.1.1"
