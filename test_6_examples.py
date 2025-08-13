"""
Test all 6 examples from mermaid_flows_test.txt to verify structure and performance
"""

import time
from mermaid_ivr_converter import convert_mermaid_to_ivr

# All 6 test cases from mermaid_flows_test.txt
test_cases = {
    "Script8 (REU Notification)": '''flowchart TD
A["Welcome<br/>This is an REU Notification.<br/>Press 1, if this is (employee).<br/>Press 3, if you need more time to get (employee/'the contact') to the phone.<br/>Press 7, if (employee) is not home.<br/>Press 9, to repeat this message."] -->|9 - repeat or invalid entry| A
A -->|3 - need more time| B["90-second message<br/>Press any key to continue..."]
A -->|7 - not home| C["Employee Not Home<br/>Please have (employee) call the REU Callout System at 866-XXX-XXXX."]
A -->|1 - this is employee/contact| D["Notification Callout<br/>This is an important call notification message. Please listen carefully."]
A -->|no input| E["Answering Machine<br/>Page 9"]
B --> A
C --> F["Goodbye<br/>Thank you.<br/>Goodbye."] --> G[Disconnect]
D --> H["Custom Message<br/>(Play selected custom message.)"]
H --> I{"Confirm<br/>To confirm receipt of this message, press 1.<br/>To replay the message, press 3."}
I -->|1 - accept| J["Accepted Response<br/>You have confirmed receipt of this message."]
I -->|3 - repeat| H
I -->|invalid input| K["Invalid Entry<br/>Invalid entry.<br/>Please try again."] -->|retry logic| I
I -->|no input| K
J --> F''',

    "Script5 (PIN Change)": '''flowchart TD
A["New PIN<br/>Please enter your new four digit PIN<br/>followed by the pound key."] -->|retry logic| A
A --> B{"Entered Digits?"}
B -->|no| C["Invalid Entry<br/>Invalid entry.<br/>Please try again."] --> A
B -->|yes| D{"Is PIN = 1234?"}
D -->|yes| E["PIN not 1234<br/>Your PIN cannot be 1234."] --> A
D -->|no| F["Re-enter PIN<br/>Please re-enter your new four<br/>digit PIN followed by the<br/>pound key."]
F --> G{"Match to<br/>first entry?"}
G -->|no| C
G -->|yes| H["PIN Changed<br/>Your pin has been<br/>changed successfully."]
H --> I{"Was the name<br/>recorded previously?"}
I -->|no| J["For first time users<br/>The automated system needs your spoken<br/>name for callouts. After the tone, please say<br/>your first and last name. To end your<br/>recording press the pound key [BEEP]."]
J -->|retry logic| J
J --> K["Name confirmation<br/>Your name has been recorded as (name).<br/>If this is correct, press 1.<br/>To re-record, press 3."]
K --> L{"Entered Digits?"}
L -->|no| C
L -->|yes| M{"Valid Digits?"}
M -->|no| C
M -->|yes| N{"Selection"}
N -->|one| O["Name Changed<br/>Your name has been<br/>successfully changed."] --> P["Employee<br/>Information"]
N -->|three| J
I -->|yes| K''',

    "Script11 (Test Contact Numbers)": '''flowchart TD
A["Test Contact Numbers<br/>You may now test your contact numbers and receive a test call.<br/>To test your permanent numbers, press 1.<br/>To test your temporary number, press 3.<br/>To return to the Main Menu, press the star key.<br/>To end this call simply hang-up"] -->|one| B["Permanent Contact Numbers<br/>Please select the number you would like to test.<br/>For the First Permanent number, press 1.<br/>For the Second Permanent number, press 2."]
A -->|three| C["Temporary Contact Numbers<br/>Please select the number you would like to test.<br/>For the First Temporary number, press 1."]
A -->|star| D["Main Menu<br/>Page 2"]
A -->|hang-up| E["Disconnect"]
A -->|invalid input - no input| F["Invalid Entry<br/>Invalid entry.<br/>Please try again."]
B -->|one| G{"Does the number exist?"}
B -->|invalid input - no input| F
G -->|no| F
G -->|yes| H["Test First Permanent<br/>Your test message has been sent to your First Permanent number<br/>which is (type-phone), number: (number).<br/>If there has been a problem, please try again or contact your supervisor."]
B -->|two/three| I["Test Second/Third Permanent<br/>Your test message has been sent to your Second Permanent number<br/>which is (type-phone), number: (number).<br/>If there has been a problem, please try again or contact your supervisor."]
C -->|no| J{"Does the number exist?"}
C -->|invalid input - no input| F
J -->|no| F
J -->|yes| K["Test Temporary Numbers<br/>Your test message has been sent to your temporary number<br/>which is (type-phone), number: (number).<br/>If there has been a problem, please try again or contact your supervisor."]
C -->|one/two/three| L["No Number Assigned<br/>A contact number has not been assigned to this selection."]
H --> M["Test Another Number<br/>To test another number, press 1.<br/>To return to the main menu, press the star key.<br/>To end this call, simply hang-up."]
I --> M
K --> M
M -->|one| M
M -->|star| D
M -->|hang-up| E
M -->|invalid input - no input| F''',

    "Script6ob (Fill Shift Pre-Arranged)": '''flowchart TD
A["Welcome<br/>This is a Fill Shift Pre-Arranged Callout from REU.<br/>Press 1, if this is (employee).<br/>Press 3, if you need more time.<br/>Press 7, if (employee) is not home.<br/>Press 9, to repeat this message."] -->|"1 - this is employee"| B{"Enter Employee PIN<br/>Please enter your four digit PIN followed by the pound key."}
A -->|"3 - need more time"| C["90-second message<br/>Press any key to continue..."]
A -->|"7 - not home"| D["Employee Not Home<br/>Please have (employee) call the REU Callout System at 866-XXX-XXXX."]
A -->|"9 - repeat, or invalid input"| A
B -->|"no"| E["Invalid Entry<br/>Invalid entry. Please try again."]
E -->|"retry logic"| B
B -->|"yes"| F["Pre-Arranged Callout<br/>This is an REU Pre-Arranged callout for work beginning on (date, time, time-zone) ending approximately on (date, time, time-zone)."]
F --> G["Callout Reason<br/>The callout reason is (callout reason)."]
G --> H["Custom Message<br/>(Play custom message, if selected.)"]
H --> I{"Available For Callout<br/>Are you available to work this callout?<br/>If yes, press 1. If no, press 3.<br/>If no one else accepts, and you want to be called again, press 7."}
I -->|"invalid input or no input"| E
I -->|"1 - accept"| J["Accepted Confirmation<br/>You pressed 1 to accept.<br/>Please press 1 again to confirm."]
I -->|"3 - decline"| K["Declined Confirmation<br/>You pressed 3 to decline.<br/>Please press 3 again to confirm."]
I -->|"7 - call back"| L["Qualified No Confirmation<br/>You pressed 9 to be called again if no one else at your center accepts.<br/>Please press 9 again to confirm."]
J -->|"invalid entry"| E
J -->|"different number (to Invalid Entry)"| E
J -->|"same number"| M["Accepted Response<br/>An accepted response has been recorded."]
K -->|"invalid entry"| E
K -->|"different number (to Invalid Entry)"| E
K -->|"same number"| N["Callout Decline<br/>Your response is being recorded as a decline."]
L -->|"invalid entry"| E
L -->|"different number (to Invalid Entry)"| E
L -->|"same number"| O["Qualified No<br/>Your response is being recorded as a qualified no.<br/>You may be called again if no one else at your center accepts."]
D --> P["Goodbye<br/>Thank you.<br/>Goodbye."]
P --> Q["Disconnect"]
M --> P
N --> P
O --> P''',

    "Script7ob (REU Callout with Answering Machine)": '''flowchart TD
A["Welcome<br/>This is an REU callout. It is (dow, date, time,)."] --> B["Emergency Callout (without Qual No)<br/>This is an REU Callout"]
A --> C["Emergency Callout (with Qualified No)<br/>This is an REU Callout"]
A --> D["Pre-Arranged Overtime<br/>This is a Pre-Arranged Callout from REU for work beginning on (dow, date, time, time zone) and ending approximately on (dow, date, time, time zone)"]
B --> E["Callout Reason<br/>The callout reason is (callout reason)."]
C --> E
D --> E
E --> F["Custom Message<br/>(Play custom message, if selected.)"]
F --> G["Call-back Number<br/>To bypass this answering machine message and respond to this callout you may press 1 or call the REU Callout System at [XXX-XXX-XXXX]"]
G --> H{"Played 2 times?"}
H -- no --> G
H -- yes --> I["Goodbye<br/>Thank you.<br/>Goodbye."]
I --> J["Disconnect"]
G --> K["input – 1, 3, 7, or 9<br/>If 1, go to Employee Enter PIN on page 2.<br/>If 3, go to need more time on page 2.<br/>If 7, go to Employee Not Home on page 2.<br/>If 9, go to Repeat Message on page 2."]''',

    "Script11ob (Automated TEST Callout)": '''flowchart TD
A["Welcome<br/>This is an automated TEST callout from REU. Again, this is a<br/>TEST callout only.<br/>Press 1 if this is (employee).<br/>Press 3 if you need more time to get (employee) to the phone.<br/>Press 7 if (employee) is not home.<br/>Press 9 to repeat this message."] -->|input| B{"1 - this is employee"}
A -->|3 - need more time| C["90-second message<br/>Press any key to continue..."]
A -->|7 - not home| D["Employee Not Home<br/>This was a test call notification for (employee)."]
A -->|9 - repeat or invalid input| E["Invalid Entry<br/>Invalid entry.<br/>Please try again."]
B -->|no input| C
B -->|input| F["Enter Employee PIN<br/>Please enter your 4 digit PIN<br/>followed by the pound key."]
F -->|no| E
F -->|yes| G{"Entered digits?"}
G -->|no| E
G -->|yes| H{"Correct PIN?"}
H -->|no| E
H -->|yes| I["Confirm Receipt<br/>This is a test callout. Do<br/>not report to work. To<br/>confirm receipt of this test<br/>call press any key."]
I -->|no input| E
I -->|any key| J["Acknowledged Call<br/>You have confirmed receipt of<br/>this test call. Again, do not<br/>report to work. This was a test<br/>call only."]
J --> K["Goodbye<br/>Thank you.<br/>Goodbye."]
D --> K
E -->|retry logic| F
J --> L["Disconnect"]
D --> L'''
}

def validate_ivr_structure(ivr_flow, script_name):
    """Validate that IVR flow has expected production structure"""
    issues = []
    
    if not ivr_flow or not isinstance(ivr_flow, list):
        issues.append("No IVR flow generated or invalid format")
        return issues
    
    node_count = len(ivr_flow)
    voice_file_count = 0
    nodes_with_branches = 0
    nodes_with_getdigits = 0
    nodes_with_gosub = 0
    
    for i, node in enumerate(ivr_flow):
        if not isinstance(node, dict):
            issues.append(f"Node {i}: Not a dictionary")
            continue
            
        # Check required fields
        if 'label' not in node:
            issues.append(f"Node {i}: Missing 'label' field")
        if 'playPrompt' not in node:
            issues.append(f"Node {i}: Missing 'playPrompt' field")
        else:
            voice_file_count += len(node['playPrompt'])
            
        # Check for production features
        if 'branch' in node:
            nodes_with_branches += 1
        if 'getDigits' in node:
            nodes_with_getdigits += 1
        if 'gosub' in node:
            nodes_with_gosub += 1
    
    # Expected ranges based on complexity
    expected_ranges = {
        "Script8 (REU Notification)": {"nodes": (8, 15), "voice_files": (8, 20)},
        "Script5 (PIN Change)": {"nodes": (10, 20), "voice_files": (10, 25)},
        "Script11 (Test Contact Numbers)": {"nodes": (10, 18), "voice_files": (10, 25)},
        "Script6ob (Fill Shift Pre-Arranged)": {"nodes": (15, 25), "voice_files": (15, 30)},
        "Script7ob (REU Callout with Answering Machine)": {"nodes": (8, 15), "voice_files": (8, 20)},
        "Script11ob (Automated TEST Callout)": {"nodes": (10, 18), "voice_files": (10, 25)}
    }
    
    if script_name in expected_ranges:
        exp_range = expected_ranges[script_name]
        if not (exp_range["nodes"][0] <= node_count <= exp_range["nodes"][1]):
            issues.append(f"Node count {node_count} outside expected range {exp_range['nodes']}")
        if not (exp_range["voice_files"][0] <= voice_file_count <= exp_range["voice_files"][1]):
            issues.append(f"Voice file count {voice_file_count} outside expected range {exp_range['voice_files']}")
    
    return issues

def test_all_examples():
    """Test all 6 examples and validate structure"""
    print("Testing All 6 Examples from mermaid_flows_test.txt")
    print("=" * 60)
    
    total_start_time = time.time()
    results = []
    
    for script_name, mermaid_code in test_cases.items():
        print(f"\nTesting: {script_name}")
        print("-" * 40)
        
        start_time = time.time()
        
        try:
            # Convert using DynamoDB integration (will fallback to CSV)
            ivr_flow, js_output = convert_mermaid_to_ivr(mermaid_code, use_dynamodb=True)
            
            conversion_time = time.time() - start_time
            
            # Validate structure
            issues = validate_ivr_structure(ivr_flow, script_name)
            
            # Calculate stats
            node_count = len(ivr_flow) if ivr_flow else 0
            voice_file_count = sum(len(node.get('playPrompt', [])) for node in ivr_flow if isinstance(node, dict))
            js_size = len(js_output) if js_output else 0
            
            result = {
                'script': script_name,
                'success': True,
                'time': conversion_time,
                'nodes': node_count,
                'voice_files': voice_file_count,
                'js_size': js_size,
                'issues': issues
            }
            
            print(f"SUCCESS: Generated {node_count} nodes in {conversion_time:.3f}s")
            print(f"Voice files: {voice_file_count}, JS size: {js_size} chars")
            
            if issues:
                print(f"ISSUES: {len(issues)} issues found:")
                for issue in issues[:3]:  # Show first 3 issues
                    print(f"  - {issue}")
            else:
                print("VALIDATION: All structure checks passed")
            
            # Show sample nodes
            if ivr_flow and len(ivr_flow) > 0:
                sample_node = ivr_flow[0]
                print(f"Sample node: {sample_node.get('label', 'No label')}")
                if 'playPrompt' in sample_node:
                    print(f"  Voice files: {sample_node['playPrompt'][:2]}...")
                if 'branch' in sample_node:
                    print(f"  Branches: {list(sample_node['branch'].keys())}")
                    
        except Exception as e:
            conversion_time = time.time() - start_time
            result = {
                'script': script_name,
                'success': False,
                'time': conversion_time,
                'error': str(e),
                'issues': [f"Conversion failed: {e}"]
            }
            print(f"FAILED: {e}")
        
        results.append(result)
    
    total_time = time.time() - total_start_time
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    successful = sum(1 for r in results if r['success'])
    total_nodes = sum(r.get('nodes', 0) for r in results if r['success'])
    total_voice_files = sum(r.get('voice_files', 0) for r in results if r['success'])
    avg_time = sum(r['time'] for r in results if r['success']) / max(successful, 1)
    
    print(f"Success Rate: {successful}/{len(results)} ({successful/len(results)*100:.1f}%)")
    print(f"Total Time: {total_time:.3f}s")
    print(f"Average Time per Script: {avg_time:.3f}s")
    print(f"Total Nodes Generated: {total_nodes}")
    print(f"Total Voice Files Referenced: {total_voice_files}")
    
    print("\nPerformance by Script:")
    for result in results:
        status = "PASS" if result['success'] else "FAIL"
        time_str = f"{result['time']:.3f}s"
        if result['success']:
            print(f"  {status}: {result['script']} - {time_str} ({result['nodes']} nodes, {result['voice_files']} voices)")
        else:
            print(f"  {status}: {result['script']} - {time_str} (ERROR)")
    
    print("\nStructural Issues:")
    total_issues = sum(len(r.get('issues', [])) for r in results)
    if total_issues == 0:
        print("  No structural issues found - all scripts generate proper IVR structure!")
    else:
        for result in results:
            if result.get('issues'):
                print(f"  {result['script']}: {len(result['issues'])} issues")
    
    return results

if __name__ == "__main__":
    test_all_examples()