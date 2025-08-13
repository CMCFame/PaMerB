"""
Test script to verify multi-flow and page reference fixes
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from mermaid_ivr_converter import convert_mermaid_to_ivr, detect_page_reference

def test_multiflow_fixes():
    """Test the multi-flow and page reference handling"""
    
    print("Testing Multi-Flow and Page Reference Fixes")
    print("=" * 50)
    
    # Test 1: Page reference detection
    print("\nTest 1: Page Reference Detection")
    test_texts = [
        "Availability Status Page 8",
        "Test Numbers Page 11", 
        "PIN and Name Page 12",
        "Regular Node",
        "Add/Change Contact Numbers Page 9"
    ]
    
    for text in test_texts:
        page_ref = detect_page_reference(text)
        print(f"  '{text}' -> Page: {page_ref}")
    
    # Test 2: Main Menu DTMF routing
    print("\nTest 2: Main Menu DTMF Routing")
    menu_mermaid = """
flowchart TD
    K["Main Menu<br/>To change your current availability status, press 1.<br/>To add or change your contact numbers, press 2.<br/>To verify or test your contact numbers, press 3.<br/>To change your PIN or to re-record your name, press 4.<br/>To repeat this menu, press 8.<br/>To end this call, simply hang up."]
    K -->|"1"| N["Availability Status<br/>Page 8"]
    K -->|"2"| O["Add/Change Contact Numbers<br/>Page 9"] 
    K -->|"3"| P["Test Numbers<br/>Page 11"]
    K -->|"4"| Q["PIN and Name<br/>Page 12"]
    """
    
    try:
        ivr_flow, js_code = convert_mermaid_to_ivr(menu_mermaid, use_dynamodb=False)
        
        # Find Main Menu node
        menu_node = None
        for node in ivr_flow:
            if 'main menu' in node.get('label', '').lower():
                menu_node = node
                break
        
        if menu_node:
            print("  Main Menu node found:")
            if 'getDigits' in menu_node:
                digits = menu_node['getDigits']
                print(f"    validChoices: {digits.get('validChoices', 'None')}")
                
            if 'branch' in menu_node:
                branches = menu_node['branch']
                print(f"    Branches: {list(branches.keys())}")
                
                # Check if branches go directly to targets (not through Input node)
                has_direct_routing = False
                for key, target in branches.items():
                    if key.isdigit() and target != 'Input':
                        has_direct_routing = True
                        print(f"      {key} -> {target}")
                
                if has_direct_routing:
                    print("    SUCCESS: Direct DTMF routing implemented")
                else:
                    print("    WARNING: Still routing through Input node")
        
        # Test 3: Page reference gosub calls
        print("\nTest 3: Page Reference Gosub Calls")
        page_nodes = [node for node in ivr_flow if 'page' in node.get('label', '').lower()]
        
        for node in page_nodes:
            label = node.get('label', '')
            print(f"  Node: {label}")
            
            if 'gosub' in node:
                print(f"    SUCCESS: Uses gosub: {node['gosub']}")
            elif 'goto' in node and node['goto'] == 'hangup':
                print(f"    INFO: Terminal node with hangup")
            else:
                print(f"    WARNING: No gosub found, uses: {node.get('goto', 'unknown')}")
    
    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\nSUMMARY: Multi-flow fixes tested")
    print("Expected improvements:")
    print("  1. Page references detected and converted to gosub calls")
    print("  2. Main Menu routes directly to options (no Input node)")
    print("  3. Proper valid choices extracted from menu text")

if __name__ == "__main__":
    test_multiflow_fixes()