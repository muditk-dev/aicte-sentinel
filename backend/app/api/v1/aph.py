import json
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.aph import APHAssistantQuery, APHSourceDocument, APHClause
from app.models.user import User
from app.security.dependencies import get_current_user
from app.schemas.aph import (
    APHQueryRequest,
    APHQueryResponse,
    APHCitation,
    APHSourceDocumentResponse,
    APHClauseResponse,
    APHFeedbackRequest,
)
from app.intelligence.aph_service import APHAssistantService

router = APIRouter(prefix="/aph", tags=["APH Grounded Regulatory Assistant"])


def _serialize_query(q: APHAssistantQuery) -> APHQueryResponse:
    citations: List[APHCitation] = []
    try:
        raw_cits = json.loads(q.citations_json or "[]")
        for c in raw_cits:
            citations.append(
                APHCitation(
                    clause_number=c.get("clause_number", ""),
                    clause_title=c.get("clause_title", ""),
                    chapter_number=c.get("chapter_number", 1),
                    chapter_title=c.get("chapter_title", ""),
                    page_number=c.get("page_number", 1),
                    norm_category=c.get("norm_category", "GENERAL"),
                    relevance_score=c.get("relevance_score", 0.0),
                    quote_excerpt=c.get("quote_excerpt", ""),
                )
            )
    except Exception:
        pass

    return APHQueryResponse(
        id=q.id,
        user_id=q.user_id,
        institution_id=q.institution_id,
        query_text=q.query_text,
        response_text=q.response_text,
        citations=citations,
        retrieval_mode=q.retrieval_mode,
        is_automated_advisory=q.is_automated_advisory,
        uncertainty_warning=q.uncertainty_warning,
        feedback_rating=q.feedback_rating,
        created_at=q.created_at,
    )


@router.post("/ask", response_model=APHQueryResponse)
async def ask_aph_assistant(
    payload: APHQueryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Submit a regulatory question regarding AICTE Approval Process Handbook (APH 2026-27).
    Returns grounded response with exact chapter/clause citations and uncertainty disclaimer.
    """
    service = APHAssistantService(db)
    query_record = await service.ask_assistant(
        user_id=current_user.id,
        query_text=payload.query_text,
        institution_id=current_user.institution_id,
    )
    return _serialize_query(query_record)


@router.get("/sources", response_model=List[APHSourceDocumentResponse])
async def list_aph_sources(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List authoritative APH source documents and editions indexed in the knowledge base.
    """
    service = APHAssistantService(db)
    sources = await service.list_sources()
    return [
        APHSourceDocumentResponse(
            id=s.id,
            title=s.title,
            edition=s.edition,
            official_reference_url=s.official_reference_url,
            sha256_hash=s.sha256_hash,
            total_chapters=s.total_chapters,
            total_clauses=s.total_clauses,
            created_at=s.created_at,
        )
        for s in sources
    ]


@router.get("/clauses", response_model=List[APHClauseResponse])
async def list_aph_clauses(
    category: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List indexed APH clauses, optionally filtered by norm category.
    """
    service = APHAssistantService(db)
    clauses = await service.list_clauses(category=category)
    return [
        APHClauseResponse(
            id=c.id,
            source_id=c.source_id,
            chapter_number=c.chapter_number,
            chapter_title=c.chapter_title,
            clause_number=c.clause_number,
            clause_title=c.clause_title,
            page_number=c.page_number,
            content_text=c.content_text,
            norm_category=c.norm_category,
        )
        for c in clauses
    ]


@router.get("/history", response_model=List[APHQueryResponse])
async def get_query_history(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve user's previous APH assistant queries and responses.
    """
    service = APHAssistantService(db)
    history = await service.list_user_history(user_id=current_user.id, limit=limit)
    return [_serialize_query(q) for q in history]


@router.post("/feedback/{query_id}", response_model=APHQueryResponse)
async def submit_query_feedback(
    query_id: str,
    payload: APHFeedbackRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Submit thumbs up (1) or thumbs down (-1) feedback on an assistant response.
    """
    service = APHAssistantService(db)
    updated = await service.record_feedback(query_id=query_id, rating=payload.rating)
    return _serialize_query(updated)
