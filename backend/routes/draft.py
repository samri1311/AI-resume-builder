# API endpoints for draft generation
# backend/routes/draft.py
"""Phase C (pivot: paste a job description + background -> tailored draft).

POST /draft/generate: reuses the existing APIResponse envelope, same
pattern as /ai/enhance and /ats/score. Nothing here is persisted to the
database - this is a preview the person reviews and edits before ever
clicking "Create Resume" (Phase D), which is what actually saves anything.

POST /draft/extract-text: the deferred "import a resume file" piece from
the original pivot plan - takes an uploaded PDF/Word file and returns its
plain text, so the frontend can drop it into the same "Your Background"
box the paste-text flow already fills. Pure text extraction (see
services/file_extraction.py) - the text still goes through the exact same
parse_background() prompt as anything typed in by hand.
"""

from fastapi import APIRouter, File, UploadFile

from backend.schemas.draft import DraftGenerateRequest
from backend.schemas.response import APIResponse
from backend.services.draft_service import generate_draft
from backend.services.file_extraction import extract_resume_text

router = APIRouter(prefix="/draft", tags=["Draft"])


@router.post("/generate", response_model=APIResponse)
def generate(request: DraftGenerateRequest):

    result = generate_draft(request.job_description, request.background_text)

    if not result["success"]:
        # Fix (2026-09-23): the frontend only ever displays `message` on the
        # error path (st.error(data.get("message", ...))), never `data` - so
        # putting the real reason in `data` and a generic string in `message`
        # meant genuine errors (e.g. Groq "model_not_found") were silently
        # swallowed and only visible in the backend console. Surface the
        # real reason in `message` instead, with the old generic string as a
        # fallback if `result["error"]` is ever empty.
        return APIResponse(
            success=False,
            message=result["error"] or "Draft generation failed",
            data=None
        )

    return APIResponse(
        success=True,
        message="Draft generated successfully",
        data=result["data"]
    )


@router.post("/extract-text", response_model=APIResponse)
async def extract_text(file: UploadFile = File(...)):

    contents = await file.read()
    result = extract_resume_text(file.filename, contents)

    if not result["success"]:
        return APIResponse(
            success=False,
            message=result["error"],
            data=None
        )

    return APIResponse(
        success=True,
        message="Text extracted successfully",
        data={"text": result["data"]}
    )
