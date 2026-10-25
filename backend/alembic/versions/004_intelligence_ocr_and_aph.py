"""Intelligence, OCR extraction, and APH assistant tables

Revision ID: 004_intelligence_ocr_and_aph
Revises: 003_evc_committees_decisions
Create Date: 2026-10-25 21:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '004_intelligence_ocr_and_aph'
down_revision: Union[str, None] = '003_evc_committees_decisions'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. model_versions
    op.create_table(
        'model_versions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('version_tag', sa.String(length=50), nullable=False),
        sa.Column('algorithm', sa.String(length=100), nullable=False),
        sa.Column('features_json', sa.Text(), nullable=False),
        sa.Column('metrics_json', sa.Text(), nullable=False),
        sa.Column('training_dataset_summary', sa.Text(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('artifact_path', sa.String(length=255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('version_tag')
    )
    op.create_index(op.f('ix_model_versions_id'), 'model_versions', ['id'], unique=False)
    op.create_index(op.f('ix_model_versions_name'), 'model_versions', ['name'], unique=False)
    op.create_index(op.f('ix_model_versions_version_tag'), 'model_versions', ['version_tag'], unique=False)

    # 2. delay_risk_predictions
    op.create_table(
        'delay_risk_predictions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('application_id', sa.String(length=36), nullable=False),
        sa.Column('model_version_id', sa.String(length=36), nullable=True),
        sa.Column('risk_score', sa.Float(), nullable=False),
        sa.Column('risk_category', sa.String(length=20), nullable=False),
        sa.Column('estimated_delay_days', sa.Float(), nullable=False),
        sa.Column('confidence_score', sa.Float(), nullable=False),
        sa.Column('factor_attributions_json', sa.Text(), nullable=False),
        sa.Column('is_automated_advisory', sa.Boolean(), nullable=False),
        sa.Column('advisory_notes', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['model_version_id'], ['model_versions.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_delay_risk_predictions_id'), 'delay_risk_predictions', ['id'], unique=False)
    op.create_index(op.f('ix_delay_risk_predictions_application_id'), 'delay_risk_predictions', ['application_id'], unique=False)
    op.create_index(op.f('ix_delay_risk_predictions_model_version_id'), 'delay_risk_predictions', ['model_version_id'], unique=False)
    op.create_index(op.f('ix_delay_risk_predictions_risk_category'), 'delay_risk_predictions', ['risk_category'], unique=False)

    # 3. ocr_jobs
    op.create_table(
        'ocr_jobs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('document_id', sa.String(length=36), nullable=False),
        sa.Column('application_id', sa.String(length=36), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('engine', sa.String(length=50), nullable=False),
        sa.Column('page_count', sa.Integer(), nullable=False),
        sa.Column('extracted_text_preview', sa.Text(), nullable=True),
        sa.Column('processing_time_ms', sa.Integer(), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ocr_jobs_id'), 'ocr_jobs', ['id'], unique=False)
    op.create_index(op.f('ix_ocr_jobs_application_id'), 'ocr_jobs', ['application_id'], unique=False)
    op.create_index(op.f('ix_ocr_jobs_document_id'), 'ocr_jobs', ['document_id'], unique=False)
    op.create_index(op.f('ix_ocr_jobs_status'), 'ocr_jobs', ['status'], unique=False)

    # 4. ocr_extracted_fields
    op.create_table(
        'ocr_extracted_fields',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('ocr_job_id', sa.String(length=36), nullable=False),
        sa.Column('document_id', sa.String(length=36), nullable=False),
        sa.Column('application_id', sa.String(length=36), nullable=False),
        sa.Column('field_name', sa.String(length=100), nullable=False),
        sa.Column('field_category', sa.String(length=50), nullable=False),
        sa.Column('raw_value', sa.Text(), nullable=False),
        sa.Column('normalized_value', sa.Text(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('page_number', sa.Integer(), nullable=False),
        sa.Column('bounding_box_json', sa.Text(), nullable=True),
        sa.Column('verification_status', sa.String(length=30), nullable=False),
        sa.Column('is_automated_advisory', sa.Boolean(), nullable=False),
        sa.Column('corrected_value', sa.Text(), nullable=True),
        sa.Column('review_comments', sa.Text(), nullable=True),
        sa.Column('reviewed_by_user_id', sa.String(length=36), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['ocr_job_id'], ['ocr_jobs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reviewed_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ocr_extracted_fields_id'), 'ocr_extracted_fields', ['id'], unique=False)
    op.create_index(op.f('ix_ocr_extracted_fields_ocr_job_id'), 'ocr_extracted_fields', ['ocr_job_id'], unique=False)
    op.create_index(op.f('ix_ocr_extracted_fields_document_id'), 'ocr_extracted_fields', ['document_id'], unique=False)
    op.create_index(op.f('ix_ocr_extracted_fields_application_id'), 'ocr_extracted_fields', ['application_id'], unique=False)
    op.create_index(op.f('ix_ocr_extracted_fields_field_name'), 'ocr_extracted_fields', ['field_name'], unique=False)
    op.create_index(op.f('ix_ocr_extracted_fields_field_category'), 'ocr_extracted_fields', ['field_category'], unique=False)
    op.create_index(op.f('ix_ocr_extracted_fields_verification_status'), 'ocr_extracted_fields', ['verification_status'], unique=False)
    op.create_index(op.f('ix_ocr_extracted_fields_reviewed_by_user_id'), 'ocr_extracted_fields', ['reviewed_by_user_id'], unique=False)

    # 5. aph_source_documents
    op.create_table(
        'aph_source_documents',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('edition', sa.String(length=50), nullable=False),
        sa.Column('official_reference_url', sa.String(length=500), nullable=True),
        sa.Column('sha256_hash', sa.String(length=64), nullable=False),
        sa.Column('total_chapters', sa.Integer(), nullable=False),
        sa.Column('total_clauses', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_aph_source_documents_id'), 'aph_source_documents', ['id'], unique=False)
    op.create_index(op.f('ix_aph_source_documents_edition'), 'aph_source_documents', ['edition'], unique=False)

    # 6. aph_clauses
    op.create_table(
        'aph_clauses',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('source_id', sa.String(length=36), nullable=False),
        sa.Column('chapter_number', sa.Integer(), nullable=False),
        sa.Column('chapter_title', sa.String(length=200), nullable=False),
        sa.Column('clause_number', sa.String(length=50), nullable=False),
        sa.Column('clause_title', sa.String(length=200), nullable=False),
        sa.Column('page_number', sa.Integer(), nullable=False),
        sa.Column('content_text', sa.Text(), nullable=False),
        sa.Column('norm_category', sa.String(length=50), nullable=False),
        sa.Column('embedding_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['source_id'], ['aph_source_documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_aph_clauses_id'), 'aph_clauses', ['id'], unique=False)
    op.create_index(op.f('ix_aph_clauses_source_id'), 'aph_clauses', ['source_id'], unique=False)
    op.create_index(op.f('ix_aph_clauses_chapter_number'), 'aph_clauses', ['chapter_number'], unique=False)
    op.create_index(op.f('ix_aph_clauses_clause_number'), 'aph_clauses', ['clause_number'], unique=False)
    op.create_index(op.f('ix_aph_clauses_norm_category'), 'aph_clauses', ['norm_category'], unique=False)

    # 7. aph_assistant_queries
    op.create_table(
        'aph_assistant_queries',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('institution_id', sa.String(length=36), nullable=True),
        sa.Column('query_text', sa.Text(), nullable=False),
        sa.Column('response_text', sa.Text(), nullable=False),
        sa.Column('citations_json', sa.Text(), nullable=False),
        sa.Column('retrieval_mode', sa.String(length=50), nullable=False),
        sa.Column('is_automated_advisory', sa.Boolean(), nullable=False),
        sa.Column('uncertainty_warning', sa.Text(), nullable=True),
        sa.Column('feedback_rating', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['institution_id'], ['institutions.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_aph_assistant_queries_id'), 'aph_assistant_queries', ['id'], unique=False)
    op.create_index(op.f('ix_aph_assistant_queries_user_id'), 'aph_assistant_queries', ['user_id'], unique=False)
    op.create_index(op.f('ix_aph_assistant_queries_institution_id'), 'aph_assistant_queries', ['institution_id'], unique=False)


def downgrade() -> None:
    op.drop_table('aph_assistant_queries')
    op.drop_table('aph_clauses')
    op.drop_table('aph_source_documents')
    op.drop_table('ocr_extracted_fields')
    op.drop_table('ocr_jobs')
    op.drop_table('delay_risk_predictions')
    op.drop_table('model_versions')
