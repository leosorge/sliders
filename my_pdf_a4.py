# Mia prima versione - per Unidata usa pdf_A4


import re
import requests
from google import genai
from google.genai import types

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
=

*Cinque punti chiave*

1. [Etichetta breve punto 1]
2. [Etichetta breve punto 2]
3. [Etichetta breve punto 3]
4. [Etichetta breve punto 4]
5. [Etichetta breve punto 5]
=

*[Titolo Punto 1]*

_[Prima riga]_
_[Seconda riga]_
*[keyword]*
=

*[Titolo Punto 2]*

_[Descrizione riga 1]_
_[Descrizione riga 2]_
*[concetto chiave]*
=

*[Titolo Punto 3]*

_[Descrizione riga 1]_
*[keyword]*
_[Descrizione riga 2]_
=

*[Titolo Punto 4]*

_[Descrizione riga 1]_
_[Descrizione riga 2]_
*[keyword]*
=

*[Titolo Punto 5]*

_[Descrizione riga 1]_
_[Descrizione riga 2]_
*[keyword]*
_[Descrizione riga 3]_

=== REGOLE ===
- Scrivi TUTTO in italiano
- Ogni sezione punto: 3-5 righe totali
- Le parole più importanti in *grassetto*, descrizioni in _corsivo_
- NON aggiungere testo fuori dal formato
- CRITICO: ogni riga DEVE essere al massimo {max_chars} caratteri inclusi spazi e marcatori.
  Se una frase e' piu' lunga, spezzala su due righe consecutive prima di raggiungere il limite.

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
            "con 'Chiunque abbia il link puo visualizzare'."
        )
    resp.raise_for_status()
    return resp.text


def fetch_document_title(doc_id: str) -> str:
    try:
        resp = requests.get(
            f"https://docs.google.com/document/d/{doc_id}/pub", timeout=15
        )
        match = re.search(
            r'<title>([^<]+?)(?:\s*[-]\s*Google [^<]*)?</title>',
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


def _wrap_line(line: str, max_chars: int) -> list[str]:
    """Splits a line exceeding max_chars at word boundaries, preserving leading markers."""
    if len(line) <= max_chars:
        return [line]

    # Detect leading marker (* or _) to reapply on continuation lines
    marker_open = ""
    marker_close = ""
    inner = line
    if line.startswith("*") and line.endswith("*") and len(line) > 2:
        marker_open, marker_close, inner = "*", "*", line[1:-1]
    elif line.startswith("_") and line.endswith("_") and len(line) > 2:
        marker_open, marker_close, inner = "_", "_", line[1:-1]

    words = inner.split(" ")
    result = []
    current = ""
    for word in words:
        candidate = (current + " " + word).strip()
        full = f"{marker_open}{candidate}{marker_close}"
        if len(full) <= max_chars:
            current = candidate
        else:
            if current:
                result.append(f"{marker_open}{current}{marker_close}")
            current = word
    if current:
        result.append(f"{marker_open}{current}{marker_close}")
    return result if result else [line]


def wrap_summary(text: str, max_chars: int) -> str:
    """Post-processes summary to enforce max_chars per line."""
    out = []
    for line in text.splitlines():
        out.extend(_wrap_line(line, max_chars))
    return "\n".join(out)


def generate_summary(
    text: str,
    title: str,
    api_key: str,
    model: str = "gemini-2.5-flash",
    max_chars: int = 60,
) -> str:
    client = genai.Client(api_key=api_key)
    prompt = PROMPT_TEMPLATE.format(
        title=title,
        text=text[:50000],
        max_chars=max_chars,
    )
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.3,
            max_output_tokens=2048,
        ),
    )
    raw = response.text.strip()
    # Enforce client-side wrap as safety net
    return wrap_summary(raw, max_chars)


def process_url(
    url: str,
    api_key: str,
    model: str = "gemini-2.5-flash",
    max_chars: int = 60,
) -> dict:
    doc_id = extract_doc_id(url)
    text = fetch_document_text(doc_id)
    if len(text) < 50:
        raise ValueError("Documento vuoto o non accessibile.")
    title = fetch_document_title(doc_id)
    summary = generate_summary(text, title, api_key, model, max_chars)
    filename = sanitize_filename(title)
    return {"title": title, "filename": filename, "summary": summary}
