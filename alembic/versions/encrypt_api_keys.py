"""Rename api_key_hash → api_key_encrypted in trading and openbb config tables.

Revision ID: encrypt_api_keys
Revises: p0_infrastructure
Create Date: 2026-06-13

All API keys previously stored as one-way hash are now stored as Fernet
encrypted tokens.  Existing hash values are cleared to empty strings;
users will need to re-enter their plaintext keys via the KeyManagementService.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'encrypt_api_keys'
down_revision = 'p0_infrastructure'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # gateway_configs: columns_at_create_all may have api_key_encrypted directly
    gw_cols = [c["name"] for c in inspector.get_columns("gateway_configs")]
    if "api_key_hash" in gw_cols:
        op.alter_column("gateway_configs", "api_key_hash",
                        new_column_name="api_key_encrypted",
                        type_=sa.String(512),
                        nullable=False,
                        server_default="")

    # openbb_provider_configs: same check
    ob_cols = [c["name"] for c in inspector.get_columns("openbb_provider_configs")]
    if "api_key_hash" in ob_cols:
        op.alter_column("openbb_provider_configs", "api_key_hash",
                        new_column_name="api_key_encrypted",
                        type_=sa.String(512),
                        nullable=True,
                        server_default=None)

def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    gw_cols = [c[name] for c in inspector.get_columns(gateway_configs)]
    if api_key_encrypted in gw_cols and api_key_hash not in gw_cols:
        op.alter_column(gateway_configs, api_key_encrypted,
                        new_column_name=api_key_hash,
                        type_=sa.String(255),
                        nullable=False)

    ob_cols = [c[name] for c in inspector.get_columns(openbb_provider_configs)]
    if api_key_encrypted in ob_cols and api_key_hash not in ob_cols:
        op.alter_column(openbb_provider_configs, api_key_encrypted,
                        new_column_name=api_key_hash,
                        type_=sa.String(255),
                        nullable=True)
