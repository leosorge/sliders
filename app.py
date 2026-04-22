import zipfile
from datetime import date
from io import BytesIO
from pathlib import Path

import streamlit as st

from core.gdocs import process_url
from core.pdf_a4 import generate_pdf_a4
from core.pdf_square import generate_pdf_square

# ── Costanti layout ───────────────────────────────────────────────────────────
_CHAR_WIDTH_RATIO = 0.55
MAX_CHARS_A4 = int((595 - 100) / (_CHAR_WIDTH_RATIO * 22 * 2 * 0.9))
MAX_CHARS_SQ = int((842 - 100) / (_CHAR_WIDTH_RATIO * 22 * 2 * 0.9 * 1.5))

st.set_page_config(page_title="Slider PDF", page_icon="📄", layout="centered")
st.title("📄 Slider PDF")
st.caption("Trasforma articoli Google Docs in PDF slider A4 e quadrati.")

# ── API key ───────────────────────────────────────────────────────────────────
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except KeyError:
    st.error("Chiave GEMINI_API_KEY non trovata. Aggiungila in .streamlit/secrets.toml")
    st.stop()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Impostazioni")
    pub_title    = st.text_input("Titolo pubblicazione", value="FT-CS Daily")
    today_str    = st.text_input("Data", value=date.today().strftime("%d/%m/%y"))
    footer_text  = st.text_input("Footer", value="Leo Sorge @ CEO Source 2026")
    gemini_model = st.selectbox(
        "Modello Gemini",
        ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"],
    )
    st.caption(f"Max caratteri/riga — A4: {MAX_CHARS_A4} | Quadrato: {MAX_CHARS_SQ}")

# ── Helper: passaggio Tab 1 → Tab 2 via session_state ────────────────────────
def _push_to_viewer(name: str, pdf_bytes: bytes) -> None:
    """Aggiunge/aggiorna un PDF A4 nello store del Viewer."""
    try:
        from core.pdf_viewer import page_count
        n = page_count(pdf_bytes)
    except Exception:
        n = 1
    store = st.session_state.setdefault("pdf_store", [])
    for entry in store:
        if entry["name"] == name:
            entry.update({"bytes": pdf_bytes, "n_pages": n, "current_page": 1})
            return
    store.append({"name": name, "bytes": pdf_bytes, "n_pages": n, "current_page": 1})


# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_genera, tab_viewer = st.tabs(["🚀 Genera da Google Docs", "📂 Viewer PDF A4"])

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 – Genera PDF da Google Docs
# ═══════════════════════════════════════════════════════════════════════════════
with tab_genera:
    articoli_path = Path("articoli.txt")
    default_urls  = articoli_path.read_text(encoding="utf-8") if articoli_path.exists() else ""

    urls_raw = st.text_area(
        "URL articoli (uno per riga)",
        value=default_urls,
        height=160,
        placeholder="https://docs.google.com/document/d/...",
    )
    urls = [
        u.strip()
        for u in urls_raw.splitlines()
        if u.strip() and not u.strip().startswith("#")
    ]

    if not urls:
        st.info("Aggiungi almeno un URL Google Docs per iniziare.")
    else:
        st.write(f"**{len(urls)} articolo/i** da elaborare.")

        if st.button("🚀 Genera PDF", type="primary"):
            # Svuota lo store viewer prima di una nuova generazione
            st.session_state.pdf_store   = []
            st.session_state.outer_start = 0

            zip_a4_buf = BytesIO()
            zip_sq_buf = BytesIO()

            with zipfile.ZipFile(zip_a4_buf, "w", zipfile.ZIP_DEFLATED) as za, \
                 zipfile.ZipFile(zip_sq_buf, "w", zipfile.ZIP_DEFLATED) as zs:

                progress = st.progress(0, text="Elaborazione in corso…")

                for idx, url in enumerate(urls):
                    progress.progress(
                        idx / len(urls),
                        text=f"Elaboro {idx + 1}/{len(urls)}: {url[:60]}…",
                    )
                    try:
                        with st.spinner(f"Articolo {idx + 1}: sintesi Gemini…"):
                            result = process_url(
                                url, GEMINI_API_KEY, gemini_model, max_chars=MAX_CHARS_A4
                            )

                        fname   = result["filename"] or f"articolo_{idx + 1:02d}"
                        summary = result["summary"]

                        with st.spinner(f"Articolo {idx + 1}: PDF A4…"):
                            pdf_a4 = generate_pdf_a4(summary, pub_title, today_str, footer_text)

                        with st.spinner(f"Articolo {idx + 1}: PDF quadrato…"):
                            pdf_sq = generate_pdf_square(summary, pub_title, today_str, footer_text)

                        za.writestr(f"{fname}_A4.pdf", pdf_a4)
                        zs.writestr(f"{fname}_sq.pdf", pdf_sq)

                        # ── Passa il PDF A4 direttamente al Viewer ────────
                        _push_to_viewer(f"{fname}_A4.pdf", pdf_a4)

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
                    width="stretch",
                )
            with col2:
                st.download_button(
                    label="⬇️ Scarica ZIP Quadrati",
                    data=zip_sq_buf,
                    file_name="slider_quadrati.zip",
                    mime="application/zip",
                    width="stretch",
                )

            n_gen = len(st.session_state.get("pdf_store", []))
            if n_gen:
                st.info(
                    f"✅ {n_gen} PDF A4 pronti nel **Viewer** — "
                    "clicca la tab **📂 Viewer PDF A4** per visualizzarli."
                )

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 – Viewer PDF A4
# ═══════════════════════════════════════════════════════════════════════════════
with tab_viewer:
    # ── Import lazy ───────────────────────────────────────────────────────────
    try:
        from core.pdf_viewer import backend_available, page_count, render_page
        _viewer_ok = backend_available()
    except ImportError:
        _viewer_ok = False

    if not _viewer_ok:
        st.warning("**PyMuPDF non trovato.** Aggiungi `pymupdf` a `requirements.txt` e rideploya.")
        st.code("pymupdf>=1.23", language="text")
        st.stop()

    # ── Sorgente dati: Tab 1 (automatica) oppure upload manuale ───────────────
    store_from_tab1 = st.session_state.get("pdf_store", [])

    if store_from_tab1:
        st.success(
            f"📥 **{len(store_from_tab1)} PDF A4** caricati automaticamente da *Genera da Google Docs*."
        )
        with st.expander("➕ Aggiungi altri PDF manualmente", expanded=False):
            extra = st.file_uploader(
                "PDF aggiuntivi",
                type=["pdf"],
                accept_multiple_files=True,
                key="viewer_extra_upload",
                label_visibility="collapsed",
            )
            if extra:
                names_in_store = {e["name"] for e in st.session_state.pdf_store}
                added = 0
                for f in extra:
                    if f.name not in names_in_store:
                        raw = f.read()
                        try:
                            n = page_count(raw)
                            st.session_state.pdf_store.append(
                                {"name": f.name, "bytes": raw, "n_pages": n, "current_page": 1}
                            )
                            added += 1
                        except Exception as e:
                            st.error(f"Errore {f.name}: {e}")
                if added:
                    st.rerun()
    else:
        # Nessun PDF generato ancora → upload manuale classico
        st.subheader("📂 Carica PDF A4")
        st.caption("Oppure genera i PDF dalla tab **🚀 Genera da Google Docs** per caricarli automaticamente.")
        uploaded = st.file_uploader(
            "Carica PDF",
            type=["pdf"],
            accept_multiple_files=True,
            key="viewer_manual_upload",
            label_visibility="collapsed",
        )
        if not uploaded:
            st.info("Carica almeno un file PDF, oppure genera i PDF dalla prima tab.")
            st.stop()

        current_names = {e["name"] for e in st.session_state.get("pdf_store", [])}
        for f in uploaded:
            if f.name not in current_names:
                raw = f.read()
                try:
                    n = page_count(raw)
                    st.session_state.setdefault("pdf_store", []).append(
                        {"name": f.name, "bytes": raw, "n_pages": n, "current_page": 1}
                    )
                except Exception as e:
                    st.error(f"Errore lettura {f.name}: {e}")

    store = st.session_state.get("pdf_store", [])
    if not store:
        st.stop()

    # ── Outer slider ──────────────────────────────────────────────────────────
    VISIBLE = 3
    n_pdfs  = len(store)

    if "outer_start" not in st.session_state:
        st.session_state.outer_start = 0
    outer = st.session_state.outer_start % n_pdfs  # wrap sicuro

    # Naviga di 1 in 1; wrap circolare; disabilitato se PDF <= VISIBLE
    can_nav = n_pdfs > VISIBLE
    col_prev, col_ind, col_next = st.columns([1, 4, 1])
    with col_prev:
        if st.button("◀", key="outer_prev", disabled=not can_nav):
            st.session_state.outer_start = (outer - 1) % n_pdfs
            st.rerun()
    with col_ind:
        shown = [(outer + i) % n_pdfs + 1 for i in range(min(VISIBLE, n_pdfs))]
        shown_str = ", ".join(str(s) for s in shown)
        st.markdown(
            f"<div style='text-align:center;color:#a0a0c0;font-size:13px;padding-top:6px'>"
            f"PDF {shown_str} / {n_pdfs}</div>",
            unsafe_allow_html=True,
        )
    with col_next:
        if st.button("▶", key="outer_next", disabled=not can_nav):
            st.session_state.outer_start = (outer + 1) % n_pdfs
            st.rerun()

    # ── Slot PDF visibili — sempre VISIBLE colonne, wrap circolare ────────────
    slots = [(outer + i) % n_pdfs for i in range(min(VISIBLE, n_pdfs))]
    cols  = st.columns(VISIBLE)  # sempre 3 colonne per layout uniforme

    for col, idx in zip(cols, slots):
        entry = store[idx]
        with col:
            ename = entry["name"]
            st.markdown(
                f"<div style='background:#0f3460;border-radius:6px 6px 0 0;"
                f"padding:4px 8px;font-size:11px;color:#a0c4ff;"
                f"text-align:center;overflow:hidden;text-overflow:ellipsis;"
                f"white-space:nowrap;' title='{ename}'>"
                f"{ename}</div>",
                unsafe_allow_html=True,
            )
            try:
                png = render_page(entry["bytes"], entry["current_page"] - 1, dpi=120)
                st.image(png, width="stretch")
            except Exception as e:
                st.error(f"Render error: {e}")

            p   = entry["current_page"]
            np_ = entry["n_pages"]
            fc1, fc2, fc3 = st.columns([1, 2, 1])
            with fc1:
                if st.button("◀", key=f"prev_{idx}", disabled=(p <= 1)):
                    store[idx]["current_page"] -= 1
                    st.rerun()
            with fc2:
                st.markdown(
                    f"<div style='text-align:center;font-size:11px;"
                    f"color:#a0c4ff;padding-top:6px'>{p} / {np_}</div>",
                    unsafe_allow_html=True,
                )
            with fc3:
                if st.button("▶", key=f"next_{idx}", disabled=(p >= np_)):
                    store[idx]["current_page"] += 1
                    st.rerun()

            st.download_button(
                label="⬇ PNG",
                data=render_page(entry["bytes"], entry["current_page"] - 1, dpi=150),
                file_name=f"{entry['name'].replace('.pdf', '')}_p{p}.png",
                mime="image/png",
                width="stretch",
                key=f"dl_{idx}",
            )

    # ── Esporta ───────────────────────────────────────────────────────────────
    st.divider()
    st.subheader("📦 Esporta")

    col_a, col_b = st.columns(2)

    with col_a:
        if st.button("🗜 Crea ZIP pagine PNG", width="stretch"):
            zip_buf = BytesIO()
            with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
                prog = st.progress(0, text="Rendering pagine…")
                total_pages = sum(e["n_pages"] for e in store)
                done = 0
                for entry in store:
                    base = entry["name"].replace(".pdf", "")
                    for pg in range(entry["n_pages"]):
                        png = render_page(entry["bytes"], pg, dpi=150)
                        zf.writestr(f"{base}/pagina_{pg+1:03d}.png", png)
                        done += 1
                        prog.progress(done / total_pages, text=f"Pagina {done}/{total_pages}…")
            zip_buf.seek(0)
            st.download_button(
                "⬇️ Scarica ZIP PNG",
                data=zip_buf,
                file_name="viewer_pagine.zip",
                mime="application/zip",
                width="stretch",
            )

    with col_b:
        if st.button("📄 ZIP PDF originali", width="stretch"):
            zip_buf = BytesIO()
            with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
                for entry in store:
                    zf.writestr(entry["name"], entry["bytes"])
            zip_buf.seek(0)
            st.download_button(
                "⬇️ Scarica ZIP PDF",
                data=zip_buf,
                file_name="viewer_pdf.zip",
                mime="application/zip",
                width="stretch",
            )
