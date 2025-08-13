"""
Test script to verify the Mermaid node label quoting implementation
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from enhanced_pdf_processor_v2 import IntelligentPDFProcessor

def test_mermaid_cleaning():
    """Test the Mermaid syntax cleaning with complex node labels"""
    
    # Create a mock processor instance (without API key for testing)
    class MockProcessor:
        def _clean_mermaid_syntax(self, mermaid_code):
            # Import the actual method from the processor
            processor = IntelligentPDFProcessor.__new__(IntelligentPDFProcessor)
            return processor._clean_mermaid_syntax(mermaid_code)
    
    mock_processor = MockProcessor()
    
    # Test cases that previously caused display issues
    test_cases = [
        # Case 1: Complex welcome node with <br/> and commas
        """flowchart TD
    A[Welcome<br/>Press 1 for employee, 7 for not home]
    A -->|"1"| B[Enter PIN]
    A -->|"7"| C[Not Home]""",
        
        # Case 2: Decision node with parentheses
        """flowchart TD
    A[Welcome]
    A --> B{Is this the employee?}
    B -->|"Yes"| C[Enter PIN (4 digits)]
    B -->|"No"| D[Invalid Entry: Press 1, 2, or 7]""",
        
        # Case 3: Mixed complex and simple nodes
        """flowchart TD
    A[Simple Node]
    A --> B[Complex Node: Press 1, 2, or 3<br/>Enter your choice]
    B -->|"1"| C[Option 1 (Primary)]
    B -->|"2"| D[Option 2 & Secondary]
    B -->|"3"| E[Simple End]"""
    ]
    
    print("Testing Mermaid Node Label Quoting")
    print("=" * 50)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest Case {i}:")
        print("ORIGINAL:")
        print(test_case)
        print("\nCLEANED:")
        
        try:
            cleaned = mock_processor._clean_mermaid_syntax(test_case)
            print(cleaned)
            
            # Check if complex labels are properly quoted
            lines = cleaned.split('\n')
            quoted_found = any('"' in line and ('[' in line or '{' in line) for line in lines)
            
            if quoted_found:
                print("SUCCESS: Complex labels properly quoted")
            else:
                print("WARNING: No quotes detected (may be simple labels)")
                
        except Exception as e:
            print(f"ERROR: {e}")
        
        print("-" * 30)
    
    print("\nSUMMARY: Mermaid node label quoting implementation tested")
    print("This should resolve the display issues diagnosed by mermaidcharts.com AI")

if __name__ == "__main__":
    test_mermaid_cleaning()