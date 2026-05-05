# Entry point for the AI Resume Builder backend
from fastapi import FastAPI
from backend.database.database import engine
from backend.database import models
from backend.routes import resume, ai
from backend.routes import ats
from backend.routes import pdf



# Create database tables
models.Base.metadata.create_all(bind=engine)

# Create FastAPI app instance
app = FastAPI(
    title="AI Resume Builder API",
    description="Backend for AI-powered resume builder",
    version="1.0.0"
)

# Root route
@app.get("/")
def read_root():
    return {"message": "Welcome to AI Resume Builder 🚀"}

# Include resume routes
app.include_router(resume.router)
app.include_router(ai.router)  
app.include_router(ats.router)
app.include_router(pdf.router)
# Health check route (optional but useful)
@app.get("/health")
def health_check():
    return {"status": "OK"}
