from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask
from sqlalchemy.orm import Session, joinedload

from backend.database.database import get_db
from backend.database import models
from backend.services.pdf_generator import generate_resume_pdf

router = APIRouter(prefix="/pdf", tags=["PDF"])


@router.get("/resume/{resume_id}")
def get_resume_pdf(resume_id: int, db: Session = Depends(get_db)):

    resume = (
        db.query(models.Resume)
        .options(
            joinedload(models.Resume.user),
            joinedload(models.Resume.experiences),
            joinedload(models.Resume.education),
            joinedload(models.Resume.skills),
            joinedload(models.Resume.certifications),
            joinedload(models.Resume.awards),
        )
        .filter(models.Resume.id == resume_id)
        .first()
    )

    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    file_path = generate_resume_pdf(resume)

    # Delete the generated file once it has been streamed back to the client,
    # so temp PDFs don't accumulate on disk (see services/pdf_generator.py).
    cleanup = BackgroundTask(lambda: Path(file_path).unlink(missing_ok=True))

    return FileResponse(
        file_path,
        media_type="application/pdf",
        filename=f"resume_{resume_id}.pdf",
        background=cleanup,
    )
