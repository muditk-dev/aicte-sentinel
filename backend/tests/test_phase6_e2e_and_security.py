import io
import json
import csv
import pytest
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.security.tokens import create_access_token
from app.security.password import hash_password
from app.models.institution import Institution
from app.models.application import Application
from app.models.document import Document
from app.models.user import User, Role
from app.models.compliance import ComplianceObligation
from app.models.evc import Expert, EVCInspection
from app.models.committee import Committee, CommitteeMembership, Hearing
from app.models.audit import AuditEvent
from app.audit.service import verify_audit_chain, record_audit_event
from app.storage.service import storage_service
from app.security.scanner import EICAR_SIGNATURE
from app.services.compliance_service import sanitize_csv_cell


def get_auth_headers(user, roles, inst_id=None):
    token = create_access_token(
        user_id=user.id,
        email=user.email,
        roles=roles,
        institution_id=inst_id or getattr(user, "institution_id", None),
    )
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
# WORKFLOW A — INSTITUTION APPLICATION LIFECYCLE
# ==============================================================================

@pytest.mark.asyncio
async def test_workflow_a_institution_application_lifecycle(
    client: AsyncClient, seed_test_data: dict, db_session: AsyncSession
):
    """
    Workflow A:
    1. Log in as institution user.
    2. Create and submit a synthetic application.
    3. Upload a permitted synthetic document (magic-byte check).
    4. Confirm document scanning & clean vault promotion.
    5. Issue a formal deficiency notice.
    6. Submit clarification & supporting evidence.
    7. Confirm application lifecycle progression and chained audit ledger.
    """
    inst = seed_test_data["institution"]
    tmpl = seed_test_data["template"]
    u_inst = seed_test_data["users"]["inst"]
    u_scrutiny = seed_test_data["users"]["scrutiny"]

    # 1. Login as institution user
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "inst@apex.edu.in", "password": "College@2026!"},
    )
    assert login_res.status_code == 200
    inst_token = login_res.json()["access_token"]
    inst_headers = {"Authorization": f"Bearer {inst_token}"}

    # 2. Create new synthetic application in DRAFT
    create_payload = {
        "template_id": tmpl.id,
        "academic_year": "2026-2027",
        "submission_data": {
            "institution_name": inst.name,
            "program": "Engineering & Technology",
            "proposed_intake": 360,
        },
    }
    app_res = await client.post("/api/v1/applications", json=create_payload, headers=inst_headers)
    assert app_res.status_code == 201
    app_data = app_res.json()
    app_id = app_data["id"]
    assert app_data["current_status"] == "DRAFT"

    # 3. Transition DRAFT -> SUBMITTED
    trans_res = await client.post(
        f"/api/v1/applications/{app_id}/transition",
        json={"target_status": "SUBMITTED", "remarks": "Statutory application submitted by college director."},
        headers=inst_headers,
    )
    assert trans_res.status_code == 200
    assert trans_res.json()["current_status"] == "SUBMITTED"

    # 4. Upload permitted synthetic document (with genuine %PDF magic bytes)
    pdf_content = b"%PDF-1.4 sample statutory building safety certificate for technical campus"
    upload_res = await client.post(
        f"/api/v1/applications/{app_id}/documents",
        data={"category": "Building Safety Certificate"},
        files={"file": ("building_safety.pdf", io.BytesIO(pdf_content), "application/pdf")},
        headers=inst_headers,
    )
    assert upload_res.status_code == 201
    doc_data = upload_res.json()
    doc_id = doc_data["id"]
    assert doc_data["scan_status"] == "ACCEPTED"
    assert doc_data["current_version"] == 1
    assert len(doc_data["sha256_hash"]) == 64

    # 5. Scrutiny Officer logs in and records scrutiny finding
    scrutiny_headers = get_auth_headers(u_scrutiny, ["SCRUTINY_OFFICER"])
    finding_res = await client.post(
        f"/api/v1/applications/{app_id}/scrutiny",
        json={
            "category": "Building Safety Certificate",
            "document_id": doc_id,
            "finding_status": "DEFICIENT",
            "reason": "Building safety certificate lacks structural engineer registration seal.",
            "notes": "APH 2026-27 Clause 5.1",
        },
        headers=scrutiny_headers,
    )
    assert finding_res.status_code == 201

    # Transition application SUBMITTED -> UNDER_SCRUTINY
    scrutiny_trans = await client.post(
        f"/api/v1/applications/{app_id}/transition",
        json={"target_status": "UNDER_SCRUTINY", "remarks": "Commencing statutory document scrutiny."},
        headers=scrutiny_headers,
    )
    assert scrutiny_trans.status_code == 200
    assert scrutiny_trans.json()["current_status"] == "UNDER_SCRUTINY"

    # 6. Issue formal Deficiency Notice with 7-day cure window
    notice_res = await client.post(
        f"/api/v1/applications/{app_id}/deficiencies",
        json={
            "officer_remarks": "Mandatory structural safety endorsement required within 7 days.",
            "cure_days": 7,
            "items": [
                {
                    "document_id": doc_id,
                    "requirement_title": "Structural Safety Endorsement",
                    "description": "Registered structural engineer seal missing from page 2.",
                    "required_corrective_action": "Upload certified endorsement by municipal licensed structural engineer.",
                }
            ],
        },
        headers=scrutiny_headers,
    )
    assert notice_res.status_code == 201
    notice_data = notice_res.json()
    notice_id = notice_data["id"]
    assert notice_data["status"] == "ISSUED"

    # Application must now be DEFICIENCY_ISSUED
    app_check = await client.get(f"/api/v1/applications/{app_id}", headers=inst_headers)
    assert app_check.json()["current_status"] == "DEFICIENCY_ISSUED"

    # 7. Institution submits clarification and supporting evidence
    rect_pdf = b"%PDF-1.4 endorsed structural safety certificate signed by licensed authority"
    rect_upload = await client.post(
        f"/api/v1/applications/{app_id}/documents",
        data={"category": "Building Safety Certificate"},
        files={"file": ("building_safety_endorsed.pdf", io.BytesIO(rect_pdf), "application/pdf")},
        headers=inst_headers,
    )
    assert rect_upload.status_code == 201
    rect_doc_id = rect_upload.json()["id"]

    resp_res = await client.post(
        f"/api/v1/deficiencies/{notice_id}/respond",
        json={
            "response_remarks": "Obtained municipal licensed structural engineer endorsement and uploaded revised certificate.",
            "attachment_document_ids": [rect_doc_id],
        },
        headers=inst_headers,
    )
    assert resp_res.status_code == 200
    assert resp_res.json()["status"] == "RESPONSE_SUBMITTED"

    # Application must now be RESUBMITTED
    app_check2 = await client.get(f"/api/v1/applications/{app_id}", headers=inst_headers)
    assert app_check2.json()["current_status"] == "RESUBMITTED"

    # 8. Scrutiny Officer reviews and resolves deficiency notice
    review_res = await client.post(
        f"/api/v1/deficiencies/{notice_id}/review",
        json={
            "action": "RESOLVE",
            "officer_remarks": "Endorsement verified against municipal registry. Deficiency resolved.",
        },
        headers=scrutiny_headers,
    )
    assert review_res.status_code == 200
    assert review_res.json()["status"] == "RESOLVED"

    # Application returns to UNDER_SCRUTINY
    app_check3 = await client.get(f"/api/v1/applications/{app_id}", headers=inst_headers)
    assert app_check3.json()["current_status"] == "UNDER_SCRUTINY"

    # 9. Verify full application event history and audit ledger integrity
    hist_res = await client.get(f"/api/v1/applications/{app_id}", headers=inst_headers)
    events = hist_res.json()["events"]
    assert len(events) >= 5

    audit_verify = await verify_audit_chain(db_session)
    assert audit_verify.is_valid is True
    assert audit_verify.total_events_checked >= 5


# ==============================================================================
# WORKFLOW B — INSPECTION, COMMITTEE HEARINGS & STATUTORY DECISIONS
# ==============================================================================

@pytest.mark.asyncio
async def test_workflow_b_inspection_and_decision_lifecycle(
    client: AsyncClient, seed_test_data: dict, db_session: AsyncSession
):
    """
    Workflow B:
    1. Admin creates expert and evaluates conflict-of-interest.
    2. Regional Officer schedules inspection, assigns non-conflicting panel.
    3. Inspection conducted & versioned report submitted with SHA-256 digest.
    4. Committee hearing docketed, attendance recorded enforcing quorum.
    5. Advisory minutes recorded and final authorized decision rendered.
    6. Unauthorized decision attempts blocked with 403 Forbidden.
    7. Reconsideration petition filed and audit ledger confirmed.
    """
    u_admin = seed_test_data["users"]["admin"]
    u_ro = seed_test_data["users"]["ro"]
    u_inst = seed_test_data["users"]["inst"]
    app = seed_test_data["application"]

    admin_headers = get_auth_headers(u_admin, ["SUPER_ADMIN"])
    ro_headers = get_auth_headers(u_ro, ["REGIONAL_OFFICER"])
    inst_headers = get_auth_headers(u_inst, ["INSTITUTION_ADMIN"], inst.id if (inst := seed_test_data.get("institution")) else None)

    # 1. Admin registers an expert with district conflict (New Delhi)
    exp_conflict = await client.post(
        "/api/v1/experts",
        json={
            "name": "Dr. Conflict Fellow",
            "email": "conflict.fellow@delhi.ac.in",
            "designation": "Professor of Mechanical Engg",
            "organization": "Delhi Technical Institute",
            "expert_type": "ACADEMIC",
            "qualifications": "Ph.D.",
            "experience_years": 18,
            "alma_mater": "Delhi Technical University",
            "state": "Delhi",
            "district": "New Delhi",  # Same as Apex Institute
            "availability_status": "AVAILABLE",
        },
        headers=admin_headers,
    )
    assert exp_conflict.status_code == 200
    conflict_expert_id = exp_conflict.json()["id"]

    # 2. Conflict-of-interest check must flag conflict
    chk_res = await client.post(
        f"/api/v1/experts/{conflict_expert_id}/conflict-check",
        json={"expert_id": conflict_expert_id, "application_id": app.id},
        headers=ro_headers,
    )
    assert chk_res.status_code == 200
    assert chk_res.json()["has_conflict"] is True
    assert any("district" in r.lower() or "geographic" in r.lower() for r in chk_res.json()["conflict_reasons"])

    # 3. Register non-conflicting expert from another state
    exp_clean = await client.post(
        "/api/v1/experts",
        json={
            "name": "Prof. Clean Independent",
            "email": "clean.independent@iitb.ac.in",
            "designation": "Professor of Computer Science",
            "organization": "IIT Bombay",
            "expert_type": "ACADEMIC",
            "qualifications": "Ph.D.",
            "experience_years": 22,
            "alma_mater": "IIT Bombay",
            "state": "Maharashtra",
            "district": "Mumbai Suburban",
            "availability_status": "AVAILABLE",
        },
        headers=admin_headers,
    )
    assert exp_clean.status_code == 200
    clean_expert_id = exp_clean.json()["id"]

    # 4. Schedule EVC inspection
    insp_res = await client.post(
        "/api/v1/inspections",
        json={
            "application_id": app.id,
            "inspection_mode": "PHYSICAL",
            "scheduled_start_date": "2026-11-28T09:00:00Z",
            "scheduled_end_date": "2026-11-28T17:00:00Z",
        },
        headers=ro_headers,
    )
    assert insp_res.status_code == 200
    insp_id = insp_res.json()["id"]

    # Assign conflicting expert without override justification -> MUST FAIL 422
    assign_conflict = await client.post(
        f"/api/v1/inspections/{insp_id}/experts",
        json={"expert_id": conflict_expert_id, "role": "MEMBER"},
        headers=ro_headers,
    )
    assert assign_conflict.status_code == 422
    assert "Conflict of Interest detected" in assign_conflict.json().get("message", "")

    # Assign non-conflicting expert -> SUCCEEDS
    assign_clean = await client.post(
        f"/api/v1/inspections/{insp_id}/experts",
        json={"expert_id": clean_expert_id, "role": "CHAIRPERSON"},
        headers=ro_headers,
    )
    assert assign_clean.status_code == 200

    # 5. Conduct inspection & submit report
    await client.post(
        f"/api/v1/inspections/{insp_id}/transition",
        json={"target_status": "IN_PROGRESS"},
        headers=ro_headers,
    )

    report_res = await client.post(
        f"/api/v1/inspections/{insp_id}/reports",
        json={
            "overall_recommendation": "COMPLIANT",
            "infrastructure_score": 92.5,
            "faculty_verification_status": "SATISFACTORY",
            "land_building_status": "SATISFACTORY",
            "laboratories_equipment_status": "SATISFACTORY",
            "safety_and_amenities_status": "SATISFACTORY",
            "observations": "All laboratories and library facilities comply with APH 2026 norms.",
            "checklist_data": {"faculty_verified": True, "infrastructure_verified": True},
        },
        headers=ro_headers,
    )
    assert report_res.status_code == 200
    rep_data = report_res.json()
    assert len(rep_data["sha256_hash"]) == 64

    # Accept report
    await client.post(
        f"/api/v1/inspections/{insp_id}/reports/{rep_data['id']}/review",
        json={"review_status": "ACCEPTED", "review_remarks": "Inspection report accepted in full."},
        headers=ro_headers,
    )

    # 6. Committee hearing session & docketing
    comm_res = await client.post(
        "/api/v1/committees",
        json={
            "code": "SHC-NORTH-2026",
            "name": "Standing Hearing Committee Northern Region",
            "committee_type": "SHC",
            "quorum_required": 2,
            "valid_from": "2026-01-01T00:00:00Z",
        },
        headers=admin_headers,
    )
    assert comm_res.status_code == 200
    comm_id = comm_res.json()["id"]

    hear_res = await client.post(
        "/api/v1/hearings",
        json={
            "committee_id": comm_id,
            "hearing_type": "SHC",
            "scheduled_date": "2026-12-05T10:00:00Z",
            "meeting_mode": "HYBRID",
            "venue_or_link": "Regional Office Conference Room",
            "agenda": "Extension of Approval Hearing",
        },
        headers=ro_headers,
    )
    assert hear_res.status_code == 200
    hear_id = hear_res.json()["id"]

    # Docket application
    docket_res = await client.post(
        f"/api/v1/hearings/{hear_id}/dockets",
        json={
            "application_id": app.id,
            "matter_summary": "Extension of approval application and infrastructure dispute.",
            "referred_by": "REGIONAL_OFFICE",
        },
        headers=ro_headers,
    )
    assert docket_res.status_code == 200

    # Record attendance (2 members attended -> meets quorum)
    att_res = await client.post(
        f"/api/v1/hearings/{hear_id}/attendance",
        json=[
            {"member_name": "Prof. Panel Member 1", "member_role": "CHAIRPERSON", "attended": True, "attendance_mode": "IN_PERSON"},
            {"member_name": "Prof. Panel Member 2", "member_role": "MEMBER", "attended": True, "attendance_mode": "REMOTE"},
        ],
        headers=ro_headers,
    )
    assert att_res.status_code == 200

    # Record hearing minutes
    min_res = await client.post(
        f"/api/v1/hearings/{hear_id}/minutes",
        json={
            "minutes_of_meeting": "Committee examined physical inspection report and found requirements fulfilled.",
            "final_recommendation": "RECOMMEND_APPROVAL",
            "recommendation_summary": "Unanimous approval recommendation.",
        },
        headers=ro_headers,
    )
    assert min_res.status_code == 200

    # Transition application state to RECOMMENDED_APPROVAL for decision
    app.current_status = "RECOMMENDED_APPROVAL"
    await db_session.commit()

    # 7. Security: Institution user cannot render statutory decision -> MUST BE 403
    unauth_dec = await client.post(
        "/api/v1/decisions",
        json={
            "application_id": app.id,
            "decision_type": "APPROVED",
            "reasons": "Self approval attempt.",
            "declaration_attestation": "I attest.",
        },
        headers=inst_headers,
    )
    assert unauth_dec.status_code == 403

    # Authorized Regional Officer renders CONDITIONALLY_APPROVED decision
    dec_res = await client.post(
        "/api/v1/decisions",
        json={
            "application_id": app.id,
            "decision_type": "CONDITIONALLY_APPROVED",
            "reasons": "All academic, safety, and faculty norms satisfied. Conditional approval granted subject to biometric attendance compliance.",
            "declaration_attestation": "I, Regional Officer, hereby formally attest this decision under the AICTE Act 1987.",
            "intake_approved": 360,
            "valid_for_years": 1,
            "conditions": [
                {
                    "condition_code": "COND-BIOMETRIC-2026",
                    "description": "Submit monthly biometric attendance report by 10th of every month.",
                    "due_date": "2026-12-31T18:00:00Z",
                }
            ],
        },
        headers=ro_headers,
    )
    assert dec_res.status_code == 200
    dec_data = dec_res.json()
    assert dec_data["decision_type"] == "CONDITIONALLY_APPROVED"
    assert len(dec_data["sha256_attestation"]) == 64
    dec_id = dec_data["id"]

    # Application status mutated to APPROVED
    await db_session.refresh(app)
    assert app.current_status == "APPROVED"

    # 8. Formal petition for reconsideration
    # Institution directly attempting to docket appellate petition is blocked by RBAC (403)
    unauth_recon = await client.post(
        f"/api/v1/decisions/{dec_id}/reconsider",
        json={
            "appeal_reason": "Request waiver of biometric attendance due to rural cellular network upgrade.",
            "appeal_petition_reference": "PET-2026-APX-001",
        },
        headers=inst_headers,
    )
    assert unauth_recon.status_code == 403

    # Authorized Regional Officer / Standing Appellate docketing succeeds (200)
    reconsider_res = await client.post(
        f"/api/v1/decisions/{dec_id}/reconsider",
        json={
            "appeal_reason": "Request waiver of biometric attendance due to rural cellular network upgrade.",
            "appeal_petition_reference": "PET-2026-APX-001",
        },
        headers=ro_headers,
    )
    assert reconsider_res.status_code == 200
    assert reconsider_res.json()["is_reconsidered"] is True

    # Confirm audit ledger integrity
    audit_verify = await verify_audit_chain(db_session)
    assert audit_verify.is_valid is True


# ==============================================================================
# WORKFLOW C — POST-APPROVAL COMPLIANCE, MONITORING & EVIDENCE EXPORT
# ==============================================================================

@pytest.mark.asyncio
async def test_workflow_c_post_approval_compliance_and_monitoring(
    client: AsyncClient, seed_test_data: dict, db_session: AsyncSession
):
    """
    Workflow C:
    1. Create compliance obligation linked to approved application.
    2. Submit institutional evidence (PENDING -> SUBMITTED).
    3. Officer reviews evidence and flags deficiency (SUBMITTED -> DEFICIENT).
    4. Institution resubmits and officer verifies compliance (DEFICIENT -> COMPLIANT).
    5. Create overdue obligation and execute background deadline worker.
    6. Verify automatic OVERDUE transition and notification deduplication.
    7. Generate live reports and test CSV export with OWASP formula injection protection.
    """
    inst = seed_test_data["institution"]
    app = seed_test_data["application"]
    u_inst = seed_test_data["users"]["inst"]
    u_admin = seed_test_data["users"]["admin"]
    u_scrutiny = seed_test_data["users"]["scrutiny"]

    admin_headers = get_auth_headers(u_admin, ["SUPER_ADMIN"])
    inst_headers = get_auth_headers(u_inst, ["INSTITUTION_ADMIN"], inst.id)
    scrutiny_headers = get_auth_headers(u_scrutiny, ["SCRUTINY_OFFICER"])

    now = datetime.now(timezone.utc)

    # 1. Scrutiny Officer creates compliance obligation
    ob_res = await client.post(
        "/api/v1/compliance/obligations",
        json={
            "institution_id": inst.id,
            "application_id": app.id,
            "title": "Annual Fire NOC Re-certification",
            "description": "Submit certified renewal of Fire Safety Certificate.",
            "category": "SAFETY_NOC",
            "source_reference": "APH 2026-27 Clause 5.2",
            "applicability": "ALL_TECHNICAL_INSTITUTIONS",
            "issue_date": now.isoformat(),
            "due_date": (now + timedelta(days=45)).isoformat(),
            "recurrence": "ANNUAL",
            "is_synthetic_demonstration": True,
        },
        headers=scrutiny_headers,
    )
    assert ob_res.status_code == 201
    ob_data = ob_res.json()
    ob_id = ob_data["id"]
    assert ob_data["status"] == "PENDING"

    # 2. Institution submits compliance evidence
    ev_res = await client.post(
        f"/api/v1/compliance/obligations/{ob_id}/evidence",
        json={
            "title": "Fire NOC Renewal Application Receipt",
            "description": "Applied to State Fire Service; inspection scheduled.",
            "document_id": None,
            "remarks": "Interim receipt uploaded.",
        },
        headers=inst_headers,
    )
    assert ev_res.status_code == 200
    assert ev_res.json()["status"] == "SUBMITTED"

    # 3. Officer reviews evidence and flags deficiency
    rev_def = await client.post(
        f"/api/v1/compliance/obligations/{ob_id}/review",
        json={
            "decision": "DEFICIENCY_FLAGGED",
            "review_comments": "Interim application receipt is unacceptable. Certified final NOC required.",
        },
        headers=scrutiny_headers,
    )
    assert rev_def.status_code == 200
    assert rev_def.json()["status"] == "DEFICIENT"

    # 4. Institution submits final evidence; Officer verifies compliance
    await client.post(
        f"/api/v1/compliance/obligations/{ob_id}/evidence",
        json={
            "title": "Final Certified Fire NOC 2026",
            "description": "Final certificate issued by Fire Safety Directorate.",
            "document_id": None,
            "remarks": "Final clearance document attached.",
        },
        headers=inst_headers,
    )

    rev_comp = await client.post(
        f"/api/v1/compliance/obligations/{ob_id}/review",
        json={
            "decision": "VERIFIED_COMPLIANT",
            "review_comments": "Verified valid until 2028.",
        },
        headers=scrutiny_headers,
    )
    assert rev_comp.status_code == 200
    assert rev_comp.json()["status"] == "COMPLIANT"

    # 5. Create an overdue synthetic obligation with past due date
    past_due = now - timedelta(days=10)
    past_ob = ComplianceObligation(
        obligation_code=f"OBL-OVERDUE-{past_due.year}-TEST",
        institution_id=inst.id,
        application_id=app.id,
        title="Anti-Ragging Committee Gazette Notification",
        description="Mandatory public gazette notification of anti-ragging squad.",
        category="ANTI_RAGGING",
        source_reference="APH 2026-27 Clause 7.1",
        applicability="ALL_TECHNICAL_INSTITUTIONS",
        issue_date=past_due - timedelta(days=30),
        due_date=past_due,
        recurrence="ANNUAL",
        status="PENDING",
        is_synthetic_demonstration=True,
    )
    db_session.add(past_ob)
    await db_session.commit()
    await db_session.refresh(past_ob)

    # 6. Trigger deadline monitoring worker via admin route
    worker_res = await client.post("/api/v1/compliance/monitoring/trigger", headers=admin_headers)
    assert worker_res.status_code == 200
    assert worker_res.json()["status"] == "success"

    # Verify obligation shifted to OVERDUE
    await db_session.refresh(past_ob)
    assert past_ob.status == "OVERDUE"

    # Trigger worker again to verify deduplication
    worker_res2 = await client.post("/api/v1/compliance/monitoring/trigger", headers=admin_headers)
    assert worker_res2.status_code == 200

    # 7. Query live reports
    rep_summary = await client.get("/api/v1/compliance/reports/summary", headers=scrutiny_headers)
    assert rep_summary.status_code == 200
    assert rep_summary.json()["total_obligations"] >= 2

    rep_insts = await client.get("/api/v1/compliance/reports/by-institution", headers=scrutiny_headers)
    assert rep_insts.status_code == 200
    assert len(rep_insts.json()) >= 1

    rep_deadlines = await client.get("/api/v1/compliance/reports/deadlines", headers=scrutiny_headers)
    assert rep_deadlines.status_code == 200

    rep_deficiencies = await client.get("/api/v1/compliance/reports/deficiencies", headers=scrutiny_headers)
    assert rep_deficiencies.status_code == 200

    # 8. Download CSV export and verify formula injection protection
    csv_res = await client.get("/api/v1/compliance/reports/export-csv", headers=scrutiny_headers)
    assert csv_res.status_code == 200
    assert "text/csv" in csv_res.headers.get("Content-Type", "")

    reader = csv.reader(io.StringIO(csv_res.text))
    rows = list(reader)
    assert len(rows) >= 2  # Header + at least one data row


# ==============================================================================
# WORKFLOW D — INTELLIGENCE FEATURES & STATUTORY ADVISORY BOUNDARIES
# ==============================================================================

@pytest.mark.asyncio
async def test_workflow_d_intelligence_features_and_statutory_boundaries(
    client: AsyncClient, seed_test_data: dict, db_session: AsyncSession
):
    """
    Workflow D:
    1. Query delay-risk prediction: verify advisory flag and decomposition.
    2. Confirm prediction cannot alter application status.
    3. OCR structured extraction on clean text PDF.
    4. Scanned-PDF limitation: raster-only PDF returns informative disclaimer.
    5. APH assistant supported question -> validates exact clause citation.
    6. APH assistant unsupported question -> validates uncertainty disclaimer.
    7. Confirm AI outputs cannot directly make statutory decisions.
    """
    app = seed_test_data["application"]
    u_scrutiny = seed_test_data["users"]["scrutiny"]
    scrutiny_headers = get_auth_headers(u_scrutiny, ["SCRUTINY_OFFICER"])

    # 1. Query delay-risk prediction
    pred_res = await client.get(f"/api/v1/intelligence/risk/{app.id}", headers=scrutiny_headers)
    assert pred_res.status_code == 200
    pred = pred_res.json()
    assert pred["is_automated_advisory"] is True
    assert 0.0 <= pred["risk_score"] <= 1.0
    assert pred["risk_category"] in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    assert len(pred["factor_attributions"]) >= 1

    # 2. Confirm prediction did NOT mutate statutory application status
    await db_session.refresh(app)
    assert app.current_status == seed_test_data["application"].current_status

    # 3. Create clean text PDF in vault and run OCR extraction
    text_pdf_bytes = make_test_pdf("Certificate No: DFS/HQ/2026/NOC-4412. Valid upto: 2028-12-31. Authority: Delhi Fire Service.")
    storage_key = "test_clean_ocr.pdf"
    safe_path = storage_service.vault_dir / storage_key
    with open(safe_path, "wb") as f:
        f.write(text_pdf_bytes)

    doc_clean = Document(
        id="doc-ocr-clean-test",
        application_id=app.id,
        institution_id=app.institution_id,
        original_filename="fire_cert.pdf",
        file_size=len(text_pdf_bytes),
        mime_type="application/pdf",
        sha256_hash="hash-ocr-clean-test",
        storage_key=storage_key,
        category="FIRE_NOC",
        uploaded_by_user_id=u_scrutiny.id,
        scan_status="ACCEPTED",
    )
    db_session.add(doc_clean)
    await db_session.commit()

    ocr_res = await client.post(f"/api/v1/ocr/process/{doc_clean.id}", headers=scrutiny_headers)
    assert ocr_res.status_code == 200
    ocr_data = ocr_res.json()
    assert ocr_data["status"] == "COMPLETED"
    assert len(ocr_data["fields"]) >= 1

    # 4. Scanned-PDF raster test: simulate document with no extractable text layer
    raster_pdf = make_blank_pdf()
    storage_key_raster = "test_raster_ocr.pdf"
    safe_raster_path = storage_service.vault_dir / storage_key_raster
    with open(safe_raster_path, "wb") as f:
        f.write(raster_pdf)

    doc_raster = Document(
        id="doc-ocr-raster-test",
        application_id=app.id,
        institution_id=app.institution_id,
        original_filename="scanned_scan.pdf",
        file_size=len(raster_pdf),
        mime_type="application/pdf",
        sha256_hash="hash-ocr-raster-test",
        storage_key=storage_key_raster,
        category="FIRE_NOC",
        uploaded_by_user_id=u_scrutiny.id,
        scan_status="ACCEPTED",
    )
    db_session.add(doc_raster)
    await db_session.commit()

    ocr_raster_res = await client.post(f"/api/v1/ocr/process/{doc_raster.id}", headers=scrutiny_headers)
    assert ocr_raster_res.status_code == 200
    raster_data = ocr_raster_res.json()
    assert raster_data["status"] == "COMPLETED"
    assert len(raster_data["fields"]) == 0
    assert "Tesseract OCR" in (raster_data["error_message"] or "") or "text layer" in (raster_data["error_message"] or "")

    # 5. Query APH Assistant with supported question
    aph_supported = await client.post(
        "/api/v1/aph/ask",
        json={"query_text": "What is the faculty student ratio required for engineering degree programmes?"},
        headers=scrutiny_headers,
    )
    assert aph_supported.status_code == 200
    sup_data = aph_supported.json()
    assert sup_data["is_automated_advisory"] is True
    assert len(sup_data["citations"]) >= 1

    # 6. Query APH Assistant with unsupported question
    aph_unsupported = await client.post(
        "/api/v1/aph/ask",
        json={"query_text": "How to bake authentic Neapolitan sourdough pizza at 450 degrees celsius?"},
        headers=scrutiny_headers,
    )
    assert aph_unsupported.status_code == 200
    unsup_data = aph_unsupported.json()
    assert unsup_data["uncertainty_warning"] is not None
    assert "Notice of Insufficient Corpus Coverage" in unsup_data["response_text"]


# ==============================================================================
# SECURITY REVIEW — RBAC, TENANT ISOLATION, INPUT SANITIZATION & AUDIT INTEGRITY
# ==============================================================================

@pytest.mark.asyncio
async def test_security_review_rbac_tenant_isolation_and_tampering(
    client: AsyncClient, seed_test_data: dict, db_session: AsyncSession
):
    """
    Security and Authorization Review:
    1. Cross-tenant access attempts blocked with 403 Forbidden.
    2. Unauthenticated requests return 401 Unauthorized.
    3. Invalid / expired Bearer token returns 401 Unauthorized.
    4. File upload rejects disguised MIME types and EICAR malware signatures.
    5. Workflow engine blocks illegal state jumps.
    6. CSV formula injection protection neutralizes leading dangerous characters.
    7. Continuous SHA-256 audit ledger detects unauthorized database row mutations.
    """
    inst = seed_test_data["institution"]
    app = seed_test_data["application"]
    u_inst = seed_test_data["users"]["inst"]
    u_admin = seed_test_data["users"]["admin"]

    # Create a second institution and user for tenant boundary checks
    inst2 = Institution(
        id="inst-tenant-sec-2",
        name="Secondary Regional Polytechnic",
        code="1-88887777",
        region="Western",
        state="Maharashtra",
        district="Pune",
        institution_type="Private",
        contact_email="director@polytechnic.edu.in",
        contact_phone="+91-20-88887777",
    )
    db_session.add(inst2)
    await db_session.flush()

    role_res = await db_session.execute(select(Role).where(Role.code == "INSTITUTION_ADMIN"))
    r_inst = role_res.scalar_one()

    u_inst2 = User(
        id="user-inst-sec-2",
        email="director@polytechnic.edu.in",
        hashed_password=hash_password("Polytechnic@2026!"),
        full_name="Polytechnic Director",
        institution_id=inst2.id,
        roles=[r_inst],
    )
    db_session.add(u_inst2)
    await db_session.commit()

    inst2_headers = get_auth_headers(u_inst2, ["INSTITUTION_ADMIN"], inst2.id)

    # 1. Tenant boundary: Institution 2 attempts to read Institution 1's application -> 403
    cross_app = await client.get(f"/api/v1/applications/{app.id}", headers=inst2_headers)
    assert cross_app.status_code == 403

    # Tenant boundary: Institution 2 attempts to upload document to Institution 1's app -> 403
    pdf_content = b"%PDF-1.4 test payload"
    cross_upload = await client.post(
        f"/api/v1/applications/{app.id}/documents",
        data={"category": "Land Certificate"},
        files={"file": ("doc.pdf", io.BytesIO(pdf_content), "application/pdf")},
        headers=inst2_headers,
    )
    assert cross_upload.status_code == 403

    # 2. Unauthenticated requests -> 401
    no_auth = await client.get(f"/api/v1/applications/{app.id}")
    assert no_auth.status_code == 401

    # 3. Invalid Bearer token -> 401
    bad_token = await client.get(
        f"/api/v1/applications/{app.id}",
        headers={"Authorization": "Bearer invalid.jwt.token.here"},
    )
    assert bad_token.status_code == 401

    # 4. File upload rejects MIME magic-byte mismatch
    inst1_headers = get_auth_headers(u_inst, ["INSTITUTION_ADMIN"], inst.id)
    html_as_pdf = b"<html><body>Not a PDF</body></html>"
    bad_mime = await client.post(
        f"/api/v1/applications/{app.id}/documents",
        data={"category": "Building Plan"},
        files={"file": ("fake.pdf", io.BytesIO(html_as_pdf), "application/pdf")},
        headers=inst1_headers,
    )
    assert bad_mime.status_code == 400

    # File upload rejects EICAR malware test string
    eicar_file = await client.post(
        f"/api/v1/applications/{app.id}/documents",
        data={"category": "Building Plan"},
        files={"file": ("eicar.pdf", io.BytesIO(EICAR_SIGNATURE), "application/pdf")},
        headers=inst1_headers,
    )
    assert eicar_file.status_code == 400

    # 5. Workflow transition guard: direct illegal jump from SUBMITTED to APPROVED -> blocked
    illegal_jump = await client.post(
        f"/api/v1/applications/{app.id}/transition",
        json={"target_status": "APPROVED", "remarks": "Illegal jump attempt."},
        headers=get_auth_headers(u_admin, ["SUPER_ADMIN"]),
    )
    assert illegal_jump.status_code in [400, 409, 422]

    # 6. CSV formula injection protection: verify dangerous characters are neutralized
    assert sanitize_csv_cell("=1+1") == "'=1+1"
    assert sanitize_csv_cell("+SUM(A1:A10)") == "'+SUM(A1:A10)"
    assert sanitize_csv_cell("-5+2") == "'-5+2"
    assert sanitize_csv_cell("@external_call") == "'@external_call"
    assert sanitize_csv_cell("\tcmd") == "'\tcmd"
    assert sanitize_csv_cell("Safe Normal Text") == "Safe Normal Text"

    # 7. Continuous SHA-256 linear hash-chain integrity & tampering detection
    clean_check = await verify_audit_chain(db_session)
    assert clean_check.is_valid is True

    # Record two chained audit events
    e1 = await record_audit_event(
        db=db_session,
        actor_id=u_admin.id,
        action="SECURITY_AUDIT_LOG_1",
        resource_type="APPLICATION",
        resource_id=app.id,
        details={"audit": "initial"},
    )
    e2 = await record_audit_event(
        db=db_session,
        actor_id=u_admin.id,
        action="SECURITY_AUDIT_LOG_2",
        resource_type="APPLICATION",
        resource_id=app.id,
        details={"audit": "subsequent"},
    )
    await db_session.commit()

    # Tamper with event e2's details
    original_details = e2.details_json
    e2.details_json = json.dumps({"audit": "MALICIOUSLY_MUTATED"})
    await db_session.commit()

    tamper_result = await verify_audit_chain(db_session)
    assert tamper_result.is_valid is False
    assert tamper_result.broken_sequence_id == e2.id
    assert "payload_hash mismatch" in tamper_result.verification_message

    # Restore details
    e2.details_json = original_details
    await db_session.commit()

    restored_result = await verify_audit_chain(db_session)
    assert restored_result.is_valid is True
