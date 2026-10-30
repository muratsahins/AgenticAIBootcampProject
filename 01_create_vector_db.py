"""
Bu dosya verilen CV dosyasını (PDF, txt veya md) okur, madde/satır bazında parçalara böler,
Qwen3 Embedding modeli ile embedding oluşturur ve FAISS vector database oluşturur.

Kullanım:
    python 01_create_vector_db.py --cv data/sample_cv.pdf
"""

import argparse

import config
from tools.cv_tools import create_cv_index, save_cv_index
from tools.document_tools import DocumentError, chunk_text, load_document


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="CV için FAISS vector database oluşturur.")
    parser.add_argument(
        "--cv",
        default=str(config.DATA_PATH / "sample_cv.pdf"),
        help="CV dosyası (.pdf/.txt/.md)",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    try:
        cv_text = load_document(args.cv)
    except DocumentError as error:
        raise SystemExit(f"[HATA] {error}")

    chunks = chunk_text(cv_text)
    index = create_cv_index(chunks, config.embeddings)
    save_cv_index(index, cv_text, config.VECTOR_PATH)

    print(f"[OK] {len(chunks)} parça indekslendi: {config.VECTOR_PATH}")


if __name__ == "__main__":
    main()
