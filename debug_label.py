#!/usr/bin/env python3
"""
Debug label generation for welcome node
"""

import re

def test_label_patterns():
    """Test label patterns against the welcome node text"""
    
    # The welcome node text from your mermaid
    welcome_text = '''Welcome
This is an electric callout from (Level 2).
Press 1, if this is (employee).
Press 3, if you need more time to get (employee) to the phone.
Press 7, if (employee) is not home.
Press 9, to repeat this message.

9 - repeat, or invalid input'''

    print("TESTING LABEL PATTERNS")
    print("=" * 40)
    print(f"Welcome text: {welcome_text}")
    print()
    
    text_lower = welcome_text.lower().strip()
    print(f"Text lower: {text_lower}")
    print()
    
    # Test the patterns from the converter
    ivr_label_patterns = [
        # Welcome/main entry node patterns (critical fix)
        (r'welcome.*this is an.*electric callout.*press 1', 'Live Answer'),
        (r'this is an.*electric callout.*press 1', 'Live Answer'), 
        (r'electric callout.*press 1.*press 3.*press 7.*press 9', 'Live Answer'),
        (r'press 1.*press 3.*press 7.*press 9', 'Live Answer'),
        # Additional patterns for electric callout welcome
        (r'this is an electric callout from.*press 1.*press 3.*press 7.*press 9', 'Live Answer'),
        (r'welcome.*press 1.*press 3.*press 7.*press 9', 'Live Answer'),
    ]
    
    for i, (pattern, replacement) in enumerate(ivr_label_patterns, 1):
        print(f"Pattern {i}: {pattern}")
        match = re.search(pattern, text_lower)
        if match:
            print(f"  MATCH! -> {replacement}")
            break
        else:
            print(f"  NO MATCH")
    
    print()
    print("SIMPLIFIED PATTERN TESTS:")
    simple_patterns = [
        r'welcome',
        r'electric callout',
        r'press 1',
        r'press 3',
        r'press 7', 
        r'press 9'
    ]
    
    for pattern in simple_patterns:
        if re.search(pattern, text_lower):
            print(f"  Found: {pattern}")
        else:
            print(f"  Missing: {pattern}")
            
    print()
    print("TESTING WITH re.DOTALL:")
    for i, (pattern, replacement) in enumerate(ivr_label_patterns, 1):
        print(f"Pattern {i}: {pattern}")
        match = re.search(pattern, text_lower, re.DOTALL)
        if match:
            print(f"  MATCH! -> {replacement}")
            break
        else:
            print(f"  NO MATCH")

if __name__ == "__main__":
    test_label_patterns()