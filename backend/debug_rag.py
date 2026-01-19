
import os
import sys

# Ensure backend can be imported
sys.path.append(os.path.join(os.path.dirname(__file__)))

from services.rag_service import rag_service

def inspect_chunks():
    print("--- Inspecting ChromaDB Chunks ---")
    if not rag_service.vector_store:
        print("Vector Store not initialized.")
        return

    
    query = "Beam"
   
    results = rag_service.vector_store.similarity_search(query, k=3)
    
    for i, doc in enumerate(results):
        print(f"\n[Result {i+1}]")
        print(f"Source: {doc.metadata.get('source')}")
        print(f"Length: {len(doc.page_content)} chars")
        print("-" * 40)
        print(doc.page_content)
        print("-" * 40)

if __name__ == "__main__":
    inspect_chunks()
