import os
import shutil
import json
import functools
from typing import List, Optional, Dict, Any

from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

# Paths
# This script is in backend/services/
# Data is in data/ (sibling to backend/)
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
CHROMA_DB_DIR = os.path.join(BACKEND_DIR, "chroma_db")

# Noah's extracted terms JSON
TERMS_JSON_PATH = os.path.join(DATA_DIR, "RSMeans_Illustrated_Construction_Dictionary/terms.json")
DICTIONARY_BASE_DIR = os.path.join(DATA_DIR, "RSMeans_Illustrated_Construction_Dictionary")

# Constants
CHUNK_SIZE = 300
CHUNK_OVERLAP = 50
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"


def load_terms_lookup() -> Dict[str, Dict[str, Any]]:
    """
    Load terms.json into a lookup dictionary.
    Keys are uppercase terms for case-insensitive matching.
    """
    terms_lookup = {}
    if os.path.exists(TERMS_JSON_PATH):
        try:
            with open(TERMS_JSON_PATH, 'r', encoding='utf-8') as f:
                terms_data = json.load(f)
                for entry in terms_data:
                    term_key = entry.get("term", "").strip().upper()
                    if term_key:
                        # Store with uppercase key for case-insensitive lookup
                        terms_lookup[term_key] = entry
            print(f"[RAG] Loaded {len(terms_lookup)} terms from JSON dictionary")
        except Exception as e:
            print(f"[RAG] Warning: Could not load terms.json: {e}")
    else:
        print(f"[RAG] Warning: Terms JSON not found at {TERMS_JSON_PATH}")
    return terms_lookup


# Load terms at module import time (singleton pattern)
TERMS_LOOKUP = load_terms_lookup()


class RAGService:
    def __init__(self):
        self.embedding_function = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)
        self.vector_store = None
        self._initialize_vector_store()

    def _initialize_vector_store(self):
        """
        Initialize the vector store. If it doesn't exist, ingest data.
        """
        if os.path.exists(CHROMA_DB_DIR) and os.listdir(CHROMA_DB_DIR):
            print(f"[RAG] Loading existing Vector DB from {CHROMA_DB_DIR}")
            self.vector_store = Chroma(
                persist_directory=CHROMA_DB_DIR,
                embedding_function=self.embedding_function
            )
        else:
            print(f"[RAG] No existing DB found. Starting ingestion from {DATA_DIR}...")
            self.ingest_data()

    def ingest_data(self):
        """
        Load PDFs, split them, and store in ChromaDB.
        """
        if not os.path.exists(DATA_DIR):
            print(f"[RAG] Warning: Data directory {DATA_DIR} not found.")
            return

        # 1. Load Documents
        loader = PyPDFDirectoryLoader(DATA_DIR)
        documents = loader.load()
        print(f"[RAG] Loaded {len(documents)} pages from PDFs.")

        if not documents:
            print("[RAG] No documents found to ingest.")
            return

        # 2. Split Text
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP
        )
        chunks = text_splitter.split_documents(documents)
        print(f"[RAG] Split into {len(chunks)} chunks.")

        # 3. Store in Chroma
        # Using a persistent client
        self.vector_store = Chroma.from_documents(
            documents=chunks,
            embedding=self.embedding_function,
            persist_directory=CHROMA_DB_DIR
        )
        self.vector_store.persist()
        print(f"[RAG] Ingestion complete. Saved to {CHROMA_DB_DIR}")

    # ── Performance: in-memory cache for vector-search results ────────────────
    # Exact-match hits are O(1) dict lookups and very fast already; we cache
    # vector-search results (which require embedding + ChromaDB round-trip) in a
    # simple bounded dict.  Max 256 entries; oldest entry evicted when full.
    _VECTOR_CACHE_MAX = 256
    _vector_cache: Dict[str, str] = {}

    def get_context(self, query: str, k: int = 3) -> str:
        """
        Retrieve relevant context for a query.
        First tries exact match in JSON dictionary, then falls back to vector search.
        Results are cached in memory to avoid repeated embedding/DB calls.
        """
        term_upper = query.strip().upper()

        # 1. Try exact JSON match first (fast O(1) lookup)
        if term_upper in TERMS_LOOKUP:
            entry = TERMS_LOOKUP[term_upper]
            page = entry.get("page", "N/A")
            definition = entry.get("definition", "")
            print(f"[RAG] JSON match for: {query} (Page {page})")
            return f"--- Source: RSMeans Dictionary (Page {page}) ---\n{definition}"

        # 2. Check vector-search cache
        cache_key = f"{term_upper}|k={k}"
        if cache_key in self._vector_cache:
            print(f"[RAG] Vector cache hit for: {query}")
            return self._vector_cache[cache_key]

        # 3. Fallback to vector search
        if not self.vector_store:
            print(f"[RAG] No vector store and no JSON match for: {query}")
            return ""

        print(f"[RAG] Fallback to vector search for: {query}")
        results = self.vector_store.similarity_search(query, k=k)

        context_parts = []
        for doc in results:
            source = os.path.basename(doc.metadata.get("source", "unknown"))
            page = doc.metadata.get("page", 0)
            context_parts.append(f"--- Source: {source} (Page {page}) ---\n{doc.page_content}")

        context = "\n\n".join(context_parts)

        # Store in cache; evict oldest entry if full
        if len(self._vector_cache) >= self._VECTOR_CACHE_MAX:
            oldest_key = next(iter(self._vector_cache))
            del self._vector_cache[oldest_key]
        self._vector_cache[cache_key] = context

        return context

    def get_term_entry(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Get the full term entry from JSON dictionary if it exists.
        Returns None if not found.
        """
        term_upper = query.strip().upper()
        return TERMS_LOOKUP.get(term_upper)

    def get_term_image(self, query: str) -> Optional[str]:
        """
        Get the image path for a term if it exists.
        Returns the relative path from the dictionary folder, or None if no image.
        """
        entry = self.get_term_entry(query)
        if entry and entry.get("image"):
            path = entry.get("image")
            print(f"[RAG] Found image for '{query}': {path}")
            return path
        print(f"[RAG] No image found for '{query}'")
        return None

    def get_term_image_absolute(self, query: str) -> Optional[str]:
        """
        Get the absolute image path for a term if it exists.
        Returns None if no image.
        """
        relative_path = self.get_term_image(query)
        if relative_path:
            absolute_path = os.path.join(DICTIONARY_BASE_DIR, relative_path)
            if os.path.exists(absolute_path):
                return absolute_path
        return None


# Singleton instance
rag_service = RAGService()

