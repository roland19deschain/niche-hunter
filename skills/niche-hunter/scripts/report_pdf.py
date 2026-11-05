"""Render the shared report model as a paginated PDF; never fetch remote assets."""

import hashlib
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

from reporting import THEME


def pdf_bytes(document, regular=None, bold=None):
    try:
        from reportlab.lib import colors
        from reportlab.graphics.shapes import Drawing, Rect, String
        from reportlab.lib.enums import TA_LEFT
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except ImportError as error:
        raise ValueError("PDF export needs ReportLab. Install requirements-pdf.txt in the chosen Python environment, or supply --pdf-file from a native client exporter.") from error
    fonts = Path(__file__).resolve().parents[1] / "assets/fonts"
    faces = []
    for path in (Path(regular) if regular else fonts / "NotoSans-Regular.ttf",
                 Path(bold) if bold else fonts / "NotoSans-Bold.ttf"):
        name = "NH" + hashlib.sha256(path.read_bytes()).hexdigest()[:16]
        if name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(name, str(path)))
        faces.append(name)
    normal_font, bold_font = faces
    # Fail visibly instead of exporting unreadable boxes for unsupported scripts.
    contents = ["Niche Hunter 0123456789 ->", document["title"], document["period"], document["summary"], *document["labels"].values(),
                *document["attributions"]]
    for section in document["providers"]:
        contents += [section["name"], section["coverage"], section["conclusion"], section["status"]]
        contents += [row[key] for row in section["rows"] for key in ("signal", "data")]
    for item in document["products"]:
        contents += [item[key] for key in ("title", "channel", "need", "description")]
    for face in faces:
        supported = pdfmetrics.getFont(face).face.charToGlyph
        if any(ord(char) not in supported for text in contents for char in text if not char.isspace()):
            raise ValueError("PDF font does not cover report text. Supply --font-regular/--font-bold or use a native client PDF exporter with suitable fonts.")
    theme = document.get("theme", THEME)
    ink, slate = colors.HexColor(theme["ink"]), colors.HexColor(theme["slate"])
    paper, sage, gold = (colors.HexColor(theme[key]) for key in ("paper", "sage", "gold"))
    styles = {
        "title": ParagraphStyle("title", fontName=bold_font, fontSize=24, leading=30, textColor=ink, spaceAfter=10),
        "heading": ParagraphStyle("heading", fontName=bold_font, fontSize=14, leading=18, textColor=ink,
                                  spaceBefore=14, spaceAfter=8, keepWithNext=True),
        "body": ParagraphStyle("body", fontName=normal_font, fontSize=9.2, leading=13.8, textColor=ink,
                               spaceAfter=8, alignment=TA_LEFT, splitLongWords=True),
        "small": ParagraphStyle("small", fontName=normal_font, fontSize=8, leading=11.5, textColor=slate, spaceAfter=8),
        "headcell": ParagraphStyle("headcell", fontName=bold_font, fontSize=8.4, leading=12, textColor=paper),
        "cell": ParagraphStyle("cell", fontName=normal_font, fontSize=8.4, leading=12.4, textColor=ink),
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
            label = '<link href="' + escape(row["url"], {'"': '&quot;'}) + '">' + escape(row["signal"]) + '</link>'
            data.append([Paragraph(label, styles["cell"]), paragraph(row["data"], "cell")])
        if len(data) == 1:
            data.append([paragraph("-", "cell"), paragraph(section["status"], "cell")])
        table = Table(data, colWidths=[width * .43, width * .57], repeatRows=1, hAlign="LEFT")
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), slate), ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [sage, paper]),
            ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LINEBELOW", (0, -1), (-1, -1), .4, sage)]))
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
                chart.add(String(0, y + 3, label, fontName=normal_font, fontSize=7.5, fillColor=slate))
                chart.add(Rect(width * .38, y, width * .30 * item["value"] / maximum, 12,
                               fillColor=slate, strokeColor=None))
                chart.add(String(width * .70, y + 3, item["formatted_value"], fontName=bold_font,
                                 fontSize=7.5, fillColor=ink))
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
            card.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), gold),
                ("BOX", (0, 0), (-1, -1), .5, slate),
                ("LEFTPADDING", (0, 0), (-1, -1), 12), ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
            story += [KeepTogether([card, Spacer(1, 9)])]
    for attribution in document["attributions"]:
        story.append(paragraph(attribution, "small"))

    def footer(canvas, document_template):
        canvas.saveState()
        canvas.setFillColor(paper)
        canvas.rect(0, 0, page_width, page_height, fill=1, stroke=0)
        canvas.setFillColor(gold)
        canvas.rect(margin, page_height - 24, width * .22, 3, fill=1, stroke=0)
        canvas.setStrokeColor(sage)
        canvas.line(margin, 31, page_width - margin, 31)
        canvas.setFont(normal_font, 7)
        canvas.setFillColor(slate)
        canvas.drawString(margin, 19, "Niche Hunter")
        canvas.drawRightString(page_width - margin, 19, str(document_template.page))
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()
