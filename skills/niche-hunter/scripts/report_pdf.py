"""Render the shared report model as a paginated PDF; never fetch remote assets."""

import hashlib
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

from reporting import THEME
from research import SKILL_DIR

# Uncovered arrows keep their meaning in ASCII; the product route already uses "->".
ASCII_FALLBACKS = {"←": "<-", "→": "->", "↔": "<->", "⇐": "<=", "⇒": "=>", "⇔": "<=>"}


def printable(value, covered, emoji):
    """Omit unsupported emoji sequences while preserving text for the coverage check."""
    if isinstance(value, dict):
        return {key: item if key in {"url", "theme"} else printable(item, covered, emoji) for key, item in value.items()}
    if isinstance(value, list):
        return [printable(item, covered, emoji) for item in value]
    if not isinstance(value, str):
        return value

    def replace_sequence(chars, data):
        # A single unqualified symbol can be ordinary text, such as a copyright sign.
        if len(chars) == 1 and data["status"] == emoji.STATUS["unqualified"]:
            return chars
        return chars if all(covered(ord(char)) for char in chars) else ""

    value = emoji.replace_emoji(value, replace=replace_sequence)
    text = []
    for char in value:
        fallback = ASCII_FALLBACKS.get(char)
        if char.isspace() or covered(ord(char)):
            text.append(char)
        elif fallback and all(covered(ord(part)) for part in fallback):
            text.append(fallback)
        else:
            text.append(char)
    return "".join(text)


def pdf_bytes(document, regular=None, bold=None):
    try:
        import emoji
        from reportlab.lib import colors
        from reportlab.graphics.shapes import Drawing, Rect, String
        from reportlab.lib.enums import TA_LEFT
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except ImportError as error:
        raise ValueError("PDF export needs the packages in requirements-pdf.txt. Install them in the chosen Python environment, or supply --pdf-file from a native client exporter.") from error
    fonts = SKILL_DIR / "assets/fonts"
    faces = []
    for path in (Path(regular) if regular else fonts / "NotoSans-Regular.ttf",
                 Path(bold) if bold else fonts / "NotoSans-Bold.ttf"):
        name = "NH" + hashlib.sha256(path.read_bytes()).hexdigest()[:16]
        if name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(name, str(path)))
        faces.append(name)
    normal_font, bold_font = faces
    glyphs = [pdfmetrics.getFont(face).face.charToGlyph for face in faces]

    def covered(code):
        return all(code in supported for supported in glyphs)

    # Emoji in quoted source text are common; Markdown and JSON keep the original characters.
    document = printable(document, covered, emoji)
    # Fail visibly instead of exporting unreadable boxes for unsupported scripts.
    contents = ["Niche Hunter 0123456789 ->", document["title"], document["period"], document["summary"], *document["labels"].values(),
                *document["attributions"]]
    for section in document["providers"]:
        contents += [section["name"], section["coverage"], section["conclusion"], section["status"]]
        contents += [row[key] for row in section["rows"] for key in ("signal", "data")]
        contents += [item[key] for item in section["chart"] or [] for key in ("label", "formatted_value")]
    for item in document["products"]:
        contents += [item[key] for key in ("title", "channel", "need", "description")]
    missing = sorted({ord(char) for text in contents for char in text if not char.isspace() and not covered(ord(char))})
    if missing:
        listed = ", ".join(f"U+{code:04X}" for code in missing[:8]) + (", ..." if len(missing) > 8 else "")
        raise ValueError("PDF font does not cover report text (" + listed + "). Supply --font-regular/--font-bold or use a native client PDF exporter with suitable fonts.")
    # Old report models may carry the former light palette; missing roles use the current theme.
    theme = {**THEME, **document.get("theme", {})}
    background, surface, surface_alt, border, text, muted, accent, cyan = (
        colors.HexColor(theme[key]) for key in
        ("background", "surface", "surface_alt", "border", "text", "muted", "accent", "cyan"))
    series = [colors.HexColor(theme[key]) for key in ("accent", "cyan", "teal", "lime")]
    styles = {
        "title": ParagraphStyle("title", fontName=bold_font, fontSize=24, leading=30, textColor=text, spaceAfter=10),
        "heading": ParagraphStyle("heading", fontName=bold_font, fontSize=14, leading=18, textColor=text,
                                  spaceBefore=14, spaceAfter=8, keepWithNext=True),
        "body": ParagraphStyle("body", fontName=normal_font, fontSize=9.2, leading=13.8, textColor=text,
                               spaceAfter=8, alignment=TA_LEFT, splitLongWords=True),
        "small": ParagraphStyle("small", fontName=normal_font, fontSize=8, leading=11.5, textColor=muted, spaceAfter=8),
        "headcell": ParagraphStyle("headcell", fontName=bold_font, fontSize=8.4, leading=12, textColor=text),
        "cell": ParagraphStyle("cell", fontName=normal_font, fontSize=8.4, leading=12.4, textColor=text),
    }

    def paragraph(text, style="body"):
        return Paragraph(escape(str(text)), styles[style])

    buffer = BytesIO()
    page_width, page_height = A4
    margin, width = 46, page_width - 92
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=margin, leftMargin=margin,
                            topMargin=42, bottomMargin=44, title=document["title"], author="Niche Hunter")
    labels = document["labels"]
    story = [paragraph(document["title"], "title"), paragraph(labels["requested"] + ": " + document["period"], "small")]
    for section in document["providers"]:
        section_start = len(story)
        story.append(paragraph(section["name"], "heading"))
        if section["coverage"]:
            story.append(paragraph(labels["coverage"] + ": " + section["coverage"], "small"))
        data = [[paragraph(labels["signal"], "headcell"), paragraph(labels["data"], "headcell")]]
        for row in section["rows"]:
            label = ('<link href="' + escape(row["url"], {'"': '&quot;'}) + '" color="' + theme["cyan"]
                     + '">' + escape(row["signal"]) + '</link>')
            data.append([Paragraph(label, styles["cell"]), paragraph(row["data"], "cell")])
        if len(data) == 1:
            data.append([paragraph("-", "cell"), paragraph(section["status"], "cell")])
        table = Table(data, colWidths=[width * .43, width * .57], repeatRows=1, hAlign="LEFT")
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), surface_alt), ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [surface, surface_alt]),
            ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LINEBELOW", (0, 0), (-1, -1), .4, border)]))
        story += [table, Spacer(1, 10)]
        if section["chart"]:
            items = section["chart"]
            chart = Drawing(width, len(items) * 24 + 8)
            maximum = max(item["value"] for item in items)
            for index, item in enumerate(items):
                y = (len(items) - index - 1) * 24 + 8
                label = item["label"]
                while label and pdfmetrics.stringWidth(label, normal_font, 7.5) > width * .36:
                    label = label[:-1]
                if label != item["label"]:
                    label = label[:-3] + "..."
                chart.add(String(0, y + 3, label, fontName=normal_font, fontSize=7.5, fillColor=muted))
                chart.add(Rect(width * .38, y, width * .30, 12, fillColor=surface_alt, strokeColor=None))
                chart.add(Rect(width * .38, y, width * .30 * item["value"] / maximum, 12,
                               fillColor=series[index % len(series)], strokeColor=None))
                chart.add(String(width * .70, y + 3, item["formatted_value"], fontName=bold_font,
                                 fontSize=7.5, fillColor=text))
            story.append(chart)
        story.append(paragraph(section["conclusion"]))
        story[section_start:] = [KeepTogether(story[section_start:])]
    story += [paragraph(labels["overall"], "heading"), paragraph(document["summary"])]
    if document["products"]:
        story.append(paragraph(labels["ideas"], "heading"))
        for index, item in enumerate(document["products"], 1):
            proposed = " (" + labels["proposed"] + ")" if item["untested"] else ""
            route = f"{index}. {item['channel']}{proposed} -> {item['need']} -> {item['title']}"
            card = Table([[paragraph(route)], [paragraph(item["description"])]], colWidths=[width])
            card.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), surface_alt),
                ("BOX", (0, 0), (-1, -1), .5, border),
                ("LINEBEFORE", (0, 0), (0, -1), 3, cyan),
                ("LEFTPADDING", (0, 0), (-1, -1), 12), ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
            story += [KeepTogether([card, Spacer(1, 9)])]
    for attribution in document["attributions"]:
        story.append(paragraph(attribution, "small"))

    def footer(canvas, document_template):
        canvas.saveState()
        canvas.setFillColor(background)
        canvas.rect(0, 0, page_width, page_height, fill=1, stroke=0)
        canvas.setFillColor(accent)
        canvas.rect(margin, page_height - 24, width * .22, 3, fill=1, stroke=0)
        canvas.setStrokeColor(border)
        canvas.line(margin, 31, page_width - margin, 31)
        canvas.setFont(normal_font, 7)
        canvas.setFillColor(muted)
        canvas.drawString(margin, 19, "Niche Hunter")
        canvas.drawRightString(page_width - margin, 19, str(document_template.page))
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()
