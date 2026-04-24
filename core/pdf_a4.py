"""
core/pdf_a4.py  —  Stile FT-CS Daily  (A4 portrait)
Sfondo navy, griglia teal, titoli teal, corpo bianco.
Font: Kanit (fallback Helvetica). Logo PNG in basso a destra.
Compatibile Python 3.14 + reportlab >= 4.2
"""
import base64
import io
import os
import re
from io import BytesIO

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

# ── Palette ─────────────────────────────────────────────────────────────────────────────────
NAVY  = HexColor("#131836")
GREEN = HexColor("#00C9A7")
GRID  = HexColor("#1C3F52")
WHITE = HexColor("#FFFFFF")

# ── Pagina ───────────────────────────────────────────────────────────────────────────────────
W, H      = A4
MARGIN    = 50
GRID_STEP = 52

# ── Tipografia ──────────────────────────────────────────────────────────────────────────────
T_SIZE = 30   # Titolo: size
T_LEAD = 36   # Titolo: leading
B_SIZE = 20   # Body: size
B_LEAD = 20   # Body: leading

# ── Font ─────────────────────────────────────────────────────────────────────────────────────
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_FONTS_REGISTERED = False
F_REG  = "Helvetica"
F_BOLD = "Helvetica-Bold"

def _find_font_dir():
    for parent in (_BASE_DIR, os.path.join(_BASE_DIR, "..")):
        for name in ("font", "fonts", "Font", "Fonts"):
            d = os.path.join(parent, name)
            if os.path.isdir(d):
                return d
    return os.path.join(_BASE_DIR, "..", "font")

def _ensure_fonts():
    global _FONTS_REGISTERED, F_REG, F_BOLD
    if _FONTS_REGISTERED:
        return
    _FONTS_REGISTERED = True
    font_dir = _find_font_dir()
    def _reg(name, *files):
        for fname in files:
            p = os.path.join(font_dir, fname)
            if os.path.isfile(p):
                try:
                    pdfmetrics.registerFont(TTFont(name, p))
                    return True
                except Exception:
                    pass
        return False
    ok_r = _reg("Kanit",      "Kanit-Regular.ttf", "Kanit.ttf")
    ok_b = _reg("Kanit-Bold", "Kanit-Bold.ttf",    "KanitBold.ttf")
    F_REG  = "Kanit"      if ok_r else "Helvetica"
    F_BOLD = "Kanit-Bold" if ok_b else "Helvetica-Bold"

# ── Logo (PNG embedded as base64) ─────────────────────────────────────────────────────────────────────────
_LOGO_B64 = 'iVBORw0KGgoAAAANSUhEUgAAAH4AAACUCAYAAABV/J1sAAAAw3pUWHRSYXcgcHJvZmlsZSB0eXBlIGV4aWYAAHjabVDbEQMhCPynipQgDxHL8XKXmXSQ8oOimbsk67ggyyAAx+v5gFsHoYDkYlpVk0OqVGruWAq0wZhk8EA5pobXOFSZAnmI3XI8TWf+iuOnQJjmXj4VsvsUtquwPiD7KkRhuHfU/X11NAsxhYCzQIuxklYr5xG2NdqCxYVOYte2f97Ft7dn/4eJDkZOzswaDXC/CtzcEWdi8UT00zgPFl6d+EL+7WkB3kA5WVP40AT8AAABhWlDQ1BJQ0MgcHJvZmlsZQAAeJx9kb9Lw0AcxV9/SFUqDhYs4pChOtlFRR1LFYtgobQVWnUwufQXNGlIUlwcBdeCgz8Wqw4uzro6uAqC4A8Q/wBxUnSREr+XFFrEeHDch3f3HnfvAG+zyhTDHwMU1dTTibiQy68KgVf4EUYfhjErMkNLZhazcB1f9/Dw9S7Ks9zP/TkG5ILBAI9AHGOabhJvEM9smhrnfeIQK4sy8TnxhE4XJH7kuuTwG+eSzV6eGdKz6XniELFQ6mKpi1lZV4iniSOyolK+N+ewzHmLs1Kts/Y9+QuDBXUlw3Wao0hgCUmkIEBCHRVUYSJKq0qKgTTtx138I7Y/RS6JXBUwciygBgWi7Qf/g9/dGsWpSScpGAd6XizrYwwI7AKthmV9H1tW6wTwPQNXasdfawJzn6Q3OlrkCBjcBi6uO5q0B1zuAOEnTdRFW/LR9BaLwPsZfVMeGLoF+tec3tr7OH0AstTV8g1wcAiMlyh73eXdvd29/Xum3d8P4fNy0wOZAu4AAA12aVRYdFhNTDpjb20uYWRvYmUueG1wAAAAAAA8P3hwYWNrZXQgYmVnaW49Iu+7vyIgaWQ9Ilc1TTBNcENlaGlIenJlU3pOVGN6a2M5ZCI/Pgo8eDp4bXBtZXRhIHhtbG5zOng9ImFkb2JlOm5zOm1ldGEvIiB4OnhtcHRrPSJYTVAgQ29yZSA0LjQuMC1FeGl2MiI+CiA8cmRmOlJERiB4bWxuczpyZGY9Imh0dHA6Ly93d3cudzMub3JnLzE5OTkvMDIvMjItcmRmLXN5bnRheC1ucyMiPgogIDxyZGY6RGVzY3JpcHRpb24gcmRmOmFib3V0PSIiCiAgICB4bWxuczp4bXBNTT0iaHR0cDovL25zLmFkb2JlLmNvbS94YXAvMS4wL21tLyIKICAgIHhtbG5zOnN0RXZ0PSJodHRwOi8vbnMuYWRvYmUuY29tL3hhcC8xLjAvc1R5cGUvUmVzb3VyY2VFdmVudCMiCiAgICB4bWxuczpkYz0iaHR0cDovL3B1cmwub3JnL2RjL2VsZW1lbnRzLzEuMS8iCiAgICB4bWxuczpHSU1QPSJodHRwOi8vd3d3LmdpbXAub3JnL3htcC8iCiAgICB4bWxuczp0aWZmPSJodHRwOi8vbnMuYWRvYmUuY29tL3RpZmYvMS4wLyIKICAgIHhtbG5zOnhtcD0iaHR0cDovL25zLmFkb2JlLmNvbS94YXAvMS4wLyIKICAgeG1wTU06RG9jdW1lbnRJRD0iZ2ltcDpkb2NpZDpnaW1wOjk5NDljMmQzLTJjMWItNDBiZC1iNjUzLTViOWExMGFiMmQ2NyIKICAgeG1wTU06SW5zdGFuY2VJRD0ieG1wLmlpZDpkOTg2Nzc4Yy01ZjBiLTQ2YTktYjFjOC05ZWNlOWMwYzYyMTIiCiAgIHhtcE1NOk9yaWdpbmFsRG9jdW1lbnRJRD0ieG1wLmRpZDo5NTlmMGQ3Yy1lYTZjLTQ2ZDAtYTM1NC0wMjM5MTY5ZGQ1NjUiCiAgIGRjOkZvcm1hdD0iaW1hZ2UvcG5nIgogICBHSU1QOkFQST0iMi4wIgogICBHSU1QOlBsYXRmb3JtPSJXaW5kb3dzIgogICBHSU1QOlRpbWVTdGFtcD0iMTc3NzAyNDMxNDAwNDUxNSIKICAgR0lNUDpWZXJzaW9uPSIyLjEwLjM2IgogICB0aWZmOk9yaWVudGF0aW9uPSIxIgogICB4bXA6Q3JlYXRvclRvb2w9IkdJTVAgMi4xMCIKICAgeG1wOk1ldGFkYXRhRGF0ZT0iMjAyNjowNDoyNFQxMTo1MTo0NCswMjowMCIKICAgeG1wOk1vZGlmeURhdGU9IjIwMjY6MDQ6MjRUMTE6NTE6NDQrMDI6MDAiPgogICA8eG1wTU06SGlzdG9yeT4KICAgIDxyZGY6U2VxPgogICAgIDxyZGY6bGkKICAgICAgc3RFdnQ6YWN0aW9uPSJzYXZlZCIKICAgICAgc3RFdnQ6Y2hhbmdlZD0iLyIKICAgICAgc3RFdnQ6aW5zdGFuY2VJRD0ieG1wLmlpZDo4MGJjZmNlMi0zOGI1LTRkZmItOTQ3NC0yMGE5YzVlYjE4MmUiCiAgICAgIHN0RXZ0OnNvZnR3YXJlQWdlbnQ9IkdpbXAgMi4xMCAoV2luZG93cykiCiAgICAgIHN0RXZ0OndoZW49IjIwMjYtMDQtMjRUMTE6NTE6NTQiLz4KICAgIDwvcmRmOlNlcT4KICAgPC94bXBNTTpIaXN0b3J5PgogIDwvcmRmOkRlc2NyaXB0aW9uPgogPC9yZGY6UkRGPgo8L3g6eG1wbWV0YT4KICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgCiAgICAgICAgICAgICAgICAgICAgICAgICAgIAo8P3hwYWNrZXQgZW5kPSJ3Ij8+ues+CgAAAAZiS0dEAMwAIQA9tEHeYwAAAAlwSFlzAAALEwAACxMBAJqcGAAAAAd0SU1FB+oEGAkzNbYv0WgAACAASURBVHja7b13gJ1VtT787Pa2U6enN0ggFCmhCAiGIr2XgVACQSACooL9ijrXctX7eUW5AgYMoZcJRToBYkIvCdIhBFJIJpNpZ2ZOe+su3x9c7o+LpBIwgfP8OWfvtdfs5127rL322kANNdRQQw011FBDDTXUUEMNNdRQQw011FBDDZsJSK0L1gBjyNG3XTtU23y0FPQrUqlm2+C24T3Rq1dPn57UiP+c4ZCH/1o/yNLnSYd/27jWkL6KD80pIh0jyxmaI7O8vqdy7gMnn/fYlvx/8hrVwEnt7ayTlaaJ0c2/WVIqNUZMY8iIIaYsk2dV2tura7AfRAhEfoBGYo0hRm0LoEb8loyj75mZeTuvb+6S7CiPKAwdNfpG1878uGFEpqK1OHXuCy/t5XAHSgeoUwR1S3r2vf/r33lqU7Q9eV4bL/cPbSrJYLybT158tTg6RGur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'

def _logo(c):
    img = ImageReader(io.BytesIO(base64.b64decode(_LOGO_B64)))
    c.drawImage(img, W - 140, 36, width=130, height=130, mask="auto")

# ── Primitivi ──────────────────────────────────────────────────────────────────────────────────
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
    c.setFont(F_REG, 9)
    c.setFillColor(WHITE)
    c.drawRightString(W - MARGIN, H - 35, f"{date_str}  |  Fig. {fig_num}")
    c.setStrokeColor(GREEN)
    c.setLineWidth(1)
    c.line(MARGIN, H - 42, W - MARGIN, H - 42)
    c.restoreState()

def _footer(c, footer_text):
    c.saveState()
    c.setStrokeColor(GREEN)
    c.setLineWidth(0.6)
    c.line(MARGIN, 30, W - MARGIN, 30)
    c.setFont(F_REG, 8)
    c.setFillColor(WHITE)
    c.drawString(MARGIN, 18, footer_text)
    c.restoreState()

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
        elif re.match(r"^_(.+)_$", line):
            result.append(("italic", line[1:-1]))
        elif re.match(r"^(\d+[\.)\]\s+|[-\u2022]\s+)", line):
            result.append(("list", re.sub(r"^(\d+[\.)\]\s+|[-\u2022]\s+)", "", line)))
        else:
            result.append(("plain", line))
    return result

# ── Rendering pagina ───────────────────────────────────────────────────────────────────────────
def _render_page(c, section, pub_title, date_str, footer_text, fig_num):
    _background(c)
    _grid(c)
    _header(c, pub_title, date_str, fig_num)
    _footer(c, footer_text)
    _logo(c)

    items         = _parse_lines(section)
    max_w         = W - 2 * MARGIN
    y             = H - 70
    in_title_zone = True   # True finche' non incontriamo contenuto non-bold non-blank

    for kind, text in items:
        if kind == "blank":
            y -= B_LEAD * 0.5
            continue

        if kind == "bold" and in_title_zone:
            # ─ Titolo: 30pt, ALL CAPS, Kanit Bold, GREEN, leading 36
            c.setFillColor(GREEN)
            c.setFont(F_BOLD, T_SIZE)
            for line in _wrap(text.upper(), F_BOLD, T_SIZE, max_w, c):
                c.drawString(MARGIN, y, line)
                y -= T_LEAD

        else:
            # Prima riga di body: aggiungi gap dopo zona titolo
            if in_title_zone:
                y -= 8
                in_title_zone = False

            if kind == "bold":
                # Bold: 20pt, Kanit Bold, WHITE, leading 20
                c.setFillColor(WHITE)
                c.setFont(F_BOLD, B_SIZE)
                for line in _wrap(text, F_BOLD, B_SIZE, max_w, c):
                    c.drawString(MARGIN, y, line)
                    y -= B_LEAD

            elif kind == "italic":
                # Corsivo: 20pt, Kanit Regular, WHITE, leading 20
                c.setFillColor(WHITE)
                c.setFont(F_REG, B_SIZE)
                for line in _wrap(text, F_REG, B_SIZE, max_w, c):
                    c.drawString(MARGIN, y, line)
                    y -= B_LEAD

            elif kind == "list":
                # Lista: 20pt, Kanit Regular, WHITE, leading 20
                c.setFillColor(WHITE)
                c.setFont(F_REG, B_SIZE)
                for i, line in enumerate(_wrap("\u2022 " + text, F_REG, B_SIZE, max_w - 16, c)):
                    c.drawString(MARGIN + (16 if i > 0 else 0), y, line)
                    y -= B_LEAD

            else:
                # Normale: 20pt, Kanit Regular, WHITE, leading 20
                c.setFillColor(WHITE)
                c.setFont(F_REG, B_SIZE)
                for line in _wrap(text, F_REG, B_SIZE, max_w, c):
                    c.drawString(MARGIN, y, line)
                    y -= B_LEAD

def generate_pdf_a4(summary, pub_title, date_str, footer_text):
    _ensure_fonts()
    buf = BytesIO()
    cv  = canvas.Canvas(buf, pagesize=(W, H))
    sections = _parse_sections(summary)
    if not sections:
        _background(cv); _grid(cv); _logo(cv)
        cv.showPage(); cv.save()
        return buf.getvalue()
    for i, section in enumerate(sections):
        _render_page(cv, section, pub_title, date_str, footer_text, i + 1)
        cv.showPage()
    cv.save()
    return buf.getvalue()
