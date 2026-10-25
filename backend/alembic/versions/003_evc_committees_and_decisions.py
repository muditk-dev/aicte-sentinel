"""EVC inspections, committee hearings, and statutory decisions

Revision ID: 003_evc_committees_decisions
Revises: 002_docs_and_deficiencies
Create Date: 2026-10-25 18:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '003_evc_committees_decisions'
down_revision: Union[str, None] = '002_docs_and_deficiencies'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Experts
    op.create_table(
        'experts',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=True),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('designation', sa.String(length=150), nullable=False),
        sa.Column('organization', sa.String(length=255), nullable=False),
        sa.Column('expert_type', sa.String(length=50), nullable=False),
        sa.Column('qualifications', sa.String(length=255), nullable=False),
        sa.Column('experience_years', sa.Integer(), nullable=False),
        sa.Column('specializations_json', sa.Text(), nullable=False),
        sa.Column('affiliated_institution_ids_json', sa.Text(), nullable=False),
        sa.Column('alma_mater', sa.String(length=255), nullable=False),
        sa.Column('state', sa.String(length=100), nullable=False),
        sa.Column('district', sa.String(length=100), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('verification_status', sa.String(length=50), nullable=False),
        sa.Column('availability_status', sa.String(length=50), nullable=False),
        sa.Column('conflict_declarations_json', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('user_id')
    )
    op.create_index(op.f('ix_experts_name'), 'experts', ['name'], unique=False)
    op.create_index(op.f('ix_experts_organization'), 'experts', ['organization'], unique=False)
    op.create_index(op.f('ix_experts_expert_type'), 'experts', ['expert_type'], unique=False)
    op.create_index(op.f('ix_experts_alma_mater'), 'experts', ['alma_mater'], unique=False)
    op.create_index(op.f('ix_experts_state'), 'experts', ['state'], unique=False)
    op.create_index(op.f('ix_experts_district'), 'experts', ['district'], unique=False)
    op.create_index(op.f('ix_experts_verification_status'), 'experts', ['verification_status'], unique=False)
    op.create_index(op.f('ix_experts_availability_status'), 'experts', ['availability_status'], unique=False)

    # 2. EVC Inspections
    op.create_table(
        'evc_inspections',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('application_id', sa.String(length=36), nullable=False),
        sa.Column('institution_id', sa.String(length=36), nullable=False),
        sa.Column('inspection_number', sa.String(length=50), nullable=False),
        sa.Column('inspection_mode', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('scheduled_start_date', sa.String(length=50), nullable=False),
        sa.Column('scheduled_end_date', sa.String(length=50), nullable=False),
        sa.Column('actual_inspection_date', sa.String(length=50), nullable=True),
        sa.Column('chairperson_id', sa.String(length=36), nullable=True),
        sa.Column('meeting_link', sa.String(length=500), nullable=True),
        sa.Column('location_coordinates', sa.String(length=100), nullable=True),
        sa.Column('location_address', sa.String(length=255), nullable=True),
        sa.Column('cancellation_reason', sa.Text(), nullable=True),
        sa.Column('assigned_by_user_id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['institution_id'], ['institutions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['chairperson_id'], ['experts.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['assigned_by_user_id'], ['users.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('inspection_number')
    )
    op.create_index(op.f('ix_evc_inspections_application_id'), 'evc_inspections', ['application_id'], unique=False)
    op.create_index(op.f('ix_evc_inspections_institution_id'), 'evc_inspections', ['institution_id'], unique=False)
    op.create_index(op.f('ix_evc_inspections_status'), 'evc_inspections', ['status'], unique=False)
    op.create_index(op.f('ix_evc_inspections_inspection_mode'), 'evc_inspections', ['inspection_mode'], unique=False)

    # 3. EVC Inspection Experts (Panel Members)
    op.create_table(
        'evc_inspection_experts',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('inspection_id', sa.String(length=36), nullable=False),
        sa.Column('expert_id', sa.String(length=36), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=False),
        sa.Column('conflict_check_passed', sa.Boolean(), nullable=False),
        sa.Column('conflict_notes', sa.Text(), nullable=True),
        sa.Column('attendance_status', sa.String(length=50), nullable=False),
        sa.Column('attendance_timestamp', sa.String(length=50), nullable=True),
        sa.Column('sign_off_status', sa.String(length=50), nullable=False),
        sa.Column('sign_off_timestamp', sa.String(length=50), nullable=True),
        sa.Column('sign_off_remarks', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['inspection_id'], ['evc_inspections.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['expert_id'], ['experts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('inspection_id', 'expert_id', name='uq_inspection_expert')
    )
    op.create_index(op.f('ix_evc_inspection_experts_inspection_id'), 'evc_inspection_experts', ['inspection_id'], unique=False)
    op.create_index(op.f('ix_evc_inspection_experts_expert_id'), 'evc_inspection_experts', ['expert_id'], unique=False)

    # 4. EVC Report Versions
    op.create_table(
        'evc_report_versions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('inspection_id', sa.String(length=36), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('application_id', sa.String(length=36), nullable=False),
        sa.Column('submitted_by_user_id', sa.String(length=36), nullable=False),
        sa.Column('submitted_at', sa.String(length=50), nullable=False),
        sa.Column('sha256_hash', sa.String(length=64), nullable=False),
        sa.Column('overall_recommendation', sa.String(length=50), nullable=False),
        sa.Column('infrastructure_score', sa.Float(), nullable=True),
        sa.Column('faculty_verification_status', sa.String(length=50), nullable=False),
        sa.Column('land_building_status', sa.String(length=50), nullable=False),
        sa.Column('laboratories_equipment_status', sa.String(length=50), nullable=False),
        sa.Column('safety_and_amenities_status', sa.String(length=50), nullable=False),
        sa.Column('observations', sa.Text(), nullable=False),
        sa.Column('deficiencies_identified', sa.Text(), nullable=True),
        sa.Column('checklist_data_json', sa.Text(), nullable=False),
        sa.Column('evidence_references_json', sa.Text(), nullable=False),
        sa.Column('location_evidence_json', sa.Text(), nullable=False),
        sa.Column('virtual_attendance_json', sa.Text(), nullable=False),
        sa.Column('review_status', sa.String(length=50), nullable=False),
        sa.Column('reviewed_by_user_id', sa.String(length=36), nullable=True),
        sa.Column('reviewed_at', sa.String(length=50), nullable=True),
        sa.Column('review_remarks', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['inspection_id'], ['evc_inspections.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['submitted_by_user_id'], ['users.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['reviewed_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('inspection_id', 'version_number', name='uq_inspection_report_version')
    )
    op.create_index(op.f('ix_evc_report_versions_inspection_id'), 'evc_report_versions', ['inspection_id'], unique=False)
    op.create_index(op.f('ix_evc_report_versions_application_id'), 'evc_report_versions', ['application_id'], unique=False)
    op.create_index(op.f('ix_evc_report_versions_sha256_hash'), 'evc_report_versions', ['sha256_hash'], unique=False)
    op.create_index(op.f('ix_evc_report_versions_review_status'), 'evc_report_versions', ['review_status'], unique=False)

    # 5. Committees
    op.create_table(
        'committees',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('committee_type', sa.String(length=50), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('quorum_required', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('valid_from', sa.String(length=50), nullable=False),
        sa.Column('valid_to', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )
    op.create_index(op.f('ix_committees_committee_type'), 'committees', ['committee_type'], unique=False)

    # 6. Committee Memberships
    op.create_table(
        'committee_memberships',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('committee_id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=True),
        sa.Column('expert_id', sa.String(length=36), nullable=True),
        sa.Column('member_name', sa.String(length=150), nullable=False),
        sa.Column('member_role', sa.String(length=50), nullable=False),
        sa.Column('conflict_declarations_json', sa.Text(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['committee_id'], ['committees.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['expert_id'], ['experts.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_committee_memberships_committee_id'), 'committee_memberships', ['committee_id'], unique=False)

    # 7. Hearings
    op.create_table(
        'hearings',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('committee_id', sa.String(length=36), nullable=False),
        sa.Column('hearing_number', sa.String(length=50), nullable=False),
        sa.Column('hearing_type', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('scheduled_date', sa.String(length=50), nullable=False),
        sa.Column('meeting_mode', sa.String(length=50), nullable=False),
        sa.Column('venue_or_link', sa.String(length=500), nullable=False),
        sa.Column('agenda', sa.Text(), nullable=False),
        sa.Column('postponement_reason', sa.Text(), nullable=True),
        sa.Column('cancellation_reason', sa.Text(), nullable=True),
        sa.Column('chairperson_name', sa.String(length=150), nullable=True),
        sa.Column('conducted_at', sa.String(length=50), nullable=True),
        sa.Column('minutes_of_meeting', sa.Text(), nullable=True),
        sa.Column('final_recommendation', sa.String(length=50), nullable=True),
        sa.Column('recommendation_summary', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['committee_id'], ['committees.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('hearing_number')
    )
    op.create_index(op.f('ix_hearings_committee_id'), 'hearings', ['committee_id'], unique=False)
    op.create_index(op.f('ix_hearings_hearing_type'), 'hearings', ['hearing_type'], unique=False)
    op.create_index(op.f('ix_hearings_status'), 'hearings', ['status'], unique=False)

    # 8. Hearing Dockets
    op.create_table(
        'hearing_dockets',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('hearing_id', sa.String(length=36), nullable=False),
        sa.Column('application_id', sa.String(length=36), nullable=False),
        sa.Column('institution_id', sa.String(length=36), nullable=False),
        sa.Column('docket_number', sa.String(length=50), nullable=False),
        sa.Column('matter_summary', sa.Text(), nullable=False),
        sa.Column('referred_by', sa.String(length=100), nullable=False),
        sa.Column('institutional_representative_name', sa.String(length=150), nullable=True),
        sa.Column('docket_status', sa.String(length=50), nullable=False),
        sa.Column('docket_recommendation', sa.String(length=50), nullable=True),
        sa.Column('docket_remarks', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['hearing_id'], ['hearings.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['institution_id'], ['institutions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('docket_number'),
        sa.UniqueConstraint('hearing_id', 'application_id', name='uq_hearing_application_docket')
    )
    op.create_index(op.f('ix_hearing_dockets_hearing_id'), 'hearing_dockets', ['hearing_id'], unique=False)
    op.create_index(op.f('ix_hearing_dockets_application_id'), 'hearing_dockets', ['application_id'], unique=False)
    op.create_index(op.f('ix_hearing_dockets_institution_id'), 'hearing_dockets', ['institution_id'], unique=False)
    op.create_index(op.f('ix_hearing_dockets_docket_status'), 'hearing_dockets', ['docket_status'], unique=False)

    # 9. Hearing Attendance
    op.create_table(
        'hearing_attendances',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('hearing_id', sa.String(length=36), nullable=False),
        sa.Column('member_name', sa.String(length=150), nullable=False),
        sa.Column('member_role', sa.String(length=50), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=True),
        sa.Column('attended', sa.Boolean(), nullable=False),
        sa.Column('attendance_mode', sa.String(length=50), nullable=False),
        sa.Column('conflict_declared_for_docket_ids', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['hearing_id'], ['hearings.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_hearing_attendances_hearing_id'), 'hearing_attendances', ['hearing_id'], unique=False)

    # 10. Statutory Decisions
    op.create_table(
        'statutory_decisions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('application_id', sa.String(length=36), nullable=False),
        sa.Column('institution_id', sa.String(length=36), nullable=False),
        sa.Column('decision_number', sa.String(length=50), nullable=False),
        sa.Column('decision_type', sa.String(length=50), nullable=False),
        sa.Column('academic_year', sa.String(length=20), nullable=False),
        sa.Column('authority_role', sa.String(length=50), nullable=False),
        sa.Column('authorized_by_user_id', sa.String(length=36), nullable=False),
        sa.Column('authorized_at', sa.String(length=50), nullable=False),
        sa.Column('governing_policy_version', sa.String(length=50), nullable=False),
        sa.Column('reasons', sa.Text(), nullable=False),
        sa.Column('evidence_references_json', sa.Text(), nullable=False),
        sa.Column('intake_approved', sa.Integer(), nullable=True),
        sa.Column('valid_for_years', sa.Integer(), nullable=False),
        sa.Column('is_final', sa.Boolean(), nullable=False),
        sa.Column('is_reconsidered', sa.Boolean(), nullable=False),
        sa.Column('reconsideration_reference', sa.String(length=100), nullable=True),
        sa.Column('sha256_attestation', sa.String(length=64), nullable=False),
        sa.Column('declaration_text', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['institution_id'], ['institutions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['authorized_by_user_id'], ['users.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('decision_number')
    )
    op.create_index(op.f('ix_statutory_decisions_application_id'), 'statutory_decisions', ['application_id'], unique=False)
    op.create_index(op.f('ix_statutory_decisions_institution_id'), 'statutory_decisions', ['institution_id'], unique=False)
    op.create_index(op.f('ix_statutory_decisions_decision_type'), 'statutory_decisions', ['decision_type'], unique=False)
    op.create_index(op.f('ix_statutory_decisions_sha256_attestation'), 'statutory_decisions', ['sha256_attestation'], unique=False)

    # 11. Decision Conditions
    op.create_table(
        'decision_conditions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('decision_id', sa.String(length=36), nullable=False),
        sa.Column('condition_code', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('due_date', sa.String(length=50), nullable=False),
        sa.Column('compliance_status', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['decision_id'], ['statutory_decisions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_decision_conditions_decision_id'), 'decision_conditions', ['decision_id'], unique=False)
    op.create_index(op.f('ix_decision_conditions_compliance_status'), 'decision_conditions', ['compliance_status'], unique=False)


def downgrade() -> None:
    op.drop_table('decision_conditions')
    op.drop_table('statutory_decisions')
    op.drop_table('hearing_attendances')
    op.drop_table('hearing_dockets')
    op.drop_table('hearings')
    op.drop_table('committee_memberships')
    op.drop_table('committees')
    op.drop_table('evc_report_versions')
    op.drop_table('evc_inspection_experts')
    op.drop_table('evc_inspections')
    op.drop_table('experts')
