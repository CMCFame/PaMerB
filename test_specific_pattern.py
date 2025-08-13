"""
Test the specific remaining pattern
"""

import re

# The problematic line
line = 'F -->|"yes"| H["Employee Information<br/>The following information is for (employee).<br/>You have [no"] pending callout requests.<br/>Your current availability status is (status).<br/>Your temporary contact numbers are [not] active.]'

print("ORIGINAL LINE:")
print(line)
print()

# Let's see what's happening step by step
print("STEP BY STEP ANALYSIS:")

# Check for the pattern
if '[not]' in line:
    print("Found [not] pattern")
else:
    print("No [not] pattern found")
    
if '[no"]' in line:
    print("Found [no\"] pattern")
else:
    print("No [no\"] pattern found")

# Let's extract just the H node content
import re
match = re.search(r'H\[(.*)\]', line)
if match:
    content = match.group(1)
    print(f"H node content: {content}")
    print()
    
    # Check what patterns are in the content
    if '[no"]' in content:
        print("Found [no\"] in H node content")
    if '[not]' in content:
        print("Found [not] in H node content")
    
    # Try specific fixes
    fixed1 = content.replace('[no"]', 'no')
    fixed2 = fixed1.replace('[not]', 'not')
    
    print(f"After fixes: {fixed2}")
    
    # Reconstruct the line
    new_line = line.replace(content, f'"{fixed2}"')
    print(f"\nFIXED LINE:")
    print(new_line)