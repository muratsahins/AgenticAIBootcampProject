"""
Bu dosyada projede kullanılacak LLM ve embedding modelleri ile genel ayarlar tanımlanır.
Değerler .env dosyasından değiştirilebilir (bkz. .env.example).
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_ollama import ChatOllama, OllamaEmbeddings


BASE_PATH = Path(__file__).resolve().parent

load_dotenv(BASE_PATH / ".env")

LLM_MODEL = os.getenv("CHAT_MODEL", "gemma3:4b")
EMBEDDING_MODEL = os.getenv("EMBED_MODEL", "qwen3-embedding:0.6b")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

OUTPUT_LANG = os.getenv("OUTPUT_LANG", "Türkçe")
MAX_REVISIONS = int(os.getenv("MAX_REVISIONS", "2"))
UNCERTAIN_SIMILARITY = float(os.getenv("UNCERTAIN_SIMILARITY", "0.62"))

DATA_PATH = BASE_PATH / "data"
VECTOR_PATH = BASE_PATH / "vector_db" / "cv"
MEMORY_PATH = Path(os.getenv("MEMORY_PATH", BASE_PATH / "memory" / "memory.json"))
OUTPUT_PATH = Path(os.getenv("OUTPUT_DIR", BASE_PATH / "output"))

llm = ChatOllama(
    model=LLM_MODEL,
    base_url=OLLAMA_BASE_URL,
    temperature=0.2,
    num_ctx=8192,
    num_predict=2048,
)
embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL, base_url=OLLAMA_BASE_URL)
