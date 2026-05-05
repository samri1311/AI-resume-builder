# API endpoints for ATS operations
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database.database import get_db
from backend.database import models
from backend.schemas.ats import ATSRequest
from backend.schemas.response import APIResponse
from backend.services.ats_engine import calculate_ats_score

router = APIRouter(prefix="/ats", tags=["ATS"])


@router.post("/score", response_model=APIResponse)
def calculate_score(request: ATSRequest, db: Session = Depends(get_db)):

    # 1. Fetch resume from DB
    resume = db.query(models.Resume).filter(models.Resume.id == request.resume_id).first()

    if not resume:
        return APIResponse(
            success=False,
            message="Resume not found",
            data=None
        )

    # 2. Load related data (important!)
    resume.experiences = db.query(models.Experience).filter_by(resume_id=resume.id).all()
    resume.education = db.query(models.Education).filter_by(resume_id=resume.id).all()
    resume.skills = db.query(models.Skill).filter_by(resume_id=resume.id).all()

    # 3. Calculate ATS score
    result = calculate_ats_score(resume, request.job_description)

    # 4. Return clean response
    return APIResponse(
        success=True,
        message="ATS score calculated successfully",
        data=result
    )
