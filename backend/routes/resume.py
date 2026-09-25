# backend/routes/resume.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from backend.database.database import get_db
from backend.database import models
from backend.schemas.resume import ResumeCreate, ResumeResponse, ResumeUpdate, TailorPreviewRequest
from backend.schemas.response import APIResponse
from backend.services.resume_service import create_resume_service, update_resume_service
from backend.services.tailor_service import build_tailoring_preview

router = APIRouter(prefix="/resume", tags=["Resume"])

_RESUME_RELATIONSHIPS = (
    joinedload(models.Resume.user),
    joinedload(models.Resume.experiences),
    joinedload(models.Resume.education),
    joinedload(models.Resume.skills),
    joinedload(models.Resume.certifications),
    joinedload(models.Resume.awards),
)


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
            .options(*_RESUME_RELATIONSHIPS)
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
        .options(*_RESUME_RELATIONSHIPS)
        .filter(models.Resume.id == resume_id)
        .first()
    )

    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    return resume


# ---------------- UPDATE RESUME (Phase F) ----------------
@router.put("/{resume_id}", response_model=ResumeResponse)
def update_resume(resume_id: int, update: ResumeUpdate, db: Session = Depends(get_db)):

    try:
        update_resume_service(db, resume_id, update)
        db.commit()
    except ValueError:
        db.rollback()
        raise HTTPException(status_code=404, detail="Resume not found")
    except Exception as e:
        db.rollback()
        print("Error updating resume:", e)
        raise HTTPException(status_code=500, detail="Internal Server Error")

    db_resume = (
        db.query(models.Resume)
        .options(*_RESUME_RELATIONSHIPS)
        .filter(models.Resume.id == resume_id)
        .first()
    )

    if not db_resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    return db_resume


# ---------------- TAILOR PREVIEW (Phase F) ----------------
# Bridges the ATS Score screen's suggestions to an actual action: runs the
# same tailoring calls the "Generate from Job Description" pivot uses
# against this resume's REAL saved experiences/summary, and returns a
# preview - nothing is saved here. The frontend calls PUT /resume/{id}
# above with whichever parts of the preview the person accepts.
@router.post("/{resume_id}/tailor-preview", response_model=APIResponse)
def tailor_preview(resume_id: int, request: TailorPreviewRequest, db: Session = Depends(get_db)):

    resume = (
        db.query(models.Resume)
        .options(*_RESUME_RELATIONSHIPS)
        .filter(models.Resume.id == resume_id)
        .first()
    )

    if not resume:
        return APIResponse(success=False, message="Resume not found", data=None)

    result = build_tailoring_preview(resume, request.job_description)

    if not result["success"]:
        return APIResponse(success=False, message=result["error"], data=None)

    return APIResponse(
        success=True,
        message="Tailoring preview generated successfully",
        data=result["data"]
    )