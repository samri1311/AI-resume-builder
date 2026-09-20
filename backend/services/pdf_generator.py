import uuid
from pathlib import Path

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import json

# Write generated PDFs to a dedicated, git-ignored directory instead of
# whatever the process's current working directory happens to be, so files
# don't scatter across the project root (see .gitignore: "generated/").
OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / "generated"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

FONTS_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"


def _register_fonts():
    """Embed Lato (bundled under backend/assets/fonts/, SIL OFL licensed) so
    the PDF gets a proper professional typeface instead of the bare-bones
    Helvetica every PDF viewer falls back to. Registering it as a font
    FAMILY (not just individual faces) is what lets the existing <b> and
    <i> tags used throughout this file automatically pick the bold/italic
    variant instead of rendering in the base weight.

    Falls back to the standard PDF fonts if the font files are ever
    missing, so a missing asset can't crash PDF generation — it would just
    look plainer.
    """
    try:
        pdfmetrics.registerFont(TTFont("Lato", str(FONTS_DIR / "Lato-Regular.ttf")))
        pdfmetrics.registerFont(TTFont("Lato-Bold", str(FONTS_DIR / "Lato-Bold.ttf")))
        pdfmetrics.registerFont(TTFont("Lato-Italic", str(FONTS_DIR / "Lato-Italic.ttf")))
        pdfmetrics.registerFont(TTFont("Lato-BoldItalic", str(FONTS_DIR / "Lato-BoldItalic.ttf")))
        pdfmetrics.registerFontFamily(
            "Lato",
            normal="Lato",
            bold="Lato-Bold",
            italic="Lato-Italic",
            boldItalic="Lato-BoldItalic",
        )
        return "Lato", "Lato-Bold"
    except Exception as e:
        print("Could not load bundled Lato fonts, falling back to Helvetica:", e)
        return "Helvetica", "Helvetica-Bold"


FONT_REGULAR, FONT_BOLD = _register_fonts()


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
    # A unique suffix (not just resume.id) avoids two concurrent requests for
    # the same resume colliding on the same file mid-write.
    file_path = str(OUTPUT_DIR / f"resume_{resume.id}_{uuid.uuid4().hex}.pdf")

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
        leading=22,
        fontName=FONT_BOLD,
        spaceAfter=2
    )

    title_style = ParagraphStyle(
        'Title',
        fontSize=12,
        leading=15,
        fontName=FONT_REGULAR,
        textColor=colors.HexColor("#444444"),
        spaceAfter=4
    )

    contact_style = ParagraphStyle(
        'Contact',
        fontSize=10,
        fontName=FONT_REGULAR,
        textColor=colors.grey,
        spaceAfter=8
    )

    section_style = ParagraphStyle(
        'Section',
        fontSize=12,
        fontName=FONT_BOLD,
        spaceBefore=10,
        spaceAfter=2
    )

    normal_style = ParagraphStyle(
        'Normal',
        fontSize=10,
        fontName=FONT_REGULAR,
        leading=13
    )

    role_style = ParagraphStyle(
        'Role',
        fontSize=10,
        fontName=FONT_REGULAR,
        leading=13,
        spaceAfter=2
    )

    bullet_style = ParagraphStyle(
        'Bullet',
        fontSize=10,
        fontName=FONT_REGULAR,
        leftIndent=10,
        leading=13,
        spaceAfter=1
    )

    elements = []

    # -------- HEADER --------
    elements.append(Paragraph(clean_text(resume.user.name), name_style))

    if resume.title:
        elements.append(Paragraph(clean_text(resume.title), title_style))

    contact_parts = [
        clean_text(resume.user.phone),
        clean_text(resume.user.email),
        clean_text(resume.user.website),
    ]
    contact = "  |  ".join(part for part in contact_parts if part)
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
            # "Present" whenever the job is marked current, even if end_date
            # was left blank (previously this just printed an empty string).
            end_label = "Present" if exp.is_current else clean_text(exp.end_date)

            # Company (left) | Dates (right)
            table = Table(
                [[
                    Paragraph(f"<b>{clean_text(exp.company)}, {clean_text(exp.location)}</b>", normal_style),
                    Paragraph(f"{clean_text(exp.start_date)} - {end_label}", normal_style)
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

            if edu.details:
                # Meant to be 1-2 short lines — cap at 2 defensively even if
                # someone pastes in more.
                detail_lines = [line.strip() for line in edu.details.splitlines() if line.strip()][:2]
                for line in detail_lines:
                    elements.append(Paragraph(f"• {clean_text(line)}", bullet_style))

            elements.append(Spacer(1, 3))

    # -------- SKILLS --------
    if resume.skills:
        elements.append(Paragraph("SKILLS", section_style))
        elements.append(HRFlowable(width="100%", thickness=0.7))
        elements.append(Spacer(1, 4))

        skills = ", ".join([clean_text(s.skill_name) for s in resume.skills])
        elements.append(Paragraph(skills, normal_style))

    # -------- CERTIFICATIONS & AWARDS --------
    if resume.certifications or resume.awards:
        elements.append(Paragraph("CERTIFICATIONS & AWARDS", section_style))
        elements.append(HRFlowable(width="100%", thickness=0.7))
        elements.append(Spacer(1, 4))

        if resume.certifications:
            cert_bits = []
            for cert in resume.certifications:
                bit = clean_text(cert.name)
                if cert.issuing_organization:
                    bit += f" ({clean_text(cert.issuing_organization)})"
                if cert.year:
                    bit += f", {clean_text(cert.year)}"
                cert_bits.append(bit)

            elements.append(Paragraph(
                f"<b>Certifications:</b> {'; '.join(cert_bits)}",
                normal_style
            ))
            elements.append(Spacer(1, 2))

        if resume.awards:
            award_bits = []
            for award in resume.awards:
                bit = clean_text(award.title)
                if award.year:
                    bit += f" ({clean_text(award.year)})"
                award_bits.append(bit)

            elements.append(Paragraph(
                f"<b>Awards &amp; Achievements:</b> {'; '.join(award_bits)}",
                normal_style
            ))

    doc.build(elements)

    return file_path
