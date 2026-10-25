import json
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.exceptions import NotFoundError, PermissionDeniedError
from app.models.application import Application
from app.models.institution import Institution
from app.models.intelligence import DelayRiskPrediction, ModelVersion
from app.models.user import User
from app.security.dependencies import get_current_user, require_roles
from app.schemas.intelligence import (
    DelayRiskPredictionResponse,
    FactorAttributionResponse,
    ModelVersionResponse,
    RiskOverviewItem,
)
from app.intelligence.delay_predictor import DelayPredictorService

router = APIRouter(prefix="/intelligence", tags=["Compliance & Risk Intelligence"])


def _serialize_prediction(p: DelayRiskPrediction) -> DelayRiskPredictionResponse:
    factors: List[FactorAttributionResponse] = []
    try:
        raw_factors = json.loads(p.factor_attributions_json or "[]")
        for f in raw_factors:
            factors.append(
                FactorAttributionResponse(
                    factor=f.get("factor", ""),
                    display_name=f.get("display_name", f.get("factor", "")),
                    impact=f.get("impact", "INCREASES_RISK"),
                    weight=f.get("weight", 0.0),
                    observed_value=f.get("observed_value", ""),
                    description=f.get("description", ""),
                )
            )
    except Exception:
        pass

    return DelayRiskPredictionResponse(
        id=p.id,
        application_id=p.application_id,
        model_version_id=p.model_version_id,
        risk_score=p.risk_score,
        risk_category=p.risk_category,
        estimated_delay_days=p.estimated_delay_days,
        confidence_score=p.confidence_score,
        factor_attributions=factors,
        is_automated_advisory=p.is_automated_advisory,
        advisory_notes=p.advisory_notes,
        created_at=p.created_at,
    )


@router.get("/risk/{application_id}", response_model=DelayRiskPredictionResponse)
async def get_application_delay_risk(
    application_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get explainable delay-risk prediction for an application.
    If no prediction exists yet, computes a fresh prediction.
    Enforces multi-tenant institutional isolation.
    """
    app_stmt = select(Application).where(Application.id == application_id)
    app_res = await db.execute(app_stmt)
    application = app_res.scalar_one_or_none()
    if not application:
        raise NotFoundError("Application", application_id)

    # Multi-tenant boundary
    user_role_codes = [r.code for r in current_user.roles]
    if "INSTITUTION_USER" in user_role_codes or "INSTITUTION_ADMIN" in user_role_codes:
        if current_user.institution_id != application.institution_id:
            raise PermissionDeniedError("Cannot inspect delay risk for another institution's application")

    service = DelayPredictorService(db)
    prediction = await service.get_latest_prediction(application_id)
    if not prediction:
        prediction = await service.predict_for_application(application_id)

    return _serialize_prediction(prediction)


@router.post("/risk/{application_id}/recompute", response_model=DelayRiskPredictionResponse)
async def recompute_application_delay_risk(
    application_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("SCRUTINY_OFFICER", "REGIONAL_OFFICER", "ADMIN")),
):
    """
    Recompute delay-risk prediction with latest workflow and deficiency state.
    Authorized regulatory officers only.
    """
    service = DelayPredictorService(db)
    prediction = await service.predict_for_application(application_id)
    return _serialize_prediction(prediction)


@router.get("/overview", response_model=List[RiskOverviewItem])
async def get_risk_overview(
    region: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("SCRUTINY_OFFICER", "REGIONAL_OFFICER", "EXECUTIVE_COMMITTEE", "ADMIN")),
):
    """
    Regional & Central Risk Intelligence Overview:
    Aggregates active pipeline applications with risk scores, categories, and bottleneck factors.
    """
    stmt = (
        select(Application, Institution)
        .join(Institution, Application.institution_id == Institution.id)
        .where(Application.current_status.notin_(["APPROVED", "REJECTED", "WITHDRAWN"]))
    )
    if region:
        stmt = stmt.where(Institution.region == region)
    if status:
        stmt = stmt.where(Application.current_status == status)

    res = await db.execute(stmt)
    rows = res.all()

    service = DelayPredictorService(db)
    items: List[RiskOverviewItem] = []

    for app, inst in rows:
        # Check if score is cached
        score = app.delay_risk_score if app.delay_risk_score is not None else 0.15
        cat = "LOW"
        if score >= 0.75:
            cat = "CRITICAL"
        elif score >= 0.50:
            cat = "HIGH"
        elif score >= 0.25:
            cat = "MEDIUM"

        est_delay = round(score * 20.0, 1)

        top_factor = None
        try:
            factors = json.loads(app.delay_risk_factors_json or "[]")
            if factors:
                top_factor = factors[0].get("display_name", factors[0].get("factor"))
        except Exception:
            pass

        items.append(
            RiskOverviewItem(
                application_id=app.id,
                application_number=app.application_number,
                institution_name=inst.name,
                region=inst.region,
                current_status=app.current_status,
                risk_score=score,
                risk_category=cat,
                estimated_delay_days=est_delay,
                top_factor=top_factor,
            )
        )

    # Sort critical risk first
    items.sort(key=lambda x: x.risk_score, reverse=True)
    return items


@router.get("/models", response_model=List[ModelVersionResponse])
async def list_model_versions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List registered machine learning / delay-risk model versions with training transparency and metrics.
    """
    service = DelayPredictorService(db)
    await service.get_or_create_model_version()
    models = await service.list_model_versions()

    results: List[ModelVersionResponse] = []
    for m in models:
        features = []
        metrics = {}
        try:
            features = json.loads(m.features_json or "[]")
            metrics = json.loads(m.metrics_json or "{}")
        except Exception:
            pass

        results.append(
            ModelVersionResponse(
                id=m.id,
                name=m.name,
                version_tag=m.version_tag,
                algorithm=m.algorithm,
                features=features,
                metrics=metrics,
                training_dataset_summary=m.training_dataset_summary,
                is_active=m.is_active,
                description=m.description,
                created_at=m.created_at,
            )
        )
    return results
