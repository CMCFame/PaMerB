#!/usr/bin/env python3
"""
Debug regex patterns for connection parsing
"""

import re

def test_connection_patterns():
    """Test regex patterns against the problematic connection"""
    
    # The problematic line from your mermaid
    test_line = 'A["Welcome<br/>This is an electric callout from (Level 2).<br/>Press 1, if this is (employee).<br/>Press 3, if you need more time to get (employee) to the phone.<br/>Press 7, if (employee) is not home.<br/>Press 9, to repeat this message.<br/><br/>9 - repeat, or invalid input"] -->|"input"| B{"1 - this is employee"}'
    
    print("TESTING CONNECTION REGEX PATTERNS")
    print("=" * 50)
    print(f"Test line: {test_line}")
    print()
    
    # Updated regex patterns from the converter
    patterns = [
        # Handle lines with node definitions: A["text"] -->|"label"| B{"text"}
        r'([A-Z]+)(?:\[.*?\]|\{.*?\})?\s*-->\s*\|"([^"]+)"\|\s*([A-Z]+)(?:\[.*?\]|\{.*?\})?',
        # Handle lines with node definitions: A["text"] -->|label| B{"text"}  
        r'([A-Z]+)(?:\[.*?\]|\{.*?\})?\s*-->\s*\|([^|]+)\|\s*([A-Z]+)(?:\[.*?\]|\{.*?\})?',
        # Handle simple connections: A --> B
        r'([A-Z]+)(?:\[.*?\]|\{.*?\})?\s*-->\s*([A-Z]+)(?:\[.*?\]|\{.*?\})?',
    ]
    
    for i, pattern in enumerate(patterns, 1):
        print(f"Pattern {i}: {pattern}")
        matches = re.findall(pattern, test_line)
        if matches:
            print(f"  MATCHES: {matches}")
        else:
            print(f"  NO MATCH")
        print()
    
    # Let's try simpler test lines
    simple_tests = [
        'A -->|"input"| B',
        'A --> B',
        'A -->|"7 - not home"| D'
    ]
    
    print("TESTING SIMPLE LINES:")
    print("-" * 30)
    
    for test in simple_tests:
        print(f"Testing: {test}")
        for i, pattern in enumerate(patterns, 1):
            matches = re.findall(pattern, test)
            if matches:
                print(f"  Pattern {i}: MATCH {matches}")
        print()

if __name__ == "__main__":
    test_connection_patterns()