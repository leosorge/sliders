# Versione per Unidata - quella standard è my_pdf_a4

"""
core/pdf_a4.py  —  Stile FT-CS Daily  (A4 portrait)
Sfondo navy, griglia teal, titoli in verde, corpo panna.
Font: Kanit (fallback Helvetica). Logo esagonale in basso a destra.
Compatibile con Python 3.14 e reportlab >= 4.2
"""
import math
import os
import re
from io import BytesIO
from typing import List, Tuple

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

# ── Palette ───────────────────────────────────────────────────────────────────
NAVY  = HexColor("#131836")
GREEN = HexColor("#00C9A7")
CREAM = HexColor("#EDE8D8")
GRID  = HexColor("#1C3F52")   # teal smorzato, niente alpha

# ── Pagina ───────────────────────────────────────────────────────────────────
W, H      = A4        # 595.27 × 841.89 pt
MARGIN    = 50
GRID_STEP = 52

# ── Font ─────────────────────────────────────────────────────────────────────
_FONT_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "fonts"
)
_FONTS_REGISTERED = False

def _ensure_fonts():
    global _FONTS_REGISTERED
    if _FONTS_REGISTERED:
        return
    _FONTS_REGISTERED = True

    def _reg(name, *files):
        for f in files:
            p = os.path.join(_FONT_DIR, f)
            if os.path.isfile(p):
                try:
                    pdfmetrics.registerFont(TTFont(name, p))
                    return True
                except Exception:
                    pass
        return False

    global F_REG, F_BOLD, F_ITAL
    ok_r = _reg("Kanit",      "Kanit-Regular.ttf", "Kanit.ttf")
    ok_b = _reg("Kanit-Bold", "Kanit-Bold.ttf",    "KanitBold.ttf")
    F_REG  = "Kanit"      if ok_r else "Helvetica"
    F_BOLD = "Kanit-Bold" if ok_b else "Helvetica-Bold"
    F_ITAL = "Kanit"      if ok_r else "Helvetica-Oblique"

F_REG  = "Helvetica"
F_BOLD = "Helvetica-Bold"
F_ITAL = "Helvetica-Oblique"

# ── Esagono helper ────────────────────────────────────────────────────────────
def _hexagon_path(c, cx, cy, r):
    """Disegna un esagono flat-top centrato in (cx, cy) con raggio r."""
    pts = [
        (cx + r * math.cos(math.radians(30 + 60 * i)),
         cy + r * math.sin(math.radians(30 + 60 * i)))
        for i in range(6)
    ]
    p = c.beginPath()
    p.moveTo(pts[0][0], pts[0][1])
    for x, y in pts[1:]:
        p.lineTo(x, y)
    p.close()
    return p


def _draw_hex_logo(c, cx, cy, hex_r=16, gap=2):
    """
    Cluster esagonale (stile logo FT-CS) centrato in (cx, cy).
    Disegna solo il bordo verde, niente fill.
    """
    c.saveState()
    c.setStrokeColor(GREEN)
    c.setFillColor(NAVY)
    c.setLineWidth(1.8)

    # Layout honeycomb: 1 centro + 6 intorno + 6 parziali fuori
    row_h  = hex_r * math.sqrt(3)
    col_w  = hex_r * 1.5 + gap

    positions = [
        (0, 0),
        (col_w,  row_h / 2),
        (col_w, -row_h / 2),
        (0,      row_h),
        (0,     -row_h),
        (-col_w, row_h / 2),
        (-col_w,-row_h / 2),
        (col_w * 2, 0),
        (-col_w * 2, 0),
        (col_w,  row_h * 1.5),
        (col_w, -row_h * 1.5),
    ]
    for dx, dy in positions:
        p = _hexagon_path(c, cx + dx, cy + dy, hex_r - gap)
        c.drawPath(p, stroke=1, fill=1)
    c.restoreState()

# ── Primitivi pagina ──────────────────────────────────────────────────────────

def _background(c):
    c.setFillColor(NAVY)
    c.rect(0, 0, W, H, stroke=0, fill=1)


def _grid(c):
    c.saveState()
    c.setStrokeColor(GRID)
    c.setLineWidth(0.4)
    x = 0.0
    while x <= W:
        c.line(x, 0, x, H)
        x += GRID_STEP
    y = 0.0
    while y <= H:
        c.line(0, y, W, y)
        y += GRID_STEP
    c.restoreState()


def _header(c, pub_title, date_str, fig_num):
    c.saveState()
    c.setFont(F_ITAL, 9)
    c.setFillColor(GREEN)
    c.drawString(MARGIN, H - MARGIN + 14,
                 f"{pub_title}  -  {date_str}  FIG. {fig_num:02d}")
    c.restoreState()


def _footer(c, footer_text):
    c.saveState()
    c.setFont(F_REG, 8)
    c.setFillColor(CREAM)
    c.drawString(MARGIN, 18, footer_text)
    c.restoreState()


def _logo(c):
    """Logo esagonale in basso a destra."""
    _draw_hex_logo(c, cx=W - 90, cy=75, hex_r=18, gap=2)

# ── Word wrap ─────────────────────────────────────────────────────────────────

def _wrap(text, font, size, max_w, c):
    words = text.split()
    lines, cur = [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if c.stringWidth(test, font, size) <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines or [""]

# ── Parsing ───────────────────────────────────────────────────────────────────

def _parse_sections(summary):
    return [s.strip() for s in summary.split("=") if s.strip()]


def _parse_lines(section):
    result = []
    for raw in section.splitlines():
        line = raw.strip()
        if not line:
            result.append(("blank", ""))
        elif re.fullmatch(r"\*(.+)\*", line):
            result.append(("bold", line[1:-1]))
        elif re.fullmatch(r"_(.+)_", line):
            result.append(("italic", line[1:-1]))
        elif re.match(r"^(\d+[\.\)]\s+|[-•]\s+)", line):
            result.append(("list", re.sub(r"^(\d+[\.\)]\s+|[-•]\s+)", "", line)))
        else:
            result.append(("plain", line))
    return result

# ── Rendering ─────────────────────────────────────────────────────────────────

def _title_page(c, section, pub_title, date_str, footer_text, fig_num):
    _background(c)
    _grid(c)
    _header(c, pub_title, date_str, fig_num)
    _footer(c, footer_text)
    _logo(c)

    items      = _parse_lines(section)
    max_w      = W - 2 * MARGIN
    t_size     = 56
    b_size     = 26

    bold_items  = [(k, t) for k, t in items if k == "bold"]
    other_items = [(k, t) for k, t in items if k != "bold"]

    # Centra verticalmente il blocco titolo
    n_lines = sum(len(_wrap(t.upper(), F_BOLD, t_size, max_w, c))
                  for _, t in bold_items)
    y = H * 0.55 + (n_lines * t_size * 1.18) / 2

    for _, text in bold_items:
        for line in _wrap(text.upper(), F_BOLD, t_size, max_w, c):
            c.setFont(F_BOLD, t_size)
            c.setFillColor(GREEN)
            c.drawString(MARGIN, y, line)
            y -= t_size * 1.18
        y -= 4

    y -= 18
    for kind, text in other_items:
        if kind == "blank":
            y -= b_size * 0.5
            continue
        font = F_ITAL if kind == "italic" else F_REG
        for line in _wrap(text, font, b_size, max_w, c):
            c.setFont(font, b_size)
            c.setFillColor(CREAM)
            c.drawString(MARGIN, y, line)
            y -= b_size * 1.35


def _content_page(c, section, pub_title, date_str, footer_text, fig_num):
    _background(c)
    _grid(c)
    _header(c, pub_title, date_str, fig_num)
    _footer(c, footer_text)
    _logo(c)

    items       = _parse_lines(section)
    max_w       = W - 2 * MARGIN
    h_size      = 36
    b_size      = 17
    l_size      = 15
    y           = H - MARGIN - 30
    header_done = False

    for kind, text in items:
        if kind == "blank":
            y -= b_size * 0.4
            continue
        if kind == "bold" and not header_done:
            for line in _wrap(text.upper(), F_BOLD, h_size, max_w, c):
                c.setFont(F_BOLD, h_size)
                c.setFillColor(GREEN)
                c.drawString(MARGIN, y, line)
                y -= h_size * 1.2
            header_done = True
            y -= 10
        elif kind == "bold":
            for line in _wrap(text, F_BOLD, b_size, max_w, c):
                c.setFont(F_BOLD, b_size)
                c.setFillColor(GREEN)
                c.drawString(MARGIN, y, line)
                y -= b_size * 1.3
        elif kind == "italic":
            for line in _wrap(text, F_ITAL, b_size, max_w, c):
                c.setFont(F_ITAL, b_size)
                c.setFillColor(CREAM)
                c.drawString(MARGIN, y, line)
                y -= b_size * 1.3
        elif kind == "list":
            for i, line in enumerate(_wrap("• " + text, F_REG, l_size, max_w - 12, c)):
                c.setFont(F_REG, l_size)
                c.setFillColor(CREAM)
                c.drawString(MARGIN + (12 if i > 0 else 0), y, line)
                y -= l_size * 1.4
            y -= 2
        else:
            for line in _wrap(text, F_REG, b_size, max_w, c):
                c.setFont(F_REG, b_size)
                c.setFillColor(CREAM)
                c.drawString(MARGIN, y, line)
                y -= b_size * 1.3

# ── API pubblica ──────────────────────────────────────────────────────────────

def generate_pdf_a4(summary, pub_title, date_str, footer_text):
    """
    Genera PDF A4 portrait stile FT-CS Daily.
    summary: testo con sezioni separate da "="
    """
    _ensure_fonts()
    buf = BytesIO()
    cv  = canvas.Canvas(buf, pagesize=(W, H))
    sections = _parse_sections(summary)
    if not sections:
        _background(cv)
        _grid(cv)
        _logo(cv)
        cv.showPage()
        cv.save()
        return buf.getvalue()
    for i, section in enumerate(sections):
        if i == 0:
            _title_page(cv, section, pub_title, date_str, footer_text, i + 1)
        else:
            _content_page(cv, section, pub_title, date_str, footer_text, i + 1)
        cv.showPage()
    cv.save()
    return buf.getvalue()
