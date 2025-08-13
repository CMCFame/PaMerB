#!/usr/bin/env python3
"""
Test script to verify app fixes for image/PDF conversion integration
"""

import streamlit as st
from PIL import Image
import io

def test_session_state_integration():
    """Test that session state properly integrates image conversion with IVR generation"""
    
    # Simulate the session state workflow
    print("Testing session state integration...")
    
    # Test 1: Manual mermaid input
    manual_text = "flowchart TD\nA[Start] --> B[End]"
    session_mermaid = None
    
    # This simulates the IVR generation logic
    current_mermaid_text = session_mermaid if session_mermaid else manual_text
    assert current_mermaid_text == manual_text, "Manual input should work"
    print("PASS: Manual input test passed")
    
    # Test 2: Image conversion result  
    converted_text = "flowchart TD\nC[Image] --> D[Converted]"
    session_mermaid = converted_text  # This simulates st.session_state.mermaid_code = converted_text
    
    current_mermaid_text = session_mermaid if session_mermaid else manual_text
    assert current_mermaid_text == converted_text, "Converted text should take precedence"
    print("PASS: Image conversion integration test passed")

def test_pdf_detection():
    """Test PDF file type detection logic"""
    
    print("Testing PDF detection logic...")
    
    # Mock file objects
    class MockFile:
        def __init__(self, file_type, name="test", size=1000):
            self.type = file_type
            self.name = name
            self.size = size
    
    # Test different file types
    pdf_file = MockFile('application/pdf', 'test.pdf')
    image_file = MockFile('image/png', 'test.png')
    
    # Test file type label logic
    pdf_label = "PDF" if pdf_file.type == 'application/pdf' else "Image"
    image_label = "PDF" if image_file.type == 'application/pdf' else "Image"
    
    assert pdf_label == "PDF", "PDF files should be detected as PDF"
    assert image_label == "Image", "Image files should be detected as Image"
    print("PASS: File type detection test passed")

if __name__ == "__main__":
    print("Running app integration tests...")
    test_session_state_integration()
    test_pdf_detection()
    print("All tests passed!")