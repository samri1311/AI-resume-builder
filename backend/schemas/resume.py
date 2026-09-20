# Pydantic models for resume
# backend/schemas/resume.py

from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime
from pydantic import Field

# ---------------- USER ----------------
class UserBase(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    website: Optional[str] = None


class UserCreate(UserBase):
    pass


class UserResponse(UserBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ---------------- EXPERIENCE ----------------
class ExperienceBase(BaseModel):
    job_title: str
    company: str
    location: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    description: Optional[str] = None
    is_current: Optional[bool] = False


class ExperienceCreate(ExperienceBase):
    pass


class ExperienceResponse(ExperienceBase):
    id: int
    ai_description: Optional[List[str]] = None

    class Config:
        from_attributes = True


# ---------------- EDUCATION ----------------
class EducationBase(BaseModel):
    college: str
    degree: str
    field_of_study: Optional[str] = None
    start_year: Optional[str] = None
    end_year: Optional[str] = None
    # Free-text, meant to hold 1-2 short lines (e.g. "Major in X", "Thesis on
    # Y") — not enforced beyond a generous length cap, this is a soft guard,
    # not a bullet counter.
    details: Optional[str] = Field(default=None, max_length=300)


class EducationCreate(EducationBase):
    pass


class EducationResponse(EducationBase):
    id: int

    class Config:
        from_attributes = True


# ---------------- SKILLS ----------------
class SkillBase(BaseModel):
    skill_name: str


class SkillCreate(SkillBase):
    pass


class SkillResponse(SkillBase):
    id: int

    class Config:
        from_attributes = True


# ---------------- CERTIFICATIONS ----------------
class CertificationBase(BaseModel):
    name: str
    issuing_organization: Optional[str] = None
    year: Optional[str] = None


class CertificationCreate(CertificationBase):
    pass


class CertificationResponse(CertificationBase):
    id: int

    class Config:
        from_attributes = True


# ---------------- AWARDS ----------------
class AwardBase(BaseModel):
    title: str
    year: Optional[str] = None


class AwardCreate(AwardBase):
    pass


class AwardResponse(AwardBase):
    id: int

    class Config:
        from_attributes = True


# ---------------- ATS SCORE ----------------
class ATSScoreBase(BaseModel):
    job_description: str


class ATSScoreCreate(ATSScoreBase):
    pass


class ATSScoreResponse(ATSScoreBase):
    id: int
    score: int
    missing_keywords: Optional[dict] = None
    suggestions: Optional[dict] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ---------------- RESUME ----------------
class ResumeBase(BaseModel):
    title: Optional[str] = None
    summary: Optional[str] = None


class ResumeCreate(ResumeBase):
    user: UserCreate
    experiences: List[ExperienceCreate] = Field(default_factory=list)
    education: List[EducationCreate] = Field(default_factory=list)
    skills: List[SkillCreate] = Field(default_factory=list)
    certifications: List[CertificationCreate] = Field(default_factory=list)
    awards: List[AwardCreate] = Field(default_factory=list)


class ResumeResponse(ResumeBase):
    id: int
    user: UserResponse
    experiences: List[ExperienceResponse]
    education: List[EducationResponse]
    skills: List[SkillResponse]
    certifications: List[CertificationResponse]
    awards: List[AwardResponse]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
