import zipfile
from datetime import date
from io import BytesIO
from pathlib import Path

import streamlit as st

from core.gdocs import process_url
from core.pdf_a4 import generate_pdf_a4
from core.pdf_square import generate_pdf_square

# Helvetica average char width ≈ 0.55 × font_size (points)
# A4 usable width = 595 - 2×50 = 495 pt  |  font_size = 22*2*0.9 = 39.6
# Square usable width = 842 - 2×50 = 742 pt  |  font_size = 22*2*0.9*1.5 = 59.4
_CHAR_WIDTH_RATIO = 0.55
MAX_CHARS_A4 = int((595 - 100) / (_CHAR_WIDTH_RATIO * 22 * 2 * 0.9))
MAX_CHARS_SQ = int((842 - 100) / (_CHAR_WIDTH_RATIO * 22 * 2 * 0.9 * 1.5))

st.set_page_config(page_title="Slider PDF", page_icon="📄", layout="centered")
st.title("📄 Slider PDF")
st.caption("Trasforma articoli Google Docs in PDF slider A4 e quadrati.")

try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except KeyError:
    st.error("Chiave GEMINI_API_KEY non trovata. Aggiungila in .streamlit/secrets.toml")
    st.stop()

with st.sidebar:
    st.header("⚙️ Impostazioni")
    pub_title = st.text_input("Titolo pubblicazione", value="FT-CS Daily")
    today_str = st.text_input("Data", value=date.today().strftime("%d/%m/%y"))
    footer_text = st.text_input("Footer", value="Leo Sorge @ CEO Source 2026")
    gemini_model = st.selectbox(
        "Modello Gemini",
        ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"],
    )
    st.caption(f"Max caratteri/riga — A4: {MAX_CHARS_A4}  |  Quadrato: {MAX_CHARS_SQ}")

articoli_path = Path("articoli.txt")
default_urls = articoli_path.read_text(encoding="utf-8") if articoli_path.exists() else ""

urls_raw = st.text_area(
    "URL articoli (uno per riga)",
    value=default_urls,
    height=160,
    placeholder="https://docs.google.com/document/d/...",
)

urls = [u.strip() for u in urls_raw.splitlines() if u.strip() and not u.strip().startswith("#")]

if not urls:
    st.info("Aggiungi almeno un URL Google Docs per iniziare.")
    st.stop()

st.write(f"**{len(urls)} articolo/i** da elaborare.")

if st.button("🚀 Genera PDF", type="primary"):
    zip_a4_buf = BytesIO()
    zip_sq_buf = BytesIO()

    with zipfile.ZipFile(zip_a4_buf, "w", zipfile.ZIP_DEFLATED) as za, \
         zipfile.ZipFile(zip_sq_buf, "w", zipfile.ZIP_DEFLATED) as zs:

        progress = st.progress(0, text="Elaborazione in corso…")

        for idx, url in enumerate(urls):
            progress.progress(idx / len(urls), text=f"Elaboro {idx + 1}/{len(urls)}: {url[:60]}…")
            try:
                with st.spinner(f"Articolo {idx + 1}: sintesi Gemini…"):
                    # Use the more restrictive max_chars (A4 is narrower)
                    result = process_url(url, GEMINI_API_KEY, gemini_model, max_chars=MAX_CHARS_A4)

                fname = result["filename"] or f"articolo_{idx + 1:02d}"
                summary = result["summary"]

                with st.spinner(f"Articolo {idx + 1}: PDF A4…"):
                    pdf_a4 = generate_pdf_a4(summary, pub_title, today_str, footer_text)

                with st.spinner(f"Articolo {idx + 1}: PDF quadrato…"):
                    pdf_sq = generate_pdf_square(summary, pub_title, today_str, footer_text)

                za.writestr(f"{fname}_A4.pdf", pdf_a4)
                zs.writestr(f"{fname}_sq.pdf", pdf_sq)

                st.success(f"✅ {result['title']}")

            except Exception as e:
                st.error(f"❌ Errore su {url[:60]}: {e}")

        progress.progress(1.0, text="Completato!")

    zip_a4_buf.seek(0)
    zip_sq_buf.seek(0)

    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            label="⬇️ Scarica ZIP A4",
            data=zip_a4_buf,
            file_name="slider_A4.zip",
            mime="application/zip",
            use_container_width=True,
        )
    with col2:
        st.download_button(
            label="⬇️ Scarica ZIP Quadrati",
            data=zip_sq_buf,
            file_name="slider_quadrati.zip",
            mime="application/zip",
            use_container_width=True,
        )
