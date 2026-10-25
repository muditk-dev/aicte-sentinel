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
api_router.include_router(audit_router)
