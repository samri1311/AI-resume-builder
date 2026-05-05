# backend/schemas/ai.py

from pydantic import BaseModel


class EnhanceRequest(BaseModel):
    text: str
    style: str = "professional"


class EnhanceResponse(BaseModel):
    enhanced_text: str