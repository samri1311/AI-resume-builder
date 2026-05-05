# backend/services/resume_service.py

from sqlalchemy.orm import Session
from backend.database import models
from backend.services.ai_engine import enhance_experience


def create_resume_service(db: Session, resume):

    # 🔹 1. Check if user already exists
    existing_user = db.query(models.User).filter_by(email=resume.user.email).first()

    if existing_user:
        db_user = existing_user
    else:
        db_user = models.User(
            name=resume.user.name,
            email=resume.user.email,
            phone=resume.user.phone
        )
        db.add(db_user)
        db.flush()

    # 🔹 2. Create Resume
    db_resume = models.Resume(
        user_id=db_user.id,
        summary=resume.summary
    )
    db.add(db_resume)
    db.flush()

    # 🔹 3. Experiences
    for exp in resume.experiences:

        ai_result = (
            enhance_experience(exp.description)
            if exp.description else {"success": False, "data": []}
        )

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
            end_year=edu.end_year
        ))

    # 🔹 5. Skills
    for skill in resume.skills:
        db.add(models.Skill(
            resume_id=db_resume.id,
            skill_name=skill.skill_name
        ))

    return db_resume