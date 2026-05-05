from backend.services.ats_engine import calculate_ats_score


class FakeSkill:
    def __init__(self, name):
        self.skill_name = name


class FakeExp:
    def __init__(self, desc):
        self.description = desc
        self.ai_description = []


class FakeEdu:
    def __init__(self):
        self.degree = "B.Tech"
        self.field_of_study = "Computer Science"


class FakeResume:
    def __init__(self):
        self.summary = "Python developer"
        self.skills = [FakeSkill("Python"), FakeSkill("FastAPI"), FakeSkill("SQL")]
        self.experiences = [FakeExp("Built REST APIs using FastAPI")]
        self.education = [FakeEdu()]


resume = FakeResume()

job_description = "Looking for a Python developer with FastAPI and SQL experience"

result = calculate_ats_score(resume, job_description)

print(result)