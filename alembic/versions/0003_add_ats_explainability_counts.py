"""Add matched/total skill and experience counts to ats_scores

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-24

Phase E (ATS score explainability): the results screen used to show bare
percentages (ats_score, similarity_score, skill_match_score) with nothing
explaining why they were what they were. These new columns store the
counts behind skill_match_score (matched/total skills) and a new
"relevant experience" metric (see backend/services/ats_engine.py's
compute_relevant_experience), so the frontend can show "3 of 8 skills
matched" instead of just "37.5%".

Adds:
- ats_scores.matched_skills_count
- ats_scores.total_skills_count
- ats_scores.relevant_experience_count
- ats_scores.total_experience_count
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("ats_scores", sa.Column("matched_skills_count", sa.Integer(), nullable=True))
    op.add_column("ats_scores", sa.Column("total_skills_count", sa.Integer(), nullable=True))
    op.add_column("ats_scores", sa.Column("relevant_experience_count", sa.Integer(), nullable=True))
    op.add_column("ats_scores", sa.Column("total_experience_count", sa.Integer(), nullable=True))


def downgrade() -> None:
    # SQLite only supports DROP COLUMN natively on newer versions (3.35+).
    # Batch mode rebuilds the table under the hood, so this works regardless
    # of the SQLite version Alembic is running against (same approach as
    # migration 0002's downgrade).
    with op.batch_alter_table("ats_scores") as batch_op:
        batch_op.drop_column("total_experience_count")
        batch_op.drop_column("relevant_experience_count")
        batch_op.drop_column("total_skills_count")
        batch_op.drop_column("matched_skills_count")
