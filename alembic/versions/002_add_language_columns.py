"""add language columns to studio tables

Revision ID: 002
Revises: 001
Create Date: 2026-04-05

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "transcript_segments",
        sa.Column("language", sa.String(length=16), nullable=True),
        schema="studio",
    )
    op.add_column(
        "generated_descriptions",
        sa.Column("language", sa.String(length=16), nullable=True),
        schema="studio",
    )
    op.add_column(
        "subtitle_artifacts",
        sa.Column("language", sa.String(length=16), nullable=True),
        schema="studio",
    )


def downgrade() -> None:
    op.drop_column("subtitle_artifacts", "language", schema="studio")
    op.drop_column("generated_descriptions", "language", schema="studio")
    op.drop_column("transcript_segments", "language", schema="studio")
