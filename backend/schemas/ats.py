from pydantic import BaseModel

class ATSRequest(BaseModel):
    resume_id: int
    job_description: str