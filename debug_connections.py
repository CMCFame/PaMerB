#!/usr/bin/env python3
"""
Debug script to understand connection parsing issues
"""

from mermaid_ivr_converter import FlexibleARCOSConverter

def debug_connection_parsing():
    """Debug the connection parsing for electric callout"""
    
    # Your electric callout mermaid
    mermaid_code = '''flowchart TD
A["Welcome<br/>This is an electric callout from (Level 2).<br/>Press 1, if this is (employee).<br/>Press 3, if you need more time to get (employee) to the phone.<br/>Press 7, if (employee) is not home.<br/>Press 9, to repeat this message.<br/><br/>9 - repeat, or invalid input"] -->|"input"| B{"1 - this is employee"}
A -->|"no input - go to pg 3"| C["30-second message<br/>Press any key to<br/>continue..."]
A -->|"7 - not home"| D["Employee Not Home<br/>Please have<br/>(employee) call the<br/>(Level 2) Callout<br/>System at<br/>866-502-7267."]
A -->|"3 - need more time"| C
A -->|"retry logic"| A'''

    print("=" * 60)
    print("DEBUGGING CONNECTION PARSING")
    print("=" * 60)
    
    # Parse the connections
    converter = FlexibleARCOSConverter()
    nodes, connections = converter._parse_mermaid_enhanced(mermaid_code)
    
    print("\nPARSED NODES:")
    for node_id, text in nodes.items():
        print(f"  {node_id}: {text[:50]}...")
    
    print(f"\nPARSED CONNECTIONS ({len(connections)} total):")
    for i, conn in enumerate(connections, 1):
        print(f"  {i}. {conn['source']} -->|'{conn['label']}'| {conn['target']}")
    
    print("\nCRITICAL CONNECTION ANALYSIS:")
    print("-" * 40)
    
    # Look for the "input" connection specifically
    input_found = False
    for conn in connections:
        if 'input' in conn['label'].lower():
            print(f"FOUND INPUT CONNECTION: {conn['source']} -> {conn['target']}")
            print(f"  Label: '{conn['label']}'")
            input_found = True
    
    if not input_found:
        print("ERROR: No 'input' connection found!")
        print("This is why choice '1' is not mapping correctly.")
    
    # Check node A connections
    print(f"\nNODE A CONNECTIONS:")
    a_connections = [conn for conn in connections if conn['source'] == 'A']
    for conn in a_connections:
        print(f"  A -->|'{conn['label']}'| {conn['target']}")
    
    print(f"\nEXPECTED MAPPING FOR NODE A:")
    print(f"  Choice '1' (input) -> B (Employee verification)")
    print(f"  Choice '3' (need more time) -> C (30-second message)")  
    print(f"  Choice '7' (not home) -> D (Employee Not Home)")
    print(f"  Choice '9' (repeat) -> A (back to welcome)")
    
    return nodes, connections

if __name__ == "__main__":
    debug_connection_parsing()