"""
viewer.py
─────────
App Streamlit standalone: solo il Viewer PDF A4.
Pensata per essere incorporata via iframe in siti esterni.

Deploy su Streamlit Cloud:
  - Stesso repo di app.py
  - Entry point: viewer.py
  - URL risultante: https://<nome>.streamlit.app/?embed=true
"""

import zipfile
from io import BytesIO

import streamlit as st

# ── Pagina ────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FT-CS Viewer",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Nascondi header/footer Streamlit quando in embed
st.markdown("""
<style>
  #MainMenu, footer, header { visibility: hidden; }
  .block-container { padding-top: 1rem; padding-bottom: 0.5rem; }
</style>
""", unsafe_allow_html=True)

# ── Import backend ────────────────────────────────────────────────────────────
try:
    from core.pdf_viewer import backend_available, page_count, render_page
    _viewer_ok = backend_available()
except ImportError:
    _viewer_ok = False

if not _viewer_ok:
    st.warning("**PyMuPDF non trovato.** Aggiungi `pymupdf` a `requirements.txt`.")
    st.stop()

# ── Upload PDF ────────────────────────────────────────────────────────────────
uploaded = st.file_uploader(
    "📂 Carica PDF A4",
    type=["pdf"],
    accept_multiple_files=True,
    label_visibility="visible",
)

# Popola store
if uploaded:
    current_names = {e["name"] for e in st.session_state.get("viewer_store", [])}
    for f in uploaded:
        if f.name not in current_names:
            raw = f.read()
            try:
                n = page_count(raw)
                st.session_state.setdefault("viewer_store", []).append(
                    {"name": f.name, "bytes": raw, "n_pages": n, "current_page": 1}
                )
            except Exception as e:
                st.error(f"Errore lettura {f.name}: {e}")
else:
    # Reset store se l'utente rimuove tutti i file
    st.session_state["viewer_store"] = []

store = st.session_state.get("viewer_store", [])

if not store:
    st.info("Carica uno o più PDF A4 per visualizzarli.")
    st.stop()

# ── Outer slider ──────────────────────────────────────────────────────────────
VISIBLE = 3
n_pdfs  = len(store)

if "v_outer" not in st.session_state:
    st.session_state.v_outer = 0
outer = st.session_state.v_outer % n_pdfs

can_nav = n_pdfs > VISIBLE
col_prev, col_ind, col_next = st.columns([1, 4, 1])
with col_prev:
    if st.button("◀", key="v_outer_prev", disabled=not can_nav):
        st.session_state.v_outer = (outer - 1) % n_pdfs
        st.rerun()
with col_ind:
    shown = [(outer + i) % n_pdfs + 1 for i in range(min(VISIBLE, n_pdfs))]
    shown_str = ", ".join(str(s) for s in shown)
    st.markdown(
        f"<div style='text-align:center;color:#888;font-size:12px;padding-top:4px'>"
        f"PDF {shown_str} / {n_pdfs}</div>",
        unsafe_allow_html=True,
    )
with col_next:
    if st.button("▶", key="v_outer_next", disabled=not can_nav):
        st.session_state.v_outer = (outer + 1) % n_pdfs
        st.rerun()

# ── Slot ──────────────────────────────────────────────────────────────────────
slots = [(outer + i) % n_pdfs for i in range(min(VISIBLE, n_pdfs))]
cols  = st.columns(VISIBLE)

for col, idx in zip(cols, slots):
    entry = store[idx]
    with col:
        ename = entry["name"]
        st.markdown(
            f"<div style='background:#0f3460;border-radius:6px 6px 0 0;"
            f"padding:4px 8px;font-size:11px;color:#a0c4ff;"
            f"text-align:center;overflow:hidden;text-overflow:ellipsis;"
            f"white-space:nowrap;' title='{ename}'>{ename}</div>",
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
            if st.button("◀", key=f"v_prev_{idx}", disabled=(p <= 1)):
                store[idx]["current_page"] -= 1
                st.rerun()
        with fc2:
            st.markdown(
                f"<div style='text-align:center;font-size:11px;"
                f"color:#a0c4ff;padding-top:6px'>{p} / {np_}</div>",
                unsafe_allow_html=True,
            )
        with fc3:
            if st.button("▶", key=f"v_next_{idx}", disabled=(p >= np_)):
                store[idx]["current_page"] += 1
                st.rerun()

        st.download_button(
            label="⬇ PNG",
            data=render_page(entry["bytes"], entry["current_page"] - 1, dpi=150),
            file_name=f"{ename.replace('.pdf', '')}_p{p}.png",
            mime="image/png",
            width="stretch",
            key=f"v_dl_{idx}",
        )

# ── Esporta ───────────────────────────────────────────────────────────────────
st.divider()
col_a, col_b = st.columns(2)

with col_a:
    if st.button("🗜 ZIP pagine PNG", width="stretch"):
        zip_buf = BytesIO()
        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
            prog = st.progress(0, text="Rendering…")
            total = sum(e["n_pages"] for e in store)
            done  = 0
            for entry in store:
                base = entry["name"].replace(".pdf", "")
                for pg in range(entry["n_pages"]):
                    zf.writestr(
                        f"{base}/pagina_{pg+1:03d}.png",
                        render_page(entry["bytes"], pg, dpi=150)
                    )
                    done += 1
                    prog.progress(done / total, text=f"{done}/{total}")
        zip_buf.seek(0)
        st.download_button("⬇️ Scarica ZIP PNG", data=zip_buf,
                           file_name="viewer_pagine.zip", mime="application/zip",
                           width="stretch")

with col_b:
    if st.button("📄 ZIP PDF", width="stretch"):
        zip_buf = BytesIO()
        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for entry in store:
                zf.writestr(entry["name"], entry["bytes"])
        zip_buf.seek(0)
        st.download_button("⬇️ Scarica ZIP PDF", data=zip_buf,
                           file_name="viewer_pdf.zip", mime="application/zip",
                           width="stretch")
