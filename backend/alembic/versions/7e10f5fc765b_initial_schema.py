"""initial schema

Revision ID: 7e10f5fc765b
Revises:
Create Date: 2026-03-22 14:46:30.540816

"""
from typing import Sequence, Union

from alembic import op

from app.core.database import Base
import app.models.models  # noqa: F401 - register all models


# revision identifiers, used by Alembic.
revision: str = "7e10f5fc765b"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the complete schema for a fresh deployment."""
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
