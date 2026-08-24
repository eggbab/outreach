"""sync schema additions

Revision ID: 98650f47e672
Revises: 7e10f5fc765b
Create Date: 2026-03-22 14:46:51.442257

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

from app.core.database import Base
import app.models.models  # noqa: F401 - register all models


# revision identifiers, used by Alembic.
revision: str = "98650f47e672"
down_revision: Union[str, None] = "7e10f5fc765b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _columns(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = inspect(bind)
    if table_name not in inspector.get_table_names():
        return set()
    return {col["name"] for col in inspector.get_columns(table_name)}


def _add_column_if_missing(table_name: str, column: sa.Column) -> None:
    if column.name not in _columns(table_name):
        op.add_column(table_name, column)


def upgrade() -> None:
    """Bring older local/prod databases up to the current model contract."""
    bind = op.get_bind()

    # Create any tables missing from partial deployments. Existing tables are not
    # modified by create_all, so column drift is handled explicitly below.
    Base.metadata.create_all(bind=bind)

    _add_column_if_missing(
        "users",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    _add_column_if_missing("users", sa.Column("reset_token", sa.String(length=128), nullable=True))
    _add_column_if_missing("users", sa.Column("reset_token_expires_at", sa.DateTime(), nullable=True))
    _add_column_if_missing("users", sa.Column("terms_accepted_at", sa.DateTime(), nullable=True))

    _add_column_if_missing("user_settings", sa.Column("email_subject", sa.String(length=200), nullable=True))
    _add_column_if_missing("prospects", sa.Column("email_valid", sa.Boolean(), nullable=True))
    _add_column_if_missing("email_logs", sa.Column("tracking_id", sa.String(length=64), nullable=True))
    _add_column_if_missing("email_logs", sa.Column("opened_at", sa.DateTime(), nullable=True))
    _add_column_if_missing("email_logs", sa.Column("clicked_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    # Keep downgrade conservative: production data columns should not be dropped
    # automatically from a catch-up migration.
    pass
