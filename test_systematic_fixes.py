#!/usr/bin/env python3
"""
Test script to validate systematic fixes with the provided VAAW mermaid
"""

from mermaid_ivr_converter import convert_mermaid_to_ivr

# VAAW mermaid from user
vaaw_mermaid = '''flowchart TD
A["Welcome<br/>This is a Virginia American Water callout. It is (dow, date, time)."] --> B["Emergency Callout<br/>This is a Virginia American Water Emergency callout."]
A --> C["Normal Callout<br/>This is a Virginia American Water Normal callout."]
A --> D["Scheduled Overtime Callout<br/>There is a Virginia American Water Scheduled Overtime callout scheduled for (dow, date, time) ending on (dow, date, time)"]
B --> E["Trouble Location<br/>The location of the work is (trouble location)."]
C --> E
D --> E
E --> F["Duty Position<br/>You are being called out as a (duty position)."]
F --> G["Callout Reason<br/>The callout reason is (callout reason)."]
G --> H["Custom Message<br/>(Play custom message, if selected.)"]
H --> I["Call-back Number<br/>To bypass this answering machine message and respond to this callout you may press 1 or call the Virginia American Water Callout System at 571-556-9640."]
I --> J{"Played 2 times?"}
J -- no --> I
J -- yes --> K["Goodbye<br/>Thank you.<br/>Goodbye."]
K --> L["Disconnect"]
I -->|"Input - 1, 3, 7, or 9"| I'''

print("TESTING SYSTEMATIC FIXES")
print("=" * 50)

try:
    ivr_flow, js_output = convert_mermaid_to_ivr(vaaw_mermaid, use_dynamodb=False)
    
    print("SYSTEMATIC FIXES VALIDATION:")
    print("-" * 30)
    
    # Check 1: Welcome node routing
    main_menu_node = next((node for node in ivr_flow if node.get('label') == 'Main Menu'), None)
    if main_menu_node and 'branch' in main_menu_node:
        branch_keys = list(main_menu_node['branch'].keys())
        numeric_keys = [k for k in branch_keys if k.isdigit()]
        print(f"1. Welcome Menu DTMF routing: {numeric_keys}")
        print(f"   Valid choices: {main_menu_node.get('getDigits', {}).get('validChoices', 'None')}")
        
        # Check if routes to callout types
        routes_correctly = any('Emergency' in str(main_menu_node['branch'].get(k, '')) or 
                             'Normal' in str(main_menu_node['branch'].get(k, '')) or 
                             'Scheduled' in str(main_menu_node['branch'].get(k, '')) 
                             for k in numeric_keys)
        print(f"   Routes to callout types: {'YES' if routes_correctly else 'NO'}")
    
    # Check 2: Input node detection
    input_nodes = [node for node in ivr_flow if 'getDigits' in node and 'Call' in node.get('label', '')]
    print(f"\n2. Input nodes detected: {len(input_nodes)}")
    for node in input_nodes:
        print(f"   {node.get('label', 'Unknown')}: {node.get('getDigits', {}).get('validChoices', 'None')}")
    
    # Check 3: Loop control handling
    loop_control_nodes = [node for node in ivr_flow if '_loop_control' in node]
    maxloop_nodes = [node for node in ivr_flow if 'maxLoop' in node]
    print(f"\n3. Loop control: {len(loop_control_nodes)} control nodes, {len(maxloop_nodes)} maxLoop nodes")
    
    # Check 4: Voice file mapping quality
    voice_files_used = []
    missing_count = 0
    for node in ivr_flow:
        prompts = node.get('playPrompt', [])
        if isinstance(prompts, list):
            for prompt in prompts:
                if isinstance(prompt, str):
                    if prompt.startswith('callflow:'):
                        voice_files_used.append(prompt)
                    elif '[VOICE FILE NEEDED]' in prompt:
                        missing_count += 1
    
    print(f"\n4. Voice file mapping: {len(voice_files_used)} mapped, {missing_count} missing")
    
    # Show sample of generated JavaScript
    print(f"\nGENERATED JAVASCRIPT SAMPLE (first 5 nodes):")
    print("-" * 40)
    
    # Parse the JS to show structure
    import json
    for i, node in enumerate(ivr_flow[:5]):
        print(f"Node {i+1}: {node.get('label', 'Unknown')}")
        if 'maxLoop' in node:
            print(f"  maxLoop: {node['maxLoop']}")
        if 'getDigits' in node:
            print(f"  getDigits: validChoices='{node['getDigits'].get('validChoices', 'None')}'")
        if 'branch' in node:
            branch_summary = {k: v for k, v in list(node['branch'].items())[:3]}
            print(f"  branch: {branch_summary}{'...' if len(node['branch']) > 3 else ''}")
        print()
    
    print("SYSTEMATIC IMPROVEMENTS SUMMARY:")
    print("+ Welcome nodes now parse all direct connections")
    print("+ Input nodes detect DTMF patterns from connection labels")
    print("+ Loop control decisions convert to maxLoop logic")
    print("+ Voice file matching expanded with common patterns")
    print("+ All node types use systematic detection logic")
    
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()