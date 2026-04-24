# Versione Unidata - la mia versione classica è my_pdf_square.py


"""
core/pdf_square.py  —  Stile FT-CS Daily (formato quadrato)
=============================================================
Stessa palette e logica di pdf_a4.py, ma pagine quadrate 595×595 pt.
Testo ridimensionato per sfruttare il formato orizzontale/quadrato.

Posiziona questo file in  <progetto>/core/pdf_square.py
"""
from __future__ import annotations
import os
import re
from io import BytesIO

from reportlab.lib.colors import Color, HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

# ── Palette brand ────────────────────────────────────────────────────────────
NAVY      = HexColor("#131836")
GREEN     = HexColor("#00C9A7")
CREAM     = HexColor("#EDE8D8")
GRID_COL  = Color(0, 0.788, 0.655, 0.18)

# ── Dimensioni quadrato ───────────────────────────────────────────────────────
SQ        = 595.0        # lato del quadrato in punti (≈ 21 cm)
W = H     = SQ
MARGIN    = 48
GRID_STEP = 50

# ── Registrazione font Kamit ─────────────────────────────────────────────────
_FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fonts")

def _reg(name: str, *candidates: str) -> bool:
    for fname in candidates:
        path = os.path.join(_FONT_DIR, fname)
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont(name, path))
                return True
            except Exception:
                pass
    return False

_ok_reg  = _reg("Kanit",       "Kanit-Regular.ttf", "Kanit.ttf",     "kanit-regular.ttf")
_ok_bold = _reg("Kanit-Bold",  "Kanit-Bold.ttf",    "KanitBold.ttf", "kanit-bold.ttf")

F_REG   = "Kanit"      if _ok_reg  else "Helvetica"
F_BOLD  = "Kanit-Bold" if _ok_bold else "Helvetica-Bold"
F_ITAL  = "Kanit"      if _ok_reg  else "Helvetica-Oblique"

# ── Primitivi grafici ────────────────────────────────────────────────────────

def _background(c: canvas.Canvas) -> None:
    c.setFillColor(NAVY)
    c.rect(0, 0, W, H, stroke=0, fill=1)


def _grid(c: canvas.Canvas) -> None:
    c.saveState()
    c.setStrokeColor(GRID_COL)
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


def _header(c: canvas.Canvas, pub_title: str,
            date_str: str, fig_num: int) -> None:
    c.saveState()
    c.setFont(F_ITAL, 9)
    c.setFillColor(GREEN)
    c.drawString(MARGIN, H - MARGIN + 14,
                 f"{pub_title}  -  {date_str}  FIG. {fig_num:02d}")
    c.restoreState()


def _footer(c: canvas.Canvas, footer_text: str) -> None:
    c.saveState()
    c.setFont(F_REG, 8)
    c.setFillColor(CREAM)
    c.drawString(MARGIN, 18, footer_text)
    c.restoreState()


def _wrap(text: str, font: str, size: float,
          max_w: float, c: canvas.Canvas) -> list[str]:
    words = text.split()
    lines: list[str] = []
    cur = ""
    for w in words:
        test = f"{cur} {w}".strip()
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

def _parse_sections(summary: str) -> list[str]:
    return [s.strip() for s in summary.split("=") if s.strip()]


def _parse_lines(section: str) -> list[tuple[str, str]]:
    result: list[tuple[str, str]] = []
    for raw in section.splitlines():
        line = raw.strip()
        if not line:
            result.append(("blank", ""))
            continue
        if re.fullmatch(r"\*(.+)\*", line):
            result.append(("bold", line[1:-1]))
        elif re.fullmatch(r"_(.+)_", line):
            result.append(("italic", line[1:-1]))
        elif re.match(r"^(\d+[\.\)]\s+|[-•]\s+)", line):
            result.append(("list", re.sub(r"^(\d+[\.\)]\s+|[-•]\s+)", "", line)))
        else:
            result.append(("plain", line))
    return result

# ── Rendering pagine ─────────────────────────────────────────────────────────

def _render_title_page(c: canvas.Canvas, section: str, pub_title: str,
                       date_str: str, footer_text: str, fig_num: int) -> None:
    _background(c)
    _grid(c)
    _header(c, pub_title, date_str, fig_num)
    _footer(c, footer_text)

    items     = _parse_lines(section)
    max_w     = W - 2 * MARGIN
    t_size    = 52         # titolo grande
    b_size    = 22         # corpo

    bold_items  = [(k, t) for k, t in items if k == "bold"]
    other_items = [(k, t) for k, t in items if k != "bold"]

    # Posizione verticale centrata: stima altezza blocco titolo
    n_title_lines = sum(
        len(_wrap(t.upper(), F_BOLD, t_size, max_w, c))
        for _, t in bold_items
    )
    title_block_h = n_title_lines * t_size * 1.18
    y = H * 0.50 + title_block_h / 2

    for _, text in bold_items:
        lines = _wrap(text.upper(), F_BOLD, t_size, max_w, c)
        for line in lines:
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
        font  = F_ITAL if kind == "italic" else F_REG
        lines = _wrap(text, font, b_size, max_w, c)
        for line in lines:
            c.setFont(font, b_size)
            c.setFillColor(CREAM)
            c.drawString(MARGIN, y, line)
            y -= b_size * 1.35


def _render_content_page(c: canvas.Canvas, section: str, pub_title: str,
                         date_str: str, footer_text: str, fig_num: int) -> None:
    _background(c)
    _grid(c)
    _header(c, pub_title, date_str, fig_num)
    _footer(c, footer_text)

    items    = _parse_lines(section)
    max_w    = W - 2 * MARGIN
    h_size   = 32
    b_size   = 16
    l_size   = 14

    y           = H - MARGIN - 28
    header_done = False

    for kind, text in items:
        if kind == "blank":
            y -= b_size * 0.4
            continue

        if kind == "bold" and not header_done:
            lines = _wrap(text.upper(), F_BOLD, h_size, max_w, c)
            for line in lines:
                c.setFont(F_BOLD, h_size)
                c.setFillColor(GREEN)
                c.drawString(MARGIN, y, line)
                y -= h_size * 1.2
            header_done = True
            y -= 10

        elif kind == "bold":
            lines = _wrap(text, F_BOLD, b_size, max_w, c)
            for line in lines:
                c.setFont(F_BOLD, b_size)
                c.setFillColor(GREEN)
                c.drawString(MARGIN, y, line)
                y -= b_size * 1.3

        elif kind == "italic":
            lines = _wrap(text, F_ITAL, b_size, max_w, c)
            for line in lines:
                c.setFont(F_ITAL, b_size)
                c.setFillColor(CREAM)
                c.drawString(MARGIN, y, line)
                y -= b_size * 1.3

        elif kind == "list":
            bullet = "• " + text
            lines  = _wrap(bullet, F_REG, l_size, max_w - 12, c)
            for i, line in enumerate(lines):
                c.setFont(F_REG, l_size)
                c.setFillColor(CREAM)
                x_off = MARGIN + (12 if i > 0 else 0)
                c.drawString(x_off, y, line)
                y -= l_size * 1.4
            y -= 2

        else:
            lines = _wrap(text, F_REG, b_size, max_w, c)
            for line in lines:
                c.setFont(F_REG, b_size)
                c.setFillColor(CREAM)
                c.drawString(MARGIN, y, line)
                y -= b_size * 1.3

# ── API pubblica ─────────────────────────────────────────────────────────────

def generate_pdf_square(summary: str, pub_title: str,
                        date_str: str, footer_text: str) -> bytes:
    """
    Genera un PDF quadrato 595×595 pt nello stile FT-CS Daily.

    Parametri
    ---------
    summary      : testo strutturato con sezioni separate da "="
    pub_title    : es. "FT-CS Daily"
    date_str     : es. "24/04/26"
    footer_text  : es. "Leo Sorge @ CEO Source 2026"

    Ritorna
    -------
    bytes del PDF generato.
    """
    buf = BytesIO()
    cv  = canvas.Canvas(buf, pagesize=(W, H))

    sections = _parse_sections(summary)
    if not sections:
        _background(cv)
        _grid(cv)
        cv.showPage()
        cv.save()
        return buf.getvalue()

    for i, section in enumerate(sections):
        if i == 0:
            _render_title_page(cv, section, pub_title, date_str,
                               footer_text, i + 1)
        else:
            _render_content_page(cv, section, pub_title, date_str,
                                 footer_text, i + 1)
        cv.showPage()

    cv.save()
    return buf.getvalue()
