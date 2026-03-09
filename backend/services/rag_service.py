"""
rag_service.py

Thin singleton wrapper around the `construction_plan_rag` package.
"""

import os
from construction_plan_rag import RAGService

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
CHROMA_DB_DIR = os.path.join(BACKEND_DIR, "chroma_db")
TERMS_JSON_PATH = os.path.join(DATA_DIR, "RSMeans_Illustrated_Construction_Dictionary", "terms.json")
DICTIONARY_BASE_DIR = os.path.join(DATA_DIR, "RSMeans_Illustrated_Construction_Dictionary")

# Initialize the RAGService singleton exported by our new package
rag_service = RAGService(
    terms_json_path=TERMS_JSON_PATH,
    dictionary_base_dir=DICTIONARY_BASE_DIR,
    chroma_db_dir=CHROMA_DB_DIR,
    data_dir=DATA_DIR
)
