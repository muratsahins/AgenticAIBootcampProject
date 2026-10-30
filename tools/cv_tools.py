"""
Bu dosyada CV için FAISS vector database oluşturma, yükleme ve arama işlemleri bulunur.
Arama sonuçları kosinüs benzerliği olarak döndürülür (1.0 = birebir aynı anlam).
"""

import hashlib
from pathlib import Path

from langchain_community.vectorstores import FAISS
from langchain_core.embeddings import Embeddings

import config


SOURCE_HASH_FILE = "source.sha1"


def text_hash(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


class CVIndex:
    """FAISS indeksini (parça, kosinüs benzerliği) çiftleri döndüren basit bir arayüze sarar."""

    def __init__(self, vector_db: FAISS):
        self.vector_db = vector_db

    def search(self, query: str, k: int = 2) -> list[tuple[str, float]]:
        results = self.vector_db.similarity_search_with_score(query, k=k)

        # normalize_L2=True ile indeks kare L2 mesafesi döndürür: cos = 1 - d / 2
        return [(doc.page_content, 1 - float(distance) / 2) for doc, distance in results]


def create_cv_index(chunks: list[str], embedding_model: Embeddings) -> CVIndex:
    vector_db = FAISS.from_texts(chunks, embedding_model, normalize_L2=True)
    return CVIndex(vector_db)


def save_cv_index(index: CVIndex, cv_text: str, folder: Path) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    index.vector_db.save_local(str(folder))
    (folder / SOURCE_HASH_FILE).write_text(text_hash(cv_text), encoding="utf-8")


def load_cv_index(folder: Path | None = None) -> CVIndex | None:
    """Kaydedilmiş indeksi yükler; yoksa None döndürür."""
    folder = folder or config.VECTOR_PATH

    if not (folder / "index.faiss").is_file():
        return None

    vector_db = FAISS.load_local(
        str(folder),
        config.embeddings,
        allow_dangerous_deserialization=True,
        normalize_L2=True,
    )

    return CVIndex(vector_db)


def index_matches_cv(cv_text: str, folder: Path | None = None) -> bool:
    """Vector database'in, verilen CV metninden üretilip üretilmediğini kontrol eder."""
    hash_file = (folder or config.VECTOR_PATH) / SOURCE_HASH_FILE

    if not hash_file.is_file():
        return False

    return hash_file.read_text(encoding="utf-8").strip() == text_hash(cv_text)
