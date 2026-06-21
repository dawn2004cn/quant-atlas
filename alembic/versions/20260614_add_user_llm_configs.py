"""Add user_llm_configs table for per-user LLM provider settings.

Revision ID: add_user_llm_configs
Revises: encrypt_api_keys
Create Date: 2026-06-14

This migration creates the user_llm_configs table where each row
stores a user's LLM provider configuration (provider, model, api_key,
etc.). API keys are stored Fernet-encrypted. System-wide defaults
use user_id=0.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "add_user_llm_configs"
down_revision = "encrypt_api_keys"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_llm_configs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), nullable=False, index=True),
        sa.Column("provider", sa.String(32), nullable=False, server_default="default"),
        sa.Column("model_name", sa.String(128), nullable=False),
        sa.Column("base_url", sa.String(512)),
        sa.Column("api_key_encrypted", sa.String(512), nullable=False),
        sa.Column("temperature", sa.Float(), server_default="0.2"),
        sa.Column("max_tokens", sa.Integer(), server_default="4096"),
        sa.Column("timeout_sec", sa.Integer(), server_default="120"),
        sa.Column("model_alias", sa.String(64)),
        sa.Column("fallback_chain_json", sa.Text()),
        sa.Column("is_active", sa.SmallInteger(), server_default="1"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "provider", name="uq_user_provider"),
    )


def downgrade() -> None:
    op.drop_table("user_llm_configs")
