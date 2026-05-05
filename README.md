# AI-resume-builder
🚀 AI Resume Builder with ATS Scoring
An end-to-end AI-powered resume builder that helps users create professional, ATS-friendly resumes with intelligent content enhancement and scoring.

📌 Overview
This project is a full-stack system that allows users to:
Create structured resumes
Enhance content using AI (LLMs)
Evaluate resumes using an ATS scoring system
Export resumes as clean, professional PDFs

🧠 Key Features
🧾 Resume Builder
Add personal details, skills, education, and experience
Structured data storage using a relational database
🤖 AI Content Enhancement
Converts raw job descriptions into professional bullet points
Uses LLMs (Groq / LLaMA 3) for intelligent rewriting
📊 ATS Scoring System 💥
Compares resume against job descriptions
Provides:
Match score (0–100)
Missing keywords
Suggestions for improvement
📄 PDF Export
Generates ATS-friendly resumes
Clean, minimal, no complex formatting

🏗️ Architecture
Frontend (Streamlit / React)
        ↓
FastAPI (API Layer)
        ↓
Service Layer (AI, ATS, PDF)
        ↓
SQLAlchemy (ORM)
        ↓
SQLite Database


📁 Project Structure
ai-resume-builder/
│
├── backend/
│   ├── main.py
│   ├── core/
│   │   └── config.py
│   ├── database/
│   │   ├── database.py
│   │   ├── models.py
│   ├── schemas/
│   │   └── resume.py
│   ├── routes/
│   │   ├── resume.py
│   │   ├── ai.py
│   │   ├── ats.py
│   ├── services/
│   │   ├── ai_engine.py
│   │   ├── ats_engine.py
│   │   ├── pdf_service.py
│   └── tests/
│
├── frontend/
│   └── streamlit_app.py
│
├── .env
├── requirements.txt
└── README.md


🛠️ Tech Stack
Backend
FastAPI
SQLAlchemy
SQLite
Pydantic
AI Layer
Groq API (LLaMA 3)
python-dotenv
ATS Engine
scikit-learn
numpy
PDF Generation
reportLab
Frontend
Streamlit

⚙️ Installation
1. Clone the Repository
git clone https://github.com/your-username/ai-resume-builder.git
cd ai-resume-builder


2. Create Virtual Environment
python -m venv venv
source venv/bin/activate  # (Linux/Mac)
venv\Scripts\activate     # (Windows)


3. Install Dependencies
pip install -r requirements.txt


4. Setup Environment Variables
Create a .env file:
GROQ_API_KEY=your_api_key_here


5. Run Backend Server
uvicorn backend.main:app --reload

Visit:
http://127.0.0.1:8000/docs


6. Run Frontend (Streamlit)
streamlit run frontend/streamlit_app.py


🔌 API Endpoints
Resume
POST /resume → Create resume
GET /resume/{id} → Fetch resume
AI
POST /ai/enhance → Improve text
ATS
POST /ats/score → Get ATS score
PDF
GET /resume/{id}/pdf → Download resume

🧠 ATS Scoring Logic
TF-IDF vectorization
Cosine similarity between:
Resume
Job Description
Keyword extraction for missing skills

🎯 Example Output
{
  "score": 82,
  "missing_keywords": ["Docker", "Kubernetes"],
  "suggestions": [
    "Add cloud deployment experience",
    "Include measurable achievements"
  ]
}


🔐 Security
API keys stored in .env
No sensitive data hardcoded

🚀 Future Improvements
User authentication (JWT)
Multiple resumes per user
React frontend
PostgreSQL integration
Resume templates

🧑‍💻 Author
Samriddhi Shanker
