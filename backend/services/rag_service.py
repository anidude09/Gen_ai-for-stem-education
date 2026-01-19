import os
import shutil
from typing import List

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

# Constants
CHUNK_SIZE = 300
CHUNK_OVERLAP = 50
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"

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

    def get_context(self, query: str, k: int = 3) -> str:
        """
        Retrieve relevant context for a query.
        """
        if not self.vector_store:
            return ""

        print(f"[RAG] Searching for: {query}")
        results = self.vector_store.similarity_search(query, k=k)
        
        # Concatenate content
        context_parts = []
        for i, doc in enumerate(results):
            source = os.path.basename(doc.metadata.get("source", "unknown"))
            page = doc.metadata.get("page", 0)
            context_parts.append(f"--- Source: {source} (Page {page}) ---\n{doc.page_content}")
            
        return "\n\n".join(context_parts)

# Singleton instance
rag_service = RAGService()
