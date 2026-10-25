"""PostgreSQL Row-Level Security (RLS) policies for tenant-owned tables

Revision ID: 006_postgresql_rls
Revises: 005_compliance_and_monitoring
Create Date: 2026-10-26 01:30:00.000000

Security Design:
- Dialect-aware: On SQLite, this migration is safely a no-op to preserve unit test portability.
- On PostgreSQL:
  - Enables and FORCES Row-Level Security on tenant-owned tables:
    1. institutions
    2. applications
    3. documents
    4. deficiency_notices
    5. compliance_obligations
  - Policies enforce:
    - Central Regulatory Officers (SUPER_ADMIN, ADMIN, REGIONAL_OFFICER, SCRUTINY_OFFICER) have audited supervisory access across tenants.
    - Institution Representatives (INSTITUTION_ADMIN, INSTITUTION_USER) are strictly constrained to rows where institution_id matches current_setting('app.current_tenant', true).
    - Setting FORCE ROW LEVEL SECURITY ensures the table owner connection is also strictly bound by the RLS policy.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '006_postgresql_rls'
down_revision: Union[str, None] = '005_compliance_and_monitoring'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Tables where tenant isolation is enforced at the database engine level
TENANT_TABLES = [
    ("institutions", "id"),
    ("applications", "institution_id"),
    ("documents", "institution_id"),
    ("deficiency_notices", "institution_id"),
    ("compliance_obligations", "institution_id"),
]


def upgrade() -> None:
    bind = op.get_bind()
    # Preserve 100% SQLite compatibility for automated testing environments
    if bind.dialect.name != "postgresql":
        return

    # PostgreSQL DDL for Row-Level Security
    # 1. Institutions table policy
    op.execute("""
        ALTER TABLE institutions ENABLE ROW LEVEL SECURITY;
        ALTER TABLE institutions FORCE ROW LEVEL SECURITY;
        
        DROP POLICY IF EXISTS rls_institutions_tenant_isolation ON institutions;
        CREATE POLICY rls_institutions_tenant_isolation ON institutions
            FOR ALL
            USING (
                current_setting('app.current_role', true) IN ('SUPER_ADMIN', 'ADMIN', 'REGIONAL_OFFICER', 'SCRUTINY_OFFICER', 'EVC_CHAIRMAN', 'EVC_EXPERT')
                OR id = current_setting('app.current_tenant', true)
            )
            WITH CHECK (
                current_setting('app.current_role', true) IN ('SUPER_ADMIN', 'ADMIN')
                OR id = current_setting('app.current_tenant', true)
            );
    """)

    # 2. Applications table policy
    op.execute("""
        ALTER TABLE applications ENABLE ROW LEVEL SECURITY;
        ALTER TABLE applications FORCE ROW LEVEL SECURITY;
        
        DROP POLICY IF EXISTS rls_applications_tenant_isolation ON applications;
        CREATE POLICY rls_applications_tenant_isolation ON applications
            FOR ALL
            USING (
                current_setting('app.current_role', true) IN ('SUPER_ADMIN', 'ADMIN', 'REGIONAL_OFFICER', 'SCRUTINY_OFFICER', 'EVC_CHAIRMAN', 'EVC_EXPERT')
                OR institution_id = current_setting('app.current_tenant', true)
            )
            WITH CHECK (
                current_setting('app.current_role', true) IN ('SUPER_ADMIN', 'ADMIN', 'REGIONAL_OFFICER', 'SCRUTINY_OFFICER')
                OR institution_id = current_setting('app.current_tenant', true)
            );
    """)

    # 3. Documents table policy
    op.execute("""
        ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
        ALTER TABLE documents FORCE ROW LEVEL SECURITY;
        
        DROP POLICY IF EXISTS rls_documents_tenant_isolation ON documents;
        CREATE POLICY rls_documents_tenant_isolation ON documents
            FOR ALL
            USING (
                current_setting('app.current_role', true) IN ('SUPER_ADMIN', 'ADMIN', 'REGIONAL_OFFICER', 'SCRUTINY_OFFICER', 'EVC_CHAIRMAN', 'EVC_EXPERT')
                OR institution_id = current_setting('app.current_tenant', true)
            )
            WITH CHECK (
                current_setting('app.current_role', true) IN ('SUPER_ADMIN', 'ADMIN', 'REGIONAL_OFFICER', 'SCRUTINY_OFFICER')
                OR institution_id = current_setting('app.current_tenant', true)
            );
    """)

    # 4. Deficiency notices table policy
    op.execute("""
        ALTER TABLE deficiency_notices ENABLE ROW LEVEL SECURITY;
        ALTER TABLE deficiency_notices FORCE ROW LEVEL SECURITY;
        
        DROP POLICY IF EXISTS rls_deficiency_notices_tenant_isolation ON deficiency_notices;
        CREATE POLICY rls_deficiency_notices_tenant_isolation ON deficiency_notices
            FOR ALL
            USING (
                current_setting('app.current_role', true) IN ('SUPER_ADMIN', 'ADMIN', 'REGIONAL_OFFICER', 'SCRUTINY_OFFICER')
                OR institution_id = current_setting('app.current_tenant', true)
            )
            WITH CHECK (
                current_setting('app.current_role', true) IN ('SUPER_ADMIN', 'ADMIN', 'REGIONAL_OFFICER', 'SCRUTINY_OFFICER')
                OR institution_id = current_setting('app.current_tenant', true)
            );
    """)

    # 5. Compliance obligations table policy
    op.execute("""
        ALTER TABLE compliance_obligations ENABLE ROW LEVEL SECURITY;
        ALTER TABLE compliance_obligations FORCE ROW LEVEL SECURITY;
        
        DROP POLICY IF EXISTS rls_compliance_obligations_tenant_isolation ON compliance_obligations;
        CREATE POLICY rls_compliance_obligations_tenant_isolation ON compliance_obligations
            FOR ALL
            USING (
                current_setting('app.current_role', true) IN ('SUPER_ADMIN', 'ADMIN', 'REGIONAL_OFFICER', 'SCRUTINY_OFFICER')
                OR institution_id = current_setting('app.current_tenant', true)
            )
            WITH CHECK (
                current_setting('app.current_role', true) IN ('SUPER_ADMIN', 'ADMIN', 'REGIONAL_OFFICER', 'SCRUTINY_OFFICER')
                OR institution_id = current_setting('app.current_tenant', true)
            );
    """)


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    for table, _ in TENANT_TABLES:
        op.execute(f"DROP POLICY IF EXISTS rls_{table}_tenant_isolation ON {table};")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY;")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;")
