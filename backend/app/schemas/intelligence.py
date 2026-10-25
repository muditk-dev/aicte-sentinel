from typing import List, Optional, Any, Dict
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class FactorAttributionResponse(BaseModel):
    factor: str
    display_name: str
    impact: str  # INCREASES_RISK or REDUCES_RISK
    weight: float
    observed_value: str
    description: str


class DelayRiskPredictionResponse(BaseModel):
    id: str
    application_id: str
    model_version_id: Optional[str] = None
    risk_score: float
    risk_category: str
    estimated_delay_days: float
    confidence_score: float
    factor_attributions: List[FactorAttributionResponse] = Field(default_factory=list)
    is_automated_advisory: bool = True
    advisory_notes: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ModelVersionResponse(BaseModel):
    id: str
    name: str
    version_tag: str
    algorithm: str
    features: List[str] = Field(default_factory=list)
    metrics: Dict[str, Any] = Field(default_factory=dict)
    training_dataset_summary: str
    is_active: bool
    description: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RiskOverviewItem(BaseModel):
    application_id: str
    application_number: str
    institution_name: str
    region: str
    current_status: str
    risk_score: float
    risk_category: str
    estimated_delay_days: float
    top_factor: Optional[str] = None
