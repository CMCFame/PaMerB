#!/usr/bin/env python3
"""
Test script for PaMerB IVR Converter
Tests the converter with the electric callout mermaid diagram
"""

import json
from mermaid_ivr_converter import convert_mermaid_to_ivr

def test_electric_callout():
    """Test the converter with the electric callout diagram"""
    
    # Electric callout mermaid diagram
    mermaid_code = '''flowchart TD
A["Welcome<br/>This is an electric callout from (Level 2).<br/>Press 1, if this is (employee).<br/>Press 3, if you need more time to get (employee) to the phone.<br/>Press 7, if (employee) is not home.<br/>Press 9, to repeat this message.<br/><br/>9 - repeat, or invalid input"] -->|"input"| B{"1 - this is employee"}
A -->|"no input - go to pg 3"| C["30-second message<br/>Press any key to<br/>continue..."]
A -->|"7 - not home"| D["Employee Not Home<br/>Please have<br/>(employee) call the<br/>(Level 2) Callout<br/>System at<br/>866-502-7267."]
A -->|"3 - need more time"| C
A -->|"retry logic"| A
B -->|"retry"| E["Invalid Entry<br/>Invalid entry.<br/>Please try again."]
E -->|"retry"| A
B -->|"yes"| F["Enter Employee PIN<br/>Please enter your 4 digit PIN<br/>followed by the pound key."]
F -->|"no"| E
F -->|"yes"| G{"Correct PIN?"}
G -->|"no"| E
G -->|"yes"| H["Electric Callout<br/>This is an electric callout."]
H --> I["Callout Reason<br/>The callout reason is (callout reason)."]
I --> J["Trouble Location<br/>The trouble location is (trouble location)."]
J --> K["Custom Message<br/>(Play custom message, if selected.)"]
K --> L{"Available For Callout<br/>Are you available to work this callout?<br/>If yes, press 1. If no, press 3.<br/>If no one else accepts, and you want to be called again, press 9."}
L -->|"retry"| E
L -->|"invalid or no input"| E
L -->|"1 - accept"| M["Accepted Response<br/>An accepted response has<br/>been recorded."]
L -->|"3 - decline"| N["Callout Decline<br/>Your response is being recorded as a decline."]
L -->|"9 - call back"| O["Qualified No<br/>You may be called again on this<br/>callout if no one accepts."]
M --> P["Goodbye<br/>Thank you.<br/>Goodbye."]
N --> P
O --> P
P --> Q["Disconnect"]
D --> Q'''

    print("="*80)
    print("TESTING ELECTRIC CALLOUT CONVERSION")
    print("="*80)
    
    try:
        # Convert the mermaid diagram
        ivr_flow, js_code = convert_mermaid_to_ivr(mermaid_code)
        
        print(f"SUCCESS: Generated {len(ivr_flow)} IVR nodes")
        print()
        
        # Analyze the results
        print("ANALYSIS OF GENERATED NODES:")
        print("-" * 40)
        
        for i, node in enumerate(ivr_flow, 1):
            label = node.get('label', f'Node_{i}')
            node_type = "Decision" if 'branch' in node else "Input" if 'getDigits' in node else "Message"
            
            print(f"{i:2d}. {label:<20} ({node_type})")
            
            # Show important attributes
            if 'playPrompt' in node:
                prompts = node['playPrompt']
                if isinstance(prompts, list) and len(prompts) > 0:
                    print(f"    Voice Files: {prompts[:3]}{'...' if len(prompts) > 3 else ''}")
            
            if 'branch' in node:
                branch = node['branch']
                choices = [k for k in branch.keys() if k.isdigit()]
                print(f"    Choices: {choices}")
            
            if 'nobarge' in node:
                print(f"    No-Barge: {node['nobarge']}")
            
            if 'maxLoop' in node:
                print(f"    Max Loop: {node['maxLoop']}")
            
            if 'returnsub' in node:
                print(f"    Return Sub: {node['returnsub']}")
        
        print()
        print("CRITICAL CHECKS:")
        print("-" * 40)
        
        # Check for welcome node mapping
        welcome_found = False
        for node in ivr_flow:
            if 'electric callout' in node.get('label', '').lower() or 'welcome' in node.get('label', '').lower():
                welcome_found = True
                branch = node.get('branch', {})
                print(f"Welcome Node: {node.get('label')}")
                if '1' in branch:
                    print(f"  [OK] Choice '1' maps to: {branch['1']}")
                else:
                    print(f"  [ERROR] Choice '1' mapping missing!")
                
                if '3' in branch:
                    print(f"  [OK] Choice '3' maps to: {branch['3']}")
                
                if '7' in branch:
                    print(f"  [OK] Choice '7' maps to: {branch['7']}")
                
                if '9' in branch:
                    print(f"  [OK] Choice '9' maps to: {branch['9']}")
                break
        
        if not welcome_found:
            print("  [ERROR] Welcome node not found!")
        
        # Check for accept/decline nodes
        accept_found = any('accept' in node.get('label', '').lower() for node in ivr_flow)
        decline_found = any('decline' in node.get('label', '').lower() for node in ivr_flow)
        
        print(f"  {'[OK]' if accept_found else '[ERROR]'} Accept response node found")
        print(f"  {'[OK]' if decline_found else '[ERROR]'} Decline response node found")
        
        # Check for gosub structures
        gosub_count = sum(1 for node in ivr_flow if 'gosub' in node)
        print(f"  [INFO] Gosub calls found: {gosub_count}")
        
        print()
        print("GENERATED JAVASCRIPT (first 1000 chars):")
        print("-" * 40)
        print(js_code[:1000])
        if len(js_code) > 1000:
            print("...")
            print(f"[Total length: {len(js_code)} characters]")
        
        # Save results for comparison
        with open('test_results.js', 'w', encoding='utf-8') as f:
            f.write(js_code)
        
        with open('test_analysis.json', 'w', encoding='utf-8') as f:
            json.dump({
                'node_count': len(ivr_flow),
                'nodes': [{'label': node.get('label'), 'type': 'decision' if 'branch' in node else 'input' if 'getDigits' in node else 'message'} for node in ivr_flow],
                'welcome_node_found': welcome_found,
                'accept_found': accept_found,
                'decline_found': decline_found,
                'gosub_count': gosub_count
            }, f, indent=2)
        
        print()
        print("Results saved to:")
        print("  - test_results.js (JavaScript code)")
        print("  - test_analysis.json (Analysis summary)")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

def compare_with_expected():
    """Compare results with expected output patterns"""
    print()
    print("COMPARISON WITH EXPECTED PATTERNS:")
    print("-" * 40)
    
    expected_patterns = [
        "Welcome node should handle multiple DTMF choices (1,3,7,9)",
        "Choice '1' should lead to employee verification",
        "PIN entry should have proper getDigits configuration",  
        "Accept/Decline should have gosub SaveCallResult calls",
        "Voice files should match actual content, not generic patterns",
        "Inbound flows should use returnsub instead of hangup"
    ]
    
    for i, pattern in enumerate(expected_patterns, 1):
        print(f"{i}. {pattern}")
    
    print()
    print("NOTE: To verify these patterns, check the generated files above.")

if __name__ == "__main__":
    print("Starting PaMerB IVR Converter Test")
    print("Testing with Electric Callout Diagram")
    print()
    
    success = test_electric_callout()
    
    if success:
        compare_with_expected()
        print()
        print("[SUCCESS] Test completed successfully!")
        print("To run the web app: streamlit run app.py --server.port 8502")
    else:
        print()
        print("[FAILED] Test failed - check errors above")
    
    print("="*80)