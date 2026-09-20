"""Add title/website fields and certifications/awards tables

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-20

Adds:
- users.website              (portfolio / LinkedIn link)
- resumes.title               (headline shown under the name, e.g. "UX Designer")
- education.details           (free-text, meant to hold 1-2 short bullet lines)
- certifications table        (new)
- awards table                (new)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("website", sa.String(), nullable=True))
    op.add_column("resumes", sa.Column("title", sa.String(), nullable=True))
    op.add_column("education", sa.Column("details", sa.Text(), nullable=True))

    op.create_table(
        "certifications",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("resume_id", sa.Integer(), sa.ForeignKey("resumes.id"), nullable=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("issuing_organization", sa.String(), nullable=True),
        sa.Column("year", sa.String(), nullable=True),
    )

    op.create_table(
        "awards",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("resume_id", sa.Integer(), sa.ForeignKey("resumes.id"), nullable=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("year", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("awards")
    op.drop_table("certifications")

    # SQLite only supports DROP COLUMN natively on newer versions (3.35+).
    # Batch mode rebuilds the table under the hood, so this works regardless
    # of the SQLite version Alembic is running against.
    with op.batch_alter_table("education") as batch_op:
        batch_op.drop_column("details")

    with op.batch_alter_table("resumes") as batch_op:
        batch_op.drop_column("title")

    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("website")
