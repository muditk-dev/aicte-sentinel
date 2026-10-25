import json
from typing import List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.evc import Expert
from app.models.institution import Institution
from app.models.application import Application
from app.core.exceptions import NotFoundError

POLICY_VERSION = "APH-2026-COI-V1.0"


class ConflictChecker:
    @staticmethod
    async def evaluate_conflict(
        db: AsyncSession,
        expert_id: str,
        application_id: str,
    ) -> Tuple[bool, bool, List[str], str, Institution]:
        """
        Evaluates potential statutory and ethical conflicts of interest between an expert
        and the applicant institution.
        
        Returns:
            (has_conflict, is_blocked, reasons, policy_version, institution)
        """
        # Fetch expert
        expert = await db.get(Expert, expert_id)
        if not expert:
            raise NotFoundError("Expert", expert_id)

        # Fetch application & institution
        stmt = select(Application).where(Application.id == application_id)
        result = await db.execute(stmt)
        application = result.scalar_one_or_none()
        if not application:
            raise NotFoundError("Application", application_id)

        institution = await db.get(Institution, application.institution_id)
        if not institution:
            raise NotFoundError("Institution", application.institution_id)

        reasons: List[str] = []

        # 1. Direct Institution Affiliation Check
        try:
            affiliations = json.loads(expert.affiliated_institution_ids_json or "[]")
        except Exception:
            affiliations = []

        if institution.id in affiliations or institution.code in affiliations:
            reasons.append(
                f"Direct affiliation declared: Expert has past or active association with {institution.name} ({institution.code})."
            )

        # 2. Geographic District Rule (APH Statutory Rule: Experts cannot inspect institutions in home district)
        if (
            expert.district
            and institution.district
            and expert.district.strip().lower() == institution.district.strip().lower()
            and (expert.state or "").strip().lower() == (institution.state or "").strip().lower()
        ):
            reasons.append(
                f"Mandatory geographic conflict: Expert resides or is based in '{expert.district}', matching applicant institution's district ({institution.district})."
            )

        # 3. Alma Mater Rule
        if expert.alma_mater and (
            expert.alma_mater.strip().lower() in institution.name.strip().lower()
            or institution.name.strip().lower() in expert.alma_mater.strip().lower()
        ):
            reasons.append(
                f"Alma mater conflict: Expert graduated from or holds declared alumni status at '{expert.alma_mater}'."
            )

        # 4. Explicit Conflict Declarations
        try:
            declarations = json.loads(expert.conflict_declarations_json or "[]")
        except Exception:
            declarations = []

        for dec in declarations:
            dec_lower = dec.lower()
            if institution.name.lower() in dec_lower or institution.code.lower() in dec_lower:
                reasons.append(f"Explicit declaration on record: {dec}")

        has_conflict = len(reasons) > 0
        # Under APH 2026, all detected conflicts are mandatory blocking conflicts unless documented reviewer override applies
        is_blocked = has_conflict

        return has_conflict, is_blocked, reasons, POLICY_VERSION, institution
