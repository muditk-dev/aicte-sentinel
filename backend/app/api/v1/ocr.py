import json
from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.exceptions import NotFoundError, PermissionDeniedError, ValidationError
from app.models.document import Document
from app.models.application import Application
from app.models.ocr import OCRJob, OCRExtractedField
from app.models.user import User
from app.security.dependencies import get_current_user, require_roles
from app.schemas.ocr import (
    OCRJobResponse,
    OCRExtractedFieldResponse,
    OCRFieldVerifyRequest,
)
from app.intelligence.ocr_service import OCRService

router = APIRouter(prefix="/ocr", tags=["Document OCR & Compliance Extraction"])


def _serialize_field(f: OCRExtractedField) -> OCRExtractedFieldResponse:
    bbox = None
    try:
        if f.bounding_box_json:
            bbox = json.loads(f.bounding_box_json)
    except Exception:
        pass

    return OCRExtractedFieldResponse(
        id=f.id,
        ocr_job_id=f.ocr_job_id,
        document_id=f.document_id,
        application_id=f.application_id,
        field_name=f.field_name,
        field_category=f.field_category,
        raw_value=f.raw_value,
        normalized_value=f.normalized_value,
        confidence=f.confidence,
        page_number=f.page_number,
        bounding_box=bbox,
        verification_status=f.verification_status,
        is_automated_advisory=f.is_automated_advisory,
        corrected_value=f.corrected_value,
        review_comments=f.review_comments,
        reviewed_by_user_id=f.reviewed_by_user_id,
        reviewed_at=f.reviewed_at,
        created_at=f.created_at,
    )


def _serialize_job(j: OCRJob) -> OCRJobResponse:
    fields = [_serialize_field(f) for f in j.fields]
    return OCRJobResponse(
        id=j.id,
        document_id=j.document_id,
        application_id=j.application_id,
        status=j.status,
        engine=j.engine,
        page_count=j.page_count,
        extracted_text_preview=j.extracted_text_preview,
        processing_time_ms=j.processing_time_ms,
        error_message=j.error_message,
        fields=fields,
        created_at=j.created_at,
    )


@router.post("/process/{document_id}", response_model=OCRJobResponse)
async def process_document_ocr(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("SCRUTINY_OFFICER", "REGIONAL_OFFICER", "ADMIN")),
):
    """
    Trigger OCR text & structured field extraction for a verified clean document.
    Clean Vault Rule: Fails if document scan_status is not 'ACCEPTED'.
    """
    service = OCRService(db)
    job = await service.run_ocr_for_document(document_id)
    return _serialize_job(job)


@router.get("/document/{document_id}", response_model=Optional[OCRJobResponse])
async def get_document_ocr(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve OCR status and extracted fields for a document.
    Enforces multi-tenant institutional privacy.
    """
    doc_stmt = select(Document).where(Document.id == document_id)
    doc_res = await db.execute(doc_stmt)
    doc = doc_res.scalar_one_or_none()
    if not doc:
        raise NotFoundError("Document", document_id)

    # Multi-tenant boundary
    user_roles = [r.code for r in current_user.roles]
    if "INSTITUTION_USER" in user_roles or "INSTITUTION_ADMIN" in user_roles:
        if current_user.institution_id != doc.institution_id:
            raise PermissionDeniedError("Cannot inspect OCR data for another institution's document")

    service = OCRService(db)
    job = await service.get_document_ocr(document_id)
    if not job:
        return None
    return _serialize_job(job)


@router.get("/application/{application_id}", response_model=List[OCRExtractedFieldResponse])
async def list_application_ocr_fields(
    application_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all OCR compliance fields extracted across all documents of an application.
    """
    app_stmt = select(Application).where(Application.id == application_id)
    app_res = await db.execute(app_stmt)
    app = app_res.scalar_one_or_none()
    if not app:
        raise NotFoundError("Application", application_id)

    # Multi-tenant check
    user_roles = [r.code for r in current_user.roles]
    if "INSTITUTION_USER" in user_roles or "INSTITUTION_ADMIN" in user_roles:
        if current_user.institution_id != app.institution_id:
            raise PermissionDeniedError("Cannot inspect OCR extractions for another institution's application")

    service = OCRService(db)
    fields = await service.list_application_fields(application_id)
    return [_serialize_field(f) for f in fields]


@router.put("/fields/{field_id}/verify", response_model=OCRExtractedFieldResponse)
async def verify_extracted_field(
    field_id: str,
    payload: OCRFieldVerifyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("SCRUTINY_OFFICER", "REGIONAL_OFFICER", "ADMIN")),
):
    """
    Scrutiny Officer verification of an AI-extracted field.
    Allows VERIFIED, CORRECTED (with corrected_value), or REJECTED.
    Emits tamper-evident SHA-256 hash-chained audit log.
    """
    service = OCRService(db)
    updated_field = await service.verify_field(
        field_id=field_id,
        verification_status=payload.verification_status,
        officer_user_id=current_user.id,
        corrected_value=payload.corrected_value,
        review_comments=payload.review_comments,
    )
    return _serialize_field(updated_field)
