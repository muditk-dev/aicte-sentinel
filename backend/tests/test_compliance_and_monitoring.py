import pytest
import csv
import io
import json
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.security.tokens import create_access_token
from app.models.compliance import (
    ComplianceObligation,
    ObligationEvidence,
    ObligationReviewHistory,
    ComplianceEscalation,
)
from app.models.institution import Institution
from app.models.user import User
from app.audit.service import verify_audit_chain
from app.workers.compliance_worker import evaluate_compliance_deadlines_and_escalations
from app.services.compliance_service import sanitize_csv_cell


def get_auth_headers(user, roles, inst_id=None):
    token = create_access_token(user_id=user.id, email=user.email, roles=roles, institution_id=inst_id)
    return {"Authorization": f"Bearer {token}"}


# ==============================================================================
# 1. OBLIGATION CREATION & VALIDATION TESTS (M14)
# ==============================================================================

@pytest.mark.asyncio
async def test_create_obligation_authorized_success(client: AsyncClient, seed_test_data):
    """
    Authorized scrutiny officer creates a post-approval compliance obligation.
    """
    data = seed_test_data
    u_scrutiny = data["users"]["scrutiny"]
    inst = data["institution"]
    headers = get_auth_headers(u_scrutiny, ["SCRUTINY_OFFICER"])

    now = datetime.now(timezone.utc)
    payload = {
        "institution_id": inst.id,
        "title": "Annual Faculty Biometric Attendance Verification",
        "description": "Submit certified Aadhaar-enabled biometric attendance logs for all approved engineering departments.",
        "category": "FACULTY_RATIO",
        "source_reference": "APH 2026-27 Clause 4.1.1",
        "applicability": "ALL_TECHNICAL_INSTITUTIONS",
        "issue_date": now.isoformat(),
        "due_date": (now + timedelta(days=30)).isoformat(),
        "recurrence": "ANNUAL",
        "is_synthetic_demonstration": True,
    }

    resp = await client.post("/api/v1/compliance/obligations", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    res_data = resp.json()

    assert res_data["obligation_code"].startswith("OBL-")
    assert res_data["title"] == payload["title"]
    assert res_data["status"] == "PENDING"
    assert res_data["category"] == "FACULTY_RATIO"
    assert len(res_data["history"]) >= 1
    assert res_data["history"][0]["action"] == "CREATED"


@pytest.mark.asyncio
async def test_create_obligation_invalid_dates_rejected(client: AsyncClient, seed_test_data):
    """
    Reject obligation creation when due_date is on or before issue_date.
    """
    data = seed_test_data
    u_scrutiny = data["users"]["scrutiny"]
    inst = data["institution"]
    headers = get_auth_headers(u_scrutiny, ["SCRUTINY_OFFICER"])

    now = datetime.now(timezone.utc)
    payload = {
        "institution_id": inst.id,
        "title": "Invalid Date Obligation",
        "description": "Due date is earlier than issue date.",
        "category": "INFRASTRUCTURE",
        "source_reference": "APH Clause 5.2.1",
        "issue_date": now.isoformat(),
        "due_date": (now - timedelta(days=5)).isoformat(),  # Invalid!
        "recurrence": "ONE_TIME",
    }

    resp = await client.post("/api/v1/compliance/obligations", json=payload, headers=headers)
    assert resp.status_code == 422 or resp.status_code == 400


# ==============================================================================
# 2. TENANT ISOLATION & RBAC TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_institution_user_cannot_create_obligation(client: AsyncClient, seed_test_data):
    """
    Institutional users are forbidden from creating statutory obligations.
    """
    data = seed_test_data
    u_inst = data["users"]["inst"]
    inst = data["institution"]
    headers = get_auth_headers(u_inst, ["INSTITUTION_USER"], inst_id=inst.id)

    now = datetime.now(timezone.utc)
    payload = {
        "institution_id": inst.id,
        "title": "Unauthorized Obligation",
        "description": "Institution trying to issue its own obligation.",
        "category": "GENERAL",
        "source_reference": "APH Clause 1.1",
        "issue_date": now.isoformat(),
        "due_date": (now + timedelta(days=30)).isoformat(),
    }

    resp = await client.post("/api/v1/compliance/obligations", json=payload, headers=headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_cross_institution_obligation_access_denied(client: AsyncClient, db_session: AsyncSession, seed_test_data):
    """
    Institution A cannot inspect or submit evidence for Institution B's obligation.
    """
    data = seed_test_data
    inst_a = data["institution"]
    u_inst_a = data["users"]["inst"]

    # Create Institution B
    inst_b = Institution(
        id="inst-tenant-b-test",
        name="Institution B University",
        code="INST-B-001",
        region="Western",
        state="Maharashtra",
        district="Pune",
        institution_type="PRIVATE",
        status="APPROVED",
        contact_email="admin@inst-b.edu.in",
        contact_phone="+919999888877",
    )
    db_session.add(inst_b)

    # Create obligation belonging to Institution B
    now = datetime.now(timezone.utc)
    ob_b = ComplianceObligation(
        id="obl-tenant-b-test",
        obligation_code="OBL-TEST-B-001",
        institution_id=inst_b.id,
        title="Institution B Fire NOC",
        description="Confidential fire NOC for Institution B",
        category="SAFETY_CLEARANCE",
        source_reference="APH Clause 1.7.3",
        applicability="ALL_TECHNICAL_INSTITUTIONS",
        issue_date=now,
        due_date=now + timedelta(days=20),
        recurrence="ANNUAL",
        status="PENDING",
    )
    db_session.add(ob_b)
    await db_session.commit()

    # User from Institution A attempts to fetch Institution B's obligation
    headers_a = get_auth_headers(u_inst_a, ["INSTITUTION_ADMIN"], inst_id=inst_a.id)
    resp = await client.get(f"/api/v1/compliance/obligations/{ob_b.id}", headers=headers_a)
    assert resp.status_code == 403

    # User from Institution A attempts to submit evidence to Institution B's obligation
    ev_payload = {
        "title": "Malicious Cross-Tenant Evidence",
        "description": "Attempting cross-tenant tampering",
    }
    ev_resp = await client.post(f"/api/v1/compliance/obligations/{ob_b.id}/evidence", json=ev_payload, headers=headers_a)
    assert ev_resp.status_code == 403


# ==============================================================================
# 3. EVIDENCE SUBMISSION & HUMAN REVIEW WORKFLOW
# ==============================================================================

@pytest.mark.asyncio
async def test_evidence_submission_and_officer_review_lifecycle(client: AsyncClient, db_session: AsyncSession, seed_test_data):
    """
    Verify complete lifecycle:
    1. Institution uploads evidence -> status moves to SUBMITTED.
    2. Officer reviews and flags DEFICIENT with cure window -> status moves to DEFICIENT.
    3. Institution resubmits evidence -> status moves to SUBMITTED.
    4. Officer verifies compliant -> status moves to COMPLIANT.
    5. Officer closes obligation -> status moves to CLOSED.
    """
    data = seed_test_data
    inst = data["institution"]
    u_inst = data["users"]["inst"]
    u_scrutiny = data["users"]["scrutiny"]
    headers_inst = get_auth_headers(u_inst, ["INSTITUTION_ADMIN"], inst_id=inst.id)
    headers_officer = get_auth_headers(u_scrutiny, ["SCRUTINY_OFFICER"])

    # Create test obligation
    now = datetime.now(timezone.utc)
    ob = ComplianceObligation(
        id="obl-lifecycle-test",
        obligation_code="OBL-LIFE-2026-001",
        institution_id=inst.id,
        title="Fire Sprinkler and Dual Staircase Verification",
        description="Verify automatic fire sprinklers across blocks exceeding 15 meters.",
        category="SAFETY_CLEARANCE",
        source_reference="APH 2026-27 Clause 1.7.3",
        applicability="ALL_TECHNICAL_INSTITUTIONS",
        issue_date=now,
        due_date=now + timedelta(days=30),
        recurrence="ANNUAL",
        status="PENDING",
    )
    db_session.add(ob)
    await db_session.commit()

    # Step 1: Institution submits initial evidence
    ev_resp = await client.post(
        f"/api/v1/compliance/obligations/{ob.id}/evidence",
        json={
            "title": "State Fire Clearance Certificate 2026",
            "description": "Signed NOC from Delhi Fire Service",
            "file_url": "/vault/compliance/fire_noc_2026.pdf",
            "submission_notes": "Certificate issued on 15-Jan-2026",
        },
        headers=headers_inst,
    )
    assert ev_resp.status_code == 200, ev_resp.text
    ev_data = ev_resp.json()
    assert ev_data["status"] == "SUBMITTED"
    assert len(ev_data["evidences"]) == 1

    # Step 2: Officer reviews and flags DEFICIENT
    rev1_resp = await client.post(
        f"/api/v1/compliance/obligations/{ob.id}/review",
        json={
            "decision": "DEFICIENCY_FLAGGED",
            "review_comments": "Certificate does not specify sprinkler inspection for Engineering Workshop Block.",
            "deficiency_cure_days": 10,
        },
        headers=headers_officer,
    )
    assert rev1_resp.status_code == 200
    rev1_data = rev1_resp.json()
    assert rev1_data["status"] == "DEFICIENT"

    # Step 3: Institution resubmits curative evidence
    resub_resp = await client.post(
        f"/api/v1/compliance/obligations/{ob.id}/evidence",
        json={
            "title": "Supplemental Fire Sprinkler Test Report",
            "description": "Engineering workshop sprinkler pressure test certificate",
        },
        headers=headers_inst,
    )
    assert resub_resp.status_code == 200
    assert resub_resp.json()["status"] == "SUBMITTED"

    # Step 4: Officer reviews and marks VERIFIED_COMPLIANT
    rev2_resp = await client.post(
        f"/api/v1/compliance/obligations/{ob.id}/review",
        json={
            "decision": "VERIFIED_COMPLIANT",
            "review_comments": "Supplemental sprinkler pressure report verified satisfactory against APH Clause 1.7.3.",
        },
        headers=headers_officer,
    )
    assert rev2_resp.status_code == 200
    rev2_data = rev2_resp.json()
    assert rev2_data["status"] == "COMPLIANT"

    # Step 5: Officer closes obligation
    close_resp = await client.post(
        f"/api/v1/compliance/obligations/{ob.id}/review",
        json={
            "decision": "CLOSED",
            "review_comments": "Annual compliance cycle completed and closed.",
        },
        headers=headers_officer,
    )
    assert close_resp.status_code == 200
    assert close_resp.json()["status"] == "CLOSED"


# ==============================================================================
# 4. INVALID STATE TRANSITION GUARDS
# ==============================================================================

@pytest.mark.asyncio
async def test_invalid_state_transition_blocked(client: AsyncClient, db_session: AsyncSession, seed_test_data):
    """
    Verify that illegal state transitions (e.g. CLOSED -> PENDING, or PENDING -> COMPLIANT without review)
    are strictly rejected with HTTP 400.
    """
    data = seed_test_data
    inst = data["institution"]
    u_admin = data["users"]["admin"]
    headers = get_auth_headers(u_admin, ["SUPER_ADMIN"])

    now = datetime.now(timezone.utc)
    ob = ComplianceObligation(
        id="obl-guard-test",
        obligation_code="OBL-GUARD-2026",
        institution_id=inst.id,
        title="Guard Test Obligation",
        description="Testing state transition guards.",
        category="GENERAL",
        source_reference="APH Clause 1.1",
        issue_date=now,
        due_date=now + timedelta(days=10),
        status="PENDING",
    )
    db_session.add(ob)
    await db_session.commit()

    # Attempt illegal transition: PENDING directly to COMPLIANT
    resp = await client.post(
        f"/api/v1/compliance/obligations/{ob.id}/transition",
        json={"target_status": "COMPLIANT", "comments": "Illegal jump"},
        headers=headers,
    )
    assert resp.status_code == 400
    assert "INVALID_STATE_TRANSITION" in resp.json().get("code", "")


# ==============================================================================
# 5. DEADLINE MONITORING, OVERDUE & DEDUPLICATION (M15)
# ==============================================================================

@pytest.mark.asyncio
async def test_deadline_monitoring_and_deduplication(db_session: AsyncSession, seed_test_data):
    """
    Tests compliance monitoring worker:
    1. Detects overdue obligation and transitions to OVERDUE.
    2. Overdue >= 7 days triggers Level 1 escalation.
    3. Consecutive worker runs do NOT create duplicate notifications (deduplication check).
    """
    inst = seed_test_data["institution"]
    now = datetime.now(timezone.utc)

    # Create obligation that is 8 days overdue
    overdue_ob = ComplianceObligation(
        id="obl-overdue-worker-test",
        obligation_code="OBL-OVERDUE-008",
        institution_id=inst.id,
        title="Overdue Laboratory Equipment Safety Certificate",
        description="Mandatory annual pressure vessel inspection.",
        category="INFRASTRUCTURE",
        source_reference="APH Clause 5.2.1",
        issue_date=now - timedelta(days=38),
        due_date=now - timedelta(days=8),  # 8 days overdue
        status="PENDING",
    )
    db_session.add(overdue_ob)
    await db_session.commit()

    # Run 1 of monitoring worker
    actions_run1 = await evaluate_compliance_deadlines_and_escalations(db_session)
    assert actions_run1 >= 1

    # Verify status transitioned to OVERDUE
    await db_session.refresh(overdue_ob)
    assert overdue_ob.status == "OVERDUE"

    # Verify Level 1 Escalation created (since overdue >= 7 days)
    esc_stmt = select(ComplianceEscalation).where(ComplianceEscalation.obligation_id == overdue_ob.id)
    esc = (await db_session.execute(esc_stmt)).scalar_one_or_none()
    assert esc is not None
    assert esc.escalation_level == 1
    assert esc.trigger_reason == "OVERDUE_7_DAYS"

    # Run 2 immediately on same database -> must NOT create duplicate notifications/escalations
    actions_run2 = await evaluate_compliance_deadlines_and_escalations(db_session)
    # actions_run2 must be 0 for this obligation because dedup_key prevents duplicate alerts
    assert actions_run2 == 0


# ==============================================================================
# 6. COMPLIANCE REPORTS & CSV FORMULA INJECTION SANITIZATION (M16)
# ==============================================================================

@pytest.mark.asyncio
async def test_compliance_reports_endpoints(client: AsyncClient, seed_test_data):
    """
    Test compliance reporting endpoints:
    - Summary report
    - Institution reports
    - Deadlines calendar report
    - Deficiencies report
    """
    u_admin = seed_test_data["users"]["admin"]
    headers = get_auth_headers(u_admin, ["SUPER_ADMIN"])

    # Summary Report
    sum_resp = await client.get("/api/v1/compliance/reports/summary", headers=headers)
    assert sum_resp.status_code == 200
    sum_data = sum_resp.json()
    assert "total_obligations" in sum_data
    assert "compliance_rate_percent" in sum_data
    assert "categories_breakdown" in sum_data

    # Institution Reports
    inst_resp = await client.get("/api/v1/compliance/reports/by-institution", headers=headers)
    assert inst_resp.status_code == 200
    inst_data = inst_resp.json()
    assert len(inst_data) >= 1
    assert "compliance_percentage" in inst_data[0]

    # Deadlines Report
    dead_resp = await client.get("/api/v1/compliance/reports/deadlines?days_ahead=90", headers=headers)
    assert dead_resp.status_code == 200
    dead_data = dead_resp.json()
    assert isinstance(dead_data, list)

    # Deficiencies Report
    def_resp = await client.get("/api/v1/compliance/reports/deficiencies", headers=headers)
    assert def_resp.status_code == 200
    assert isinstance(def_resp.json(), list)


@pytest.mark.asyncio
async def test_csv_export_and_formula_injection_protection(client: AsyncClient, db_session: AsyncSession, seed_test_data):
    """
    Tests CSV export security against Spreadsheet Formula Injection (CSV Injection).
    OWASP Standard: Prepends apostrophe (') to cells beginning with '=', '+', '-', '@', tab.
    """
    inst = seed_test_data["institution"]
    u_admin = seed_test_data["users"]["admin"]
    headers = get_auth_headers(u_admin, ["SUPER_ADMIN"])

    now = datetime.now(timezone.utc)
    # Create obligation with malicious formula in title and reference
    malicious_ob = ComplianceObligation(
        id="obl-formula-injection-test",
        obligation_code="=cmd|' /C calc'!A0",  # Malicious formula!
        institution_id=inst.id,
        title="+SUM(1, 2) Dangerous Formula",  # Malicious leading '+'
        description="Testing CSV formula escape.",
        category="@DDE(server,topic,item)",  # Malicious leading '@'
        source_reference="-10+20 Formula",  # Malicious leading '-'
        issue_date=now,
        due_date=now + timedelta(days=20),
        status="PENDING",
    )
    db_session.add(malicious_ob)
    await db_session.commit()

    # Trigger CSV export
    resp = await client.get("/api/v1/compliance/reports/export-csv", headers=headers)
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    csv_text = resp.text

    # Parse exported CSV
    reader = csv.reader(io.StringIO(csv_text))
    rows = list(reader)
    assert len(rows) >= 2  # Header + rows

    # Verify that dangerous formulas are safely sanitized with leading single-quote
    found_malicious_row = False
    for row in rows:
        code_cell = row[0]
        title_cell = row[2]
        cat_cell = row[3]
        src_cell = row[4]

        if "cmd" in code_cell or "SUM" in title_cell:
            found_malicious_row = True
            # Assert all leading dangerous characters are safely prepended with single quote (')
            assert code_cell.startswith("'="), f"Formula injection vulnerability! Cell unescaped: {code_cell}"
            assert title_cell.startswith("'+"), f"Formula injection vulnerability! Cell unescaped: {title_cell}"
            assert cat_cell.startswith("'@"), f"Formula injection vulnerability! Cell unescaped: {cat_cell}"
            assert src_cell.startswith("'-"), f"Formula injection vulnerability! Cell unescaped: {src_cell}"

    assert found_malicious_row, "Malicious test row was not exported in CSV"


# ==============================================================================
# 7. AUDIT CHAIN INTEGRITY TEST
# ==============================================================================

@pytest.mark.asyncio
async def test_compliance_actions_maintain_audit_hash_chain(client: AsyncClient, db_session: AsyncSession, seed_test_data):
    """
    Ensure all compliance actions maintain an unbroken SHA-256 continuous hash-chained ledger.
    """
    inst = seed_test_data["institution"]
    u_admin = seed_test_data["users"]["admin"]
    headers = get_auth_headers(u_admin, ["SUPER_ADMIN"])

    # Create obligation via API
    now = datetime.now(timezone.utc)
    payload = {
        "institution_id": inst.id,
        "title": "Chained Audit Verification Obligation",
        "description": "Verifying SHA-256 cryptographic chaining of compliance actions.",
        "category": "ANNUAL_REPORT",
        "source_reference": "APH Clause 7.1",
        "issue_date": now.isoformat(),
        "due_date": (now + timedelta(days=45)).isoformat(),
    }
    resp = await client.post("/api/v1/compliance/obligations", json=payload, headers=headers)
    assert resp.status_code == 201

    # Verify audit chain integrity
    audit_res = await verify_audit_chain(db_session)
    assert audit_res.is_valid is True
    assert audit_res.total_events_checked >= 1
