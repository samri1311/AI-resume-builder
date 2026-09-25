# Database models
# backend/database/models.py

from sqlalchemy import Column, Integer, String, Text, ForeignKey, Boolean, DateTime, JSON, Float
from sqlalchemy.orm import relationship
from datetime import datetime

from .database import Base


# ---------------- USERS ----------------
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    phone = Column(String)
    website = Column(String)  # portfolio / LinkedIn / personal site — stable across resumes
    created_at = Column(DateTime, default=datetime.utcnow)

    resume = relationship("Resume", back_populates="user", uselist=False)


# ---------------- RESUMES ----------------
class Resume(Base):
    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String)  # headline shown under the name, e.g. "UX Designer" — varies per resume
    summary = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="resume")
    experiences = relationship("Experience", back_populates="resume", cascade="all, delete")
    education = relationship("Education", back_populates="resume", cascade="all, delete")
    skills = relationship("Skill", back_populates="resume", cascade="all, delete")
    ats_scores = relationship("ATSScore", back_populates="resume", cascade="all, delete")
    certifications = relationship("Certification", back_populates="resume", cascade="all, delete")
    awards = relationship("Award", back_populates="resume", cascade="all, delete")


# ---------------- EXPERIENCES ----------------
class Experience(Base):
    __tablename__ = "experiences"

    id = Column(Integer, primary_key=True, index=True)
    resume_id = Column(Integer, ForeignKey("resumes.id"))

    job_title = Column(String)
    company = Column(String)
    location = Column(String)

    start_date = Column(String)
    end_date = Column(String)

    description = Column(Text)
    ai_description = Column(JSON)

    is_current = Column(Boolean, default=False)

    resume = relationship("Resume", back_populates="experiences")


# ---------------- EDUCATION ----------------
class Education(Base):
    __tablename__ = "education"

    id = Column(Integer, primary_key=True, index=True)
    resume_id = Column(Integer, ForeignKey("resumes.id"))

    college = Column(String)
    degree = Column(String)
    field_of_study = Column(String)

    start_year = Column(String)
    end_year = Column(String)

    # Free-text notes rendered as 1-2 bullets under the entry (e.g. "Major in
    # X", "Thesis on Y") — not a repeatable list, just a couple of lines.
    details = Column(Text)

    resume = relationship("Resume", back_populates="education")


# ---------------- SKILLS ----------------
class Skill(Base):
    __tablename__ = "skills"

    id = Column(Integer, primary_key=True, index=True)
    resume_id = Column(Integer, ForeignKey("resumes.id"))

    skill_name = Column(String)

    resume = relationship("Resume", back_populates="skills")


# ---------------- ATS SCORES ----------------
class ATSScore(Base):
    __tablename__ = "ats_scores"

    id = Column(Integer, primary_key=True, index=True)
    resume_id = Column(Integer, ForeignKey("resumes.id"))

    job_description = Column(Text)
    score = Column(Integer)  # legacy column, kept for backward compatibility with older rows

    # Added by backend/database/update_ats_table.py — mapped here so the ORM
    # actually knows about them (previously the raw ALTER TABLE ran with no
    # matching model fields, so these columns existed on disk but were
    # invisible to SQLAlchemy).
    ats_score = Column(Float)
    similarity_score = Column(Float)
    skill_match_score = Column(Float)
    matched_skills = Column(JSON)

    missing_keywords = Column(JSON)
    suggestions = Column(JSON)

    # Phase E (ATS score explainability): the counts behind skill_match_score
    # and the new "relevant experience" metric, so the frontend can show
    # "3 of 8 skills matched" instead of just a bare percentage.
    matched_skills_count = Column(Integer)
    total_skills_count = Column(Integer)
    relevant_experience_count = Column(Integer)
    total_experience_count = Column(Integer)

    created_at = Column(DateTime, default=datetime.utcnow)

    resume = relationship("Resume", back_populates="ats_scores")


# ---------------- CERTIFICATIONS ----------------
class Certification(Base):
    __tablename__ = "certifications"

    id = Column(Integer, primary_key=True, index=True)
    resume_id = Column(Integer, ForeignKey("resumes.id"))

    name = Column(String, nullable=False)
    issuing_organization = Column(String)
    year = Column(String)

    resume = relationship("Resume", back_populates="certifications")


# ---------------- AWARDS ----------------
class Award(Base):
    __tablename__ = "awards"

    id = Column(Integer, primary_key=True, index=True)
    resume_id = Column(Integer, ForeignKey("resumes.id"))

    title = Column(String, nullable=False)
    year = Column(String)

    resume = relationship("Resume", back_populates="awards")