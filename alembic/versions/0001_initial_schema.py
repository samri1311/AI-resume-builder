"""Initial schema baseline

Revision ID: 0001
Revises:
Create Date: 2026-09-18

This migration captures the schema exactly as it already exists in
backend/database/models.py (users, resumes, experiences, education,
skills, ats_scores — including the ats_score / similarity_score /
skill_match_score / matched_skills columns that were previously added by
hand through backend/database/update_ats_table.py).

IMPORTANT — how to apply this, depending on your situation:

* If you already have a resumes.db with these tables in it (e.g. your
  current dev database), do NOT run `alembic upgrade head` — that would
  try to CREATE TABLE on things that already exist and fail. Instead run:

      alembic stamp head

  This just records "the database is already at revision 0001" without
  touching any tables.

* If you're starting from a brand new, empty database, run:

      alembic upgrade head

  which creates every table from scratch.

From here on, schema changes should go through
`alembic revision --autogenerate -m "..."` + `alembic upgrade head`,
not another hand-written ALTER TABLE script.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False, unique=True),
        sa.Column("phone", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "resumes",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "experiences",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("resume_id", sa.Integer(), sa.ForeignKey("resumes.id"), nullable=True),
        sa.Column("job_title", sa.String(), nullable=True),
        sa.Column("company", sa.String(), nullable=True),
        sa.Column("location", sa.String(), nullable=True),
        sa.Column("start_date", sa.String(), nullable=True),
        sa.Column("end_date", sa.String(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("ai_description", sa.JSON(), nullable=True),
        sa.Column("is_current", sa.Boolean(), nullable=True),
    )

    op.create_table(
        "education",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("resume_id", sa.Integer(), sa.ForeignKey("resumes.id"), nullable=True),
        sa.Column("college", sa.String(), nullable=True),
        sa.Column("degree", sa.String(), nullable=True),
        sa.Column("field_of_study", sa.String(), nullable=True),
        sa.Column("start_year", sa.String(), nullable=True),
        sa.Column("end_year", sa.String(), nullable=True),
    )

    op.create_table(
        "skills",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("resume_id", sa.Integer(), sa.ForeignKey("resumes.id"), nullable=True),
        sa.Column("skill_name", sa.String(), nullable=True),
    )

    op.create_table(
        "ats_scores",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("resume_id", sa.Integer(), sa.ForeignKey("resumes.id"), nullable=True),
        sa.Column("job_description", sa.Text(), nullable=True),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("ats_score", sa.Float(), nullable=True),
        sa.Column("similarity_score", sa.Float(), nullable=True),
        sa.Column("skill_match_score", sa.Float(), nullable=True),
        sa.Column("matched_skills", sa.JSON(), nullable=True),
        sa.Column("missing_keywords", sa.JSON(), nullable=True),
        sa.Column("suggestions", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    # Reverse order so foreign keys never point at an already-dropped table.
    op.drop_table("ats_scores")
    op.drop_table("skills")
    op.drop_table("education")
    op.drop_table("experiences")
    op.drop_table("resumes")
    op.drop_table("users")
