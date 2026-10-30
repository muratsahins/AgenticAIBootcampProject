"""
Bu dosyada CV ve ilan dokümanlarını okumak (PDF, txt, URL) ve parçalara bölmek için
kullanılan araçlar bulunur.
"""

import re
import urllib.error
import urllib.request
from html import unescape
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError


class DocumentError(RuntimeError):
    """Doküman okunamadı veya içeriği kullanılamaz."""


MIN_TEXT_LENGTH = 80


def _strip_html(html: str) -> str:
    html = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", html)
    text = re.sub(r"(?s)<[^>]+>", "\n", html)
    text = unescape(text)
    return re.sub(r"\n\s*\n+", "\n\n", text).strip()


def _fetch_url(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "cvcoach/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return _strip_html(resp.read().decode("utf-8", errors="replace"))
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        raise DocumentError(f"URL okunamadı ({url}): {exc}") from exc


def load_document(source: str) -> str:
    """PDF, txt/md dosyası veya http(s) URL'sinden düz metin okur."""
    if source.lower().startswith(("http://", "https://")):
        text = _fetch_url(source)
    else:
        path = Path(source)
        if not path.is_file():
            raise DocumentError(f"Dosya bulunamadı: {source}")
        try:
            if path.suffix.lower() == ".pdf":
                text = "\n".join(p.extract_text() or "" for p in PdfReader(path).pages)
            else:
                text = path.read_text(encoding="utf-8")
        except (PdfReadError, UnicodeDecodeError, OSError) as exc:
            raise DocumentError(f"Dosya okunamadı ({source}): {exc}") from exc
    text = text.strip()
    if len(text) < MIN_TEXT_LENGTH:
        raise DocumentError(
            f"'{source}' içinden yeterli metin çıkarılamadı (taranmış/boş PDF olabilir)."
        )
    return text


BULLET_MARKERS = ("-", "•", "*", "–")


def chunk_text(text: str, min_chars: int = 40) -> list[str]:
    """Metni madde/satır bazında parçalar; kısa satırlar (başlık vb.) bir sonrakiyle birleşir.

    PDF'te sarılmış satırlar (küçük harfle başlayan devam satırları) bir önceki maddeye eklenir.
    Küçük parçalar, anlamsal aramada tek bir beceriye ait kanıtı net yakalar.
    """
    chunks: list[str] = []
    buf = ""
    for line in (ln.strip() for ln in text.splitlines()):
        if not line:
            continue
        if chunks and not buf and line[0].islower() and chunks[-1].startswith(BULLET_MARKERS):
            chunks[-1] = f"{chunks[-1]} {line}"
            continue
        buf = f"{buf}\n{line}".strip() if buf else line
        if len(buf) >= min_chars:
            chunks.append(buf)
            buf = ""
    if buf:
        if chunks:
            chunks[-1] = f"{chunks[-1]}\n{buf}"
        else:
            chunks.append(buf)
    return chunks
