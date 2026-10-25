from typing import List, Optional, Any, Dict
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class APHCitation(BaseModel):
    clause_number: str
    clause_title: str
    chapter_number: int
    chapter_title: str
    page_number: int
    norm_category: str
    relevance_score: float
    quote_excerpt: str


class APHClauseResponse(BaseModel):
    id: str
    source_id: str
    chapter_number: int
    chapter_title: str
    clause_number: str
    clause_title: str
    page_number: int
    content_text: str
    norm_category: str

    model_config = ConfigDict(from_attributes=True)


class APHSourceDocumentResponse(BaseModel):
    id: str
    title: str
    edition: str
    official_reference_url: Optional[str] = None
    sha256_hash: str
    total_chapters: int
    total_clauses: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class APHQueryRequest(BaseModel):
    query_text: str = Field(..., min_length=3, max_length=1500, description="Regulatory question regarding APH 2026-27 norms")


class APHQueryResponse(BaseModel):
    id: str
    user_id: str
    institution_id: Optional[str] = None
    query_text: str
    response_text: str
    citations: List[APHCitation] = Field(default_factory=list)
    retrieval_mode: str
    is_automated_advisory: bool = True
    uncertainty_warning: Optional[str] = None
    feedback_rating: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class APHFeedbackRequest(BaseModel):
    rating: int = Field(..., description="1 for helpful, -1 for unhelpful")
