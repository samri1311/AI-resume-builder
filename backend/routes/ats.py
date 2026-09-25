# API endpoints for ATS operations
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from backend.database.database import get_db
from backend.database import models
from backend.schemas.ats import ATSRequest
from backend.schemas.response import APIResponse
from backend.services.ats_engine import calculate_ats_score

router = APIRouter(prefix="/ats", tags=["ATS"])


@router.post("/score", response_model=APIResponse)
def calculate_score(request: ATSRequest, db: Session = Depends(get_db)):

    # 1. Fetch resume + related data in one query (joinedload, not a manual
    #    reassignment of the relationship attributes — see review notes)
    resume = (
        db.query(models.Resume)
        .options(
            joinedload(models.Resume.experiences),
            joinedload(models.Resume.education),
            joinedload(models.Resume.skills),
        )
        .filter(models.Resume.id == request.resume_id)
        .first()
    )

    if not resume:
        return APIResponse(
            success=False,
            message="Resume not found",
            data=None
        )

    # 2. Calculate ATS score
    result = calculate_ats_score(resume, request.job_description)

    # 3. Persist this score so each resume keeps a history of past checks,
    #    instead of the result only ever living in the API response.
    score_row = models.ATSScore(
        resume_id=resume.id,
        job_description=request.job_description,
        score=int(round(result["ats_score"])),
        ats_score=result["ats_score"],
        similarity_score=result["similarity_score"],
        skill_match_score=result["skill_match_score"],
        matched_skills=result["matched_skills"],
        missing_keywords=result["missing_keywords"],
        suggestions=result["suggestions"],
        # Phase E (ATS score explainability)
        matched_skills_count=result["matched_skills_count"],
        total_skills_count=result["total_skills_count"],
        relevant_experience_count=result["relevant_experience_count"],
        total_experience_count=result["total_experience_count"],
    )
    db.add(score_row)
    db.commit()

    # 4. Return clean response
    return APIResponse(
        success=True,
        message="ATS score calculated successfully",
        data=result
    )
