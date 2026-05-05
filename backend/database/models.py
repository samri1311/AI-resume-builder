# Database models
# backend/database/models.py

from sqlalchemy import Column, Integer, String, Text, ForeignKey, Boolean, DateTime, JSON
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
    created_at = Column(DateTime, default=datetime.utcnow)

    resume = relationship("Resume", back_populates="user", uselist=False)


# ---------------- RESUMES ----------------
class Resume(Base):
    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    summary = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="resume")
    experiences = relationship("Experience", back_populates="resume", cascade="all, delete")
    education = relationship("Education", back_populates="resume", cascade="all, delete")
    skills = relationship("Skill", back_populates="resume", cascade="all, delete")
    ats_scores = relationship("ATSScore", back_populates="resume", cascade="all, delete")


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
    score = Column(Integer)

    missing_keywords = Column(JSON)
    suggestions = Column(JSON)

    created_at = Column(DateTime, default=datetime.utcnow)

    resume = relationship("Resume", back_populates="ats_scores")