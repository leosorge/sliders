# Slider PDF

Streamlit app che legge una lista di Google Docs, genera una sintesi in 5 punti con Gemini e produce due ZIP scaricabili: PDF A4 e PDF quadrati (842×842 pt).

## Setup locale

```bash
git clone https://github.com/TUO_USERNAME/slider-pdf.git
cd slider-pdf
pip install -r requirements.txt
cp .env.example .streamlit/secrets.toml
# Modifica .streamlit/secrets.toml con la tua GEMINI_API_KEY
streamlit run app.py
```

## Deploy su Streamlit Community Cloud

1. Fai fork/push di questo repo su GitHub
2. Vai su [share.streamlit.io](https://share.streamlit.io) → New app → seleziona il repo
3. In **Settings > Secrets** aggiungi:
   ```
   GEMINI_API_KEY = "la-tua-chiave"
   ```
4. Clicca Deploy

## Utilizzo

- Inserisci gli URL dei Google Docs in `articoli.txt` (uno per riga) oppure direttamente nel text area
- I documenti devono essere condivisi con "Chiunque abbia il link può visualizzare"
- Clicca **Genera PDF** e scarica i due ZIP

## Struttura

```
slider-pdf/
├── app.py                  # UI Streamlit
├── core/
│   ├── gdocs.py            # Fetch Google Docs + sintesi Gemini
│   ├── pdf_a4.py           # Generatore PDF A4
│   └── pdf_square.py       # Generatore PDF 842×842
├── articoli.txt            # Lista URL (editabile)
├── requirements.txt
└── .streamlit/
    └── secrets.toml        # Non committato
```

## Crediti

Leo Sorge @ FT-CS / CEO Source 2026
