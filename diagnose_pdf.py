"""
Diagnostic tool to test PDF base64 encoding/decoding
Helps debug issues with PDF uploads from Custom GPT
"""
import base64
import fitz
import sys

def test_pdf_base64(base64_string):
    """Test if a base64 string can be decoded and opened as a PDF"""
    print(f"Base64 string length: {len(base64_string)}")
    print(f"First 50 chars: {base64_string[:50]}")
    print(f"Last 50 chars: {base64_string[-50:]}")
    
    # Test decoding
    try:
        pdf_bytes = base64.b64decode(base64_string)
        print(f"✅ Base64 decoded successfully")
        print(f"Decoded bytes length: {len(pdf_bytes)}")
        print(f"First 10 bytes: {pdf_bytes[:10]}")
    except Exception as e:
        print(f"❌ Failed to decode base64: {e}")
        return False
    
    # Test opening as PDF
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        print(f"✅ PDF opened successfully")
        print(f"Page count: {doc.page_count}")
        
        # Try to extract text from first page
        if doc.page_count > 0:
            page = doc[0]
            text = page.get_text()
            print(f"First page text length: {len(text)}")
            print(f"First 200 chars: {text[:200]}")
        
        doc.close()
        return True
    except Exception as e:
        print(f"❌ Failed to open PDF: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Test from file
        with open(sys.argv[1], 'r') as f:
            base64_string = f.read().strip()
    else:
        # Test with a simple PDF
        print("Creating test PDF...")
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)
        page.insert_text((72, 72), "This is a test PDF.", fontsize=12)
        pdf_bytes = doc.tobytes()
        doc.close()
        base64_string = base64.b64encode(pdf_bytes).decode('utf-8')
        print(f"✅ Test PDF created and encoded")
    
    print("\n" + "=" * 50)
    print("Testing PDF Base64")
    print("=" * 50 + "\n")
    
    result = test_pdf_base64(base64_string)
    
    if result:
        print("\n✅ PDF is valid and can be processed")
    else:
        print("\n❌ PDF has issues and cannot be processed")
