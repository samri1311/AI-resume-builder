# backend/tests/test_resume_update.py
"""Phase F: update_resume_service - the first way to change a saved resume
in place rather than only ever create a new one.

Uses a throwaway in-memory SQLite DB and builds fixtures directly via the
ORM (bypassing create_resume_service, which calls Groq) so these stay
fast, deterministic unit tests with no network/mocking involved.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database.database import Base
from backend.database import models
from backend.schemas.resume import ExperienceUpdate, ResumeUpdate
from backend.services.resume_service import update_resume_service


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def saved_resume(db_session):
    user = models.User(name="Jordan Rivera", email="jordan@example.com")
    db_session.add(user)
    db_session.flush()

    resume = models.Resume(user_id=user.id, summary="Original summary")
    db_session.add(resume)
    db_session.flush()

    exp = models.Experience(
        resume_id=resume.id,
        job_title="Engineer",
        company="Acme",
        description="Original description",
        ai_description=[],
    )
    db_session.add(exp)
    db_session.commit()

    return resume


def test_update_resume_service_updates_summary(db_session, saved_resume):
    update = ResumeUpdate(summary="New tailored summary", experiences=[])

    update_resume_service(db_session, saved_resume.id, update)
    db_session.commit()

    refreshed = db_session.query(models.Resume).filter_by(id=saved_resume.id).first()
    assert refreshed.summary == "New tailored summary"


def test_update_resume_service_updates_experience_ai_description(db_session, saved_resume):
    exp_id = saved_resume.experiences[0].id
    update = ResumeUpdate(
        experiences=[
            ExperienceUpdate(id=exp_id, ai_description=["Tailored bullet one.", "Tailored bullet two."])
        ],
    )

    update_resume_service(db_session, saved_resume.id, update)
    db_session.commit()

    refreshed_exp = db_session.query(models.Experience).filter_by(id=exp_id).first()
    assert refreshed_exp.ai_description == ["Tailored bullet one.", "Tailored bullet two."]
    # description untouched since it wasn't part of this update
    assert refreshed_exp.description == "Original description"


def test_update_resume_service_can_update_description_too(db_session, saved_resume):
    exp_id = saved_resume.experiences[0].id
    update = ResumeUpdate(
        experiences=[ExperienceUpdate(id=exp_id, description="Edited raw description")],
    )

    update_resume_service(db_session, saved_resume.id, update)
    db_session.commit()

    refreshed_exp = db_session.query(models.Experience).filter_by(id=exp_id).first()
    assert refreshed_exp.description == "Edited raw description"


def test_update_resume_service_ignores_experience_id_not_on_this_resume(db_session, saved_resume):
    update = ResumeUpdate(experiences=[ExperienceUpdate(id=999999, ai_description=["Should not apply"])])

    # Should not raise - a bad/stale id is silently skipped rather than
    # failing the whole update.
    update_resume_service(db_session, saved_resume.id, update)
    db_session.commit()


def test_update_resume_service_raises_for_missing_resume(db_session):
    update = ResumeUpdate(summary="Doesn't matter")

    with pytest.raises(ValueError):
        update_resume_service(db_session, 999999, update)


def test_update_resume_service_leaves_summary_unset_when_none(db_session, saved_resume):
    update = ResumeUpdate(summary=None, experiences=[])

    update_resume_service(db_session, saved_resume.id, update)
    db_session.commit()

    refreshed = db_session.query(models.Resume).filter_by(id=saved_resume.id).first()
    assert refreshed.summary == "Original summary"
