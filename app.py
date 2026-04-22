import zipfile
from datetime import date
from io import BytesIO
from pathlib import Path

import streamlit as st

from core.gdocs import process_url
from core.pdf_a4 import generate_pdf_a4
from core.pdf_square import generate_pdf_square

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(page_title="Slider PDF", page_icon="📄", layout="centered")
st.title("📄 Slider PDF")
st.caption("Trasforma articoli Google Docs in PDF slider A4 e quadrati.")

# ── Secrets / config ─────────────────────────────────────────────────────────
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except KeyError:
    st.error("Chiave GEMINI_API_KEY non trovata. Aggiungila in .streamlit/secrets.toml")
    st.stop()

# ── Sidebar settings ─────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Impostazioni")
    pub_title = st.text_input("Titolo pubblicazione", value="FT-CS Daily")
    today_str = st.text_input("Data", value=date.today().strftime("%d/%m/%y"))
    footer_text = st.text_input("Footer", value="Leo Sorge @ CEO Source 2026")
    gemini_model = st.selectbox(
        "Modello Gemini",
        ["gemini-2.5-flash", "gemini-1.5-flash", "gemini-1.0-pro"],
    )

# ── Load articoli.txt ─────────────────────────────────────────────────────────
articoli_path = Path("articoli.txt")
if articoli_path.exists():
    default_urls = articoli_path.read_text(encoding="utf-8")
else:
    default_urls = ""

urls_raw = st.text_area(
    "URL articoli (uno per riga)",
    value=default_urls,
    height=160,
    placeholder="https://docs.google.com/document/d/...",
)

urls = [u.strip() for u in urls_raw.splitlines() if u.strip()]

if not urls:
    st.info("Aggiungi almeno un URL Google Docs per iniziare.")
    st.stop()

st.write(f"**{len(urls)} articolo/i** da elaborare.")

# ── Process ───────────────────────────────────────────────────────────────────
if st.button("🚀 Genera PDF", type="primary"):
    zip_a4_buf = BytesIO()
    zip_sq_buf = BytesIO()

    with zipfile.ZipFile(zip_a4_buf, "w", zipfile.ZIP_DEFLATED) as za, \
         zipfile.ZipFile(zip_sq_buf, "w", zipfile.ZIP_DEFLATED) as zs:

        progress = st.progress(0, text="Elaborazione in corso…")

        for idx, url in enumerate(urls):
            progress.progress((idx) / len(urls), text=f"Elaboro {idx + 1}/{len(urls)}: {url[:60]}…")
            try:
                with st.spinner(f"Articolo {idx + 1}: sintesi Gemini…"):
                    result = process_url(url, GEMINI_API_KEY, gemini_model)

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
