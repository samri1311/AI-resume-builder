# backend/routes/resume.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from backend.database.database import get_db
from backend.database import models
from backend.schemas.resume import ResumeCreate, ResumeResponse
from backend.services.resume_service import create_resume_service

router = APIRouter(prefix="/resume", tags=["Resume"])


# ---------------- CREATE RESUME ----------------
@router.post("/", response_model=ResumeResponse)
def create_resume(resume: ResumeCreate, db: Session = Depends(get_db)):

    try:
        # Call service
        db_resume = create_resume_service(db, resume)

        # Commit once
        db.commit()

        # Reload full object with relationships
        db_resume = (
            db.query(models.Resume)
            .options(
                joinedload(models.Resume.user),
                joinedload(models.Resume.experiences),
                joinedload(models.Resume.education),
                joinedload(models.Resume.skills),
                joinedload(models.Resume.certifications),
                joinedload(models.Resume.awards)
            )
            .filter(models.Resume.id == db_resume.id)
            .first()
        )

        if not db_resume:
            raise HTTPException(status_code=404, detail="Resume not found after creation")

        return db_resume

    except Exception as e:
        db.rollback()
        print("Error creating resume:", e)
        raise HTTPException(status_code=500, detail="Internal Server Error")


# ---------------- GET RESUME ----------------
@router.get("/{resume_id}", response_model=ResumeResponse)
def get_resume(resume_id: int, db: Session = Depends(get_db)):

    resume = (
        db.query(models.Resume)
        .options(
            joinedload(models.Resume.user),
            joinedload(models.Resume.experiences),
            joinedload(models.Resume.education),
            joinedload(models.Resume.skills),
            joinedload(models.Resume.certifications),
            joinedload(models.Resume.awards)
        )
        .filter(models.Resume.id == resume_id)
        .first()
    )

    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    return resume