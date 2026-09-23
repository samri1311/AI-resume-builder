# backend/schemas/draft.py
"""Phase A (pivot: paste a job description + background -> tailored draft).

Schema for the AI's best-effort extraction of a person's background
(pasted resume text, a LinkedIn export, rough notes, whatever they paste)
into structured fields.

Deliberately permissive - every field is optional and every list defaults
to empty. The whole point of this schema is that the model may not find
everything in a given piece of text, and a partial parse should still come
back as something usable rather than raising a validation error. The
person reviews and fills in gaps in the existing form afterward (Phase D),
so "mostly right, with some blanks" is a fine outcome here - "crashes
because a date was in an unexpected format" is not.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class ParsedExperience(BaseModel):
    job_title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    description: Optional[str] = None
    is_current: Optional[bool] = False


class ParsedEducation(BaseModel):
    college: Optional[str] = None
    degree: Optional[str] = None
    field_of_study: Optional[str] = None
    start_year: Optional[str] = None
    end_year: Optional[str] = None
    details: Optional[str] = None


class ParsedCertification(BaseModel):
    name: Optional[str] = None
    issuing_organization: Optional[str] = None
    year: Optional[str] = None


class ParsedAward(BaseModel):
    title: Optional[str] = None
    year: Optional[str] = None


class ParsedBackground(BaseModel):
    # Not EmailStr on purpose: this is a best-effort AI extraction, not a
    # validated submission, and a malformed or missing email shouldn't
    # crash the whole parse. Whatever comes back gets validated properly
    # (as EmailStr) only later, if and when the person submits the
    # reviewed form for real via the existing ResumeCreate/UserCreate
    # schemas in resume.py.
    name: Optional[str] = None
    title: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    summary: Optional[str] = None
    experiences: List[ParsedExperience] = Field(default_factory=list)
    education: List[ParsedEducation] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    certifications: List[ParsedCertification] = Field(default_factory=list)
    awards: List[ParsedAward] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Phase C (pivot: paste a job description + background -> tailored draft).
#
# Ties Phase A's parsing and Phase B's job-description-aware tailoring
# together into one request/response pair for the new POST /draft/generate
# route (see backend/services/draft_service.py and backend/routes/draft.py).
# ---------------------------------------------------------------------------

class DraftGenerateRequest(BaseModel):
    job_description: str
    background_text: str


class DraftExperience(ParsedExperience):
    # Populated with the job-tailored bullets from
    # ai_engine.enhance_experience_for_job(_async). Deliberately reuses the
    # same field name Experience/ExperienceCreate already use elsewhere in
    # the app (schemas/resume.py) so that, once the person reviews this
    # draft and clicks "Create Resume" (Phase D), it flows straight into
    # ExperienceCreate.ai_description and resume_service's existing
    # Phase 1 dedup logic (_enhance_or_skip) - which already skips
    # re-calling Groq whenever ai_description is already populated -
    # without Phase D having to know or care that these bullets came from
    # job tailoring rather than the plain "Enhance Experience" button.
    ai_description: List[str] = Field(default_factory=list)


class DraftResponse(BaseModel):
    # Flat, mirroring ParsedBackground's own top-level shape exactly (not
    # nested under a "user" sub-object) so the frontend can review/edit it
    # with the same shape it already knows from parse_background.
    name: Optional[str] = None
    title: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    summary: Optional[str] = None
    experiences: List[DraftExperience] = Field(default_factory=list)
    education: List[ParsedEducation] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    certifications: List[ParsedCertification] = Field(default_factory=list)
    awards: List[ParsedAward] = Field(default_factory=list)
    # Soft, non-blocking heads-up for the person reviewing the draft (e.g.
    # "no email found", "no work experience found") - never prevents the
    # draft from being returned, just flags what to double check.
    warnings: List[str] = Field(default_factory=list)
