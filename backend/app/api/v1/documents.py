import json
import uuid
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, UploadFile, File, Form, Request, status, Response
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.exceptions import NotFoundError, PermissionDeniedError, ConflictError
from app.models.application import Application, ApplicationEvent
from app.models.document import Document, DocumentVersion
from app.models.user import User
from app.schemas.document import DocumentResponse, DocumentVersionResponse
from app.security.dependencies import get_current_user
from app.security.file_validator import validate_uploaded_file
from app.security.scanner import scanner, ScanStatus
from app.storage.service import storage_service
from app.audit.service import record_audit_event

router = APIRouter(tags=["Document Management & Scrutiny"])


@router.post("/applications/{application_id}/documents", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    application_id: str,
    request: Request,
    category: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Secure document upload pipeline:
    1. Tenant access control
    2. File size & magic byte signature verification
    3. Staging into quarantine storage
    4. Malware scanning (ClamAV / signature inspection)
    5. Promotion to clean vault if accepted, or quarantine retention if unverified/rejected
    6. Version tracking and tamper-evident audit logging
    """
    # 1. Fetch Application and check tenant authorization
    stmt = select(Application).where(Application.id == application_id)
    result = await db.execute(stmt)
    app = result.scalar_one_or_none()
    if not app:
        raise NotFoundError("Application", application_id)

    user_roles = [r.code for r in current_user.roles]
    if "INSTITUTION_ADMIN" in user_roles and "SUPER_ADMIN" not in user_roles:
        if app.institution_id != current_user.institution_id:
            raise PermissionDeniedError("Cannot upload documents to an application belonging to another institution.")

    # 2. Read bytes and perform strict byte-level validation
    raw_bytes = await file.read()
    val_meta = validate_uploaded_file(
        filename=file.filename or "uploaded_file",
        declared_content_type=file.content_type or "application/octet-stream",
        data=raw_bytes,
    )

    # 3. Generate server-side random storage key (never use user-supplied filename as path)
    doc_uuid = uuid.uuid4().hex
    safe_ext = val_meta.detected_mime.split("/")[-1].replace("jpeg", "jpg")
    storage_key = f"app_{app.id}/{doc_uuid}.{safe_ext}"

    # 4. Save into isolated quarantine storage
    await storage_service.save_quarantine(storage_key, raw_bytes)

    # 5. Execute Antivirus Scanning
    # In test/dev environment with simulation enabled, inspects EICAR & checks ClamAV if configured
    scan_result = scanner.scan_bytes(raw_bytes, allow_simulation_pass=True)

    if scan_result.status == ScanStatus.ACCEPTED:
        # Promote from quarantine to clean vault
        await storage_service.move_to_vault(storage_key)
    elif scan_result.status == ScanStatus.REJECTED:
        # Delete rejected payload from quarantine
        await storage_service.delete_quarantine(storage_key)

    # 6. Check if document of this category already exists (Version management)
    doc_stmt = (
        select(Document)
        .options(selectinload(Document.versions))
        .where(Document.application_id == app.id, Document.category == category, Document.is_active.is_(True))
    )
    existing_doc_result = await db.execute(doc_stmt)
    existing_doc = existing_doc_result.scalar_one_or_none()

    if existing_doc:
        # Increment version
        new_version_num = existing_doc.current_version + 1
        existing_doc.current_version = new_version_num
        existing_doc.storage_key = storage_key
        existing_doc.sha256_hash = val_meta.sha256_hash
        existing_doc.file_size = val_meta.file_size
        existing_doc.mime_type = val_meta.detected_mime
        existing_doc.original_filename = val_meta.original_filename
        existing_doc.scan_status = scan_result.status.value
        existing_doc.scan_result_details = scan_result.details
        existing_doc.scan_timestamp = scan_result.scan_timestamp
        existing_doc.rejection_reason = scan_result.rejection_reason
        # Reset verification status on new version upload
        existing_doc.verification_status = "PENDING"

        # Record version
        ver = DocumentVersion(
            document_id=existing_doc.id,
            version_number=new_version_num,
            storage_key=storage_key,
            sha256_hash=val_meta.sha256_hash,
            file_size=val_meta.file_size,
            uploaded_by_user_id=current_user.id,
            scan_status=scan_result.status.value,
        )
        db.add(ver)
        doc_obj = existing_doc
    else:
        # Create new Document entity
        doc_obj = Document(
            application_id=app.id,
            institution_id=app.institution_id,
            category=category,
            original_filename=val_meta.original_filename,
            storage_key=storage_key,
            mime_type=val_meta.detected_mime,
            file_size=val_meta.file_size,
            sha256_hash=val_meta.sha256_hash,
            uploaded_by_user_id=current_user.id,
            scan_status=scan_result.status.value,
            scan_result_details=scan_result.details,
            scan_timestamp=scan_result.scan_timestamp,
            rejection_reason=scan_result.rejection_reason,
            verification_status="PENDING",
            current_version=1,
            is_active=True,
        )
        db.add(doc_obj)
        await db.flush()

        ver = DocumentVersion(
            document_id=doc_obj.id,
            version_number=1,
            storage_key=storage_key,
            sha256_hash=val_meta.sha256_hash,
            file_size=val_meta.file_size,
            uploaded_by_user_id=current_user.id,
            scan_status=scan_result.status.value,
        )
        db.add(ver)

    # 7. Record application event
    event = ApplicationEvent(
        application_id=app.id,
        actor_id=current_user.id,
        event_type="DOCUMENT_UPLOADED",
        remarks=f"Uploaded {category} (v{doc_obj.current_version}). Antivirus status: {scan_result.status.value}",
        event_payload_json=json.dumps({
            "category": category,
            "filename": val_meta.original_filename,
            "sha256": val_meta.sha256_hash,
            "scan_status": scan_result.status.value,
        }),
    )
    db.add(event)

    # 8. Record cryptographically chained audit record
    await record_audit_event(
        db=db,
        actor_id=current_user.id,
        action="DOCUMENT_UPLOAD_AND_SCAN",
        resource_type="Document",
        resource_id=doc_obj.id,
        details={
            "application_id": app.id,
            "category": category,
            "sha256": val_meta.sha256_hash,
            "file_size": val_meta.file_size,
            "scan_status": scan_result.status.value,
            "scan_details": scan_result.details,
        },
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )

    await db.commit()
    await db.refresh(doc_obj)

    # Reload with versions
    reloaded_stmt = select(Document).options(selectinload(Document.versions)).where(Document.id == doc_obj.id)
    reloaded_doc = (await db.execute(reloaded_stmt)).scalar_one()
    return reloaded_doc


@router.get("/applications/{application_id}/documents", response_model=List[DocumentResponse])
async def list_documents(
    application_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lists all active documents uploaded for an application docket."""
    stmt = select(Application).where(Application.id == application_id)
    result = await db.execute(stmt)
    app = result.scalar_one_or_none()
    if not app:
        raise NotFoundError("Application", application_id)

    user_roles = [r.code for r in current_user.roles]
    if "INSTITUTION_ADMIN" in user_roles and "SUPER_ADMIN" not in user_roles:
        if app.institution_id != current_user.institution_id:
            raise PermissionDeniedError("Access to documents of other institutions is strictly disallowed under tenant isolation.")

    doc_stmt = (
        select(Document)
        .options(selectinload(Document.versions))
        .where(Document.application_id == application_id, Document.is_active.is_(True))
        .order_by(Document.created_at.desc())
    )
    docs_result = await db.execute(doc_stmt)
    docs = docs_result.scalars().all()
    return docs


@router.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document_metadata(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve document metadata with versions."""
    stmt = select(Document).options(selectinload(Document.versions)).where(Document.id == document_id)
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()
    if not doc:
        raise NotFoundError("Document", document_id)

    user_roles = [r.code for r in current_user.roles]
    if "INSTITUTION_ADMIN" in user_roles and "SUPER_ADMIN" not in user_roles:
        if doc.institution_id != current_user.institution_id:
            raise PermissionDeniedError("Access to this document is denied under institutional tenant isolation.")

    return doc


@router.get("/documents/{document_id}/download")
async def download_document(
    document_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Downloads an accepted document from the clean vault.
    Security rules:
    - Quarantined, scanning, or rejected documents CANNOT be downloaded.
    - Tenant boundaries enforced.
    - Audit log entry recorded on download.
    """
    stmt = select(Document).where(Document.id == document_id)
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()
    if not doc:
        raise NotFoundError("Document", document_id)

    # 1. Tenant boundary check
    user_roles = [r.code for r in current_user.roles]
    if "INSTITUTION_ADMIN" in user_roles and "SUPER_ADMIN" not in user_roles:
        if doc.institution_id != current_user.institution_id:
            raise PermissionDeniedError("Access denied: Document belongs to a different institution.")

    # 2. Security status check
    if doc.scan_status != ScanStatus.ACCEPTED.value:
        raise PermissionDeniedError(
            f"Download blocked: Document is in '{doc.scan_status}' state and has not been verified by antivirus checks."
        )

    # 3. Retrieve bytes from vault
    file_bytes = await storage_service.get_vault_file(doc.storage_key)

    # 4. Record audit event
    await record_audit_event(
        db=db,
        actor_id=current_user.id,
        action="DOCUMENT_DOWNLOAD",
        resource_type="Document",
        resource_id=doc.id,
        details={"filename": doc.original_filename, "sha256": doc.sha256_hash},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )
    await db.commit()

    return Response(
        content=file_bytes,
        media_type=doc.mime_type,
        headers={
            "Content-Disposition": f'inline; filename="{doc.original_filename}"',
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/documents/{document_id}/versions", response_model=List[DocumentVersionResponse])
async def list_document_versions(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve full version history of a document."""
    stmt = select(Document).where(Document.id == document_id)
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()
    if not doc:
        raise NotFoundError("Document", document_id)

    user_roles = [r.code for r in current_user.roles]
    if "INSTITUTION_ADMIN" in user_roles and "SUPER_ADMIN" not in user_roles:
        if doc.institution_id != current_user.institution_id:
            raise PermissionDeniedError("Access denied under institutional tenant isolation.")

    v_stmt = (
        select(DocumentVersion)
        .where(DocumentVersion.document_id == document_id)
        .order_by(DocumentVersion.version_number.desc())
    )
    versions_res = await db.execute(v_stmt)
    return versions_res.scalars().all()
