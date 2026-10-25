"""Documents, scrutiny findings, and deficiency workflow

Revision ID: 002_docs_and_deficiencies
Revises: 001_initial_core
Create Date: 2026-10-25 15:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '002_docs_and_deficiencies'
down_revision: Union[str, None] = '001_initial_core'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Documents table
    op.create_table(
        'documents',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('application_id', sa.String(length=36), nullable=False),
        sa.Column('institution_id', sa.String(length=36), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=False),
        sa.Column('original_filename', sa.String(length=255), nullable=False),
        sa.Column('storage_key', sa.String(length=255), nullable=False),
        sa.Column('mime_type', sa.String(length=100), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('sha256_hash', sa.String(length=64), nullable=False),
        sa.Column('uploaded_by_user_id', sa.String(length=36), nullable=False),
        sa.Column('scan_status', sa.String(length=50), nullable=False, server_default='QUARANTINED'),
        sa.Column('scan_result_details', sa.Text(), nullable=True),
        sa.Column('scan_timestamp', sa.String(length=50), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('verification_status', sa.String(length=50), nullable=False, server_default='PENDING'),
        sa.Column('current_version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['institution_id'], ['institutions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['uploaded_by_user_id'], ['users.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('storage_key'),
    )
    op.create_index('ix_documents_application_id', 'documents', ['application_id'])
    op.create_index('ix_documents_institution_id', 'documents', ['institution_id'])
    op.create_index('ix_documents_category', 'documents', ['category'])
    op.create_index('ix_documents_sha256_hash', 'documents', ['sha256_hash'])

    # 2. Document Versions
    op.create_table(
        'document_versions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('document_id', sa.String(length=36), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('storage_key', sa.String(length=255), nullable=False),
        sa.Column('sha256_hash', sa.String(length=64), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('uploaded_by_user_id', sa.String(length=36), nullable=False),
        sa.Column('scan_status', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['uploaded_by_user_id'], ['users.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_document_versions_document_id', 'document_versions', ['document_id'])

    # 3. Scrutiny Findings
    op.create_table(
        'scrutiny_findings',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('application_id', sa.String(length=36), nullable=False),
        sa.Column('document_id', sa.String(length=36), nullable=True),
        sa.Column('category', sa.String(length=100), nullable=False),
        sa.Column('officer_id', sa.String(length=36), nullable=False),
        sa.Column('finding_status', sa.String(length=50), nullable=False),
        sa.Column('reason', sa.String(length=255), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('is_advisory_ai', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['officer_id'], ['users.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_scrutiny_findings_application_id', 'scrutiny_findings', ['application_id'])

    # 4. Deficiency Notices
    op.create_table(
        'deficiency_notices',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('notice_number', sa.String(length=50), nullable=False),
        sa.Column('application_id', sa.String(length=36), nullable=False),
        sa.Column('institution_id', sa.String(length=36), nullable=False),
        sa.Column('issuing_officer_id', sa.String(length=36), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='DRAFT'),
        sa.Column('due_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('officer_remarks', sa.Text(), nullable=True),
        sa.Column('issued_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['institution_id'], ['institutions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['issuing_officer_id'], ['users.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('notice_number'),
    )
    op.create_index('ix_deficiency_notices_application_id', 'deficiency_notices', ['application_id'])
    op.create_index('ix_deficiency_notices_institution_id', 'deficiency_notices', ['institution_id'])

    # 5. Deficiency Items
    op.create_table(
        'deficiency_items',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('notice_id', sa.String(length=36), nullable=False),
        sa.Column('document_id', sa.String(length=36), nullable=True),
        sa.Column('requirement_title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('required_corrective_action', sa.Text(), nullable=False),
        sa.Column('item_status', sa.String(length=50), nullable=False, server_default='PENDING'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['notice_id'], ['deficiency_notices.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_deficiency_items_notice_id', 'deficiency_items', ['notice_id'])

    # 6. Deficiency Responses
    op.create_table(
        'deficiency_responses',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('notice_id', sa.String(length=36), nullable=False),
        sa.Column('submitted_by_user_id', sa.String(length=36), nullable=False),
        sa.Column('response_remarks', sa.Text(), nullable=False),
        sa.Column('attachments_json', sa.Text(), nullable=False, server_default='[]'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['notice_id'], ['deficiency_notices.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['submitted_by_user_id'], ['users.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_deficiency_responses_notice_id', 'deficiency_responses', ['notice_id'])

    # 7. Notifications
    op.create_table(
        'notifications',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=True),
        sa.Column('institution_id', sa.String(length=36), nullable=True),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False, server_default='SYSTEM'),
        sa.Column('link_url', sa.String(length=255), nullable=True),
        sa.Column('is_read', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('delivery_status', sa.String(length=50), nullable=False, server_default='DELIVERED'),
        sa.Column('dedup_key', sa.String(length=150), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['institution_id'], ['institutions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('dedup_key'),
    )
    op.create_index('ix_notifications_institution_id', 'notifications', ['institution_id'])
    op.create_index('ix_notifications_user_id', 'notifications', ['user_id'])


def downgrade() -> None:
    op.drop_table('notifications')
    op.drop_table('deficiency_responses')
    op.drop_table('deficiency_items')
    op.drop_table('deficiency_notices')
    op.drop_table('scrutiny_findings')
    op.drop_table('document_versions')
    op.drop_table('documents')
