from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
import json


def clean_text(value):
    return str(value).strip() if value else ""


def extract_bullets(ai_desc):
    if not ai_desc:
        return []

    if isinstance(ai_desc, str):
        text = ai_desc.strip()
        if not text:
            return []

        try:
            ai_desc = json.loads(text)
        except json.JSONDecodeError:
            return [
                line.lstrip("-\u2022* ").strip()
                for line in text.splitlines()
                if line.strip()
            ]

    if isinstance(ai_desc, dict):
        for key in ("bullets", "data", "bullet", "text"):
            if key in ai_desc:
                ai_desc = ai_desc[key]
                break
        else:
            return []

    if isinstance(ai_desc, list):
        bullets = []
        for item in ai_desc:
            if isinstance(item, str):
                bullets.append(item)
            elif isinstance(item, dict):
                bullets.extend(extract_bullets(item))
            elif item:
                bullets.append(str(item))
        return bullets

    return []


def generate_resume_pdf(resume):
    file_path = f"resume_{resume.id}.pdf"

    doc = SimpleDocTemplate(
        file_path,
        pagesize=A4,
        rightMargin=28,
        leftMargin=28,
        topMargin=20,
        bottomMargin=20
    )

    styles = getSampleStyleSheet()

    # -------- STYLES --------
    name_style = ParagraphStyle(
        'Name',
        fontSize=18,
        fontName="Helvetica-Bold",
        spaceAfter=4
    )

    contact_style = ParagraphStyle(
        'Contact',
        fontSize=10,
        textColor=colors.grey,
        spaceAfter=8
    )

    section_style = ParagraphStyle(
        'Section',
        fontSize=12,
        fontName="Helvetica-Bold",
        spaceBefore=10,
        spaceAfter=2
    )

    normal_style = ParagraphStyle(
        'Normal',
        fontSize=10,
        leading=13
    )

    role_style = ParagraphStyle(
        'Role',
        fontSize=10,
        leading=13,
        spaceAfter=2
    )

    bullet_style = ParagraphStyle(
        'Bullet',
        fontSize=10,
        leftIndent=10,
        leading=13,
        spaceAfter=1
    )

    elements = []

    # -------- HEADER --------
    elements.append(Paragraph(clean_text(resume.user.name), name_style))

    contact = f"{clean_text(resume.user.phone)}  |  {clean_text(resume.user.email)}"
    elements.append(Paragraph(contact, contact_style))

    # -------- SUMMARY --------
    if resume.summary:
        elements.append(Paragraph("SUMMARY", section_style))
        elements.append(HRFlowable(width="100%", thickness=0.7))
        elements.append(Spacer(1, 4))
        elements.append(Paragraph(clean_text(resume.summary), normal_style))

    # -------- EXPERIENCE --------
    if resume.experiences:
        elements.append(Paragraph("EXPERIENCE", section_style))
        elements.append(HRFlowable(width="100%", thickness=0.7))
        elements.append(Spacer(1, 4))

        for exp in resume.experiences:
            # Company (left) | Dates (right)
            table = Table(
                [[
                    Paragraph(f"<b>{clean_text(exp.company)}, {clean_text(exp.location)}</b>", normal_style),
                    Paragraph(f"{clean_text(exp.start_date)} - {clean_text(exp.end_date)}", normal_style)
                ]],
                colWidths=[4.5 * inch, 2 * inch]
            )

            table.setStyle(TableStyle([
                ('ALIGN', (1, 0), (1, 0), 'RIGHT')
            ]))

            elements.append(table)

            # Role
            elements.append(Paragraph(f"<i>{clean_text(exp.job_title)}</i>", role_style))

            # Bullets
            bullets = extract_bullets(exp.ai_description)

            if bullets:
                for b in bullets:
                    elements.append(Paragraph(f"\u2022 {clean_text(b)}", bullet_style))
            elif exp.description:
                description_bullets = extract_bullets(exp.description)
                if description_bullets:
                    for b in description_bullets:
                        elements.append(Paragraph(f"\u2022 {clean_text(b)}", bullet_style))
                else:
                    elements.append(Paragraph(clean_text(exp.description), normal_style))

            elements.append(Spacer(1, 4))

    # -------- EDUCATION --------
    if resume.education:
        elements.append(Paragraph("EDUCATION", section_style))
        elements.append(HRFlowable(width="100%", thickness=0.7))
        elements.append(Spacer(1, 4))

        for edu in resume.education:
            elements.append(Paragraph(
                f"<b>{clean_text(edu.degree)} - {clean_text(edu.college)}</b>",
                normal_style
            ))

            elements.append(Paragraph(
                f"{clean_text(edu.field_of_study)} ({clean_text(edu.start_year)} - {clean_text(edu.end_year)})",
                normal_style
            ))

            elements.append(Spacer(1, 3))

    # -------- SKILLS --------
    if resume.skills:
        elements.append(Paragraph("SKILLS", section_style))
        elements.append(HRFlowable(width="100%", thickness=0.7))
        elements.append(Spacer(1, 4))

        skills = ", ".join([clean_text(s.skill_name) for s in resume.skills])
        elements.append(Paragraph(skills, normal_style))

    doc.build(elements)

    return file_path
