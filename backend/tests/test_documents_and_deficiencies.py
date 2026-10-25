import pytest
import io
from datetime import datetime, timedelta, timezone
from httpx import AsyncClient
from app.security.scanner import EICAR_SIGNATURE
from app.workers.scheduler import evaluate_deficiency_deadlines
from app.models.deficiency import DeficiencyNotice, Notification
from sqlalchemy import select


@pytest.mark.asyncio
async def test_valid_document_upload_and_metadata(client: AsyncClient, seed_test_data):
    # Log in as institution admin
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "inst@apex.edu.in", "password": "College@2026!"},
    )
    token = login_res.json()["access_token"]
    app_id = seed_test_data["application"].id

    # Valid PDF bytes
    pdf_content = b"%PDF-1.4 sample pdf content for AICTE regulatory scrutiny"
    files = {"file": ("land_deed.pdf", io.BytesIO(pdf_content), "application/pdf")}
    data = {"category": "Land Title & Conversion Certificate"}

    response = await client.post(
        f"/api/v1/applications/{app_id}/documents",
        headers={"Authorization": f"Bearer {token}"},
        data=data,
        files=files,
    )
    assert response.status_code == 201
    doc_data = response.json()
    assert doc_data["category"] == "Land Title & Conversion Certificate"
    assert doc_data["mime_type"] == "application/pdf"
    assert doc_data["current_version"] == 1
    assert doc_data["scan_status"] == "ACCEPTED"
    assert len(doc_data["sha256_hash"]) == 64


@pytest.mark.asyncio
async def test_mime_magic_byte_mismatch_rejected(client: AsyncClient, seed_test_data):
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "inst@apex.edu.in", "password": "College@2026!"},
    )
    token = login_res.json()["access_token"]
    app_id = seed_test_data["application"].id

    # Plain text file disguised as PDF
    fake_content = b"<html>This is an HTML file not a PDF</html>"
    files = {"file": ("malicious.pdf", io.BytesIO(fake_content), "application/pdf")}
    data = {"category": "Building Plan"}

    response = await client.post(
        f"/api/v1/applications/{app_id}/documents",
        headers={"Authorization": f"Bearer {token}"},
        data=data,
        files=files,
    )
    assert response.status_code == 400
    err = response.json()
    assert err["code"] == "FILE_VALIDATION_ERROR"
    assert "signature" in err["message"].lower() or "mismatch" in err["message"].lower()


@pytest.mark.asyncio
async def test_malware_eicar_signature_rejected(client: AsyncClient, seed_test_data):
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "inst@apex.edu.in", "password": "College@2026!"},
    )
    token = login_res.json()["access_token"]
    app_id = seed_test_data["application"].id

    # Valid PDF header containing EICAR test signature
    eicar_pdf = b"%PDF-1.4 " + EICAR_SIGNATURE
    files = {"file": ("infected.pdf", io.BytesIO(eicar_pdf), "application/pdf")}
    data = {"category": "Fire Safety NOC"}

    response = await client.post(
        f"/api/v1/applications/{app_id}/documents",
        headers={"Authorization": f"Bearer {token}"},
        data=data,
        files=files,
    )
    assert response.status_code == 201
    doc_data = response.json()
    assert doc_data["scan_status"] == "REJECTED"
    assert "EICAR" in doc_data["rejection_reason"]


@pytest.mark.asyncio
async def test_quarantined_or_rejected_download_denied(client: AsyncClient, seed_test_data):
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "inst@apex.edu.in", "password": "College@2026!"},
    )
    token = login_res.json()["access_token"]
    app_id = seed_test_data["application"].id

    # Upload infected file that gets REJECTED
    eicar_pdf = b"%PDF-1.4 " + EICAR_SIGNATURE
    files = {"file": ("infected.pdf", io.BytesIO(eicar_pdf), "application/pdf")}
    data = {"category": "Fire Safety NOC"}

    upload_res = await client.post(
        f"/api/v1/applications/{app_id}/documents",
        headers={"Authorization": f"Bearer {token}"},
        data=data,
        files=files,
    )
    doc_id = upload_res.json()["id"]

    # Attempt download of rejected/quarantined doc
    download_res = await client.get(
        f"/api/v1/documents/{doc_id}/download",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert download_res.status_code == 403
    assert "blocked" in download_res.json()["message"].lower()


@pytest.mark.asyncio
async def test_cross_institution_document_access_denied(client: AsyncClient, seed_test_data, db_session):
    from app.models.institution import Institution
    from app.models.user import User, Role
    from app.security.password import hash_password

    # Create second institution and user
    inst2 = Institution(
        id="inst-other-2",
        name="Other Technical College",
        code="1-OTHER99",
        region="Western",
        state="Maharashtra",
        district="Mumbai",
        institution_type="Private",
        contact_email="other@college.edu",
        contact_phone="+91-22-12345678",
    )
    db_session.add(inst2)
    await db_session.flush()

    role_stmt = select(Role).where(Role.code == "INSTITUTION_ADMIN")
    role_inst = (await db_session.execute(role_stmt)).scalar_one()

    u_other = User(
        id="user-other-2",
        email="other@college.edu",
        hashed_password=hash_password("OtherPass123!"),
        full_name="Other Principal",
        institution_id=inst2.id,
        roles=[role_inst],
    )
    db_session.add(u_other)
    await db_session.commit()

    # User 2 logs in
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "other@college.edu", "password": "OtherPass123!"},
    )
    token_other = login_res.json()["access_token"]

    # Tries to access application 1's documents
    app1_id = seed_test_data["application"].id
    res = await client.get(
        f"/api/v1/applications/{app1_id}/documents",
        headers={"Authorization": f"Bearer {token_other}"},
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_scrutiny_finding_recorded_by_officer(client: AsyncClient, seed_test_data):
    # Scrutiny officer logs in
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "scrutiny@aicte-india.org", "password": "Scrutiny@2026!"},
    )
    token = login_res.json()["access_token"]
    app_id = seed_test_data["application"].id

    res = await client.post(
        f"/api/v1/applications/{app_id}/scrutiny",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "category": "Land Title & Conversion Certificate",
            "finding_status": "ACCEPTED",
            "reason": "Clear title deed verified under Chapter I norms.",
            "notes": "Verified against state revenue portal.",
        },
    )
    assert res.status_code == 201
    finding = res.json()
    assert finding["finding_status"] == "ACCEPTED"
    assert finding["is_advisory_ai"] is False


@pytest.mark.asyncio
async def test_deficiency_notice_issuance_response_and_resolution(client: AsyncClient, seed_test_data):
    # 1. Scrutiny officer logs in and issues a formal notice
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "scrutiny@aicte-india.org", "password": "Scrutiny@2026!"},
    )
    officer_token = login_res.json()["access_token"]
    app_id = seed_test_data["application"].id

    create_notice_res = await client.post(
        f"/api/v1/applications/{app_id}/deficiencies",
        headers={"Authorization": f"Bearer {officer_token}"},
        json={
            "officer_remarks": "Immediate statutory cure required for deficiency items.",
            "cure_days": 7,
            "items": [
                {
                    "requirement_title": "Faculty Cadre Ratio",
                    "description": "Shortfall of 1 Professor in CSE department.",
                    "required_corrective_action": "Submit appointment order for PhD qualified Professor.",
                }
            ],
        },
    )
    assert create_notice_res.status_code == 201
    notice = create_notice_res.json()
    assert notice["status"] == "ISSUED"
    assert len(notice["items"]) == 1
    notice_id = notice["id"]

    # 2. Institution logs in and submits response
    login_inst = await client.post(
        "/api/v1/auth/login",
        json={"email": "inst@apex.edu.in", "password": "College@2026!"},
    )
    inst_token = login_inst.json()["access_token"]

    respond_res = await client.post(
        f"/api/v1/deficiencies/{notice_id}/respond",
        headers={"Authorization": f"Bearer {inst_token}"},
        json={
            "response_remarks": "Prof. R. Sen appointed as Professor in CSE. Joining report attached.",
            "attachment_document_ids": [],
        },
    )
    assert respond_res.status_code == 200
    updated_notice = respond_res.json()
    assert updated_notice["status"] == "RESPONSE_SUBMITTED"

    # 3. Scrutiny officer reviews and resolves the deficiency notice
    resolve_res = await client.post(
        f"/api/v1/deficiencies/{notice_id}/review",
        headers={"Authorization": f"Bearer {officer_token}"},
        json={
            "action": "RESOLVE",
            "officer_remarks": "Appointment verified against University selection committee approval. Cleared.",
        },
    )
    assert resolve_res.status_code == 200
    resolved_notice = resolve_res.json()
    assert resolved_notice["status"] == "RESOLVED"
    assert resolved_notice["items"][0]["item_status"] == "RESOLVED"


@pytest.mark.asyncio
async def test_deficiency_response_after_deadline_blocked(client: AsyncClient, seed_test_data, db_session):
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "inst@apex.edu.in", "password": "College@2026!"},
    )
    inst_token = login_res.json()["access_token"]
    app_id = seed_test_data["application"].id

    # Create expired notice directly in DB
    past_due = datetime.now(timezone.utc) - timedelta(days=2)
    expired_notice = DeficiencyNotice(
        notice_number="DEF-TEST-EXPIRED",
        application_id=app_id,
        institution_id=seed_test_data["institution"].id,
        issuing_officer_id=seed_test_data["users"]["admin"].id,
        status="ISSUED",
        due_date=past_due,
        officer_remarks="Past statutory deadline.",
    )
    db_session.add(expired_notice)
    await db_session.commit()

    # Attempt to submit clarification after due date
    res = await client.post(
        f"/api/v1/deficiencies/{expired_notice.id}/respond",
        headers={"Authorization": f"Bearer {inst_token}"},
        json={"response_remarks": "Late clarification attempt."},
    )
    assert res.status_code == 409
    assert "expired" in res.json()["message"].lower()


@pytest.mark.asyncio
async def test_deadline_escalation_job_idempotent(db_session, seed_test_data):
    # Add a notice with deadline in 24 hours
    app_id = seed_test_data["application"].id
    inst_id = seed_test_data["institution"].id
    due_24h = datetime.now(timezone.utc) + timedelta(hours=24)

    notice = DeficiencyNotice(
        notice_number="DEF-URGENT-01",
        application_id=app_id,
        institution_id=inst_id,
        issuing_officer_id=seed_test_data["users"]["admin"].id,
        status="ISSUED",
        due_date=due_24h,
    )
    db_session.add(notice)
    await db_session.commit()

    # Run deadline evaluation twice using test session
    await evaluate_deficiency_deadlines(db=db_session)
    await evaluate_deficiency_deadlines(db=db_session)

    # Check notification count with this notice dedup key
    stmt = select(Notification).where(Notification.dedup_key.like(f"approaching_{notice.id}%"))
    notifs = (await db_session.execute(stmt)).scalars().all()
    # Exactly 1 notification must exist (idempotent, no duplicates)
    assert len(notifs) == 1
    assert notifs[0].category == "DEADLINE_APPROACHING"
