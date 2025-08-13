"""
Test script to fix the specific Mermaid syntax issues
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from enhanced_pdf_processor_v2 import IntelligentPDFProcessor

def test_mermaid_syntax_fix():
    """Test the Mermaid syntax cleaning with the problematic code"""
    
    # Create a mock processor instance
    class MockProcessor:
        def _clean_mermaid_syntax(self, mermaid_code):
            processor = IntelligentPDFProcessor.__new__(IntelligentPDFProcessor)
            return processor._clean_mermaid_syntax(mermaid_code)
    
    mock_processor = MockProcessor()
    
    # The problematic Mermaid code from the user
    problematic_mermaid = '''flowchart TD
    A["Welcome<br/>You have reached the [REU"] Callout System.] --> B["Enter Employee ID<br/>Please enter your X-digit employee ID<br/>followed by the pound key."]
    B -->|"invalid input<br/>or no input"| C["Invalid Entry<br/>Invalid entry.<br/>Please try again."]
    C -->|"retry<br/>logic"| B
    F -->|"no"| G["Invalid Number<br/>The employee ID or<br/>PIN is not valid.<br/>Please try again."]
    F -->|"yes"| H["Employee Information<br/>The following information is for (employee).<br/>You have [no"] pending callout requests.<br/>Your current availability status is (status).<br/>Your temporary contact numbers are [not] active.]'''
    
    print("Testing Mermaid Syntax Fix")
    print("=" * 50)
    print("ORIGINAL (with issues):")
    print(problematic_mermaid)
    print("\nCLEANED:")
    
    try:
        cleaned = mock_processor._clean_mermaid_syntax(problematic_mermaid)
        print(cleaned)
        
        # Check if the problematic patterns are fixed
        issues_found = []
        if '[REU"]' in cleaned:
            issues_found.append("Unmatched brackets in REU still present")
        if '[no"]' in cleaned:
            issues_found.append("Unmatched brackets in 'no' still present")
        if '"] ' in cleaned:
            issues_found.append("Broken quote-bracket pattern still present")
        
        if issues_found:
            print("\nISSUES STILL PRESENT:")
            for issue in issues_found:
                print(f"  - {issue}")
        else:
            print("\nSUCCESS: All syntax issues appear to be fixed!")
        
        # Test line by line to identify specific fixes
        lines = cleaned.split('\n')
        print(f"\nLINE-BY-LINE ANALYSIS ({len(lines)} lines):")
        for i, line in enumerate(lines, 1):
            line = line.strip()
            if line and not line.startswith('flowchart'):
                # Check for properly quoted complex content
                if '"' in line and ('[' in line or '(' in line or '<br/>' in line):
                    print(f"  Line {i}: PROPERLY QUOTED - {line[:60]}...")
                elif line.startswith('A') or line.startswith('B') or line.startswith('F') or line.startswith('H'):
                    print(f"  Line {i}: CHECKED - {line[:60]}...")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_mermaid_syntax_fix()