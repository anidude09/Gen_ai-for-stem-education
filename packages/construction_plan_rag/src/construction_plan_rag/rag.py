"""
rag.py

Core logic for Retrieval-Augmented Generation (RAG).
Handles exact matches against a JSON dictionary, with a fallback to ChromaDB vector search.
"""

import os
import json
from typing import Dict, Any, Optional

from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings


class RAGService:
    def __init__(
        self,
        terms_json_path: str,
        dictionary_base_dir: str,
        chroma_db_dir: str,
        data_dir: str,
        embedding_model_name: str = "all-MiniLM-L6-v2",
        chunk_size: int = 300,
        chunk_overlap: int = 50
    ):
        self.terms_json_path = terms_json_path
        self.dictionary_base_dir = dictionary_base_dir
        self.chroma_db_dir = chroma_db_dir
        self.data_dir = data_dir
        self.embedding_model_name = embedding_model_name
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        self._embedding_function = None
        self._vector_store = None
        self._initialized = False

        self._vector_cache: Dict[str, str] = {}
        self._VECTOR_CACHE_MAX = 256
        
        self.terms_lookup = self._load_terms_lookup()

    def _load_terms_lookup(self) -> Dict[str, Dict[str, Any]]:
        """Load terms.json into a lookup dictionary."""
        lookup = {}
        if os.path.exists(self.terms_json_path):
            try:
                with open(self.terms_json_path, 'r', encoding='utf-8') as f:
                    terms_data = json.load(f)
                    for entry in terms_data:
                        term_key = entry.get("term", "").strip().upper()
                        if term_key:
                            lookup[term_key] = entry
                print(f"[construction_plan_rag] Loaded {len(lookup)} terms from JSON dictionary")
            except Exception as e:
                print(f"[construction_plan_rag] Warning: Could not load terms.json: {e}")
        else:
            print(f"[construction_plan_rag] Warning: Terms JSON not found at {self.terms_json_path}")
        return lookup

    @property
    def embedding_function(self):
        if self._embedding_function is None:
            print("[construction_plan_rag] Loading HuggingFace embeddings (first use)…")
            self._embedding_function = HuggingFaceEmbeddings(model_name=self.embedding_model_name)
        return self._embedding_function

    @property
    def vector_store(self):
        if not self._initialized:
            self._initialized = True
            self._initialize_vector_store()
        return self._vector_store

    @vector_store.setter
    def vector_store(self, value):
        self._vector_store = value

    def _initialize_vector_store(self):
        if os.path.exists(self.chroma_db_dir) and os.listdir(self.chroma_db_dir):
            print(f"[construction_plan_rag] Loading existing Vector DB from {self.chroma_db_dir}")
            self._vector_store = Chroma(
                persist_directory=self.chroma_db_dir,
                embedding_function=self.embedding_function
            )
        else:
            print(f"[construction_plan_rag] No existing DB found. Starting ingestion from {self.data_dir}...")
            self.ingest_data()

    def ingest_data(self):
        """Load PDFs, split them, and store in ChromaDB."""
        if not os.path.exists(self.data_dir):
            print(f"[construction_plan_rag] Warning: Data directory {self.data_dir} not found.")
            return

        loader = PyPDFDirectoryLoader(self.data_dir)
        documents = loader.load()
        print(f"[construction_plan_rag] Loaded {len(documents)} pages from PDFs.")

        if not documents:
            print("[construction_plan_rag] No documents found to ingest.")
            return

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap
        )
        chunks = text_splitter.split_documents(documents)
        print(f"[construction_plan_rag] Split into {len(chunks)} chunks.")

        self.vector_store = Chroma.from_documents(
            documents=chunks,
            embedding=self.embedding_function,
            persist_directory=self.chroma_db_dir
        )
        self.vector_store.persist()
        print(f"[construction_plan_rag] Ingestion complete. Saved to {self.chroma_db_dir}")

    def get_context(self, query: str, k: int = 3) -> str:
        """
        Retrieve relevant context for a query.
        First tries exact match in JSON dictionary, then falls back to vector search.
        Results are cached in memory.
        """
        term_upper = query.strip().upper()

        # 1. Exact JSON match
        if term_upper in self.terms_lookup:
            entry = self.terms_lookup[term_upper]
            page = entry.get("page", "N/A")
            definition = entry.get("definition", "")
            print(f"[construction_plan_rag] JSON match for: {query} (Page {page})")
            return f"--- Source: RSMeans Dictionary (Page {page}) ---\n{definition}"

        # 2. Vector-search cache
        cache_key = f"{term_upper}|k={k}"
        if cache_key in self._vector_cache:
            print(f"[construction_plan_rag] Vector cache hit for: {query}")
            return self._vector_cache[cache_key]

        # 3. Vector search fallback
        if not self.vector_store:
            print(f"[construction_plan_rag] No vector store and no JSON match for: {query}")
            return ""

        print(f"[construction_plan_rag] Fallback to vector search for: {query}")
        results = self.vector_store.similarity_search(query, k=k)

        context_parts = []
        for doc in results:
            source = os.path.basename(doc.metadata.get("source", "unknown"))
            page = doc.metadata.get("page", 0)
            context_parts.append(f"--- Source: {source} (Page {page}) ---\n{doc.page_content}")

        context = "\n\n".join(context_parts)

        if len(self._vector_cache) >= self._VECTOR_CACHE_MAX:
            oldest_key = next(iter(self._vector_cache))
            del self._vector_cache[oldest_key]
        self._vector_cache[cache_key] = context

        return context

    def get_term_entry(self, query: str) -> Optional[Dict[str, Any]]:
        term_upper = query.strip().upper()
        return self.terms_lookup.get(term_upper)

    def get_term_image(self, query: str) -> Optional[str]:
        entry = self.get_term_entry(query)
        if entry and entry.get("image"):
            path = entry.get("image")
            print(f"[construction_plan_rag] Found image for '{query}': {path}")
            return path
        print(f"[construction_plan_rag] No image found for '{query}'")
        return None

    def get_term_image_absolute(self, query: str) -> Optional[str]:
        relative_path = self.get_term_image(query)
        if relative_path:
            absolute_path = os.path.join(self.dictionary_base_dir, relative_path)
            if os.path.exists(absolute_path):
                return absolute_path
        return None
