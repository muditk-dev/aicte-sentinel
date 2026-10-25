import asyncio
import json
import uuid
import sys
import os
from datetime import datetime, timedelta, timezone

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import AsyncSessionLocal, init_db
from app.core.config import settings
from app.models.institution import Institution
from app.models.user import User, Role, Permission
from app.models.workflow import WorkflowTemplate, WorkflowVersion
from app.models.application import Application, ApplicationEvent
from app.models.document import Document, DocumentVersion, ScrutinyFinding
from app.models.deficiency import DeficiencyNotice, DeficiencyItem, DeficiencyResponse, Notification
from app.security.password import hash_password
from app.workflows.engine import DEFAULT_STATE_MACHINE
from app.audit.service import record_audit_event
from app.storage.service import storage_service


async def seed():
    print("Initializing database tables...")
    await init_db()

    async with AsyncSessionLocal() as db:
        print("Checking if database is already seeded...")
        stmt = select(User).where(User.email == settings.SEED_SUPERADMIN_EMAIL)
        existing_admin = (await db.execute(stmt)).scalar_one_or_none()
        if existing_admin:
            # Check if documents exist, if not seed documents & deficiencies
            doc_check = (await db.execute(select(Document).limit(1))).scalar_one_or_none()
            if doc_check:
                print("Database already contains seed data and documents. Skipping seed.")
                return

        print("Seeding statutory permissions and roles...")
        permissions_data = [
            ("app:create", "Create Application", "Ability to submit initial statutory applications"),
            ("app:view", "View Application", "Ability to inspect applications within tenant context"),
            ("scrutiny:execute", "Perform Scrutiny", "Review academic, physical, and financial documents"),
            ("evc:inspect", "Conduct EVC Inspection", "Submit physical/virtual inspection reports"),
            ("decision:grant", "Grant Statutory Approval", "Authorized signatory for approvals and rejections"),
            ("audit:inspect", "Inspect Audit Ledger", "Verify cryptographic audit chain"),
            ("policy:configure", "Configure APH Rules", "Maker-checker policy management"),
        ]

        perm_map = {}
        for code, name, desc in permissions_data:
            perm = Permission(code=code, name=name, description=desc)
            db.add(perm)
            perm_map[code] = perm

        await db.flush()

        # Roles
        roles_data = [
            ("SUPER_ADMIN", "Central AICTE Administrator", "Full statutory governance over all national jurisdictions", list(perm_map.values())),
            ("REGIONAL_OFFICER", "Regional Office Director", "Jurisdiction over regional institutional dockets", [perm_map["app:view"], perm_map["scrutiny:execute"], perm_map["decision:grant"], perm_map["audit:inspect"]]),
            ("SCRUTINY_OFFICER", "Scrutiny Officer", "Scrutiny and deficiency cycle authority", [perm_map["app:view"], perm_map["scrutiny:execute"]]),
            ("EVC_EXPERT", "EVC Expert Committee Member", "On-site and hybrid verification expert", [perm_map["app:view"], perm_map["evc:inspect"]]),
            ("INSTITUTION_ADMIN", "Institution Authorized Signatory", "Institutional representative for applications and replies", [perm_map["app:create"], perm_map["app:view"]]),
        ]

        role_map = {}
        for code, name, desc, perms in roles_data:
            role = Role(code=code, name=name, description=desc, permissions=perms)
            db.add(role)
            role_map[code] = role

        await db.flush()

        print("Seeding sample technical institutions...")
        inst1 = Institution(
            name="Delhi Institute of Technology & Management",
            code="1-10029384",
            region="Northern",
            state="Delhi",
            district="North West Delhi",
            institution_type="Government-Aided",
            established_year=2008,
            status="ACTIVE",
            contact_email="director@ditm-delhi.edu.in",
            contact_phone="+91-11-27891234",
            address="Sector 14, Institutional Area, Rohini, New Delhi 110085",
        )
        inst2 = Institution(
            name="Maharashtra College of Engineering & Emerging Technologies",
            code="1-20038475",
            region="Western",
            state="Maharashtra",
            district="Pune",
            institution_type="Private-Self Financed",
            established_year=2014,
            status="ACTIVE",
            contact_email="principal@mcoe-pune.ac.in",
            contact_phone="+91-20-25678901",
            address="Survey No. 42, Hinjawadi Phase 2, Pune 411057",
        )
        inst3 = Institution(
            name="Karnataka Institute of Artificial Intelligence & Robotics",
            code="1-30049586",
            region="South-Western",
            state="Karnataka",
            district="Bengaluru Urban",
            institution_type="Private-Self Financed",
            established_year=2021,
            status="ACTIVE",
            contact_email="dean@kiai-bengaluru.edu.in",
            contact_phone="+91-80-28456789",
            address="Whitefield Tech Corridor, Bengaluru 560066",
        )
        db.add_all([inst1, inst2, inst3])
        await db.flush()

        print("Seeding demo users across statutory roles...")
        users = [
            User(
                email=settings.SEED_SUPERADMIN_EMAIL,
                hashed_password=hash_password(settings.SEED_SUPERADMIN_PASSWORD),
                full_name="Dr. Rajesh V. Sharma",
                designation="Member Secretary, Central Council",
                roles=[role_map["SUPER_ADMIN"]],
            ),
            User(
                email="ro.delhi@aicte-india.org",
                hashed_password=hash_password("Regional@2026!"),
                full_name="Prof. Anita Deshmukh",
                designation="Regional Officer, Northern Region",
                assigned_region="Northern",
                roles=[role_map["REGIONAL_OFFICER"]],
            ),
            User(
                email="scrutiny.lead@aicte-india.org",
                hashed_password=hash_password("Scrutiny@2026!"),
                full_name="Shri K. Sundaram",
                designation="Senior Scrutiny Officer",
                assigned_region="Northern",
                roles=[role_map["SCRUTINY_OFFICER"]],
            ),
            User(
                email="evc.prof@iitd.ac.in",
                hashed_password=hash_password("Expert@2026!"),
                full_name="Prof. Manas Ranjan Pradhan",
                designation="EVC Committee Chairperson",
                roles=[role_map["EVC_EXPERT"]],
            ),
            User(
                email="director@ditm-delhi.edu.in",
                hashed_password=hash_password("College@2026!"),
                full_name="Dr. Sunita Aggarwal",
                designation="Director / Authorized Signatory",
                institution_id=inst1.id,
                roles=[role_map["INSTITUTION_ADMIN"]],
            ),
        ]
        db.add_all(users)
        await db.flush()

        print("Seeding statutory workflow templates & published APH versions...")
        tmpl1 = WorkflowTemplate(
            code="EXTENSION_OF_APPROVAL",
            name="Extension of Approval (EoA) 2026-27",
            description="Annual extension of approval for existing technical institutions under Chapter I of APH.",
            category="Engineering & Technology",
            is_active=True,
        )
        tmpl2 = WorkflowTemplate(
            code="NEW_INSTITUTION",
            name="Establishment of New Technical Institution",
            description="Statutory approval for setting up a greenfield technical institute under Chapter II of APH.",
            category="Multi-Disciplinary",
            is_active=True,
        )
        tmpl3 = WorkflowTemplate(
            code="NEW_PROGRAM_EMERGING_TECH",
            name="Introduction of Emerging Tech Programs & Supernumerary Seats",
            description="Addition of AI/ML, Data Science, VLSI Design, and Industry 4.0 courses under Chapter III of APH.",
            category="Emerging Technologies",
            is_active=True,
        )
        db.add_all([tmpl1, tmpl2, tmpl3])
        await db.flush()

        version1 = WorkflowVersion(
            template_id=tmpl1.id,
            version_number=1,
            aph_edition="APH 2026-27",
            state_machine_json=json.dumps(DEFAULT_STATE_MACHINE),
            checklist_rules_json=json.dumps({
                "mandatory_documents": [
                    "Land Title & Conversion Certificate",
                    "Building Plan & Occupancy Certificate",
                    "Faculty Roster with Cadre Ratio (1:20)",
                    "FDR / Corpus Deposit Verification",
                    "AICTE Barrier-Free Ramp & Specially Abled Facilities"
                ],
                "minimum_land_acres": 2.5,
                "library_titles_minimum": 5000
            }),
            is_published=True,
            proposed_by_user_id=users[0].id,
            approved_by_user_id=users[0].id,
            approval_timestamp="2026-09-01T10:00:00Z",
        )
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
                    "Fire Safety NOC & Environmental Clearance"
                ],
                "minimum_land_acres": 7.5,
                "initial_fund_deposit_lakhs": 100
            }),
            is_published=True,
            proposed_by_user_id=users[0].id,
            approved_by_user_id=users[0].id,
            approval_timestamp="2026-09-01T10:00:00Z",
        )
        db.add_all([version1, version2])
        await db.flush()

        print("Seeding sample applications with timeline history...")
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
            applicant_user_id=users[4].id,
            assigned_scrutiny_officer_id=users[2].id,
            assigned_regional_officer_id=users[1].id,
            delay_risk_score=0.22,
            delay_risk_factors_json=json.dumps([
                {"factor": "Faculty Cadre Ratio", "impact": "LOW", "detail": "Assistant Professor to Professor ratio is 1:2.8 (Threshold 1:3)"},
                {"factor": "Regional Scrutiny Queue", "impact": "MEDIUM", "detail": "Northern Region scrutiny processing latency averaging 4.2 days"}
            ]),
        )
        app2 = Application(
            application_number="AICTE-2026-NEW-99341",
            institution_id=inst2.id,
            template_id=tmpl2.id,
            version_id=version2.id,
            current_status="SUBMITTED",
            academic_year="2026-2027",
            submission_data_json=json.dumps({
                "proposed_intake": 300,
                "programs": ["Artificial Intelligence & Machine Learning", "Data Science & Cyber Physical Systems"],
                "total_builtup_area_sqm": 8500,
            }),
            submission_date="2026-10-20T09:15:00Z",
            sla_deadline="2026-12-01T18:00:00Z",
            applicant_user_id=users[0].id,
            assigned_regional_officer_id=users[1].id,
            delay_risk_score=0.68,
            delay_risk_factors_json=json.dumps([
                {"factor": "Land Conversion Verification Pending", "impact": "HIGH", "detail": "District revenue certificate pending digital signature verification"},
                {"factor": "New Greenfield Entity", "impact": "MEDIUM", "detail": "Mandatory physical EVC required under Chapter II"}
            ]),
        )
        db.add_all([app1, app2])
        await db.flush()

        # Application Timeline Events
        ev1 = ApplicationEvent(
            application_id=app1.id,
            actor_id=users[4].id,
            event_type="SUBMISSION",
            from_status="DRAFT",
            to_status="SUBMITTED",
            remarks="Application formally submitted with statutory portal fee.",
        )
        ev2 = ApplicationEvent(
            application_id=app1.id,
            actor_id=users[1].id,
            event_type="ASSIGNMENT",
            from_status="SUBMITTED",
            to_status="UNDER_SCRUTINY",
            remarks="Docket allocated to Senior Scrutiny Desk (Northern Region).",
        )
        db.add_all([ev1, ev2])
        await db.flush()

        print("Seeding sample documents with physical files in vault...")
        # Create sample PDF byte payloads
        pdf_bytes = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj 3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000052 00000 n \n0000000102 00000 n \ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n178\n%%EOF"
        import hashlib
        pdf_hash = hashlib.sha256(pdf_bytes).hexdigest()

        key1 = f"app_{app1.id}/land_title_deed.pdf"
        key2 = f"app_{app1.id}/building_occupancy.pdf"
        key3 = f"app_{app1.id}/faculty_roster.pdf"

        # Save to local vault
        await storage_service.save_quarantine(key1, pdf_bytes)
        await storage_service.move_to_vault(key1)

        await storage_service.save_quarantine(key2, pdf_bytes)
        await storage_service.move_to_vault(key2)

        await storage_service.save_quarantine(key3, pdf_bytes)
        await storage_service.move_to_vault(key3)

        doc1 = Document(
            application_id=app1.id,
            institution_id=inst1.id,
            category="Land Title & Conversion Certificate",
            original_filename="Registered_Sale_Deed_Delhi_SubRegistrar.pdf",
            storage_key=key1,
            mime_type="application/pdf",
            file_size=len(pdf_bytes),
            sha256_hash=pdf_hash,
            uploaded_by_user_id=users[4].id,
            scan_status="ACCEPTED",
            scan_result_details="ClamAV Verified: Clean payload",
            scan_timestamp="2026-10-12T14:35:00Z",
            verification_status="ACCEPTED",
            current_version=1,
            is_active=True,
        )
        doc2 = Document(
            application_id=app1.id,
            institution_id=inst1.id,
            category="Building Plan & Occupancy Certificate",
            original_filename="Municipal_Corporation_Delhi_Occupancy.pdf",
            storage_key=key2,
            mime_type="application/pdf",
            file_size=len(pdf_bytes),
            sha256_hash=pdf_hash,
            uploaded_by_user_id=users[4].id,
            scan_status="ACCEPTED",
            scan_result_details="ClamAV Verified: Clean payload",
            scan_timestamp="2026-10-12T14:36:00Z",
            verification_status="ACCEPTED",
            current_version=1,
            is_active=True,
        )
        doc3 = Document(
            application_id=app1.id,
            institution_id=inst1.id,
            category="Faculty Roster with Cadre Ratio",
            original_filename="Faculty_List_AICTE_Format.pdf",
            storage_key=key3,
            mime_type="application/pdf",
            file_size=len(pdf_bytes),
            sha256_hash=pdf_hash,
            uploaded_by_user_id=users[4].id,
            scan_status="ACCEPTED",
            scan_result_details="ClamAV Verified: Clean payload",
            scan_timestamp="2026-10-12T14:37:00Z",
            verification_status="DEFICIENT",
            current_version=1,
            is_active=True,
        )
        db.add_all([doc1, doc2, doc3])
        await db.flush()

        ver1 = DocumentVersion(
            document_id=doc1.id,
            version_number=1,
            storage_key=key1,
            sha256_hash=pdf_hash,
            file_size=len(pdf_bytes),
            uploaded_by_user_id=users[4].id,
            scan_status="ACCEPTED",
        )
        ver2 = DocumentVersion(
            document_id=doc2.id,
            version_number=1,
            storage_key=key2,
            sha256_hash=pdf_hash,
            file_size=len(pdf_bytes),
            uploaded_by_user_id=users[4].id,
            scan_status="ACCEPTED",
        )
        ver3 = DocumentVersion(
            document_id=doc3.id,
            version_number=1,
            storage_key=key3,
            sha256_hash=pdf_hash,
            file_size=len(pdf_bytes),
            uploaded_by_user_id=users[4].id,
            scan_status="ACCEPTED",
        )
        db.add_all([ver1, ver2, ver3])
        await db.flush()

        print("Seeding scrutiny findings...")
        finding1 = ScrutinyFinding(
            application_id=app1.id,
            document_id=doc1.id,
            category=doc1.category,
            officer_id=users[2].id,
            finding_status="ACCEPTED",
            reason="Verified against Sub-Registrar record. Land area 3.2 acres exceeds 2.5 acre norm.",
            notes="No encumbrances found.",
        )
        finding2 = ScrutinyFinding(
            application_id=app1.id,
            document_id=doc3.id,
            category=doc3.category,
            officer_id=users[2].id,
            finding_status="DEFICIENT",
            reason="Cadre ratio for Professors is deficient in Electronics & VLSI branch.",
            notes="Requires 2 Professors; only 1 Professor and 3 Associate Professors listed.",
        )
        db.add_all([finding1, finding2])
        await db.flush()

        print("Seeding formal statutory deficiency notice...")
        now = datetime.now(timezone.utc)
        notice1 = DeficiencyNotice(
            notice_number="DEF-2026-0001",
            application_id=app1.id,
            institution_id=inst1.id,
            issuing_officer_id=users[2].id,
            status="ISSUED",
            due_date=now + timedelta(days=7),
            officer_remarks="The following statutory non-compliances were identified during scrutiny under APH 2026-27 Chapter I.",
            issued_at=now - timedelta(days=2),
        )
        db.add(notice1)
        await db.flush()

        item1 = DeficiencyItem(
            notice_id=notice1.id,
            document_id=doc3.id,
            requirement_title="Faculty Cadre Ratio Shortfall in ECE/VLSI",
            description="Cadre ratio does not fulfill AICTE Norm 1:2:6 (Professor: Associate Professor: Assistant Professor).",
            required_corrective_action="Submit appointment letter and joining report for 1 additional Professor with PhD in VLSI.",
            item_status="PENDING",
        )
        item2 = DeficiencyItem(
            notice_id=notice1.id,
            document_id=None,
            requirement_title="Specially-Abled Barrier-Free Accessibility Verification",
            description="Ramp slope test certificate from chartered architect missing.",
            required_corrective_action="Upload certificate confirming 1:12 slope ramp and dedicated lift accessibility.",
            item_status="PENDING",
        )
        db.add_all([item1, item2])
        await db.flush()

        print("Seeding in-app notifications...")
        notif1 = Notification(
            institution_id=inst1.id,
            title=f"Statutory Deficiency Notice Issued: {notice1.notice_number}",
            message=f"Deficiencies flagged in application {app1.application_number}. Statutory cure deadline: {(now + timedelta(days=5)).strftime('%d-%b-%Y')}.",
            category="DEFICIENCY_ISSUED",
            link_url=f"/applications/{app1.id}",
            is_read=False,
            dedup_key=f"notice_issued_{notice1.id}",
        )
        db.add(notif1)

        print("Recording tamper-evident audit trail entries...")
        await record_audit_event(
            db=db,
            actor_id=users[0].id,
            action="SYSTEM_INITIALIZE",
            resource_type="System",
            resource_id="ROOT",
            details={"version": "1.0.0", "edition": "APH 2026-27"},
        )
        await record_audit_event(
            db=db,
            actor_id=users[4].id,
            action="SUBMIT_APPLICATION",
            resource_type="Application",
            resource_id=app1.id,
            details={"application_number": app1.application_number, "status": "SUBMITTED"},
        )
        await record_audit_event(
            db=db,
            actor_id=users[4].id,
            action="DOCUMENT_UPLOAD_AND_SCAN",
            resource_type="Document",
            resource_id=doc1.id,
            details={"category": doc1.category, "scan_status": "ACCEPTED"},
        )
        await record_audit_event(
            db=db,
            actor_id=users[2].id,
            action="RECORD_SCRUTINY_FINDING",
            resource_type="ScrutinyFinding",
            resource_id=finding1.id,
            details={"category": doc1.category, "status": "ACCEPTED"},
        )
        await record_audit_event(
            db=db,
            actor_id=users[2].id,
            action="ISSUE_DEFICIENCY_NOTICE",
            resource_type="DeficiencyNotice",
            resource_id=notice1.id,
            details={"notice_number": notice1.notice_number},
        )

        await db.commit()
        print("Deterministic synthetic seed data generated successfully!")


if __name__ == "__main__":
    asyncio.run(seed())
