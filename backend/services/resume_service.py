# backend/services/resume_service.py

import asyncio

from sqlalchemy.orm import Session
from backend.database import models
from backend.services.ai_engine import enhance_experience_async


async def _enhance_or_skip(description):
    if not description:
        return {"success": False, "data": []}
    return await enhance_experience_async(description)


async def _enhance_all(experiences):
    # asyncio.gather() must be called from inside a running event loop —
    # building the gather() call before asyncio.run() has started one
    # raises "a coroutine was expected, got <_GatheringFuture ...>", so this
    # wrapper is what actually gets handed to asyncio.run() below.
    return await asyncio.gather(*[_enhance_or_skip(exp.description) for exp in experiences])


def create_resume_service(db: Session, resume):

    # 🔹 1. Check if user already exists
    existing_user = db.query(models.User).filter_by(email=resume.user.email).first()

    if existing_user:
        db_user = existing_user
    else:
        db_user = models.User(
            name=resume.user.name,
            email=resume.user.email,
            phone=resume.user.phone,
            website=resume.user.website
        )
        db.add(db_user)
        db.flush()

    # 🔹 2. Create Resume
    db_resume = models.Resume(
        user_id=db_user.id,
        title=resume.title,
        summary=resume.summary
    )
    db.add(db_resume)
    db.flush()

    # 🔹 3. Experiences — enhance every experience's description concurrently
    # (one Groq round-trip in parallel per experience) instead of awaiting
    # them one at a time, so a resume with several jobs listed doesn't wait
    # on N sequential AI calls. This function itself stays a plain `def`
    # (FastAPI runs it in a worker thread), so asyncio.run() here starts its
    # own event loop just for this batch — it doesn't touch or block the
    # app's main event loop.
    ai_results = asyncio.run(_enhance_all(resume.experiences))

    for exp, ai_result in zip(resume.experiences, ai_results):

        db_exp = models.Experience(
            resume_id=db_resume.id,
            job_title=exp.job_title,
            company=exp.company,
            location=exp.location,
            start_date=exp.start_date,
            end_date=exp.end_date,
            description=exp.description,
            ai_description=ai_result["data"] if ai_result["success"] else [],
            is_current=exp.is_current
        )

        db.add(db_exp)

    # 🔹 4. Education
    for edu in resume.education:
        db.add(models.Education(
            resume_id=db_resume.id,
            college=edu.college,
            degree=edu.degree,
            field_of_study=edu.field_of_study,
            start_year=edu.start_year,
            end_year=edu.end_year,
            details=edu.details
        ))

    # 🔹 5. Skills
    for skill in resume.skills:
        db.add(models.Skill(
            resume_id=db_resume.id,
            skill_name=skill.skill_name
        ))

    # 🔹 6. Certifications
    for cert in resume.certifications:
        db.add(models.Certification(
            resume_id=db_resume.id,
            name=cert.name,
            issuing_organization=cert.issuing_organization,
            year=cert.year
        ))

    # 🔹 7. Awards
    for award in resume.awards:
        db.add(models.Award(
            resume_id=db_resume.id,
            title=award.title,
            year=award.year
        ))

    return db_resume
