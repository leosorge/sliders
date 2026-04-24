# Versione per Unidata - quella standard è my_pdf_a4


"""
core/pdf_a4.py  —  Stile FT-CS Daily
======================================
Sfondo navy scuro, griglia teal sottile, titoli in verde,
testo corpo in panna. Font: Kamit (fallback Helvetica).

Posiziona questo file in  <progetto>/core/pdf_a4.py
e inserisci i file .ttf di Kamit nella cartella  <progetto>/fonts/
"""
from __future__ import annotations
import os
import re
from io import BytesIO

from reportlab.lib.colors import Color, HexColor
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

# ── Palette brand FT-CS Daily ────────────────────────────────────────────────
NAVY      = HexColor("#131836")           # sfondo
GREEN     = HexColor("#00C9A7")           # titolo + griglia
CREAM     = HexColor("#EDE8D8")           # corpo
GRID_COL  = Color(0, 0.788, 0.655, 0.18) # verde 18 % opacità

# ── Dimensioni A4 ────────────────────────────────────────────────────────────
W, H       = A4          # 595.27 × 841.89 pt
MARGIN     = 50
GRID_STEP  = 52          # passo griglia in punti

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

_ok_reg  = _reg("Kamit",       "Kamit.ttf",       "kamit.ttf",      "Kamit-Regular.ttf")
_ok_bold = _reg("Kamit-Bold",  "Kamit-Bold.ttf",  "KamitBold.ttf",  "Kamit-Bold.otf")

F_REG   = "Kamit"      if _ok_reg  else "Helvetica"
F_BOLD  = "Kamit-Bold" if _ok_bold else "Helvetica-Bold"
F_ITAL  = "Kamit"      if _ok_reg  else "Helvetica-Oblique"

# ── Primitivi grafici ────────────────────────────────────────────────────────

def _background(c: canvas.Canvas, pw: float, ph: float) -> None:
    c.setFillColor(NAVY)
    c.rect(0, 0, pw, ph, stroke=0, fill=1)


def _grid(c: canvas.Canvas, pw: float, ph: float) -> None:
    c.saveState()
    c.setStrokeColor(GRID_COL)
    c.setLineWidth(0.4)
    x = 0.0
    while x <= pw:
        c.line(x, 0, x, ph)
        x += GRID_STEP
    y = 0.0
    while y <= ph:
        c.line(0, y, pw, y)
        y += GRID_STEP
    c.restoreState()


def _header(c: canvas.Canvas, pub_title: str, date_str: str,
            fig_num: int, ph: float) -> None:
    c.saveState()
    c.setFont(F_ITAL, 9)
    c.setFillColor(GREEN)
    c.drawString(MARGIN, ph - MARGIN + 14,
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
    """Word-wrap manuale: ritorna lista di righe."""
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

# ── Parsing del testo strutturato ────────────────────────────────────────────

def _parse_sections(summary: str) -> list[str]:
    return [s.strip() for s in summary.split("=") if s.strip()]


def _parse_lines(section: str) -> list[tuple[str, str]]:
    """
    Ritorna lista di (tipo, testo):
      'bold'   → *testo*
      'italic' → _testo_
      'list'   → 1. testo  /  - testo  /  • testo
      'blank'  → riga vuota
      'plain'  → tutto il resto
    """
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
                       date_str: str, footer_text: str, fig_num: int,
                       pw: float, ph: float) -> None:
    _background(c, pw, ph)
    _grid(c, pw, ph)
    _header(c, pub_title, date_str, fig_num, ph)
    _footer(c, footer_text)

    items    = _parse_lines(section)
    max_w    = pw - 2 * MARGIN
    t_size   = 56          # dimensione titolo
    b_size   = 26          # dimensione corpo

    # Conta le righe bold per centrare verticalmente il blocco titolo
    bold_items  = [(k, t) for k, t in items if k == "bold"]
    other_items = [(k, t) for k, t in items if k != "bold"]

    # Stima altezza titolo
    est_title_h = len(bold_items) * t_size * 1.15 * 2  # stima generosa
    y = ph * 0.55 + est_title_h / 2

    for _, text in bold_items:
        lines = _wrap(text.upper(), F_BOLD, t_size, max_w, c)
        for line in lines:
            c.setFont(F_BOLD, t_size)
            c.setFillColor(GREEN)
            c.drawString(MARGIN, y, line)
            y -= t_size * 1.18
        y -= 6

    y -= 16  # gap tra titolo e corpo
    for kind, text in other_items:
        if kind == "blank":
            y -= b_size * 0.5
            continue
        font = F_ITAL if kind == "italic" else F_REG
        lines = _wrap(text, font, b_size, max_w, c)
        for line in lines:
            c.setFont(font, b_size)
            c.setFillColor(CREAM)
            c.drawString(MARGIN, y, line)
            y -= b_size * 1.35


def _render_content_page(c: canvas.Canvas, section: str, pub_title: str,
                         date_str: str, footer_text: str, fig_num: int,
                         pw: float, ph: float) -> None:
    _background(c, pw, ph)
    _grid(c, pw, ph)
    _header(c, pub_title, date_str, fig_num, ph)
    _footer(c, footer_text)

    items    = _parse_lines(section)
    max_w    = pw - 2 * MARGIN
    h_size   = 36          # intestazione sezione
    b_size   = 17          # corpo
    l_size   = 15          # lista

    y            = ph - MARGIN - 30
    header_done  = False

    for kind, text in items:
        if kind == "blank":
            y -= b_size * 0.4
            continue

        if kind == "bold" and not header_done:
            # Prima bold = intestazione sezione in verde
            lines = _wrap(text.upper(), F_BOLD, h_size, max_w, c)
            for line in lines:
                c.setFont(F_BOLD, h_size)
                c.setFillColor(GREEN)
                c.drawString(MARGIN, y, line)
                y -= h_size * 1.2
            header_done = True
            y -= 10

        elif kind == "bold":
            # Bold successivi = keyword verde più piccolo
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
            lines = _wrap(bullet, F_REG, l_size, max_w - 12, c)
            for i, line in enumerate(lines):
                c.setFont(F_REG, l_size)
                c.setFillColor(CREAM)
                x_off = MARGIN + (14 if i > 0 else 0)
                c.drawString(x_off, y, line)
                y -= l_size * 1.4
            y -= 2

        else:  # plain
            lines = _wrap(text, F_REG, b_size, max_w, c)
            for line in lines:
                c.setFont(F_REG, b_size)
                c.setFillColor(CREAM)
                c.drawString(MARGIN, y, line)
                y -= b_size * 1.3

# ── API pubblica ─────────────────────────────────────────────────────────────

def generate_pdf_a4(summary: str, pub_title: str,
                    date_str: str, footer_text: str) -> bytes:
    """
    Genera un PDF A4 (portrait) multi-pagina nello stile FT-CS Daily.

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
        # PDF vuoto di sicurezza
        _background(cv, W, H)
        _grid(cv, W, H)
        cv.showPage()
        cv.save()
        return buf.getvalue()

    for i, section in enumerate(sections):
        if i == 0:
            _render_title_page(cv, section, pub_title, date_str,
                               footer_text, i + 1, W, H)
        else:
            _render_content_page(cv, section, pub_title, date_str,
                                 footer_text, i + 1, W, H)
        cv.showPage()

    cv.save()
    return buf.getvalue()
