import json
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.evc import Expert, EVCInspection, EVCInspectionExpert, EVCReportVersion
from app.models.committee import Committee, CommitteeMembership, Hearing, HearingDocket, HearingAttendance
from app.models.decision import StatutoryDecision, DecisionCondition
from app.models.institution import Institution
from app.models.application import Application
from app.security.tokens import create_access_token


@pytest.mark.asyncio
async def test_expert_registry_listing_and_masking(client: AsyncClient, seed_test_data: dict, db_session: AsyncSession):
    admin = seed_test_data["users"]["admin"]
    inst_user = seed_test_data["users"]["inst"]
    admin_token = create_access_token(user_id=admin.id, email=admin.email, roles=["SUPER_ADMIN"])
    inst_token = create_access_token(user_id=inst_user.id, email=inst_user.email, roles=["INSTITUTION_ADMIN"], institution_id=inst_user.institution_id)

    # 1. Admin creates expert
    payload = {
        "name": "Dr. Pradeep Joshi",
        "email": "pradeep.joshi@iitd.ac.in",
        "phone": "+91-9876543210",
        "designation": "Professor of Electrical Engineering",
        "organization": "Indian Institute of Technology Delhi",
        "expert_type": "ACADEMIC",
        "qualifications": "Ph.D. in Power Systems (IIT Kanpur)",
        "experience_years": 24,
        "specializations": ["High Voltage Labs", "Grid Compliance"],
        "affiliated_institution_ids": ["inst-test-uuid-1"],
        "alma_mater": "IIT Kanpur",
        "state": "Delhi",
        "district": "New Delhi",
        "availability_status": "AVAILABLE",
        "conflict_declarations": ["Former advisory consultant for Apex Institute"],
    }
    res = await client.post(
        "/api/v1/experts",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 200
    expert_data = res.json()
    assert expert_data["name"] == "Dr. Pradeep Joshi"
    assert expert_data["phone"] == "+91-9876543210"
    assert len(expert_data["conflict_declarations"]) == 1

    # 2. Institution user lists experts - sensitive phone and conflicts must be masked
    res_inst = await client.get(
        "/api/v1/experts",
        headers={"Authorization": f"Bearer {inst_token}"},
    )
    assert res_inst.status_code == 200
    items = res_inst.json()
    assert len(items) >= 1
    target = next(e for e in items if e["email"] == "pradeep.joshi@iitd.ac.in")
    assert target["phone"] is None
    assert len(target["conflict_declarations"]) == 0


@pytest.mark.asyncio
async def test_conflict_of_interest_detection_and_blocking(client: AsyncClient, seed_test_data: dict, db_session: AsyncSession):
    admin = seed_test_data["users"]["admin"]
    ro = seed_test_data["users"]["ro"]
    app = seed_test_data["application"]
    ro_token = create_access_token(user_id=ro.id, email=ro.email, roles=["REGIONAL_OFFICER"])

    # Create an expert with mandatory geographic district conflict (Target institution is in New Delhi, Delhi)
    expert_conflict = Expert(
        name="Dr. Local Expert",
        email="local.expert@delhi.ac.in",
        designation="Professor",
        organization="Delhi Technical University",
        expert_type="ACADEMIC",
        qualifications="Ph.D.",
        experience_years=15,
        alma_mater="DTU",
        state="Delhi",
        district="New Delhi",  # Exact match with inst.district
        is_active=True,
        verification_status="VERIFIED",
        availability_status="AVAILABLE",
    )
    db_session.add(expert_conflict)
    await db_session.commit()
    await db_session.refresh(expert_conflict)

    # Schedule an inspection
    insp_res = await client.post(
        "/api/v1/inspections",
        json={
            "application_id": app.id,
            "inspection_mode": "PHYSICAL",
            "scheduled_start_date": "2026-11-10T09:00:00Z",
            "scheduled_end_date": "2026-11-10T17:00:00Z",
        },
        headers={"Authorization": f"Bearer {ro_token}"},
    )
    assert insp_res.status_code == 200
    insp_id = insp_res.json()["id"]

    # Conflict check endpoint test
    check_res = await client.post(
        f"/api/v1/experts/{expert_conflict.id}/conflict-check",
        json={"expert_id": expert_conflict.id, "application_id": app.id},
        headers={"Authorization": f"Bearer {ro_token}"},
    )
    assert check_res.status_code == 200
    check_data = check_res.json()
    assert check_data["has_conflict"] is True
    assert check_data["is_blocked"] is True
    assert any("geographic conflict" in r for r in check_data["conflict_reasons"])

    # Attempt to assign to panel WITHOUT override -> MUST BE BLOCKED
    assign_blocked = await client.post(
        f"/api/v1/inspections/{insp_id}/experts",
        json={
            "expert_id": expert_conflict.id,
            "role": "MEMBER",
            "override_conflict": False,
        },
        headers={"Authorization": f"Bearer {ro_token}"},
    )
    assert assign_blocked.status_code == 422
    err_msg = assign_blocked.json().get("message", str(assign_blocked.json()))
    assert "Statutory Conflict of Interest detected" in err_msg


@pytest.mark.asyncio
async def test_conflict_override_with_justification(client: AsyncClient, seed_test_data: dict, db_session: AsyncSession):
    ro = seed_test_data["users"]["ro"]
    app = seed_test_data["application"]
    ro_token = create_access_token(user_id=ro.id, email=ro.email, roles=["REGIONAL_OFFICER"])

    # Create expert with declared conflict
    expert = Expert(
        name="Dr. Exemption Candidate",
        email="exempt.expert@state.edu",
        designation="Professor",
        organization="State University",
        expert_type="ACADEMIC",
        qualifications="Ph.D.",
        experience_years=20,
        alma_mater="Apex Institute of Technology",  # Alma mater conflict
        state="Haryana",
        district="Gurgaon",
        is_active=True,
        verification_status="VERIFIED",
        availability_status="AVAILABLE",
    )
    db_session.add(expert)
    await db_session.commit()
    await db_session.refresh(expert)

    # Schedule inspection
    insp_res = await client.post(
        "/api/v1/inspections",
        json={
            "application_id": app.id,
            "inspection_mode": "HYBRID",
            "scheduled_start_date": "2026-11-15T09:00:00Z",
            "scheduled_end_date": "2026-11-15T17:00:00Z",
        },
        headers={"Authorization": f"Bearer {ro_token}"},
    )
    insp_id = insp_res.json()["id"]

    # Assign WITH documented justification override
    justification = "Authorized exemption: Sole available subject matter specialist in Micro-grid systems under Chapter I Special Provision."
    assign_res = await client.post(
        f"/api/v1/inspections/{insp_id}/experts",
        json={
            "expert_id": expert.id,
            "role": "SPECIALIST",
            "override_conflict": True,
            "override_justification": justification,
        },
        headers={"Authorization": f"Bearer {ro_token}"},
    )
    assert assign_res.status_code == 200
    data = assign_res.json()
    assert data["conflict_check_passed"] is True
    assert "OVERRIDDEN" in data["conflict_notes"]
    assert "Alma mater conflict" in data["conflict_notes"]


@pytest.mark.asyncio
async def test_expert_scheduling_conflict_prevention(client: AsyncClient, seed_test_data: dict, db_session: AsyncSession):
    ro = seed_test_data["users"]["ro"]
    ro_token = create_access_token(user_id=ro.id, email=ro.email, roles=["REGIONAL_OFFICER"])

    # Create 2 applications
    inst = seed_test_data["institution"]
    tmpl = seed_test_data["template"]
    ver = seed_test_data["version"]
    user_inst = seed_test_data["users"]["inst"]

    app1 = seed_test_data["application"]
    app2 = Application(
        application_number="AICTE-2026-TEST-SCHED-002",
        institution_id=inst.id,
        template_id=tmpl.id,
        version_id=ver.id,
        current_status="SUBMITTED",
        applicant_user_id=user_inst.id,
    )
    db_session.add(app2)

    expert = Expert(
        name="Dr. Busy Expert",
        email="busy.expert@univ.ac.in",
        designation="Professor",
        organization="Central University",
        expert_type="ACADEMIC",
        qualifications="Ph.D.",
        experience_years=18,
        alma_mater="IIT Kanpur",
        state="Uttar Pradesh",
        district="Kanpur Nagar",
        is_active=True,
        verification_status="VERIFIED",
        availability_status="AVAILABLE",
    )
    db_session.add(expert)
    await db_session.commit()
    await db_session.refresh(app2)
    await db_session.refresh(expert)

    # Inspection 1: Nov 20 to Nov 22
    insp1_res = await client.post(
        "/api/v1/inspections",
        json={
            "application_id": app1.id,
            "inspection_mode": "PHYSICAL",
            "scheduled_start_date": "2026-11-20T09:00:00Z",
            "scheduled_end_date": "2026-11-22T17:00:00Z",
        },
        headers={"Authorization": f"Bearer {ro_token}"},
    )
    insp1_id = insp1_res.json()["id"]

    # Assign to Inspection 1
    assign1 = await client.post(
        f"/api/v1/inspections/{insp1_id}/experts",
        json={"expert_id": expert.id, "role": "CHAIRPERSON"},
        headers={"Authorization": f"Bearer {ro_token}"},
    )
    assert assign1.status_code == 200

    # Inspection 2: Nov 21 to Nov 23 (Overlaps Nov 21-22)
    insp2_res = await client.post(
        "/api/v1/inspections",
        json={
            "application_id": app2.id,
            "inspection_mode": "PHYSICAL",
            "scheduled_start_date": "2026-11-21T09:00:00Z",
            "scheduled_end_date": "2026-11-23T17:00:00Z",
        },
        headers={"Authorization": f"Bearer {ro_token}"},
    )
    insp2_id = insp2_res.json()["id"]

    # Assigning to Inspection 2 MUST FAIL due to scheduling conflict
    assign2 = await client.post(
        f"/api/v1/inspections/{insp2_id}/experts",
        json={"expert_id": expert.id, "role": "MEMBER"},
        headers={"Authorization": f"Bearer {ro_token}"},
    )
    assert assign2.status_code == 422
    err_msg2 = assign2.json().get("message", str(assign2.json()))
    assert "Scheduling conflict" in err_msg2


@pytest.mark.asyncio
async def test_inspection_report_versioning_and_sha256(client: AsyncClient, seed_test_data: dict, db_session: AsyncSession):
    ro = seed_test_data["users"]["ro"]
    app = seed_test_data["application"]
    ro_token = create_access_token(user_id=ro.id, email=ro.email, roles=["REGIONAL_OFFICER"])

    insp_res = await client.post(
        "/api/v1/inspections",
        json={
            "application_id": app.id,
            "inspection_mode": "PHYSICAL",
            "scheduled_start_date": "2026-11-25T09:00:00Z",
            "scheduled_end_date": "2026-11-25T17:00:00Z",
        },
        headers={"Authorization": f"Bearer {ro_token}"},
    )
    insp_id = insp_res.json()["id"]

    # 1. Transition to IN_PROGRESS
    trans_res = await client.post(
        f"/api/v1/inspections/{insp_id}/transition",
        json={"target_status": "IN_PROGRESS"},
        headers={"Authorization": f"Bearer {ro_token}"},
    )
    assert trans_res.status_code == 200
    assert trans_res.json()["status"] == "IN_PROGRESS"

    # 2. Submit Report Version 1
    report_payload_v1 = {
        "overall_recommendation": "DEFICIENT",
        "infrastructure_score": 68.0,
        "faculty_verification_status": "DEFICIENT",
        "land_building_status": "SATISFACTORY",
        "laboratories_equipment_status": "SATISFACTORY",
        "safety_and_amenities_status": "SATISFACTORY",
        "observations": "Cadre ratio short by 1 Associate Professor. Ramp slope certificate missing.",
        "deficiencies_identified": "Faculty cadre ratio shortfall in Electronics department.",
        "checklist_data": {"faculty_verified": False, "infrastructure_verified": True},
        "location_evidence": {"gps": "28.5355, 77.3910"},
    }
    rep_res1 = await client.post(
        f"/api/v1/inspections/{insp_id}/reports",
        json=report_payload_v1,
        headers={"Authorization": f"Bearer {ro_token}"},
    )
    assert rep_res1.status_code == 200
    rep1_data = rep_res1.json()
    assert rep1_data["version_number"] == 1
    assert len(rep1_data["sha256_hash"]) == 64
    assert rep1_data["overall_recommendation"] == "DEFICIENT"
    assert rep1_data["review_status"] == "PENDING"

    # 3. RO reviews report -> RETURNED_FOR_CORRECTION
    review_res = await client.post(
        f"/api/v1/inspections/{insp_id}/reports/{rep1_data['id']}/review",
        json={"review_status": "RETURNED_FOR_CORRECTION", "review_remarks": "Re-verify faculty roster following supplementary appointment documents."},
        headers={"Authorization": f"Bearer {ro_token}"},
    )
    assert review_res.status_code == 200
    assert review_res.json()["review_status"] == "RETURNED_FOR_CORRECTION"

    # Inspection status should now be RETURNED_FOR_CORRECTION
    insp_check = await client.get(f"/api/v1/inspections/{insp_id}", headers={"Authorization": f"Bearer {ro_token}"})
    assert insp_check.json()["status"] == "RETURNED_FOR_CORRECTION"

    # 4. Submit Report Version 2
    report_payload_v2 = {
        "overall_recommendation": "RECOMMENDED",
        "infrastructure_score": 86.5,
        "faculty_verification_status": "SATISFACTORY",
        "land_building_status": "SATISFACTORY",
        "laboratories_equipment_status": "SATISFACTORY",
        "safety_and_amenities_status": "SATISFACTORY",
        "observations": "Supplementary joining report verified. All cadre ratios now compliant.",
        "checklist_data": {"faculty_verified": True, "infrastructure_verified": True},
        "location_evidence": {"gps": "28.5355, 77.3910"},
    }
    rep_res2 = await client.post(
        f"/api/v1/inspections/{insp_id}/reports",
        json=report_payload_v2,
        headers={"Authorization": f"Bearer {ro_token}"},
    )
    assert rep_res2.status_code == 200
    rep2_data = rep_res2.json()
    assert rep2_data["version_number"] == 2
    assert rep2_data["overall_recommendation"] == "RECOMMENDED"

    # 5. RO accepts Report Version 2
    accept_res = await client.post(
        f"/api/v1/inspections/{insp_id}/reports/{rep2_data['id']}/review",
        json={"review_status": "ACCEPTED", "review_remarks": "Satisfactory compliance established."},
        headers={"Authorization": f"Bearer {ro_token}"},
    )
    assert accept_res.status_code == 200
    assert accept_res.json()["review_status"] == "ACCEPTED"

    # Check inspection status is now ACCEPTED
    insp_final = await client.get(f"/api/v1/inspections/{insp_id}", headers={"Authorization": f"Bearer {ro_token}"})
    assert insp_final.json()["status"] == "ACCEPTED"


@pytest.mark.asyncio
async def test_committee_quorum_and_hearing_workflow(client: AsyncClient, seed_test_data: dict, db_session: AsyncSession):
    ro = seed_test_data["users"]["ro"]
    app = seed_test_data["application"]
    ro_token = create_access_token(user_id=ro.id, email=ro.email, roles=["REGIONAL_OFFICER"])

    # 1. Create Committee with Quorum = 3
    comm_res = await client.post(
        "/api/v1/committees",
        json={
            "code": "SHC-TEST-BENCH",
            "name": "Standing Hearing Committee Test Bench",
            "committee_type": "SHC",
            "quorum_required": 3,
            "valid_from": "2026-01-01T00:00:00Z",
        },
        headers={"Authorization": f"Bearer {ro_token}"},
    )
    assert comm_res.status_code == 200
    comm_id = comm_res.json()["id"]

    # 2. Schedule Hearing
    hear_res = await client.post(
        "/api/v1/hearings",
        json={
            "committee_id": comm_id,
            "hearing_type": "SHC",
            "scheduled_date": "2026-11-28T10:00:00Z",
            "meeting_mode": "HYBRID",
            "venue_or_link": "Regional Office Conference Room",
            "agenda": "Hearing on Infrastructure and Land Title Disputes",
        },
        headers={"Authorization": f"Bearer {ro_token}"},
    )
    assert hear_res.status_code == 200
    hear_id = hear_res.json()["id"]

    # 3. Docket Application
    docket_res = await client.post(
        f"/api/v1/hearings/{hear_id}/dockets",
        json={
            "application_id": app.id,
            "matter_summary": "Dispute on built-up area and ramp slope certification.",
            "referred_by": "REGIONAL_OFFICE",
        },
        headers={"Authorization": f"Bearer {ro_token}"},
    )
    assert docket_res.status_code == 200
    assert docket_res.json()["docket_status"] == "PENDING"

    # 4. Record Deficient Attendance (Only 1 member attended, but quorum is 3)
    att_res = await client.post(
        f"/api/v1/hearings/{hear_id}/attendance",
        json=[
            {"member_name": "Prof. Chairperson", "member_role": "CHAIRPERSON", "attended": True, "attendance_mode": "IN_PERSON"},
            {"member_name": "Dr. Member 1", "member_role": "MEMBER", "attended": False, "attendance_mode": "IN_PERSON"},
            {"member_name": "Dr. Member 2", "member_role": "MEMBER", "attended": False, "attendance_mode": "REMOTE"},
        ],
        headers={"Authorization": f"Bearer {ro_token}"},
    )
    assert att_res.status_code == 200

    # Attempt to record minutes when quorum is deficient -> MUST FAIL
    minutes_blocked = await client.post(
        f"/api/v1/hearings/{hear_id}/minutes",
        json={
            "minutes_of_meeting": "Committee reviewed institutional submission and recorded findings.",
            "final_recommendation": "RECOMMEND_APPROVAL",
            "recommendation_summary": "Institutional clarification accepted.",
        },
        headers={"Authorization": f"Bearer {ro_token}"},
    )
    assert minutes_blocked.status_code == 422
    err_q = minutes_blocked.json().get("message", str(minutes_blocked.json()))
    assert "Statutory Quorum not met" in err_q

    # 5. Record Compliant Attendance (3 members attended)
    await client.post(
        f"/api/v1/hearings/{hear_id}/attendance",
        json=[
            {"member_name": "Dr. Member 1", "member_role": "MEMBER", "attended": True, "attendance_mode": "IN_PERSON"},
            {"member_name": "Dr. Member 2", "member_role": "MEMBER", "attended": True, "attendance_mode": "REMOTE"},
        ],
        headers={"Authorization": f"Bearer {ro_token}"},
    )

    # Record minutes now succeeds
    minutes_res = await client.post(
        f"/api/v1/hearings/{hear_id}/minutes",
        json={
            "minutes_of_meeting": "Committee reviewed institutional submission and architectural drawings. Explanations found compliant with Chapter I.",
            "final_recommendation": "RECOMMEND_APPROVAL",
            "recommendation_summary": "Unanimously recommend granting Extension of Approval.",
        },
        headers={"Authorization": f"Bearer {ro_token}"},
    )
    assert minutes_res.status_code == 200
    assert minutes_res.json()["status"] == "RECOMMENDATION_RECORDED"
    assert minutes_res.json()["final_recommendation"] == "RECOMMEND_APPROVAL"


@pytest.mark.asyncio
async def test_statutory_decision_authorization_and_immutability(client: AsyncClient, seed_test_data: dict, db_session: AsyncSession):
    ro = seed_test_data["users"]["ro"]
    inst_user = seed_test_data["users"]["inst"]
    app = seed_test_data["application"]
    ro_token = create_access_token(user_id=ro.id, email=ro.email, roles=["REGIONAL_OFFICER"])
    inst_token = create_access_token(user_id=inst_user.id, email=inst_user.email, roles=["INSTITUTION_ADMIN"], institution_id=inst_user.institution_id)

    # Set application to RECOMMENDED_APPROVAL state
    app.current_status = "RECOMMENDED_APPROVAL"
    await db_session.commit()

    # 1. Unauthorized role attempt (Institution Admin) -> MUST BE 403
    unauth_res = await client.post(
        "/api/v1/decisions",
        json={
            "application_id": app.id,
            "decision_type": "APPROVED",
            "reasons": "Self approval attempt by institution signatory.",
            "declaration_attestation": "I attest compliance.",
        },
        headers={"Authorization": f"Bearer {inst_token}"},
    )
    assert unauth_res.status_code == 403

    # 2. Conditional Approval without conditions -> MUST BE 422
    cond_missing = await client.post(
        "/api/v1/decisions",
        json={
            "application_id": app.id,
            "decision_type": "CONDITIONALLY_APPROVED",
            "reasons": "Core requirements fulfilled. Conditional approval granted subject to conditions.",
            "declaration_attestation": "I, Regional Officer, hereby formally attest this decision under statutory authority.",
            "conditions": [],
        },
        headers={"Authorization": f"Bearer {ro_token}"},
    )
    assert cond_missing.status_code == 422
    err_cond = cond_missing.json().get("message", str(cond_missing.json()))
    assert "at least one explicit compliance condition" in err_cond

    # 3. Valid Conditional Approval issuance
    valid_dec = await client.post(
        "/api/v1/decisions",
        json={
            "application_id": app.id,
            "decision_type": "CONDITIONALLY_APPROVED",
            "reasons": "All academic and infrastructure parameters verified satisfactory. Fire NOC renewal pending submission.",
            "declaration_attestation": "I, Prof. Anita Deshmukh, Regional Officer, hereby formally attest this statutory decision in accordance with the AICTE Act 1987.",
            "intake_approved": 480,
            "valid_for_years": 1,
            "conditions": [
                {
                    "condition_code": "COND-FIRE-NOC-2026",
                    "description": "Submit certified renewal of Fire NOC within 60 days of session commencement.",
                    "due_date": "2026-12-30T18:00:00Z",
                }
            ],
        },
        headers={"Authorization": f"Bearer {ro_token}"},
    )
    assert valid_dec.status_code == 200
    dec_data = valid_dec.json()
    assert dec_data["decision_type"] == "CONDITIONALLY_APPROVED"
    assert len(dec_data["sha256_attestation"]) == 64
    assert len(dec_data["conditions"]) == 1
    assert dec_data["conditions"][0]["condition_code"] == "COND-FIRE-NOC-2026"

    # Application state must have mutated to APPROVED
    await db_session.refresh(app)
    assert app.current_status == "APPROVED"

    # 4. Immutability guard: Attempt to issue a second decision on same application -> MUST BE BLOCKED
    duplicate_res = await client.post(
        "/api/v1/decisions",
        json={
            "application_id": app.id,
            "decision_type": "APPROVED",
            "reasons": "Attempt to overwrite finalized statutory decision.",
            "declaration_attestation": "I attest compliance.",
        },
        headers={"Authorization": f"Bearer {ro_token}"},
    )
    assert duplicate_res.status_code == 422
    err_dup = duplicate_res.json().get("message", str(duplicate_res.json()))
    assert "already finalized" in err_dup

    # 5. Reconsideration request -> Reopens case into APPELLATE_REVIEW
    reconsider_res = await client.post(
        f"/api/v1/decisions/{dec_data['id']}/reconsider",
        json={
            "appeal_petition_reference": "SAC-PETITION-2026-00441",
            "appeal_reason": "Institution disputes the conditional deadline on fire clearance due to state municipal strike.",
        },
        headers={"Authorization": f"Bearer {ro_token}"},
    )
    assert reconsider_res.status_code == 200
    assert reconsider_res.json()["is_reconsidered"] is True
    assert reconsider_res.json()["reconsideration_reference"] == "SAC-PETITION-2026-00441"

    # Application state must now be APPELLATE_REVIEW
    await db_session.refresh(app)
    assert app.current_status == "APPELLATE_REVIEW"
