#!/usr/bin/env python3
"""
Test script to show generated JavaScript output
"""

from mermaid_ivr_converter import convert_mermaid_to_ivr

# VAAW mermaid from test file
vaaw_mermaid = """flowchart TD
A["This is a Virginia Service Alert..."] --> B{"Is this employee available?"}
B -->|"Yes"| C["Press 1 if you are available..."]
B -->|"No"| D["Press 2 if you are not available..."]
C --> E{"Employee presses 1"}
E -->|"Yes"| F["The call has been successfully entered"]
E -->|"No"| G["Invalid entry"]
G --> H["Disconnect"]
D --> I["The call has been successfully entered"]
I --> J["Disconnect"]
F --> J"""

print("GENERATING VAAW JAVASCRIPT OUTPUT")
print("=" * 50)

try:
    ivr_flow, js_output = convert_mermaid_to_ivr(vaaw_mermaid, use_dynamodb=False)
    
    print("GENERATED JAVASCRIPT:")
    print("-" * 30)
    print(js_output)
    
    print("\nFILE WOULD BE SAVED AS: VAAW_1050.js (NO _ib suffix for outbound)")
    print(f"TOTAL NODES: {len(ivr_flow)}")
    
    # Check for key improvements
    improvements = []
    
    # Check maxLoop
    if any('maxLoop' in str(node) for node in ivr_flow):
        improvements.append("+ MaxLoop retry logic implemented")
    
    # Check getDigits
    if any('getDigits' in str(node) for node in ivr_flow):
        improvements.append("+ GetDigits DTMF collection implemented")
    
    # Check Problems node
    if any('Problems' in str(node.get('label', '')) for node in ivr_flow):
        improvements.append("+ Problems node for error handling")
    
    # Check Goodbye node
    if any('Goodbye' in str(node.get('label', '')) for node in ivr_flow):
        improvements.append("+ Goodbye node for termination")
    
    # Check template variables
    if any('{{' in str(node) for node in ivr_flow):
        improvements.append("+ Template variables implemented")
    
    # Check voice file coverage
    voice_files = [prompt for node in ivr_flow for prompt in node.get('playPrompt', []) if 'callflow:' in str(prompt)]
    if voice_files:
        improvements.append(f"+ {len(voice_files)} voice files mapped")
    
    print("\nKEY IMPROVEMENTS IMPLEMENTED:")
    for improvement in improvements:
        print(f"  {improvement}")
    
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()