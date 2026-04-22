import re
from io import BytesIO

from PIL import Image, ImageDraw
from reportlab.lib.colors import Color
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

TEXT_COLOR = Color(232 / 255, 224 / 255, 200 / 255)
TOP_PAGE_MARGIN = 40
SPACE_AFTER_HEADER = 72
SPACE_BEFORE_HEADER = SPACE_AFTER_HEADER / 2
BOTTOM_MARGIN = 50


def _make_background(w: int, h: int) -> ImageReader:
    base_color = (19, 27, 54)
    bg = Image.new("RGB", (w, h), base_color)
    draw = ImageDraw.Draw(bg)
    for y in range(0, h, 140):
        draw.line((0, y, w, y), fill=(50, 70, 100), width=1)
    bg_rgba = bg.convert("RGBA")
    vignette = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    dv = ImageDraw.Draw(vignette)
    dv.ellipse((-w // 3, -h // 3, w + w // 3, h + h // 3), fill=(0, 0, 0, 70))
    final = Image.alpha_composite(bg_rgba, vignette).convert("RGB")
    buf = BytesIO()
    final.save(buf, "JPEG", quality=5)
    buf.seek(0)
    return ImageReader(buf)


def _draw_inline_line(text_obj, line, normal, bold, italic, size):
    parts = re.split(r'(\*[^\*]*\*|_.*?_)', line)
    for part in parts:
        if part.startswith('*') and part.endswith('*') and len(part) > 1:
            text_obj.setFont(bold, size)
            text_obj.textOut(part[1:-1])
        elif part.startswith('_') and part.endswith('_') and len(part) > 1:
            text_obj.setFont(italic, size)
            text_obj.textOut(part[1:-1])
        elif part:
            text_obj.setFont(normal, size)
            text_obj.textOut(part)
    text_obj.textLine('')


def generate_pdf_a4(
    summary_text: str,
    title: str,
    date: str,
    footer: str = "Leo Sorge @ CEO Source 2026",
) -> bytes:
    """Returns A4 PDF as bytes."""
    page_w, page_h = A4
    bg = _make_background(1240, 1754)

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)

    pages = [p.strip() for p in summary_text.split("=") if p.strip()]

    font_normal = "Helvetica"
    font_bold = "Helvetica-Bold"
    font_italic = "Helvetica-Oblique"
    font_size = 22 * 2 * 0.9
    line_leading = 33 * 2 * 0.9

    current_page_number = 1

    for i, block in enumerate(pages):
        lines = block.split("\n")
        line_idx = 0

        while line_idx < len(lines):
            if current_page_number > 1:
                c.showPage()

            c.drawImage(bg, 0, 0, width=page_w, height=page_h)

            c.setFont("Helvetica-Oblique", 10)
            c.setFillColor(TEXT_COLOR)
            suffix = "" if line_idx == 0 else " (cont.)"
            header_text = f"{title}  -  {date} FIG. {str(i + 1).zfill(2)}{suffix}"
            header_y = page_h - TOP_PAGE_MARGIN - SPACE_BEFORE_HEADER
            c.drawString(50, header_y, header_text)

            text_obj = c.beginText()
            start_y = header_y - SPACE_AFTER_HEADER
            text_obj.setTextOrigin(50, start_y)
            text_obj.setFont(font_normal, font_size)
            text_obj.setLeading(line_leading)
            text_obj.setFillColor(TEXT_COLOR)

            max_lines = int((start_y - BOTTOM_MARGIN) / line_leading) if line_leading > 0 else 0
            drawn = 0
            while line_idx < len(lines) and drawn < max_lines:
                _draw_inline_line(text_obj, lines[line_idx], font_normal, font_bold, font_italic, font_size)
                drawn += 1
                line_idx += 1

            c.drawText(text_obj)

            c.setFont("Helvetica", 8)
            c.setFillColor(TEXT_COLOR)
            tw = c.stringWidth(footer, "Helvetica", 8)
            c.drawString((page_w - tw) / 2, 30, footer)

            current_page_number += 1

    c.save()
    return buf.getvalue()
