from fastapi import APIRouter
from app.api.v1.health import router as health_router
from app.api.v1.auth import router as auth_router
from app.api.v1.institutions import router as institutions_router
from app.api.v1.workflows import router as workflows_router
from app.api.v1.applications import router as applications_router
from app.api.v1.audit import router as audit_router
from app.api.v1.documents import router as documents_router
from app.api.v1.scrutiny import router as scrutiny_router
from app.api.v1.deficiencies import router as deficiencies_router
from app.api.v1.notifications import router as notifications_router
from app.api.v1.experts import router as experts_router
from app.api.v1.inspections import router as inspections_router
from app.api.v1.committees import router as committees_router
from app.api.v1.hearings import router as hearings_router
from app.api.v1.decisions import router as decisions_router
from app.api.v1.intelligence import router as intelligence_router
from app.api.v1.ocr import router as ocr_router
from app.api.v1.aph import router as aph_router
from app.api.v1.compliance import router as compliance_router

api_router = APIRouter()

# Diagnostics & Probes (also accessible at root /api/health and /api/ready)
api_router.include_router(health_router)

# Domain Routers
api_router.include_router(auth_router)
api_router.include_router(institutions_router)
api_router.include_router(workflows_router)
api_router.include_router(applications_router)
api_router.include_router(documents_router)
api_router.include_router(scrutiny_router)
api_router.include_router(deficiencies_router)
api_router.include_router(notifications_router)
api_router.include_router(experts_router)
api_router.include_router(inspections_router)
api_router.include_router(committees_router)
api_router.include_router(hearings_router)
api_router.include_router(decisions_router)
api_router.include_router(intelligence_router)
api_router.include_router(ocr_router)
api_router.include_router(aph_router)
api_router.include_router(compliance_router)
api_router.include_router(audit_router)
