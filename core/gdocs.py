"""
core/gdocs.py
─────────────
Recupera testo e titolo da due sorgenti:
  • Google Docs  — export diretto in .txt via API pubblica
  • URL web      — estrazione testo con trafilatura (filtra nav/footer/ads)
Punto di ingresso unico: process_url()
"""
from __future__ import annotations
import re
import requests
# ── Gemini ────────────────────────────────────────────────────────────────────
from google import genai
from google.genai import types
# ── Prompt ────────────────────────────────────────────────────────────────────
PROMPT_TEMPLATE = """
Sei un esperto di comunicazione e sintesi. Analizza il documento seguente e crea una sintesi strutturata in 5 punti chiave.

=== TIPI DI RIGA ===
Titolo   → PRIMA RIGA della sezione, testo semplice SENZA NESSUN MARCATORE (grande, verde nel PDF)
*testo*  → riga intera in grassetto — solo nel corpo, MAI come prima riga (verde nel PDF)
_testo_  → riga intera in corsivo — descrizioni brevi (bianco nel PDF)
testo    → riga normale senza marcatori — elenchi, note (bianco nel PDF)
=        → separatore di sezione (solo = su una riga)

=== REGOLA FONDAMENTALE ===
OGNI RIGA contiene UN SOLO tipo.
VIETATO mescolare * e _ sulla stessa riga.
Il Titolo è SEMPRE la prima riga della sezione: NIENTE ASTERISCHI, NIENTE UNDERSCORE.

SBAGLIATO (non fare MAI):
*Calcolo Fotonico*          ← asterischi sul titolo: VIETATO
_e_ *Data center spaziali*  ← marcatori misti: VIETATO
*Smart* _meter_ connesso    ← marcatori misti: VIETATO

CORRETTO:
Calcolo Fotonico
_Smart meter connesso_

=== STRUTTURA OBBLIGATORIA ===
[Titolo del documento — prima parte]
[Titolo seconda parte se serve]
=
Cinque punti chiave
1. [punto 1]
2. [punto 2]
3. [punto 3]
4. [punto 4]
5. [punto 5]
=
[Titolo Punto 1]
_[descrizione riga 1]_
_[descrizione riga 2]_
*[keyword chiave]*
=
[Titolo Punto 2]
_[descrizione riga 1]_
_[descrizione riga 2]_
*[keyword chiave]*
=
[Titolo Punto 3]
_[descrizione riga 1]_
_[descrizione riga 2]_
*[keyword chiave]*
=
[Titolo Punto 4]
_[descrizione riga 1]_
_[descrizione riga 2]_
*[keyword chiave]*
=
[Titolo Punto 5]
_[descrizione riga 1]_
_[descrizione riga 2]_
*[keyword chiave]*

=== ULTERIORI REGOLE ===
- Tutto in italiano
- Ogni sezione: 3-5 righe totali
- Ogni riga: massimo {max_chars} caratteri (spazi e marcatori inclusi)
- Se una riga supera {max_chars} caratteri, spezzala in due righe consecutive dello stesso tipo
- NON aggiungere testo fuori dal formato sopra

=== DOCUMENTO DA ANALIZZARE ===
Titolo: {title}
{text}
"""
# ── Helpers comuni ────────────────────────────────────────────────────────────
def sanitize_filename(name: str) -> str:
    return re.sub(r'[\\/\*?:"<>|\n\r\t]', "", name).strip()
def _wrap_line(line: str, max_chars: int) -> list[str]:
    if len(line) <= max_chars:
        return [line]
    marker_open = marker_close = ""
    inner = line
    if line.startswith("*") and line.endswith("*") and len(line) > 2:
        marker_open, marker_close, inner = "*", "*", line[1:-1]
    elif line.startswith("_") and line.endswith("_") and len(line) > 2:
        marker_open, marker_close, inner = "_", "_", line[1:-1]
    words = inner.split(" ")
    result, current = [], ""
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
    return result or [line]
def wrap_summary(text: str, max_chars: int) -> str:
    out = []
    for line in text.splitlines():
        out.extend(_wrap_line(line, max_chars))
    return "\n".join(out)
# ── Google Docs ───────────────────────────────────────────────────────────────
def _is_gdocs(url: str) -> bool:
    return "docs.google.com/document/d/" in url
def _extract_doc_id(url: str) -> str:
    match = re.search(r"/document/d/([a-zA-Z0-9_-]+)", url)
    if not match:
        raise ValueError(f"URL Google Docs non valido: {url!r}")
    return match.group(1)
def _fetch_gdocs_text(doc_id: str) -> str:
    url = f"https://docs.google.com/document/d/{doc_id}/export?format=txt"
    resp = requests.get(url, allow_redirects=True, timeout=30)
    if resp.status_code == 403:
        raise PermissionError(
            "Accesso negato (403). Verifica che il documento sia condiviso "
            "con 'Chiunque abbia il link può visualizzare'."
        )
    resp.raise_for_status()
    return resp.text
def _fetch_gdocs_title(doc_id: str) -> str:
    try:
        resp = requests.get(
            f"https://docs.google.com/document/d/{doc_id}/pub", timeout=15
        )
        match = re.search(
            r"<title>([^<]+?)(?:\s*[-]\s*Google [^<]*)?\s*</title>",
            resp.text,
            re.IGNORECASE,
        )
        if match:
            return match.group(1).strip()
    except Exception:
        pass
    return doc_id
# ── URL web arbitrari ─────────────────────────────────────────────────────────
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "it-IT,it;q=0.9,en;q=0.8",
}
def _fetch_web(url: str) -> tuple[str, str]:
    """
    Restituisce (title, text) da un URL web generico.
    Scarica con requests (User-Agent browser) + estrae con trafilatura.
    """
    try:
        import trafilatura
    except ImportError:
        raise ImportError(
            "trafilatura non installato. Aggiungi `trafilatura` a requirements.txt."
        )
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.mount("http://",  HTTPAdapter(max_retries=retry))
    try:
        resp = session.get(url, headers=_HEADERS, timeout=15, allow_redirects=True)
    except requests.exceptions.ConnectTimeout:
        raise TimeoutError(
            f"Il sito non risponde (timeout): {url}\n"
            "Verifica che l'URL sia raggiungibile dal browser."
        )
    except requests.exceptions.ConnectionError as e:
        raise ConnectionError(f"Impossibile connettersi a {url}: {e}")
    if resp.status_code == 403:
        raise PermissionError(
            f"Accesso negato (403) a {url}. "
            "Il sito potrebbe richiedere login o bloccare i bot."
        )
    resp.raise_for_status()
    html = resp.text
    text = trafilatura.extract(
        html,
        url=url,
        include_comments=False,
        include_tables=True,
        favor_recall=True,
    )
    if not text or len(text.strip()) < 50:
        raise ValueError(
            f"Testo non estraibile da: {url}\n"
            "Il sito potrebbe essere dietro paywall o usare JS dinamico."
        )
    meta = trafilatura.extract_metadata(html, default_url=url)
    title = (meta.title if meta and meta.title else "") or url
    return title.strip(), text.strip()
# ── Prezzi Gemini (USD per 1M token, aggiornati aprile 2026) ─────────────────
GEMINI_PRICING: dict[str, dict[str, float]] = {
    "gemini-2.5-flash": {"input": 0.30,   "output": 2.50},
    "gemini-2.0-flash": {"input": 0.10,   "output": 0.40},
    "gemini-1.5-flash": {"input": 0.075,  "output": 0.30},
}
_FALLBACK_PRICE = {"input": 0.30, "output": 2.50}
def tokens_to_usd(input_tokens: int, output_tokens: int, model: str) -> float:
    """Calcola il costo in USD dato il conteggio token e il modello."""
    price = GEMINI_PRICING.get(model, _FALLBACK_PRICE)
    return (input_tokens * price["input"] + output_tokens * price["output"]) / 1_000_000
# ── Gemini summary ────────────────────────────────────────────────────────────
def generate_summary(
    text: str,
    title: str,
    api_key: str,
    model: str = "gemini-2.5-flash",
    max_chars: int = 60,
) -> tuple[str, int, int]:
    """
    Restituisce (summary, input_tokens, output_tokens).
    """
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
    # Leggi token usage dalla risposta (disponibile in google-genai >= 0.8)
    usage = getattr(response, "usage_metadata", None)
    in_tok  = getattr(usage, "prompt_token_count",     0) if usage else 0
    out_tok = getattr(usage, "candidates_token_count", 0) if usage else 0
    return wrap_summary(raw, max_chars), in_tok, out_tok
# ── Punto di ingresso pubblico ────────────────────────────────────────────────
def process_url(
    url: str,
    api_key: str,
    model: str = "gemini-2.5-flash",
    max_chars: int = 60,
) -> dict:
    """
    Accetta indifferentemente:
      - URL Google Docs  (docs.google.com/document/d/...)
      - URL web arbitrari (articoli, blog, qualsiasi pagina HTML)
    Ritorna: {
        "title": str, "filename": str, "summary": str,
        "input_tokens": int, "output_tokens": int, "cost_usd": float
    }
    """
    if _is_gdocs(url):
        doc_id = _extract_doc_id(url)
        text   = _fetch_gdocs_text(doc_id)
        if len(text.strip()) < 50:
            raise ValueError("Documento Google Docs vuoto o non accessibile.")
        title  = _fetch_gdocs_title(doc_id)
    else:
        title, text = _fetch_web(url)
    summary, in_tok, out_tok = generate_summary(text, title, api_key, model, max_chars)
    cost_usd = tokens_to_usd(in_tok, out_tok, model)
    filename = sanitize_filename(title)
    return {
        "title":         title,
        "filename":      filename,
        "summary":       summary,
        "input_tokens":  in_tok,
        "output_tokens": out_tok,
        "cost_usd":      cost_usd,
    }