"""
Test script for review endpoints
Tests /review/query and /review/annotate functionality
"""
import requests
import json
import base64
import os
from dotenv import load_dotenv

load_dotenv()

# Configuration
BASE_URL = "http://localhost:8001"
API_KEY = os.getenv("APP_API_KEY")
HEADERS = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}


def test_review_query():
    """Test /review/query endpoint"""
    print("\n=== Testing /review/query ===")
    
    # Sample paragraphs from discussion/conclusion
    payload = {
        "paragraphs": [
            "The building exhibits signs of differential settlement with cracks observed in the eastern wall.",
            "Foundation reinforcement is recommended to prevent further structural movement."
        ],
        "report_type": "building movement"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/review/query",
            headers=HEADERS,
            json=payload
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Success: {result['success']}")
            print(f"Message: {result['message']}")
            print(f"Results: {len(result['results'])} paragraph groups")
            
            for idx, paragraph_matches in enumerate(result['results']):
                print(f"\nParagraph {idx + 1}: {len(paragraph_matches)} matches")
                for match_idx, match in enumerate(paragraph_matches):
                    print(f"  Match {match_idx + 1}:")
                    print(f"    Report ID: {match['report_id']}")
                    print(f"    Section: {match['section']}")
                    print(f"    Relevance Score: {match['relevance_score']:.4f}")
                    print(f"    Text Preview: {match['text'][:100]}...")
            
            return True
        else:
            print(f"Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"Exception: {e}")
        return False


def test_review_annotate():
    """Test /review/annotate endpoint"""
    print("\n=== Testing /review/annotate ===")
    
    # Create a simple test PDF
    try:
        import fitz
        
        # Create a simple PDF with some text
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)  # A4 size
        
        # Add some text to the page
        text = """Discussion

The building exhibits signs of differential settlement with cracks observed 
in the eastern wall. The foundation shows evidence of soil compression 
beneath the footing area.

Conclusion

Foundation reinforcement is recommended to prevent further structural 
movement. Regular monitoring should be conducted quarterly."""
        
        page.insert_text((72, 72), text, fontsize=12)
        
        # Save to bytes
        pdf_bytes = doc.tobytes()
        doc.close()
        
        # Encode to base64
        pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
        
        # Create annotation request
        payload = {
            "pdf_base64": pdf_base64,
            "annotations": [
                {
                    "paragraph_text": "The building exhibits signs of differential settlement with cracks observed \nin the eastern wall.",
                    "spans": [[0, 30], [50, 80]],  # Highlight two sections
                    "page_hint": 1,
                    "recommendation": "Consider soil stabilization techniques as discussed in report J250123-1."
                },
                {
                    "paragraph_text": "Foundation reinforcement is recommended to prevent further structural \nmovement.",
                    "spans": [[0, 50]],
                    "page_hint": 1,
                    "recommendation": "Refer to retaining wall specifications in section 4.2."
                }
            ]
        }
        
        response = requests.post(
            f"{BASE_URL}/review/annotate",
            headers=HEADERS,
            json=payload
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Success: {result['success']}")
            print(f"Message: {result['message']}")
            print(f"Annotated Count: {result['annotated_count']}")
            print(f"Error Count: {result['error_count']}")
            
            if result['errors']:
                print("\nErrors encountered:")
                for error in result['errors']:
                    print(f"  - {error}")
            
            # Save annotated PDF
            if result.get('pdf_base64'):
                annotated_bytes = base64.b64decode(result['pdf_base64'])
                output_path = "test_annotated.pdf"
                with open(output_path, 'wb') as f:
                    f.write(annotated_bytes)
                print(f"\n✅ Annotated PDF saved to: {output_path}")
            
            return True
        else:
            print(f"Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"Exception: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_health():
    """Test health endpoint"""
    print("\n=== Testing /health ===")
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Exception: {e}")
        return False


if __name__ == "__main__":
    print("Starting Review Endpoint Tests")
    print("=" * 50)
    
    # Test health first
    health_ok = test_health()
    
    if not health_ok:
        print("\n❌ Server health check failed. Is the server running?")
        exit(1)
    
    # Test review/query
    query_ok = test_review_query()
    
    # Test review/annotate
    annotate_ok = test_review_annotate()
    
    # Summary
    print("\n" + "=" * 50)
    print("Test Summary:")
    print(f"  Health: {'✅' if health_ok else '❌'}")
    print(f"  Review Query: {'✅' if query_ok else '❌'}")
    print(f"  Review Annotate: {'✅' if annotate_ok else '❌'}")
    
    if health_ok and query_ok and annotate_ok:
        print("\n✅ All tests passed!")
    else:
        print("\n❌ Some tests failed")
