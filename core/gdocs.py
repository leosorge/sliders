import re
import requests
import google.generativeai as genai

PROMPT_TEMPLATE = """
Sei un esperto di comunicazione e sintesi. Analizza il documento seguente e crea una sintesi strutturata in 5 punti chiave.

=== FORMATO DI OUTPUT (seguilo ESATTAMENTE) ===

Usa questi marcatori:
- *testo*   → grassetto (titoli, keyword importanti)
- _testo_   → corsivo  (descrizioni, spiegazioni)
- =         → separatore di sezione (da solo su una riga)

STRUTTURA:

*[Prima parola/tema del titolo]*
*[Seconda parte del titolo]*
*[Eventuale terza riga del titolo]*
=

*Cinque punti*
*chiave*

1. [Etichetta breve punto 1]
2. [Etichetta breve punto 2]
3. [Etichetta breve punto 3]
4. [Etichetta breve punto 4]
5. [Etichetta breve punto 5]
=

*[Titolo Punto 1]*

_[Prima riga di descrizione]_
_[Seconda riga]_
*[keyword o concetto centrale]*
_[eventuale terza riga]_
=

*[Titolo Punto 2]*

_[Descrizione riga 1]_
_[Descrizione riga 2]_
*[concetto chiave]*
=

*[Titolo Punto 3]*

_[Descrizione riga 1]_
*[keyword]_
_[Descrizione riga 2]_
_[Descrizione riga 3]_
=

*[Titolo Punto 4]*

_[Descrizione riga 1]_
_[Descrizione riga 2]_
*[keyword/concetto]*
=

*[Titolo Punto 5]*

_[Descrizione riga 1]_
_[Descrizione riga 2]_
*[keyword/concetto]*
_[Descrizione riga 3]_

=== REGOLE ===
- Scrivi TUTTO in italiano
- Ogni sezione punto: 3-5 righe totali
- Le parole più importanti DEVONO essere in *grassetto*
- Le descrizioni narrative in _corsivo_
- NON aggiungere testo extra fuori dal formato
- Il titolo (prima sezione) deve riflettere il tema centrale del documento

=== DOCUMENTO DA ANALIZZARE ===
Titolo: {title}

{text}
"""


def extract_doc_id(url: str) -> str:
    match = re.search(r'/document/d/([a-zA-Z0-9_-]+)', url)
    if not match:
        raise ValueError(f"URL non valido: {url!r}")
    return match.group(1)


def fetch_document_text(doc_id: str) -> str:
    url = f"https://docs.google.com/document/d/{doc_id}/export?format=txt"
    resp = requests.get(url, allow_redirects=True, timeout=30)
    if resp.status_code == 403:
        raise PermissionError(
            "Accesso negato (403). Verifica che il documento sia condiviso "
            "con 'Chiunque abbia il link può visualizzare'."
        )
    resp.raise_for_status()
    return resp.text


def fetch_document_title(doc_id: str) -> str:
    try:
        resp = requests.get(
            f"https://docs.google.com/document/d/{doc_id}/pub", timeout=15
        )
        match = re.search(
            r'<title>([^<]+?)(?:\s*[–\-]\s*Google [^<]*)?</title>',
            resp.text,
            re.IGNORECASE,
        )
        if match:
            return match.group(1).strip()
    except Exception:
        pass
    return doc_id


def sanitize_filename(name: str) -> str:
    return re.sub(r'[\\/*?:"<>|\n\r\t]', "", name).strip()


def generate_summary(text: str, title: str, api_key: str, model: str = "gemini-2.5-flash") -> str:
    genai.configure(api_key=api_key)
    gemini_model = genai.GenerativeModel(model)
    prompt = PROMPT_TEMPLATE.format(title=title, text=text[:50000])
    response = gemini_model.generate_content(
        prompt,
        generation_config=genai.GenerationConfig(temperature=0.3, max_output_tokens=2048),
    )
    return response.text.strip()


def process_url(url: str, api_key: str, model: str = "gemini-2.5-flash") -> dict:
    """Fetches a Google Doc URL and returns a dict with title and summary text."""
    doc_id = extract_doc_id(url)
    text = fetch_document_text(doc_id)
    if len(text) < 50:
        raise ValueError("Documento vuoto o non accessibile.")
    title = fetch_document_title(doc_id)
    summary = generate_summary(text, title, api_key, model)
    filename = sanitize_filename(title)
    return {"title": title, "filename": filename, "summary": summary}
