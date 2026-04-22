"""
core/pdf_viewer.py
──────────────────
Utilità per il modulo Viewer A4 integrato in app.py.

Converte ogni pagina di un PDF in un'immagine PNG in memoria usando
PyMuPDF (fitz) — già disponibile come dipendenza leggera, senza
poppler/ghostscript richiesti.
"""

from __future__ import annotations

from io import BytesIO
from typing import Iterator

try:
    import fitz  # PyMuPDF
    _BACKEND = "pymupdf"
except ImportError:
    fitz = None  # type: ignore
    _BACKEND = None

try:
    from PIL import Image
    _PIL = True
except ImportError:
    _PIL = False


def backend_available() -> bool:
    """True se PyMuPDF è installato."""
    return fitz is not None


def page_count(pdf_bytes: bytes) -> int:
    """Restituisce il numero di pagine del PDF."""
    if not fitz:
        raise RuntimeError("PyMuPDF non installato. Aggiungi pymupdf a requirements.txt")
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    n = doc.page_count
    doc.close()
    return n


def render_page(pdf_bytes: bytes, page_index: int, dpi: int = 150) -> bytes:
    """
    Renderizza una singola pagina (0-based) in PNG.

    Parameters
    ----------
    pdf_bytes   : contenuto del PDF
    page_index  : indice 0-based della pagina
    dpi         : risoluzione (default 150 per anteprima rapida)

    Returns
    -------
    bytes PNG della pagina renderizzata
    """
    if not fitz:
        raise RuntimeError("PyMuPDF non installato. Aggiungi pymupdf a requirements.txt")
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page = doc.load_page(page_index)
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    png_bytes = pix.tobytes("png")
    doc.close()
    return png_bytes


def render_all_pages(pdf_bytes: bytes, dpi: int = 150) -> list[bytes]:
    """Renderizza tutte le pagine e restituisce lista di PNG bytes."""
    n = page_count(pdf_bytes)
    return [render_page(pdf_bytes, i, dpi) for i in range(n)]


def iter_pages(pdf_bytes: bytes, dpi: int = 150) -> Iterator[tuple[int, bytes]]:
    """Generator: (page_number_1based, png_bytes) per ogni pagina."""
    n = page_count(pdf_bytes)
    for i in range(n):
        yield (i + 1, render_page(pdf_bytes, i, dpi))
