"""Extract text from uploaded documents."""
from __future__ import annotations

from pathlib import Path


def extract_text_from_file(path: Path, file_type: str) -> tuple[str, str | None]:
    """Returns (text, error)."""
    ft = (file_type or "").lower()
    try:
        if ft in ("txt", "text", "md"):
            return path.read_text(encoding="utf-8", errors="ignore")[:200000], None
        if ft == "pdf":
            try:
                from pypdf import PdfReader
            except ImportError:
                return "", "pypdf not installed — cannot parse PDF"
            reader = PdfReader(str(path))
            parts = []
            for page in reader.pages[:80]:
                parts.append(page.extract_text() or "")
            text = "\n".join(parts).strip()
            if not text:
                return "", "PDF contained no extractable text (scanned PDFs need OCR later)"
            return text[:200000], None
        if ft in ("docx", "doc"):
            try:
                import docx
            except ImportError:
                return "", "python-docx not installed — cannot parse DOCX"
            doc = docx.Document(str(path))
            text = "\n".join(p.text for p in doc.paragraphs if p.text).strip()
            if not text:
                return "", "DOCX contained no text"
            return text[:200000], None
        return "", f"Unsupported file type: {file_type}"
    except Exception as exc:
        return "", str(exc)
