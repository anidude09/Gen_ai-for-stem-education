"""
Test script to debug image path for 'accordion partition'.
"""
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.rag_service import rag_service

def test_accordion():
    term = "accordion partition"
    print(f"Testing term: '{term}'")
    
    # 1. Check if term exists in lookup
    entry = rag_service.get_term_entry(term)
    if entry:
        print("✅ Found entry in JSON")
        print(f"   Key: {term.upper()}")
        print(f"   Image field in JSON: '{entry.get('image')}'")
    else:
        print("❌ Entry NOT found in JSON")
        return

    # 2. Check get_term_image method
    image_path = rag_service.get_term_image(term)
    print(f"   get_term_image() returned: '{image_path}'")
    
    # 3. Simulate llm.py logic
    image_url = None
    if image_path:
        if image_path.startswith("images/"):
            image_url = "/dict-images/" + image_path[7:]
        else:
            image_url = "/dict-images/" + image_path
            
    print(f"   Constructed URL (simulated): '{image_url}'")
    
    # 4. Check file existence
    full_path = os.path.join(rag_service.get_term_image_absolute(term) or "NOT_FOUND")
    print(f"   Absolute path check: {full_path}")
    print(f"   Exists on disk? {os.path.exists(full_path)}")

if __name__ == "__main__":
    test_accordion()
