"""Initial core domain migration

Revision ID: 001_initial_core
Revises: 
Create Date: 2026-10-25 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '001_initial_core'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Institutions
    op.create_table(
        'institutions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('region', sa.String(length=100), nullable=False),
        sa.Column('state', sa.String(length=100), nullable=False),
        sa.Column('district', sa.String(length=100), nullable=False),
        sa.Column('institution_type', sa.String(length=100), nullable=False),
        sa.Column('established_year', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='ACTIVE'),
        sa.Column('contact_email', sa.String(length=255), nullable=False),
        sa.Column('contact_phone', sa.String(length=50), nullable=False),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code'),
    )
    op.create_index('ix_institutions_code', 'institutions', ['code'])
    op.create_index('ix_institutions_region', 'institutions', ['region'])
    op.create_index('ix_institutions_state', 'institutions', ['state'])

    # 2. Permissions & Roles
    op.create_table(
        'permissions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('code', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code'),
    )
    op.create_index('ix_permissions_code', 'permissions', ['code'])

    op.create_table(
        'roles',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code'),
    )
    op.create_index('ix_roles_code', 'roles', ['code'])

    op.create_table(
        'role_permissions',
        sa.Column('role_id', sa.String(length=36), nullable=False),
        sa.Column('permission_id', sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(['permission_id'], ['permissions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('role_id', 'permission_id'),
    )

    # 3. Users
    op.create_table(
        'users',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=150), nullable=False),
        sa.Column('designation', sa.String(length=100), nullable=True),
        sa.Column('phone_number', sa.String(length=50), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('is_mfa_enabled', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('mfa_secret', sa.String(length=100), nullable=True),
        sa.Column('institution_id', sa.String(length=36), nullable=True),
        sa.Column('assigned_region', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['institution_id'], ['institutions.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
    )
    op.create_index('ix_users_email', 'users', ['email'])
    op.create_index('ix_users_institution_id', 'users', ['institution_id'])

    op.create_table(
        'user_roles',
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('role_id', sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id', 'role_id'),
    )

    # 4. Workflow Templates & Versions
    op.create_table(
        'workflow_templates',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('code', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(length=100), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code'),
    )
    op.create_index('ix_workflow_templates_code', 'workflow_templates', ['code'])

    op.create_table(
        'workflow_versions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('template_id', sa.String(length=36), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('aph_edition', sa.String(length=50), nullable=False),
        sa.Column('state_machine_json', sa.Text(), nullable=False),
        sa.Column('checklist_rules_json', sa.Text(), nullable=False),
        sa.Column('is_published', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('proposed_by_user_id', sa.String(length=36), nullable=True),
        sa.Column('approved_by_user_id', sa.String(length=36), nullable=True),
        sa.Column('approval_timestamp', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['template_id'], ['workflow_templates.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_workflow_versions_template_id', 'workflow_versions', ['template_id'])

    # 5. Applications & Events
    op.create_table(
        'applications',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('application_number', sa.String(length=50), nullable=False),
        sa.Column('institution_id', sa.String(length=36), nullable=False),
        sa.Column('template_id', sa.String(length=36), nullable=False),
        sa.Column('version_id', sa.String(length=36), nullable=False),
        sa.Column('current_status', sa.String(length=50), nullable=False, server_default='DRAFT'),
        sa.Column('academic_year', sa.String(length=20), nullable=False),
        sa.Column('submission_data_json', sa.Text(), nullable=False),
        sa.Column('submission_date', sa.String(length=50), nullable=True),
        sa.Column('sla_deadline', sa.String(length=50), nullable=True),
        sa.Column('applicant_user_id', sa.String(length=36), nullable=False),
        sa.Column('assigned_scrutiny_officer_id', sa.String(length=36), nullable=True),
        sa.Column('assigned_regional_officer_id', sa.String(length=36), nullable=True),
        sa.Column('delay_risk_score', sa.Float(), nullable=True),
        sa.Column('delay_risk_factors_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['applicant_user_id'], ['users.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['assigned_regional_officer_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['assigned_scrutiny_officer_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['institution_id'], ['institutions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['template_id'], ['workflow_templates.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['version_id'], ['workflow_versions.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('application_number'),
    )
    op.create_index('ix_applications_number', 'applications', ['application_number'])
    op.create_index('ix_applications_status', 'applications', ['current_status'])

    op.create_table(
        'application_events',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('application_id', sa.String(length=36), nullable=False),
        sa.Column('actor_id', sa.String(length=36), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('from_status', sa.String(length=50), nullable=True),
        sa.Column('to_status', sa.String(length=50), nullable=True),
        sa.Column('remarks', sa.Text(), nullable=True),
        sa.Column('event_payload_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['actor_id'], ['users.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    # 6. Audit Events & Merkle Roots
    op.create_table(
        'audit_events',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('sequence_number', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('actor_id', sa.String(length=50), nullable=False),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('resource_type', sa.String(length=100), nullable=False),
        sa.Column('resource_id', sa.String(length=100), nullable=False),
        sa.Column('ip_address', sa.String(length=50), nullable=True),
        sa.Column('user_agent', sa.String(length=255), nullable=True),
        sa.Column('previous_entry_hash', sa.String(length=64), nullable=False),
        sa.Column('payload_hash', sa.String(length=64), nullable=False),
        sa.Column('entry_hash', sa.String(length=64), nullable=False),
        sa.Column('details_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('entry_hash'),
        sa.UniqueConstraint('sequence_number'),
    )
    op.create_index('ix_audit_events_seq', 'audit_events', ['sequence_number'])

    op.create_table(
        'merkle_roots',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('batch_start_seq', sa.Integer(), nullable=False),
        sa.Column('batch_end_seq', sa.Integer(), nullable=False),
        sa.Column('merkle_root_hash', sa.String(length=64), nullable=False),
        sa.Column('total_events', sa.Integer(), nullable=False),
        sa.Column('signature', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('merkle_root_hash'),
    )


def downgrade() -> None:
    op.drop_table('merkle_roots')
    op.drop_table('audit_events')
    op.drop_table('application_events')
    op.drop_table('applications')
    op.drop_table('workflow_versions')
    op.drop_table('workflow_templates')
    op.drop_table('user_roles')
    op.drop_table('users')
    op.drop_table('role_permissions')
    op.drop_table('roles')
    op.drop_table('permissions')
    op.drop_table('institutions')
