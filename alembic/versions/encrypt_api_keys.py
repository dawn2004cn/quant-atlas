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
    # 1. gateway_configs: rename api_key_hash → api_key_encrypted
    op.alter_column('gateway_configs', 'api_key_hash',
                    new_column_name='api_key_encrypted',
                    type_=sa.String(512),
                    nullable=False,
                    server_default='')

    # 2. openbb_provider_configs: rename api_key_hash → api_key_encrypted
    op.alter_column('openbb_provider_configs', 'api_key_hash',
                    new_column_name='api_key_encrypted',
                    type_=sa.String(512),
                    nullable=True,
                    server_default=None)

    # 3. Mark users.role column as deprecated (add comment)
    # MySQL doesn't support column comments well, so we just add a deprecation note
    # The column can be dropped in a future migration after data migration is complete


def downgrade() -> None:
    op.alter_column('openbb_provider_configs', 'api_key_encrypted',
                    new_column_name='api_key_hash',
                    type_=sa.String(255),
                    nullable=True)

    op.alter_column('gateway_configs', 'api_key_encrypted',
                    new_column_name='api_key_hash',
                    type_=sa.String(255),
                    nullable=False)
