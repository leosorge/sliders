# Legacy wrapper — per Unidata usa pdf_A4
# Tutta la logica è ora centralizzata in gdocs.py per evitare duplicazione.
# Qualsiasi chiamata a questo modulo continua a funzionare invariata.
from gdocs import (  # noqa: F401
    PROMPT_TEMPLATE,
    extract_doc_id,
    fetch_document_text,
    fetch_document_title,
    sanitize_filename,
    _wrap_line,
    wrap_summary,
    generate_summary,
    process_url,
)
