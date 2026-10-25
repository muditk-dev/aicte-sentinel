import sys
import os
from pathlib import Path

# Ensure backend directory is in python search path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import asyncio
import json
import hashlib
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models import (
    User,
    Role,
    Permission,
    Institution,
    WorkflowTemplate,
    WorkflowVersion,
    Application,
    ApplicationEvent,
    Document,
    DocumentVersion,
    ScrutinyFinding,
    DeficiencyNotice,
    DeficiencyItem,
    Notification,
    Expert,
    EVCInspection,
    EVCInspectionExpert,
    EVCReportVersion,
    Committee,
    CommitteeMembership,
    Hearing,
    HearingDocket,
    HearingAttendance,
    StatutoryDecision,
    DecisionCondition,
)
from app.workflows.engine import DEFAULT_STATE_MACHINE
from app.security.password import hash_password
from app.audit.service import record_audit_event
from app.storage.service import storage_service


async def seed():
    print("Initiating AICTE Sentinel comprehensive statutory seed sequence...")

    async with AsyncSessionLocal() as db:
        print("Checking if database is already seeded...")
        stmt = select(User).where(User.email == settings.SEED_SUPERADMIN_EMAIL)
        existing_admin = (await db.execute(stmt)).scalar_one_or_none()
        
        # If admin exists, check if experts & decisions exist. If so, skip.
        if existing_admin:
            exp_check = (await db.execute(select(Expert).limit(1))).scalar_one_or_none()
            if exp_check:
                print("Database already contains seed data, experts, and statutory decisions. Skipping seed.")
                return

        print("Seeding statutory permissions and roles...")
        permissions_data = [
            ("app:create", "Create Application", "Ability to submit initial statutory applications"),
            ("app:view", "View Application", "Ability to inspect applications within tenant context"),
            ("scrutiny:execute", "Perform Scrutiny", "Review academic, physical, and financial documents"),
            ("evc:inspect", "Conduct EVC Inspection", "Submit physical/virtual inspection reports"),
            ("committee:manage", "Manage Standing Committees", "Constitute benches and hearing dockets"),
            ("decision:grant", "Grant Statutory Approval", "Authorized signatory for approvals and rejections"),
            ("audit:inspect", "Inspect Audit Ledger", "Verify cryptographic audit chain"),
            ("policy:configure", "Configure APH Rules", "Maker-checker policy management"),
        ]

        perm_map = {}
        for code, name, desc in permissions_data:
            existing_p = (await db.execute(select(Permission).where(Permission.code == code))).scalar_one_or_none()
            if not existing_p:
                perm = Permission(code=code, name=name, description=desc)
                db.add(perm)
                perm_map[code] = perm
            else:
                perm_map[code] = existing_p

        await db.flush()

        # Roles
        roles_data = [
            ("SUPER_ADMIN", "Central AICTE Administrator", "Full statutory governance over all national jurisdictions", list(perm_map.values())),
            ("REGIONAL_OFFICER", "Regional Office Director", "Jurisdiction over regional institutional dockets", [perm_map["app:view"], perm_map["scrutiny:execute"], perm_map["committee:manage"], perm_map["decision:grant"], perm_map["audit:inspect"]]),
            ("SCRUTINY_OFFICER", "Scrutiny Officer", "Scrutiny and deficiency cycle authority", [perm_map["app:view"], perm_map["scrutiny:execute"]]),
            ("EVC_EXPERT", "EVC Expert Committee Member", "On-site and hybrid verification expert", [perm_map["app:view"], perm_map["evc:inspect"]]),
            ("INSTITUTION_ADMIN", "Institution Authorized Signatory", "Institutional representative for applications and replies", [perm_map["app:create"], perm_map["app:view"]]),
        ]

        role_map = {}
        for code, name, desc, perms in roles_data:
            existing_r = (await db.execute(select(Role).where(Role.code == code))).scalar_one_or_none()
            if not existing_r:
                role = Role(code=code, name=name, description=desc, permissions=perms)
                db.add(role)
                role_map[code] = role
            else:
                role_map[code] = existing_r

        await db.flush()

        print("Seeding sample technical institutions...")
        inst1 = (await db.execute(select(Institution).where(Institution.code == "1-109283741"))).scalar_one_or_none()
        if not inst1:
            inst1 = Institution(
                name="Delhi Institute of Technology & Management",
                code="1-109283741",
                region="Northern",
                institution_type="ENGINEERING",
                state="Delhi",
                district="South West Delhi",
                contact_email="admin@ditm-delhi.edu.in",
                contact_phone="+91-11-26781234",
                address="Sector 14, Dwarka, New Delhi 110078",
            )
            db.add(inst1)

        inst2 = (await db.execute(select(Institution).where(Institution.code == "1-884729103"))).scalar_one_or_none()
        if not inst2:
            inst2 = Institution(
                name="Maharashtra Institute of Artificial Intelligence & Robotics",
                code="1-884729103",
                region="Western",
                institution_type="STANDALONE_PG",
                state="Maharashtra",
                district="Pune",
                contact_email="contact@miair-pune.ac.in",
                contact_phone="+91-20-25679812",
                address="Hinjawadi Infotech Park Phase 2, Pune 411057",
            )
            db.add(inst2)

        inst3 = (await db.execute(select(Institution).where(Institution.code == "1-554192847"))).scalar_one_or_none()
        if not inst3:
            inst3 = Institution(
                name="Karnataka Technological Academy",
                code="1-554192847",
                region="South-Western",
                institution_type="POLYTECHNIC",
                state="Karnataka",
                district="Bengaluru Urban",
                contact_email="registrar@kta-bangalore.edu.in",
                contact_phone="+91-80-28456789",
                address="Whitefield Tech Corridor, Bengaluru 560066",
            )
            db.add(inst3)

        await db.flush()

        print("Seeding demo users across statutory roles...")
        user_admin = (await db.execute(select(User).where(User.email == settings.SEED_SUPERADMIN_EMAIL))).scalar_one_or_none()
        if not user_admin:
            user_admin = User(
                email=settings.SEED_SUPERADMIN_EMAIL,
                hashed_password=hash_password(settings.SEED_SUPERADMIN_PASSWORD),
                full_name="Dr. Rajesh V. Sharma",
                designation="Member Secretary, Central Council",
                roles=[role_map["SUPER_ADMIN"]],
            )
            db.add(user_admin)

        user_ro = (await db.execute(select(User).where(User.email == "ro.delhi@aicte-india.org"))).scalar_one_or_none()
        if not user_ro:
            user_ro = User(
                email="ro.delhi@aicte-india.org",
                hashed_password=hash_password("Regional@2026!"),
                full_name="Prof. Anita Deshmukh",
                designation="Regional Officer, Northern Region",
                assigned_region="Northern",
                roles=[role_map["REGIONAL_OFFICER"]],
            )
            db.add(user_ro)

        user_scrutiny = (await db.execute(select(User).where(User.email == "scrutiny.lead@aicte-india.org"))).scalar_one_or_none()
        if not user_scrutiny:
            user_scrutiny = User(
                email="scrutiny.lead@aicte-india.org",
                hashed_password=hash_password("Scrutiny@2026!"),
                full_name="Shri K. Sundaram",
                designation="Senior Scrutiny Officer",
                assigned_region="Northern",
                roles=[role_map["SCRUTINY_OFFICER"]],
            )
            db.add(user_scrutiny)

        user_expert = (await db.execute(select(User).where(User.email == "evc.prof@iitd.ac.in"))).scalar_one_or_none()
        if not user_expert:
            user_expert = User(
                email="evc.prof@iitd.ac.in",
                hashed_password=hash_password("Expert@2026!"),
                full_name="Prof. Manas Ranjan Pradhan",
                designation="EVC Committee Chairperson",
                roles=[role_map["EVC_EXPERT"]],
            )
            db.add(user_expert)

        user_inst = (await db.execute(select(User).where(User.email == "director@ditm-delhi.edu.in"))).scalar_one_or_none()
        if not user_inst:
            user_inst = User(
                email="director@ditm-delhi.edu.in",
                hashed_password=hash_password("College@2026!"),
                full_name="Dr. Sunita Aggarwal",
                designation="Director / Authorized Signatory",
                institution_id=inst1.id,
                roles=[role_map["INSTITUTION_ADMIN"]],
            )
            db.add(user_inst)

        await db.flush()

        print("Seeding statutory workflow templates & published APH versions...")
        tmpl1 = (await db.execute(select(WorkflowTemplate).where(WorkflowTemplate.code == "EXTENSION_OF_APPROVAL"))).scalar_one_or_none()
        if not tmpl1:
            tmpl1 = WorkflowTemplate(
                code="EXTENSION_OF_APPROVAL",
                name="Extension of Approval (EoA) 2026-27",
                description="Annual extension of approval for existing technical institutions under Chapter I of APH.",
                category="Engineering & Technology",
                is_active=True,
            )
            db.add(tmpl1)

        tmpl2 = (await db.execute(select(WorkflowTemplate).where(WorkflowTemplate.code == "NEW_INSTITUTION"))).scalar_one_or_none()
        if not tmpl2:
            tmpl2 = WorkflowTemplate(
                code="NEW_INSTITUTION",
                name="Establishment of New Technical Institution",
                description="Statutory approval for setting up a greenfield technical institute under Chapter II of APH.",
                category="Multi-Disciplinary",
                is_active=True,
            )
            db.add(tmpl2)

        await db.flush()

        version1 = (await db.execute(select(WorkflowVersion).where(WorkflowVersion.template_id == tmpl1.id))).scalar_one_or_none()
        if not version1:
            version1 = WorkflowVersion(
                template_id=tmpl1.id,
                version_number=1,
                aph_edition="APH 2026-27",
                state_machine_json=json.dumps(DEFAULT_STATE_MACHINE),
                checklist_rules_json=json.dumps({
                    "mandatory_documents": [
                        "Land Title Deed / Building Completion Certificate",
                        "Fire Safety & Life Protection NOC",
                        "Faculty Cadre & Bio-metric Roster",
                        "Audited Financial Balance Sheet (Last 3 Years)",
                    ],
                    "faculty_student_ratio": "1:20",
                    "minimum_library_titles": 2500,
                }),
                is_published=True,
                proposed_by_user_id=user_admin.id,
                approved_by_user_id=user_admin.id,
                approval_timestamp="2026-09-01T10:00:00Z",
            )
            db.add(version1)

        version2 = (await db.execute(select(WorkflowVersion).where(WorkflowVersion.template_id == tmpl2.id))).scalar_one_or_none()
        if not version2:
            version2 = WorkflowVersion(
                template_id=tmpl2.id,
                version_number=1,
                aph_edition="APH 2026-27",
                state_machine_json=json.dumps(DEFAULT_STATE_MACHINE),
                checklist_rules_json=json.dumps({
                    "mandatory_documents": [
                        "Registered Sale Deed / Lease Deed (Min 30 Yrs)",
                        "Master Structural Plan approved by Town Planning Authority",
                        "Bank Solvency Certificate from Nationalized Bank",
                        "Fire Safety NOC & Environmental Clearance",
                    ],
                    "minimum_land_acres": 7.5,
                    "initial_fund_deposit_lakhs": 100,
                }),
                is_published=True,
                proposed_by_user_id=user_admin.id,
                approved_by_user_id=user_admin.id,
                approval_timestamp="2026-09-01T10:00:00Z",
            )
            db.add(version2)

        await db.flush()

        print("Seeding sample applications with timeline history...")
        app1 = (await db.execute(select(Application).where(Application.application_number == "AICTE-2026-EOA-10821"))).scalar_one_or_none()
        if not app1:
            app1 = Application(
                application_number="AICTE-2026-EOA-10821",
                institution_id=inst1.id,
                template_id=tmpl1.id,
                version_id=version1.id,
                current_status="UNDER_SCRUTINY",
                academic_year="2026-2027",
                submission_data_json=json.dumps({
                    "proposed_intake": 480,
                    "existing_intake": 420,
                    "programs": ["Computer Science & Engineering", "Electronics & VLSI", "Mechanical Engineering"],
                    "faculty_count": 28,
                }),
                submission_date="2026-10-12T14:30:00Z",
                sla_deadline="2026-11-15T18:00:00Z",
                applicant_user_id=user_inst.id,
                assigned_scrutiny_officer_id=user_scrutiny.id,
                assigned_regional_officer_id=user_ro.id,
                delay_risk_score=0.22,
                delay_risk_factors_json=json.dumps([
                    {"factor": "Faculty Cadre Ratio", "impact": "LOW", "detail": "Assistant Professor to Professor ratio is 1:2.8 (Threshold 1:3)"},
                    {"factor": "Regional Scrutiny Queue", "impact": "MEDIUM", "detail": "Northern Region scrutiny processing latency averaging 4.2 days"},
                ]),
            )
            db.add(app1)

        app2 = (await db.execute(select(Application).where(Application.application_number == "AICTE-2026-NEW-99341"))).scalar_one_or_none()
        if not app2:
            app2 = Application(
                application_number="AICTE-2026-NEW-99341",
                institution_id=inst2.id,
                template_id=tmpl2.id,
                version_id=version2.id,
                current_status="EVC_CONDUCTED",
                academic_year="2026-2027",
                submission_data_json=json.dumps({
                    "proposed_intake": 300,
                    "programs": ["Artificial Intelligence & Machine Learning", "Data Science & Cyber Physical Systems"],
                    "total_builtup_area_sqm": 8500,
                }),
                submission_date="2026-10-20T09:15:00Z",
                sla_deadline="2026-12-01T18:00:00Z",
                applicant_user_id=user_admin.id,
                assigned_regional_officer_id=user_ro.id,
                delay_risk_score=0.35,
                delay_risk_factors_json=json.dumps([
                    {"factor": "Greenfield Entity Verification", "impact": "MEDIUM", "detail": "Physical EVC successfully completed with compliant land title"},
                ]),
            )
            db.add(app2)

        app3 = (await db.execute(select(Application).where(Application.application_number == "AICTE-2026-EOA-77412"))).scalar_one_or_none()
        if not app3:
            app3 = Application(
                application_number="AICTE-2026-EOA-77412",
                institution_id=inst3.id,
                template_id=tmpl1.id,
                version_id=version1.id,
                current_status="APPROVED",
                academic_year="2026-2027",
                submission_data_json=json.dumps({
                    "proposed_intake": 540,
                    "existing_intake": 540,
                    "programs": ["Information Science", "Civil Engineering", "Mechatronics"],
                    "faculty_count": 36,
                }),
                submission_date="2026-10-05T10:00:00Z",
                sla_deadline="2026-11-05T18:00:00Z",
                applicant_user_id=user_admin.id,
                assigned_regional_officer_id=user_ro.id,
                delay_risk_score=0.08,
                delay_risk_factors_json=json.dumps([]),
            )
            db.add(app3)

        await db.flush()

        print("Seeding synthetic experts roster for EVC...")
        exp1 = Expert(
            user_id=user_expert.id,
            name="Dr. Rajiv Raman",
            email="rajiv.raman@iitd.ac.in",
            phone="+91-9811099234",
            designation="Professor of Computer Science & Engineering",
            organization="Indian Institute of Technology Delhi",
            expert_type="ACADEMIC",
            qualifications="Ph.D. in Computer Science (IIT Bombay)",
            experience_years=18,
            specializations_json=json.dumps(["Artificial Intelligence", "Distributed Systems", "Infrastructure Scrutiny"]),
            affiliated_institution_ids_json=json.dumps([inst1.id]),
            alma_mater="IIT Bombay",
            state="Delhi",
            district="South West Delhi",
            is_active=True,
            verification_status="VERIFIED",
            availability_status="AVAILABLE",
            conflict_declarations_json=json.dumps(["Academic Advisory Board Member: Delhi Institute of Technology (2021-2023)"]),
        )
        exp2 = Expert(
            name="Dr. Ananya Sengupta",
            email="ananya.sengupta@vjti.ac.in",
            phone="+91-9820011892",
            designation="Dean of Mechanical Engineering",
            organization="Veermata Jijabai Technological Institute (VJTI) Mumbai",
            expert_type="ACADEMIC",
            qualifications="Ph.D. in Mechanical Systems (IIT Madras)",
            experience_years=22,
            specializations_json=json.dumps(["CAD/CAM", "Robotics Labs", "Workshop Machinery Norms"]),
            affiliated_institution_ids_json=json.dumps([]),
            alma_mater="IIT Madras",
            state="Maharashtra",
            district="Mumbai Suburban",
            is_active=True,
            verification_status="VERIFIED",
            availability_status="AVAILABLE",
            conflict_declarations_json=json.dumps([]),
        )
        exp3 = Expert(
            name="Prof. Vikramaditya Rao",
            email="vikram.rao@bharatsilicon.org",
            phone="+91-9945088219",
            designation="Chief Systems Architect",
            organization="Bharat Silicon Technologies Ltd",
            expert_type="INDUSTRY",
            qualifications="M.Tech in VLSI Systems (IISc Bangalore)",
            experience_years=16,
            specializations_json=json.dumps(["Semiconductor Fab Testing", "High Performance Computing", "Industry 4.0"]),
            affiliated_institution_ids_json=json.dumps([]),
            alma_mater="IISc Bangalore",
            state="Karnataka",
            district="Bengaluru Urban",
            is_active=True,
            verification_status="VERIFIED",
            availability_status="AVAILABLE",
            conflict_declarations_json=json.dumps([]),
        )
        exp4 = Expert(
            name="Dr. Sunita Mehra",
            email="sunita.mehra@annauniv.edu",
            phone="+91-9444077312",
            designation="Professor of Structural Engineering",
            organization="Anna University, Chennai",
            expert_type="ACADEMIC",
            qualifications="Ph.D. in Structural Safety (Anna University)",
            experience_years=20,
            specializations_json=json.dumps(["Built-up Area Scrutiny", "Fire Safety Norms", "Barrier-Free Accessibility"]),
            affiliated_institution_ids_json=json.dumps([]),
            alma_mater="Anna University",
            state="Tamil Nadu",
            district="Chennai",
            is_active=True,
            verification_status="VERIFIED",
            availability_status="AVAILABLE",
            conflict_declarations_json=json.dumps([]),
        )
        db.add_all([exp1, exp2, exp3, exp4])
        await db.flush()

        print("Seeding EVC inspection with verified report for Application 2...")
        insp2 = EVCInspection(
            application_id=app2.id,
            institution_id=inst2.id,
            inspection_number="EVC-AICTE-2026-NEW-99341-001",
            inspection_mode="HYBRID",
            status="ACCEPTED",
            scheduled_start_date="2026-10-22T09:00:00Z",
            scheduled_end_date="2026-10-22T17:00:00Z",
            actual_inspection_date="2026-10-22T16:30:00Z",
            chairperson_id=exp2.id,
            meeting_link="https://meet.aicte-india.org/evc-miair-pune-2026",
            location_coordinates="18.5913, 73.7389",
            location_address="Hinjawadi Infotech Park Phase 2, Pune, Maharashtra",
            assigned_by_user_id=user_ro.id,
        )
        db.add(insp2)
        await db.flush()

        pm1 = EVCInspectionExpert(
            inspection_id=insp2.id,
            expert_id=exp2.id,
            role="CHAIRPERSON",
            conflict_check_passed=True,
            attendance_status="PRESENT",
            attendance_timestamp="2026-10-22T09:05:00Z",
            sign_off_status="SIGNED",
            sign_off_timestamp="2026-10-22T16:45:00Z",
            sign_off_remarks="Inspected laboratory infrastructure and faculty readiness. Fully compliant with Chapter II norms.",
        )
        pm2 = EVCInspectionExpert(
            inspection_id=insp2.id,
            expert_id=exp4.id,
            role="MEMBER",
            conflict_check_passed=True,
            attendance_status="PRESENT",
            attendance_timestamp="2026-10-22T09:10:00Z",
            sign_off_status="SIGNED",
            sign_off_timestamp="2026-10-22T16:40:00Z",
            sign_off_remarks="Verified structural plan and fire safety measures in person.",
        )
        db.add_all([pm1, pm2])
        await db.flush()

        # EVC Report Version 1
        now_iso = datetime.now(timezone.utc).isoformat()
        payload_str = f"{insp2.id}:1:RECOMMENDED:Site inspection verified:2026-10-22T17:00:00Z:{user_expert.id}"
        rep_digest = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()

        rep1 = EVCReportVersion(
            inspection_id=insp2.id,
            version_number=1,
            application_id=app2.id,
            submitted_by_user_id=user_ro.id,
            submitted_at="2026-10-22T17:00:00Z",
            sha256_hash=rep_digest,
            overall_recommendation="RECOMMENDED",
            infrastructure_score=92.5,
            faculty_verification_status="SATISFACTORY",
            land_building_status="SATISFACTORY",
            laboratories_equipment_status="SATISFACTORY",
            safety_and_amenities_status="SATISFACTORY",
            observations="Site verification confirmed 8.5 acres contiguous freehold land, 8,600 sqm constructed academic complex, and 4 advanced AI/Robotics laboratories with calibrated equipment.",
            deficiencies_identified=None,
            checklist_data_json=json.dumps({
                "land_boundary_wall_verified": True,
                "barrier_free_access_verified": True,
                "safety_clearance_valid": True,
                "internet_bandwidth_mbps": 1000,
            }),
            evidence_references_json=json.dumps(["doc_land_deed", "doc_fire_noc", "photo_geo_stamped_main_block"]),
            location_evidence_json=json.dumps({"gps": "18.5913, 73.7389", "time_lock": "2026-10-22T11:45:00Z"}),
            virtual_attendance_json=json.dumps({"platform": "AICTE-SecureMeet", "duration_mins": 380}),
            review_status="ACCEPTED",
            reviewed_by_user_id=user_ro.id,
            reviewed_at="2026-10-23T11:00:00Z",
            review_remarks="EVC report accepted in full. Meets all Chapter II statutory conditions for establishment.",
        )
        db.add(rep1)
        await db.flush()

        print("Seeding Standing Hearing & Standing Appellate Committees...")
        comm1 = Committee(
            code="SHC-NORTH-2026",
            name="Standing Hearing Committee (Northern Region)",
            committee_type="SHC",
            description="Statutory committee for adjudicating institutional representations and deficiency appeals.",
            quorum_required=3,
            is_active=True,
            valid_from="2026-01-01T00:00:00Z",
        )
        comm2 = Committee(
            code="SAC-CENTRAL-2026",
            name="Standing Appellate Committee (Apex Council)",
            committee_type="SAC",
            description="Appellate authority presided over by retired High Court Judge / Senior Academician.",
            quorum_required=3,
            is_active=True,
            valid_from="2026-01-01T00:00:00Z",
        )
        db.add_all([comm1, comm2])
        await db.flush()

        m1 = CommitteeMembership(
            committee_id=comm1.id,
            user_id=user_ro.id,
            member_name="Prof. Anita Deshmukh",
            member_role="CHAIRPERSON",
            conflict_declarations_json=json.dumps([]),
            is_active=True,
        )
        m2 = CommitteeMembership(
            committee_id=comm1.id,
            user_id=user_scrutiny.id,
            member_name="Shri K. Sundaram",
            member_role="MEMBER_SECRETARY",
            conflict_declarations_json=json.dumps([]),
            is_active=True,
        )
        m3 = CommitteeMembership(
            committee_id=comm1.id,
            expert_id=exp4.id,
            member_name="Dr. Sunita Mehra",
            member_role="ACADEMIC_EXPERT",
            conflict_declarations_json=json.dumps([]),
            is_active=True,
        )
        db.add_all([m1, m2, m3])
        await db.flush()

        print("Seeding scheduled SHC hearing session and docket for Application 1...")
        hear1 = Hearing(
            committee_id=comm1.id,
            hearing_number="HEAR-SHC-NORTH-2026-001",
            hearing_type="SHC",
            status="SCHEDULED",
            scheduled_date="2026-11-02T10:30:00Z",
            meeting_mode="HYBRID",
            venue_or_link="AICTE Northern Regional Office, Board Room / Webex",
            agenda="Hearing on Cadre Ratio and Special Accessibility Deficiency Notices.",
            chairperson_name="Prof. Anita Deshmukh",
        )
        db.add(hear1)
        await db.flush()

        docket1 = HearingDocket(
            hearing_id=hear1.id,
            application_id=app1.id,
            institution_id=inst1.id,
            docket_number=f"DKT-{hear1.hearing_number}-{app1.application_number}",
            matter_summary="Institution representation on faculty recruitment timeline for PhD Assistant Professors in VLSI and architect's ramp slope certificate.",
            referred_by="NORTHERN_REGIONAL_OFFICE",
            institutional_representative_name="Dr. Sunita Aggarwal (Director)",
            docket_status="PENDING",
        )
        db.add(docket1)
        await db.flush()

        print("Seeding finalized Statutory Decision for Application 3...")
        dec_str = f"{app3.id}:CONDITIONALLY_APPROVED:Approved based on satisfactory compliance:2026-10-25T12:00:00Z:AICTE-APH-2026-V1"
        dec_attest = hashlib.sha256(dec_str.encode("utf-8")).hexdigest()

        dec1 = StatutoryDecision(
            application_id=app3.id,
            institution_id=inst3.id,
            decision_number="AICTE-DEC-AICTE-2026-EOA-77412-20261025",
            decision_type="CONDITIONALLY_APPROVED",
            academic_year="2026-2027",
            authority_role="REGIONAL_OFFICER",
            authorized_by_user_id=user_ro.id,
            authorized_at="2026-10-25T12:00:00Z",
            governing_policy_version="AICTE-APH-2026-V1",
            reasons="All Chapter I core statutory norms fulfilled. Conditional approval granted subject to submission of updated Fire Safety renewal prior to academic commencement.",
            evidence_references_json=json.dumps(["SCRUTINY-CLEARANCE-77412", "ANNUAL-AUDIT-2025-26"]),
            intake_approved=540,
            valid_for_years=1,
            is_final=True,
            is_reconsidered=False,
            sha256_attestation=dec_attest,
            declaration_text="I, Prof. Anita Deshmukh, Regional Officer, hereby attest and grant statutory conditional approval under the powers vested by the AICTE Act 1987 and APH 2026-27.",
        )
        db.add(dec1)
        await db.flush()

        cond1 = DecisionCondition(
            decision_id=dec1.id,
            condition_code="COND-FIRE-NOC-2026",
            description="Submit renewal certificate of Fire Safety NOC from State Fire Services within 60 days.",
            due_date="2026-12-24T18:00:00Z",
            compliance_status="PENDING",
        )
        db.add(cond1)
        await db.flush()

        print("Recording tamper-evident audit trail entries...")
        await record_audit_event(
            db=db,
            actor_id=user_admin.id,
            action="SYSTEM_INITIALIZE",
            resource_type="System",
            resource_id="ROOT",
            details={"version": "1.0.0", "edition": "APH 2026-27"},
        )
        await record_audit_event(
            db=db,
            actor_id=user_ro.id,
            action="EVC_INSPECTION_COMPLETED",
            resource_type="EVCInspection",
            resource_id=insp2.id,
            details={"inspection_number": insp2.inspection_number, "status": "ACCEPTED"},
        )
        await record_audit_event(
            db=db,
            actor_id=user_ro.id,
            action="STATUTORY_DECISION_CONDITIONALLY_APPROVED",
            resource_type="StatutoryDecision",
            resource_id=dec1.id,
            details={"decision_number": dec1.decision_number, "sha256": dec_attest},
        )

        await db.commit()
        print("Deterministic synthetic seed data generated successfully!")


if __name__ == "__main__":
    asyncio.run(seed())
