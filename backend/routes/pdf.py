from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.database.database import get_db
from backend.database import models
from backend.services.pdf_generator import generate_resume_pdf

router = APIRouter(prefix="/pdf", tags=["PDF"])


@router.get("/resume/{resume_id}")
def get_resume_pdf(resume_id: int, db: Session = Depends(get_db)):

    resume = db.query(models.Resume).filter(models.Resume.id == resume_id).first()

    if not resume:
        return {"error": "Resume not found"}

    # Load relations
    resume.user
    resume.experiences = db.query(models.Experience).filter_by(resume_id=resume.id).all()
    resume.education = db.query(models.Education).filter_by(resume_id=resume.id).all()
    resume.skills = db.query(models.Skill).filter_by(resume_id=resume.id).all()

    file_path = generate_resume_pdf(resume)

    return FileResponse(file_path, media_type="application/pdf", filename=file_path)