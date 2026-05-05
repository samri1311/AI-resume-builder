# API endpoints for AI operations
# backend/routes/ai.py

from fastapi import APIRouter
from backend.schemas.ai import EnhanceRequest
from backend.schemas.response import APIResponse
from backend.services.ai_engine import enhance_experience

router = APIRouter(prefix="/ai", tags=["AI"])


@router.post("/enhance", response_model=APIResponse)
def enhance_text(request: EnhanceRequest):

    result = enhance_experience(request.text, request.style)

    if not result["success"]:
        return APIResponse(
            success=False,
            message="AI enhancement failed",
            data=result["error"]
        )

    return APIResponse(
        success=True,
        message="Text enhanced successfully",
        data={
            "status": "completed",
            "bullets": result["data"]
        }
    )