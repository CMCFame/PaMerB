#!/usr/bin/env python3
"""
Test script to validate lead programmer fixes
Tests the VAAW 1050 example with all the implemented fixes
"""

import os
import sys
import json
from mermaid_ivr_converter import convert_mermaid_to_ivr
from callout_config import CalloutConfigurationManager, CalloutConfiguration, CalloutDirection

def test_vaaw_fixes():
    """Test VAAW 1050 example with all fixes applied"""
    print("TESTING LEAD PROGRAMMER FIXES")
    print("=" * 60)
    
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
    
    # Test 1: File naming fix
    print("\nTEST 1: File Naming Convention")
    config = CalloutConfiguration(
        schema="VAAW",
        callout_type_id="1050", 
        direction=CalloutDirection.OUTBOUND
    )
    expected_filename = "VAAW_1050.js"  # Should NOT have _ib suffix
    actual_filename = config.get_filename()
    print(f"Expected: {expected_filename}")
    print(f"Actual: {actual_filename}")
    print(f"PASS" if actual_filename == expected_filename else f"FAIL")
    
    # Test 2: IVR conversion with all fixes
    print("\nTEST 2: IVR Code Generation")
    try:
        ivr_flow, js_output = convert_mermaid_to_ivr(vaaw_mermaid, use_dynamodb=False)
        
        print(f"Generated {len(ivr_flow)} nodes successfully")
        
        # Test 3: Check for essential nodes
        print("\nTEST 3: Essential Nodes Check")
        node_labels = [node.get('label', '') for node in ivr_flow]
        
        essential_checks = [
            ('Problems', 'Problems node for error handling'),
            ('Goodbye', 'Goodbye node for termination'),
        ]
        
        for label, description in essential_checks:
            found = any(label in node_label for node_label in node_labels)
            print(f"{'PASS' if found else 'FAIL'} {description}: {'Found' if found else 'Missing'}")
        
        # Test 4: Check maxLoop implementation
        print("\nTEST 4: MaxLoop Implementation")
        has_maxloop = any('maxLoop' in node for node in ivr_flow)
        print(f"{'PASS' if has_maxloop else 'FAIL'} MaxLoop retry logic: {'Found' if has_maxloop else 'Missing'}")
        
        # Test 5: Check DTMF branching
        print("\nTEST 5: DTMF Branching")
        has_getdigits = any('getDigits' in node for node in ivr_flow)
        print(f"{'PASS' if has_getdigits else 'FAIL'} getDigits configuration: {'Found' if has_getdigits else 'Missing'}")
        
        numeric_branches = []
        for node in ivr_flow:
            if 'branch' in node:
                branch_keys = node['branch'].keys()
                numeric_keys = [k for k in branch_keys if k.isdigit()]
                if numeric_keys:
                    numeric_branches.extend(numeric_keys)
        
        print(f"{'PASS' if numeric_branches else 'FAIL'} Numeric DTMF keys: {numeric_branches if numeric_branches else 'None found'}")
        
        # Test 6: Check playLog arrays vs single log
        print("\nTEST 6: PlayLog Structure")
        playlog_count = sum(1 for node in ivr_flow if 'playLog' in node)
        single_log_count = sum(1 for node in ivr_flow if 'log' in node and 'playLog' not in node)
        print(f"Nodes with playLog arrays: {playlog_count}")
        print(f"Nodes with single log: {single_log_count}")
        
        # Test 7: Voice file coverage
        print("\nTEST 7: Voice File Coverage")
        voice_files_used = []
        missing_files = []
        
        for node in ivr_flow:
            prompts = node.get('playPrompt', [])
            if isinstance(prompts, list):
                for prompt in prompts:
                    if isinstance(prompt, str):
                        if prompt.startswith('callflow:'):
                            voice_files_used.append(prompt)
                        elif '[VOICE FILE NEEDED]' in prompt:
                            missing_files.append(prompt)
        
        print(f"Voice files used: {len(voice_files_used)}")
        print(f"{'WARNING' if missing_files else 'PASS'} Missing voice files: {len(missing_files)}")
        
        # Test 8: Template variables
        print("\nTEST 8: Template Variables")
        template_vars = []
        for node in ivr_flow:
            prompts = node.get('playPrompt', [])
            if isinstance(prompts, list):
                for prompt in prompts:
                    if isinstance(prompt, str) and '{{' in prompt:
                        template_vars.append(prompt)
        
        print(f"{'PASS' if template_vars else 'WARNING'} Template variables found: {len(template_vars)}")
        if template_vars:
            print(f"   Examples: {template_vars[:3]}")
        
        # Show generated code sample
        print("\nGENERATED CODE SAMPLE (First 3 nodes):")
        print("-" * 40)
        for i, node in enumerate(ivr_flow[:3]):
            print(f"Node {i+1}: {node.get('label', 'Unknown')}")
            if 'playLog' in node:
                print(f"  playLog: {node['playLog']}")
            elif 'log' in node:
                print(f"  log: {node['log']}")
            if 'maxLoop' in node:
                print(f"  maxLoop: {node['maxLoop']}")
            if 'getDigits' in node:
                print(f"  getDigits: {node['getDigits']}")
            print()
        
        print("ALL TESTS COMPLETED!")
        print(f"Expected filename: {expected_filename}")
        print(f"Total nodes generated: {len(ivr_flow)}")
        
        return True
        
    except Exception as e:
        print(f"TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_vaaw_fixes()
    sys.exit(0 if success else 1)