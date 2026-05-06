# Streamlit frontend application
import streamlit as st
import requests

BASE_URL = "http://127.0.0.1:8000"

# ---------------- SESSION STATE ----------------

if "experiences" not in st.session_state:
    st.session_state.experiences = [
        {
            "job_title": "",
            "company": "",
            "location": "",
            "start_date": "",
            "end_date": "",
            "description": "",
            "ai_description": [],
            "is_current": False
        }
    ]

if "education" not in st.session_state:
    st.session_state.education = [
        {
            "college": "",
            "degree": "",
            "field_of_study": "",
            "start_year": "",
            "end_year": ""
        }
    ]


def render_resume_preview(resume):
    user = resume.get("user", {})

    st.subheader(user.get("name", "Resume"))
    contact = " | ".join(
        item for item in [user.get("email"), user.get("phone")] if item
    )
    if contact:
        st.caption(contact)

    if resume.get("summary"):
        st.markdown("#### Summary")
        st.write(resume["summary"])

    experiences = resume.get("experiences", [])
    if experiences:
        st.markdown("#### Experience")
        for exp in experiences:
            title = " - ".join(
                item for item in [exp.get("job_title"), exp.get("company")] if item
            )
            st.markdown(f"**{title or 'Experience'}**")
            meta = " | ".join(
                item
                for item in [
                    exp.get("location"),
                    f"{exp.get('start_date') or ''} - {exp.get('end_date') or 'Present'}",
                ]
                if item and item.strip(" -")
            )
            if meta:
                st.caption(meta)

            bullets = exp.get("ai_description") or []
            if bullets:
                for bullet in bullets:
                    st.markdown(f"- {bullet}")
            elif exp.get("description"):
                st.write(exp["description"])

    education = resume.get("education", [])
    if education:
        st.markdown("#### Education")
        for edu in education:
            st.markdown(f"**{edu.get('degree', '')} - {edu.get('college', '')}**")
            details = " | ".join(
                item
                for item in [
                    edu.get("field_of_study"),
                    f"{edu.get('start_year') or ''} - {edu.get('end_year') or ''}",
                ]
                if item and item.strip(" -")
            )
            if details:
                st.caption(details)

    skills = [skill.get("skill_name") for skill in resume.get("skills", []) if skill.get("skill_name")]
    if skills:
        st.markdown("#### Skills")
        st.write(", ".join(skills))

st.set_page_config(page_title="AI Resume Builder", layout="centered")

st.title("🚀 AI Resume Builder")

# ---------------- USER INFO ----------------
st.header("👤 User Info")

name = st.text_input("Name")
email = st.text_input("Email")
phone = st.text_input("Phone")

# ---------------- SUMMARY ----------------
st.header("🧾 Summary")
summary = st.text_area("Professional Summary")

# ---------------- EXPERIENCE ----------------
st.header("💼 Experience")

for i, exp in enumerate(st.session_state.experiences):

    st.subheader(f"Experience {i+1}")

    col1, col2 = st.columns(2)

    with col1:
        exp["job_title"] = st.text_input(
            "Job Title",
            value=exp.get("job_title", ""),
            key=f"job_title_{i}"
        )

        exp["company"] = st.text_input(
            "Company",
            value=exp.get("company", ""),
            key=f"company_{i}"
        )

        exp["location"] = st.text_input(
            "Location",
            value=exp.get("location", ""),
            key=f"location_{i}"
        )

    with col2:
        exp["start_date"] = st.text_input(
            "Start Date",
            value=exp.get("start_date", ""),
            key=f"start_date_{i}"
        )

        exp["end_date"] = st.text_input(
            "End Date",
            value=exp.get("end_date", ""),
            key=f"end_date_{i}"
        )

    exp["is_current"] = st.checkbox(
        "Currently Working Here",
        value=exp.get("is_current", False),
        key=f"is_current_{i}"
    )

    exp["description"] = st.text_area(
        "Experience Description",
        value=exp.get("description", ""),
        key=f"description_{i}"
    )
    if st.button("✨ Enhance Experience", key=f"enhance_{i}"):
        try:
            res = requests.post(f"{BASE_URL}/ai/enhance", 
                                json={
                                    "text": exp["description"],
                                    "style": "professional"
                                })
            data = res.json()
            if data["success"]:
                bullets = data["data"]["bullets"]
                exp["ai_description"] = bullets
                st.success("AI Enhanced Experience!")
                for b in bullets:
                    st.write(f"- {b}")
            else:
                st.error(data.get("message", "Failed to enhance experience"))        
                
        except Exception as e:
            st.error(f"Error: {e}")


    # REMOVE BUTTON
    if len(st.session_state.experiences) > 1:
        if st.button(f"❌ Remove Experience {i+1}", key=f"remove_exp_{i}"):
            st.session_state.experiences.pop(i)
            st.rerun()

    st.divider()

# ADD EXPERIENCE BUTTON
if st.button("➕ Add Experience"):
    st.session_state.experiences.append({
        "job_title": "",
        "company": "",
        "location": "",
        "start_date": "",
        "end_date": "",
        "description": "",
        "ai_description": [],
        "is_current": False
    })

    st.rerun()

# ---------------- EDUCATION ----------------
# ---------------- EDUCATION ----------------
st.header("🎓 Education")

for i, edu in enumerate(st.session_state.education):

    st.subheader(f"Education {i+1}")

    edu["college"] = st.text_input(
        "College",
        value=edu.get("college", ""),
        key=f"college_{i}"
    )

    edu["degree"] = st.text_input(
        "Degree",
        value=edu.get("degree", ""),
        key=f"degree_{i}"
    )

    edu["field_of_study"] = st.text_input(
        "Field of Study",
        value=edu.get("field_of_study", ""),
        key=f"field_{i}"
    )

    col1, col2 = st.columns(2)

    with col1:
        edu["start_year"] = st.text_input(
            "Start Year",
            value=edu.get("start_year", ""),
            key=f"start_year_{i}"
        )

    with col2:
        edu["end_year"] = st.text_input(
            "End Year",
            value=edu.get("end_year", ""),
            key=f"end_year_{i}"
        )

    # REMOVE BUTTON
    if len(st.session_state.education) > 1:
        if st.button(f"❌ Remove Education {i+1}", key=f"remove_edu_{i}"):
            st.session_state.education.pop(i)
            st.rerun()

    st.divider()

# ADD EDUCATION BUTTON
if st.button("➕ Add Education"):
    st.session_state.education.append({
        "college": "",
        "degree": "",
        "field_of_study": "",
        "start_year": "",
        "end_year": ""
    })

    st.rerun()

# ---------------- SKILLS ----------------
st.header("🛠 Skills")

skills_input = st.text_input("Skills (comma separated)")

# ---------------- AI ENHANCEMENT ----------------

# ---------------- CREATE RESUME ----------------
if st.button("Create Resume"):

    skills_list = [{"skill_name": s.strip()} for s in skills_input.split(",") if s.strip()]

    payload = {
        "user": {
            "name": name,
            "email": email,
            "phone": phone
        },
        "summary": summary,
        "experiences": st.session_state.experiences,
        "education": st.session_state.education,
        "skills": skills_list
    }

    try:
        res = requests.post(f"{BASE_URL}/resume/", json=payload)
        data = res.json()

        if res.status_code == 200:
            st.success("✅ Resume Created!")

            resume_id = data["id"]
            st.session_state["resume_id"] = resume_id
            st.session_state["resume"] = data

        else:
            st.error(f"Status: {res.status_code}")
            st.json(data)

    except Exception as e:
        st.error(f"Error: {e}")

if "resume" in st.session_state:
    st.header("📄 Resume Preview")
    render_resume_preview(st.session_state["resume"])


# ---------------- ATS SCORE ----------------
st.header("📊 ATS Score")

if "resume_id" in st.session_state:
    jd = st.text_area("Paste Job Description")

    if st.button("Check ATS Score"):

        payload = {
            "resume_id": st.session_state["resume_id"],
            "job_description": jd
        }

        try:
            res = requests.post(f"{BASE_URL}/ats/score", json=payload)
            data = res.json()

            if data["success"]:
                result = data["data"]

                st.subheader("📈 Results")

                st.metric("ATS Score", f"{result['ats_score']}%")
                st.metric("Similarity", f"{result['similarity_score']}%")
                st.metric("Skill Match", f"{result['skill_match_score']}%")

                st.subheader("✅ Matched Skills")
                st.write(result.get("matched_skills", []))

                st.subheader("❌ Missing Keywords")
                st.write(result.get("missing_keywords", []))

                st.subheader("💡 Suggestions")
                for s in result.get("suggestions", []):
                    st.write(f"- {s}")

            else:
                st.error(data["message"])

        except Exception as e:
            st.error(f"Error: {e}")

else:
    st.info("Create a resume first")


# ---------------- PDF DOWNLOAD ----------------
st.header("📥 Download Resume")

if "resume_id" in st.session_state:

    if st.button("Generate PDF"):
        try:
            pdf_url = f"{BASE_URL}/pdf/resume/{st.session_state['resume_id']}"
            response = requests.get(pdf_url)

            if response.status_code == 200:
                st.download_button(
                    label="Download PDF",
                    data=response.content,
                    file_name="resume.pdf",
                    mime="application/pdf"
                )
            else:
                st.error("Failed to generate PDF")
                st.write(response.text)

        except Exception as e:
            st.error(f"Error: {e}")
