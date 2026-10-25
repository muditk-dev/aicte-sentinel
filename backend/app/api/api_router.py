from fastapi import APIRouter
from app.api.v1.health import router as health_router
from app.api.v1.auth import router as auth_router
from app.api.v1.institutions import router as institutions_router
from app.api.v1.workflows import router as workflows_router
from app.api.v1.applications import router as applications_router
from app.api.v1.audit import router as audit_router

api_router = APIRouter()

# Diagnostics & Probes (also accessible at root /api/health and /api/ready)
api_router.include_router(health_router)

# Domain Routers
api_router.include_router(auth_router)
api_router.include_router(institutions_router)
api_router.include_router(workflows_router)
api_router.include_router(applications_router)
api_router.include_router(audit_router)
