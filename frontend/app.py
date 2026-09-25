# Streamlit frontend application
#
# --- Frontend correction pass (Phases 1-6) ---
# Search this file for "Phase 1" / "Phase 2" / ... / "Phase 6" comments to
# find each change:
#   Phase 1 - "Enhance Experience" bullets are now sent along with the
#             resume-creation payload (see the new "ai_description" field
#             on each experience) so the backend's own enhancement call
#             (backend/services/resume_service.py) can reuse them instead
#             of independently calling Groq a second time with possibly
#             different output. If the description is edited after
#             enhancing, the stale bullets are cleared automatically so
#             they're never sent as if still current. Requires the
#             matching backend/schemas/resume.py + resume_service.py
#             changes made alongside this file - not frontend-only.
#   Phase 2 - explicit timeout= on every requests.post/get call, plus a
#             dedicated "timed out" message instead of a generic error.
#   Phase 3 - the generated PDF now persists in session_state, so the
#             download button no longer disappears on the next rerun.
#   Phase 4 - API response parsing uses .get(...) instead of direct dict
#             indexing (e.g. data["success"]), so an unexpected response
#             shape shows a message instead of a raw KeyError.
#   Phase 5 - basic validation (name/email) before "Create Resume" submits,
#             instead of relying on the backend's 422 response.
#   Phase 6 - removed a duplicated section-header comment and an orphaned
#             one with no code under it.
#
# --- Pivot: paste a job description + background -> tailored draft ---
#   Phase D - a mode choice ("Build manually" / "Generate from Job
#             Description") right under the title. The manual form below
#             is completely unchanged either way; the new mode just adds a
#             "Generate Tailored Draft" call to the backend's new
#             /draft/generate route (Phases A-C) that pre-fills the same
#             session_state structures the manual form already reads from
#             - so the person lands in the same familiar, editable form
#             either way, just with a head start. See "Phase D" comments
#             below for exactly what that pre-fill touches.
#   Phase D (fix) - the manual form now stays hidden in "Generate from Job
#             Description" mode until a draft has actually been generated,
#             instead of always rendering an empty form right under the
#             draft inputs.
#   Import Resume File - an "Use This File as Background" option next to
#             the "Your Background" box: uploads a PDF/Word resume to the
#             new backend route POST /draft/extract-text (see
#             backend/services/file_extraction.py) and drops the extracted
#             plain text into that same box for review, as an alternative
#             to typing/pasting it. Requires new dependencies - see
#             requirements.txt (pypdf, python-docx, python-multipart).
import os

import streamlit as st
import requests
from dotenv import load_dotenv

load_dotenv()

# Was hardcoded to localhost — now overridable via .env / the environment so
# this can point at a deployed backend without editing source.
BASE_URL = os.getenv("RESUME_BUILDER_API_URL", "http://127.0.0.1:8000")

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
            # Phase 1: the description text that "ai_description" above was
            # actually generated from, so we can tell later if it's gone
            # stale (see the invalidation check in the Experience loop).
            "ai_description_source": "",
            # Phase F: a proposed-but-not-yet-applied Enhance Experience
            # result, and the description text it was generated from.
            "_pending_ai_bullets": [],
            "_pending_ai_source": "",
            "_pending_ai_style": "",
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
            "end_year": "",
            "details": ""
        }
    ]

if "certifications" not in st.session_state:
    st.session_state.certifications = []

if "awards" not in st.session_state:
    st.session_state.awards = []

# Phase D (fix): tracks whether a tailored draft has actually been
# generated yet this session - see the entry-mode section below, and the
# "if entry_mode == ... or st.session_state.get("draft_ready")" guard
# further down that decides whether the manual form is shown at all.
if "draft_ready" not in st.session_state:
    st.session_state.draft_ready = False


def render_resume_preview(resume):
    user = resume.get("user", {})

    st.subheader(user.get("name", "Resume"))

    if resume.get("title"):
        st.caption(resume["title"])

    contact = " | ".join(
        item for item in [user.get("email"), user.get("phone"), user.get("website")] if item
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

            if edu.get("details"):
                for line in edu["details"].splitlines():
                    if line.strip():
                        st.markdown(f"- {line.strip()}")

    skills = [skill.get("skill_name") for skill in resume.get("skills", []) if skill.get("skill_name")]
    if skills:
        st.markdown("#### Skills")
        st.write(", ".join(skills))

    certifications = resume.get("certifications", [])
    awards = resume.get("awards", [])
    if certifications or awards:
        st.markdown("#### Certifications & Awards")
        for cert in certifications:
            bit = cert.get("name", "")
            if cert.get("issuing_organization"):
                bit += f" ({cert['issuing_organization']})"
            if cert.get("year"):
                bit += f", {cert['year']}"
            st.markdown(f"- {bit}")
        for award in awards:
            bit = award.get("title", "")
            if award.get("year"):
                bit += f" ({award['year']})"
            st.markdown(f"- {bit}")

st.set_page_config(page_title="AI Resume Builder", layout="centered")

st.title("🚀 AI Resume Builder")

# ---------------- ENTRY MODE (Phase D) ----------------
# Phase D: a second way into the same form below - paste a job description
# + your background and let the backend (Phases A-C: parse_background +
# job-description-aware tailoring) produce a first draft, instead of
# typing everything in by hand. "Build manually" is the default so nothing
# changes for anyone who ignores this section entirely - the form under
# it is identical either way, this only ever pre-fills it.
st.header("📝 How would you like to start?")

entry_mode = st.radio(
    "Choose how to start this resume",
    ["Build manually", "Generate from Job Description"],
    key="entry_mode",
    label_visibility="collapsed"
)

if entry_mode == "Generate from Job Description":
    draft_job_description = st.text_area(
        "Job Description",
        key="draft_job_description",
        help="Paste the job posting you're tailoring this resume for."
    )

    # Import Resume File: an alternative to typing/pasting the background
    # text below - lets someone upload an existing resume (PDF or Word) and
    # have its text pulled out and dropped into the same box. Deliberately
    # a separate, explicit button rather than extracting automatically the
    # moment a file is chosen - every other AI/parsing action in this app
    # (Enhance Experience, Generate Tailored Draft, Create Resume...) is a
    # distinct click too, and extracting on every widget rerun would mean
    # re-uploading the same file to the backend far more often than needed.
    st.caption("Or import an existing resume to use as your background:")
    uploaded_resume = st.file_uploader(
        "Import a resume (PDF or Word)",
        type=["pdf", "docx"],
        key="background_file_upload",
        label_visibility="collapsed"
    )

    if uploaded_resume is not None and st.button("📄 Use This File as Background"):
        try:
            files = {"file": (uploaded_resume.name, uploaded_resume.getvalue())}
            # Text extraction itself is fast (no Groq call involved) - this
            # timeout is really just guarding against a stalled connection,
            # not slow processing.
            res = requests.post(f"{BASE_URL}/draft/extract-text", files=files, timeout=30)
            data = res.json()

            if data.get("success"):
                # Setting the "Your Background" widget's own session_state
                # key BEFORE that widget is created just below is what
                # actually makes the imported text show up there - see the
                # same pattern (and the same reason) in the "Generate
                # Tailored Draft" handler further down. This REPLACES
                # whatever was already typed in that box, which matches
                # what the button says it does ("use this file AS the
                # background") - it's still fully editable afterward.
                st.session_state["draft_background_text"] = data.get("data", {}).get("text", "")
                st.success(f"Imported text from {uploaded_resume.name} - review it below, then generate your draft.")
            else:
                st.error(data.get("message", "Couldn't extract text from that file."))

        except requests.exceptions.Timeout:
            st.error("Importing the file timed out. Please try again.")
        except Exception as e:
            st.error(f"Error: {e}")

    draft_background_text = st.text_area(
        "Your Background",
        key="draft_background_text",
        help="Paste your existing resume, a LinkedIn export, or just describe your experience in your own words - or import a file above."
    )

    if st.button("✨ Generate Tailored Draft"):
        if not draft_job_description.strip():
            st.warning("Paste a job description first.")
        elif not draft_background_text.strip():
            st.warning("Paste some background first.")
        else:
            try:
                # Generous timeout: unlike the other calls in this file,
                # this one runs parse_background first and only THEN the
                # tailoring calls (summary + every experience, concurrently)
                # - two sequential Groq round-trips, not one - so it's the
                # slowest single request this app makes.
                res = requests.post(
                    f"{BASE_URL}/draft/generate",
                    json={
                        "job_description": draft_job_description,
                        "background_text": draft_background_text
                    },
                    timeout=90
                )
                data = res.json()

                if data.get("success"):
                    draft = data.get("data", {})

                    # Pre-fill the same top-level fields the manual form's
                    # widgets below read from. Setting a widget's own
                    # session_state key (not just a plain variable) BEFORE
                    # that widget is created further down this same script
                    # run is what actually makes the new value show up -
                    # the widget's `value=` argument is only ever used the
                    # first time a key appears, never to overwrite it.
                    st.session_state["user_name"] = draft.get("name") or ""
                    st.session_state["user_title"] = draft.get("title") or ""
                    st.session_state["user_email"] = draft.get("email") or ""
                    st.session_state["user_phone"] = draft.get("phone") or ""
                    st.session_state["user_website"] = draft.get("website") or ""
                    st.session_state["user_summary"] = draft.get("summary") or ""
                    st.session_state["skills_text"] = ", ".join(draft.get("skills") or [])

                    # Experience/Education rows are a different case: their
                    # widget keys are per-row (e.g. "job_title_0"), so
                    # replacing st.session_state.experiences alone isn't
                    # enough once a row index has already been rendered
                    # once before (its widgets already "own" that key) -
                    # each row's own keys need the same direct treatment.
                    # Only overwrite when the draft actually found
                    # something, so an unusually sparse parse doesn't wipe
                    # out rows the person may already have filled in by hand.
                    new_experiences = [
                        {
                            "job_title": exp.get("job_title") or "",
                            "company": exp.get("company") or "",
                            "location": exp.get("location") or "",
                            "start_date": exp.get("start_date") or "",
                            "end_date": exp.get("end_date") or "",
                            "description": exp.get("description") or "",
                            # Already job-tailored by draft_service - marking
                            # ai_description_source as matching "description"
                            # here means Phase 1's staleness check (below,
                            # in the Experience loop) sees these bullets as
                            # already current, so "Create Resume" won't
                            # re-call Groq for them a third time.
                            "ai_description": exp.get("ai_description") or [],
                            "ai_description_source": exp.get("description") or "",
                            "is_current": bool(exp.get("is_current")),
                        }
                        for exp in (draft.get("experiences") or [])
                    ]
                    if new_experiences:
                        st.session_state.experiences = new_experiences
                        for i, exp in enumerate(new_experiences):
                            st.session_state[f"job_title_{i}"] = exp["job_title"]
                            st.session_state[f"company_{i}"] = exp["company"]
                            st.session_state[f"location_{i}"] = exp["location"]
                            st.session_state[f"start_date_{i}"] = exp["start_date"]
                            st.session_state[f"end_date_{i}"] = exp["end_date"]
                            st.session_state[f"description_{i}"] = exp["description"]
                            st.session_state[f"is_current_{i}"] = exp["is_current"]

                    new_education = [
                        {
                            "college": edu.get("college") or "",
                            "degree": edu.get("degree") or "",
                            "field_of_study": edu.get("field_of_study") or "",
                            "start_year": edu.get("start_year") or "",
                            "end_year": edu.get("end_year") or "",
                            "details": edu.get("details") or "",
                        }
                        for edu in (draft.get("education") or [])
                    ]
                    if new_education:
                        st.session_state.education = new_education
                        for i, edu in enumerate(new_education):
                            st.session_state[f"college_{i}"] = edu["college"]
                            st.session_state[f"degree_{i}"] = edu["degree"]
                            st.session_state[f"field_{i}"] = edu["field_of_study"]
                            st.session_state[f"start_year_{i}"] = edu["start_year"]
                            st.session_state[f"end_year_{i}"] = edu["end_year"]
                            st.session_state[f"edu_details_{i}"] = edu["details"]

                    new_certifications = [
                        {
                            "name": cert.get("name") or "",
                            "issuing_organization": cert.get("issuing_organization") or "",
                            "year": cert.get("year") or "",
                        }
                        for cert in (draft.get("certifications") or [])
                    ]
                    if new_certifications:
                        st.session_state.certifications = new_certifications
                        for i, cert in enumerate(new_certifications):
                            st.session_state[f"cert_name_{i}"] = cert["name"]
                            st.session_state[f"cert_org_{i}"] = cert["issuing_organization"]
                            st.session_state[f"cert_year_{i}"] = cert["year"]

                    new_awards = [
                        {
                            "title": award.get("title") or "",
                            "year": award.get("year") or "",
                        }
                        for award in (draft.get("awards") or [])
                    ]
                    if new_awards:
                        st.session_state.awards = new_awards
                        for i, award in enumerate(new_awards):
                            st.session_state[f"award_title_{i}"] = award["title"]
                            st.session_state[f"award_year_{i}"] = award["year"]

                    for warning in draft.get("warnings") or []:
                        st.warning(warning)

                    # Phase D (fix): this is what actually reveals the
                    # manual form below - see the "draft_ready" guard
                    # further down. Before this line runs for the first
                    # time, that form stays hidden entirely instead of
                    # showing up empty underneath the draft inputs.
                    st.session_state.draft_ready = True

                    st.success("Draft generated - review and edit it in the form below before creating the resume.")
                else:
                    st.error(data.get("message", "Draft generation failed"))

            except requests.exceptions.Timeout:
                st.error("Draft generation timed out. Please try again.")
            except Exception as e:
                st.error(f"Error: {e}")

    st.divider()

# Phase D: the manual form only appears once there is something to fill
# in or review - either you chose to type it in yourself, or a draft has
# already been generated. In "Generate from Job Description" mode, before
# that button is clicked, this whole section stays hidden instead of
# showing an empty, unrelated-looking form under the draft inputs.
if entry_mode == "Build manually" or st.session_state.get("draft_ready"):
    # ---------------- USER INFO ----------------
    st.header("👤 User Info")

    # Phase D: value= is only used the first time a key appears in
    # session_state - once "Generate Tailored Draft" (above) has set it, this
    # just reflects that value back; typing here still works exactly as
    # before, since the widget itself keeps session_state[key] up to date.
    name = st.text_input("Name", value=st.session_state.get("user_name", ""), key="user_name")
    title = st.text_input(
        "Professional Title (e.g. UX Designer)",
        value=st.session_state.get("user_title", ""),
        key="user_title"
    )
    email = st.text_input("Email", value=st.session_state.get("user_email", ""), key="user_email")
    phone = st.text_input("Phone", value=st.session_state.get("user_phone", ""), key="user_phone")
    website = st.text_input(
        "Website / Portfolio / LinkedIn (optional)",
        value=st.session_state.get("user_website", ""),
        key="user_website"
    )

    # ---------------- SUMMARY ----------------
    st.header("🧾 Summary")
    summary = st.text_area(
        "Professional Summary",
        value=st.session_state.get("user_summary", ""),
        key="user_summary"
    )

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

        # Phase 1: if the description has changed since these bullets were
        # generated, they no longer describe this experience - drop them so a
        # stale preview never gets sent to "Create Resume" as if it were still
        # current. (resume_service on the backend treats a non-empty
        # ai_description as "already enhanced, don't re-call Groq" - so this
        # check is what keeps that shortcut honest.)
        if exp.get("ai_description") and exp["description"] != exp.get("ai_description_source"):
            exp["ai_description"] = []
            exp["ai_description_source"] = ""

        # Phase F: same invalidation, but for a PENDING proposal that hasn't
        # been applied yet - if the description changes while a proposal is
        # sitting there unapplied, that proposal no longer describes this
        # experience either.
        if exp.get("_pending_ai_bullets") and exp["description"] != exp.get("_pending_ai_source"):
            exp["_pending_ai_bullets"] = []
            exp["_pending_ai_source"] = ""

        # Phase F: the applied AI version used to be invisible after the
        # instant it was generated (the "AI Enhanced Experience!" message
        # only showed inside the same script run as the button click) even
        # though ai_description was quietly the thing actually used
        # everywhere (ATS scoring, the PDF). Now it's a persistent, visible
        # state with an explicit way back.
        if exp.get("ai_description"):
            st.caption("✓ Using the AI-enhanced version below for this experience.")
            for b in exp["ai_description"]:
                st.write(f"- {b}")
            if st.button("↩️ Revert to Original Description", key=f"revert_{i}"):
                exp["ai_description"] = []
                exp["ai_description_source"] = ""
                st.rerun()

        # Phase G: ai_engine.py has always supported three distinct rewrite
        # styles (professional/impactful/concise - see
        # ai_engine._build_system_prompt), but the frontend never actually
        # exposed a way to pick one - "Enhance Experience" hardcoded
        # "professional" every time. That's also why regenerating looked
        # like nothing changed: the same description, through the same
        # style prompt, tends to converge on near-identical phrasing.
        style_labels = {"Professional": "professional", "Impactful": "impactful", "Concise": "concise"}
        selected_style_label = st.selectbox(
            "Enhancement Style",
            options=list(style_labels.keys()),
            key=f"enhance_style_{i}",
        )
        selected_style = style_labels[selected_style_label]

        # Phase G: a pending proposal generated under a different style no
        # longer reflects what's currently selected - same invalidation
        # philosophy as the description-change checks above.
        if exp.get("_pending_ai_bullets") and exp.get("_pending_ai_style") != selected_style:
            exp["_pending_ai_bullets"] = []
            exp["_pending_ai_source"] = ""
            exp["_pending_ai_style"] = ""

        button_label = "🔁 Regenerate AI Version" if exp.get("ai_description") else "✨ Enhance Experience"
        if st.button(button_label, key=f"enhance_{i}"):
            try:
                # Phase 2: explicit timeout so a slow/hung backend doesn't
                # freeze this button forever with no feedback.
                res = requests.post(f"{BASE_URL}/ai/enhance",
                                    json={
                                        "text": exp["description"],
                                        "style": selected_style
                                    },
                                    timeout=30)
                data = res.json()
                # Phase 4: .get(...) instead of direct dict indexing, so an
                # unexpected response shape can't crash this with a raw
                # KeyError - it just falls through to the error branch.
                if data.get("success"):
                    # Phase F: proposed, not yet applied - "Enhance
                    # Experience" used to write straight to ai_description
                    # with no review step. Stashing it as a pending
                    # proposal instead means nothing changes until the
                    # person explicitly clicks Apply below.
                    exp["_pending_ai_bullets"] = data.get("data", {}).get("bullets", [])
                    exp["_pending_ai_source"] = exp["description"]
                    exp["_pending_ai_style"] = selected_style
                else:
                    st.error(data.get("message", "Failed to enhance experience"))

            # Phase 2: dedicated Timeout branch, so a timeout gets a specific
            # message instead of the generic "Error: ..." below.
            except requests.exceptions.Timeout:
                st.error("The AI enhancement request timed out. Please try again.")
            except Exception as e:
                st.error(f"Error: {e}")

        # Phase F: the proposal stays visible (and re-appears on every
        # rerun) until the person explicitly applies or discards it -
        # instead of flashing once and then only living on invisibly in
        # session state.
        if exp.get("_pending_ai_bullets"):
            st.info("Proposed AI-Enhanced Version:")
            for b in exp["_pending_ai_bullets"]:
                st.write(f"- {b}")

            pending_col1, pending_col2 = st.columns(2)
            with pending_col1:
                if st.button("✅ Apply This Version", key=f"apply_enhance_{i}"):
                    exp["ai_description"] = exp["_pending_ai_bullets"]
                    exp["ai_description_source"] = exp["_pending_ai_source"]
                    exp["_pending_ai_bullets"] = []
                    exp["_pending_ai_source"] = ""
                    exp["_pending_ai_style"] = ""
                    st.rerun()
            with pending_col2:
                if st.button("✖️ Discard", key=f"discard_enhance_{i}"):
                    exp["_pending_ai_bullets"] = []
                    exp["_pending_ai_source"] = ""
                    exp["_pending_ai_style"] = ""
                    st.rerun()


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
            "ai_description_source": "",  # Phase 1: see note in the initial seed above.
            "_pending_ai_bullets": [],
            "_pending_ai_source": "",  # Phase F: see note in the initial seed above.
            "_pending_ai_style": "",  # Phase G: see note in the initial seed above.
            "is_current": False
        })

        st.rerun()

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

        edu["details"] = st.text_area(
            "Details (optional, 1-2 short lines — e.g. major, thesis title)",
            value=edu.get("details", ""),
            key=f"edu_details_{i}",
            height=68
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
            "end_year": "",
            "details": ""
        })

        st.rerun()

    # ---------------- SKILLS ----------------
    st.header("🛠 Skills")

    skills_input = st.text_input(
        "Skills (comma separated)",
        value=st.session_state.get("skills_text", ""),
        key="skills_text"
    )

    # ---------------- CERTIFICATIONS ----------------
    st.header("📜 Certifications")

    for i, cert in enumerate(st.session_state.certifications):
        st.subheader(f"Certification {i+1}")

        cert["name"] = st.text_input(
            "Certification Name",
            value=cert.get("name", ""),
            key=f"cert_name_{i}"
        )

        col1, col2 = st.columns(2)
        with col1:
            cert["issuing_organization"] = st.text_input(
                "Issuing Organization (optional)",
                value=cert.get("issuing_organization", ""),
                key=f"cert_org_{i}"
            )
        with col2:
            cert["year"] = st.text_input(
                "Year (optional)",
                value=cert.get("year", ""),
                key=f"cert_year_{i}"
            )

        if st.button(f"❌ Remove Certification {i+1}", key=f"remove_cert_{i}"):
            st.session_state.certifications.pop(i)
            st.rerun()

        st.divider()

    if st.button("➕ Add Certification"):
        st.session_state.certifications.append({"name": "", "issuing_organization": "", "year": ""})
        st.rerun()

    # ---------------- AWARDS & ACHIEVEMENTS ----------------
    st.header("🏆 Awards & Achievements")

    for i, award in enumerate(st.session_state.awards):
        st.subheader(f"Award {i+1}")

        award["title"] = st.text_input(
            "Award / Achievement",
            value=award.get("title", ""),
            key=f"award_title_{i}"
        )

        award["year"] = st.text_input(
            "Year (optional)",
            value=award.get("year", ""),
            key=f"award_year_{i}"
        )

        if st.button(f"❌ Remove Award {i+1}", key=f"remove_award_{i}"):
            st.session_state.awards.pop(i)
            st.rerun()

        st.divider()

    if st.button("➕ Add Award"):
        st.session_state.awards.append({"title": "", "year": ""})
        st.rerun()

    # ---------------- CREATE RESUME ----------------
    if st.button("Create Resume"):

        # Phase 5: basic client-side validation, so an empty name or an
        # obviously malformed email is caught here with a clear message
        # instead of round-tripping to the backend for a raw 422 response.
        validation_errors = []
        if not name.strip():
            validation_errors.append("Name is required.")
        if not email.strip():
            validation_errors.append("Email is required.")
        elif "@" not in email or "." not in email.split("@")[-1]:
            validation_errors.append("Email doesn't look valid.")

        if validation_errors:
            for err in validation_errors:
                st.warning(err)
        else:
            skills_list = [{"skill_name": s.strip()} for s in skills_input.split(",") if s.strip()]
            certifications_list = [c for c in st.session_state.certifications if c.get("name", "").strip()]
            awards_list = [a for a in st.session_state.awards if a.get("title", "").strip()]

            payload = {
                "title": title,
                "user": {
                    "name": name,
                    "email": email,
                    "phone": phone,
                    "website": website
                },
                "summary": summary,
                "experiences": st.session_state.experiences,
                "education": st.session_state.education,
                "skills": skills_list,
                "certifications": certifications_list,
                "awards": awards_list
            }

            try:
                # Phase 2: explicit timeout. Creating a resume awaits
                # concurrent AI enhancement calls on the backend, so this one
                # gets a longer allowance than the simpler requests below.
                res = requests.post(f"{BASE_URL}/resume/", json=payload, timeout=60)
                data = res.json()

                if res.status_code == 200:
                    st.success("✅ Resume Created!")

                    resume_id = data["id"]
                    st.session_state["resume_id"] = resume_id
                    st.session_state["resume"] = data

                else:
                    st.error(f"Status: {res.status_code}")
                    st.json(data)

            # Phase 2: dedicated Timeout branch.
            except requests.exceptions.Timeout:
                st.error("Creating the resume timed out. Please try again.")
            except Exception as e:
                st.error(f"Error: {e}")

    if "resume" in st.session_state:
        st.header("📄 Resume Preview")
        render_resume_preview(st.session_state["resume"])
else:
    st.info("Generate a tailored draft above, or switch to \"Build manually\", to continue.")


# ---------------- ATS SCORE ----------------
st.header("📊 ATS Score")


def _check_ats_score(resume_id, job_description):
    """Phase F: pulled out of the button's if-block so both "Check ATS
    Score" and the auto-recheck after applying a tailoring preview can call
    the same thing. Stores the result in session_state (rather than a
    local variable) so it - and the "Tailor My Resume to This Job" button
    below it - survive reruns triggered by unrelated widgets."""
    try:
        # Phase 2: explicit timeout.
        res = requests.post(
            f"{BASE_URL}/ats/score",
            json={"resume_id": resume_id, "job_description": job_description},
            timeout=30
        )
        data = res.json()

        if data.get("success"):
            st.session_state["last_ats_result"] = data.get("data", {})
            st.session_state["last_ats_job_description"] = job_description
        else:
            st.session_state["last_ats_result"] = None
            st.error(data.get("message", "ATS scoring failed"))

    # Phase 2: dedicated Timeout branch.
    except requests.exceptions.Timeout:
        st.error("The ATS score request timed out. Please try again.")
    except Exception as e:
        st.error(f"Error: {e}")


if "resume_id" in st.session_state:
    jd = st.text_area("Paste Job Description", key="ats_job_description")

    if st.button("Check ATS Score"):
        _check_ats_score(st.session_state["resume_id"], jd)

    result = st.session_state.get("last_ats_result")

    # Phase F: only show results for the job description they were
    # actually computed against - if the person edits the text area after
    # checking, the numbers below no longer describe what's currently
    # pasted there.
    if result and st.session_state.get("last_ats_job_description") == jd:

        if st.session_state.pop("_resume_updated_flag", False):
            st.success("Resume updated - your ATS score below has been refreshed.")

        st.subheader("📈 Results")

        # Phase E: each number now sits next to the explanation for
        # why it is what it is, instead of three bare percentages
        # with the supporting detail scattered further down the page.
        skills_matched = result.get("matched_skills_count", 0)
        skills_total = result.get("total_skills_count", 0)
        exp_relevant = result.get("relevant_experience_count", 0)
        exp_total = result.get("total_experience_count", 0)

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("ATS Score", f"{result.get('ats_score', 0)}%")
            st.caption("70% wording similarity + 30% skill match.")

        with col2:
            st.metric("Skill Match", f"{result.get('skill_match_score', 0)}%")
            if skills_total:
                st.caption(f"{skills_matched} of {skills_total} listed skills appear in this job description.")
            else:
                st.caption("No skills listed on this resume yet.")

        with col3:
            st.metric("Relevant Experience", f"{exp_relevant}/{exp_total}" if exp_total else "0/0")
            if exp_total:
                st.caption(f"{exp_relevant} of {exp_total} experience entries closely relate to this job description.")
            else:
                st.caption("No experience entries to compare yet.")

        st.caption(f"Wording similarity to the job description: {result.get('similarity_score', 0)}%.")

        st.subheader("✅ Matched Skills")
        matched = result.get("matched_skills", [])
        st.write(", ".join(matched) if matched else "None of your listed skills were found in this job description.")

        st.subheader("❌ Missing Keywords")
        missing = result.get("missing_keywords", [])
        st.write(", ".join(missing) if missing else "No notable missing keywords found.")

        st.subheader("💡 Suggestions")
        for s in result.get("suggestions", []):
            st.write(f"- {s}")

        # ---------------- TAILOR TO THIS JOB (Phase F) ----------------
        # The bridge from "here's what's wrong" to "here's how to fix it" -
        # reuses the exact same tailoring calls the "Generate from Job
        # Description" flow uses higher up the page, just pointed at this
        # already-saved resume's real experiences/summary instead of a
        # freeform background.
        st.subheader("🪄 Act on These Suggestions")

        if st.button("✨ Tailor My Resume to This Job"):
            try:
                res = requests.post(
                    f"{BASE_URL}/resume/{st.session_state['resume_id']}/tailor-preview",
                    json={"job_description": jd},
                    timeout=90
                )
                data = res.json()
                if data.get("success"):
                    st.session_state["tailor_preview"] = data.get("data")
                else:
                    st.error(data.get("message", "Could not generate a tailoring preview"))
            except requests.exceptions.Timeout:
                st.error("The tailoring request timed out. Please try again.")
            except Exception as e:
                st.error(f"Error: {e}")

        preview = st.session_state.get("tailor_preview")
        if preview:
            st.caption(
                "Nothing is saved yet - review the AI-tailored version below, then Apply "
                "if you want to keep it."
            )

            st.markdown("**Summary**")
            sum_col1, sum_col2 = st.columns(2)
            with sum_col1:
                st.caption("Current")
                st.write(preview.get("original_summary") or "_(none)_")
            with sum_col2:
                st.caption("AI-Tailored")
                st.write(preview.get("tailored_summary") or "_(no change proposed)_")

            for exp_preview in preview.get("experiences", []):
                st.markdown(f"**{exp_preview.get('job_title') or 'Experience'}**")
                exp_col1, exp_col2 = st.columns(2)

                with exp_col1:
                    st.caption("Current")
                    current_bullets = exp_preview.get("current_ai_description") or []
                    if current_bullets:
                        for b in current_bullets:
                            st.write(f"- {b}")
                    else:
                        st.write(exp_preview.get("original_description") or "_(none)_")

                with exp_col2:
                    st.caption("AI-Tailored")
                    tailored_bullets = exp_preview.get("tailored_bullets") or []
                    if tailored_bullets:
                        for b in tailored_bullets:
                            st.write(f"- {b}")
                    else:
                        st.write("_(no change proposed)_")

            apply_col, discard_col = st.columns(2)

            with apply_col:
                if st.button("✅ Apply All Changes"):
                    update_payload = {
                        "summary": preview.get("tailored_summary"),
                        "experiences": [
                            {"id": e["id"], "ai_description": e["tailored_bullets"]}
                            for e in preview.get("experiences", [])
                            if e.get("tailored_bullets")
                        ],
                    }
                    try:
                        res = requests.put(
                            f"{BASE_URL}/resume/{st.session_state['resume_id']}",
                            json=update_payload,
                            timeout=30
                        )
                        if res.status_code == 200:
                            st.session_state["resume"] = res.json()
                            st.session_state["tailor_preview"] = None
                            # Auto re-check, so the improvement shows up
                            # immediately instead of asking the person to
                            # click "Check ATS Score" again themselves.
                            _check_ats_score(st.session_state["resume_id"], jd)
                            # A message written here would never actually
                            # reach the browser - st.rerun() below discards
                            # this run's output immediately. Stashing a flag
                            # and showing the message on the NEW run instead
                            # (right where the refreshed numbers render) is
                            # what actually makes it visible.
                            st.session_state["_resume_updated_flag"] = True
                            st.rerun()
                        else:
                            st.error(f"Failed to update resume (status {res.status_code}).")
                    except requests.exceptions.Timeout:
                        st.error("Updating the resume timed out. Please try again.")
                    except Exception as e:
                        st.error(f"Error: {e}")

            with discard_col:
                if st.button("✖️ Discard Preview"):
                    st.session_state["tailor_preview"] = None
                    st.rerun()

else:
    st.info("Create a resume first")


# ---------------- PDF DOWNLOAD ----------------
st.header("📥 Download Resume")

if "resume_id" in st.session_state:

    if st.button("Generate PDF"):
        try:
            pdf_url = f"{BASE_URL}/pdf/resume/{st.session_state['resume_id']}"
            # Phase 2: explicit timeout.
            response = requests.get(pdf_url, timeout=30)

            if response.status_code == 200:
                # Phase 3: store the generated PDF bytes (and which resume
                # they belong to) in session_state instead of only holding
                # them in this button's local `response` variable. Streamlit
                # reruns the whole script on every interaction, so without
                # this the download button below would disappear the
                # moment the user touches anything else on the page.
                st.session_state["generated_pdf_bytes"] = response.content
                st.session_state["generated_pdf_resume_id"] = st.session_state["resume_id"]
            else:
                st.error("Failed to generate PDF")
                st.write(response.text)

        # Phase 2: dedicated Timeout branch.
        except requests.exceptions.Timeout:
            st.error("PDF generation timed out. Please try again.")
        except Exception as e:
            st.error(f"Error: {e}")

    # Phase 3: render the download button from session_state on every
    # rerun (not only inside the button's own `if` block above), and only
    # for the resume it was actually generated for - so switching to a
    # different resume_id doesn't offer a stale PDF for download.
    if (
        st.session_state.get("generated_pdf_bytes")
        and st.session_state.get("generated_pdf_resume_id") == st.session_state["resume_id"]
    ):
        st.download_button(
            label="Download PDF",
            data=st.session_state["generated_pdf_bytes"],
            file_name="resume.pdf",
            mime="application/pdf"
        )
