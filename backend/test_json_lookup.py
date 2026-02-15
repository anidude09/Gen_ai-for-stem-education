"""
Test script to verify JSON term lookup is working correctly.
Run from the backend directory: python test_json_lookup.py
"""

import os
import sys

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.rag_service import rag_service, TERMS_LOOKUP

def test_json_lookup():
    """Test that JSON lookup works for known terms."""
    
    print("=" * 60)
    print("Testing JSON Term Lookup")
    print("=" * 60)
    
    # Check if terms were loaded
    print(f"\n✓ Total terms loaded: {len(TERMS_LOOKUP)}")
    
    # Test some known terms
    test_terms = ["BEAM", "SOFFIT", "AGGREGATE", "ABC extinguisher", "A-block", "HVAC"]
    
    print("\n--- Testing Known Terms ---\n")
    for term in test_terms:
        context = rag_service.get_context(term)
        image = rag_service.get_term_image(term)
        
        print(f"Term: {term}")
        print(f"  Context: {context[:100]}..." if len(context) > 100 else f"  Context: {context}")
        print(f"  Image: {image if image else 'None'}")
        print()
    
    # Test a term that likely doesn't exist (should fallback to vector search)
    print("\n--- Testing Fallback to Vector Search ---\n")
    unknown_term = "XYZNONEXISTENT123"
    context = rag_service.get_context(unknown_term)
    print(f"Term: {unknown_term}")
    print(f"  Result: {'Vector search fallback' if context else 'No result (expected)'}")
    
    print("\n" + "=" * 60)
    print("Test Complete!")
    print("=" * 60)

if __name__ == "__main__":
    test_json_lookup()
