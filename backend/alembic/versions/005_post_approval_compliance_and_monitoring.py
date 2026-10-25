"""Post-approval compliance, obligations, and monitoring tables

Revision ID: 005_compliance_and_monitoring
Revises: 004_intelligence_ocr_and_aph
Create Date: 2026-10-25 22:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '005_compliance_and_monitoring'
down_revision: Union[str, None] = '004_intelligence_ocr_and_aph'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. compliance_obligations
    op.create_table(
        'compliance_obligations',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('obligation_code', sa.String(length=50), nullable=False),
        sa.Column('institution_id', sa.String(length=36), nullable=False),
        sa.Column('application_id', sa.String(length=36), nullable=True),
        sa.Column('decision_id', sa.String(length=36), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('source_reference', sa.String(length=255), nullable=False),
        sa.Column('applicability', sa.String(length=100), nullable=False),
        sa.Column('assigned_officer_id', sa.String(length=36), nullable=True),
        sa.Column('issue_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('due_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('recurrence', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('is_synthetic_demonstration', sa.Boolean(), nullable=False),
        sa.Column('is_automated_advisory', sa.Boolean(), nullable=False),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('closed_by_user_id', sa.String(length=36), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['institution_id'], ['institutions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['decision_id'], ['statutory_decisions.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['assigned_officer_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['closed_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_compliance_obligations_obligation_code'), 'compliance_obligations', ['obligation_code'], unique=True)
    op.create_index(op.f('ix_compliance_obligations_institution_id'), 'compliance_obligations', ['institution_id'], unique=False)
    op.create_index(op.f('ix_compliance_obligations_application_id'), 'compliance_obligations', ['application_id'], unique=False)
    op.create_index(op.f('ix_compliance_obligations_decision_id'), 'compliance_obligations', ['decision_id'], unique=False)
    op.create_index(op.f('ix_compliance_obligations_assigned_officer_id'), 'compliance_obligations', ['assigned_officer_id'], unique=False)
    op.create_index(op.f('ix_compliance_obligations_category'), 'compliance_obligations', ['category'], unique=False)
    op.create_index(op.f('ix_compliance_obligations_due_date'), 'compliance_obligations', ['due_date'], unique=False)
    op.create_index(op.f('ix_compliance_obligations_status'), 'compliance_obligations', ['status'], unique=False)
    op.create_index('ix_obligations_inst_status', 'compliance_obligations', ['institution_id', 'status'], unique=False)
    op.create_index('ix_obligations_due_status', 'compliance_obligations', ['due_date', 'status'], unique=False)

    # 2. obligation_evidences
    op.create_table(
        'obligation_evidences',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('obligation_id', sa.String(length=36), nullable=False),
        sa.Column('document_id', sa.String(length=36), nullable=True),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('file_url', sa.String(length=500), nullable=True),
        sa.Column('sha256_hash', sa.String(length=64), nullable=True),
        sa.Column('uploaded_by_user_id', sa.String(length=36), nullable=False),
        sa.Column('submission_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['obligation_id'], ['compliance_obligations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['uploaded_by_user_id'], ['users.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_obligation_evidences_obligation_id'), 'obligation_evidences', ['obligation_id'], unique=False)
    op.create_index(op.f('ix_obligation_evidences_document_id'), 'obligation_evidences', ['document_id'], unique=False)
    op.create_index(op.f('ix_obligation_evidences_uploaded_by_user_id'), 'obligation_evidences', ['uploaded_by_user_id'], unique=False)

    # 3. obligation_review_history
    op.create_table(
        'obligation_review_history',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('obligation_id', sa.String(length=36), nullable=False),
        sa.Column('actor_id', sa.String(length=36), nullable=False),
        sa.Column('actor_role', sa.String(length=50), nullable=False),
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('previous_status', sa.String(length=50), nullable=False),
        sa.Column('new_status', sa.String(length=50), nullable=False),
        sa.Column('comments', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['obligation_id'], ['compliance_obligations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['actor_id'], ['users.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_obligation_review_history_obligation_id'), 'obligation_review_history', ['obligation_id'], unique=False)
    op.create_index(op.f('ix_obligation_review_history_actor_id'), 'obligation_review_history', ['actor_id'], unique=False)

    # 4. compliance_escalations
    op.create_table(
        'compliance_escalations',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('obligation_id', sa.String(length=36), nullable=False),
        sa.Column('institution_id', sa.String(length=36), nullable=False),
        sa.Column('escalation_level', sa.Integer(), nullable=False),
        sa.Column('severity', sa.String(length=50), nullable=False),
        sa.Column('trigger_reason', sa.String(length=100), nullable=False),
        sa.Column('days_overdue', sa.Integer(), nullable=False),
        sa.Column('notified_roles_json', sa.Text(), nullable=False),
        sa.Column('notification_id', sa.String(length=36), nullable=True),
        sa.Column('is_resolved', sa.Boolean(), nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved_by_user_id', sa.String(length=36), nullable=True),
        sa.Column('resolution_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['obligation_id'], ['compliance_obligations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['institution_id'], ['institutions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['notification_id'], ['notifications.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['resolved_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_compliance_escalations_obligation_id'), 'compliance_escalations', ['obligation_id'], unique=False)
    op.create_index(op.f('ix_compliance_escalations_institution_id'), 'compliance_escalations', ['institution_id'], unique=False)
    op.create_index(op.f('ix_compliance_escalations_is_resolved'), 'compliance_escalations', ['is_resolved'], unique=False)


def downgrade() -> None:
    op.drop_table('compliance_escalations')
    op.drop_table('obligation_review_history')
    op.drop_table('obligation_evidences')
    op.drop_table('compliance_obligations')
