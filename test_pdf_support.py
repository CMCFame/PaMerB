#!/usr/bin/env python3
"""
Test script to verify PDF processing support
"""

def test_pymupdf_import():
    """Test that PyMuPDF can be imported"""
    try:
        import fitz  # PyMuPDF
        print("PASS: PyMuPDF imported successfully")
        print(f"PyMuPDF version: {fitz.version}")
        return True
    except ImportError as e:
        print(f"FAIL: PyMuPDF import failed: {e}")
        return False

def test_pdf_basic_functionality():
    """Test basic PDF functionality without actual PDF files"""
    try:
        import fitz
        import io
        
        # Test that we can create a PDF document in memory
        doc = fitz.open()  # Create empty PDF
        page = doc.new_page()  # Add a page
        page.insert_text((50, 50), "Test PDF")  # Add some text
        
        # Convert to bytes
        pdf_bytes = doc.tobytes()
        doc.close()
        
        # Test that we can reopen it
        doc2 = fitz.open(stream=pdf_bytes, filetype="pdf")
        print(f"PASS: PDF has {len(doc2)} pages")
        doc2.close()
        
        return True
    except Exception as e:
        print(f"FAIL: PDF functionality test failed: {e}")
        return False

if __name__ == "__main__":
    print("Testing PDF processing support...")
    
    success = True
    success &= test_pymupdf_import()
    success &= test_pdf_basic_functionality()
    
    if success:
        print("All PDF tests passed!")
    else:
        print("Some PDF tests failed!")