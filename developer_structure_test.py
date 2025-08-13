#!/usr/bin/env python3
"""
Developer Structure Validation Test Suite
Tests the 6 flows from mermaid_flows_test.txt to ensure our converter
generates code that matches the developer's expected structure patterns.
"""

import os
import json
import time
from typing import Dict, List, Any
from mermaid_ivr_converter import FlexibleARCOSConverter

class DeveloperStructureValidator:
    def __init__(self):
        self.converter = FlexibleARCOSConverter()
        self.test_results = []
        self.validation_issues = []
        
    def run_developer_structure_tests(self):
        """Run all 6 flows and validate against developer structure patterns"""
        print("DEVELOPER STRUCTURE VALIDATION SUITE")
        print("=" * 60)
        
        test_flows = [
            self.test_script8_inbound(),
            self.test_script5_inbound(),
            self.test_script11_inbound(),
            self.test_script6ob_outbound(),
            self.test_script7ob_outbound(),
            self.test_script11ob_outbound()
        ]
        
        for i, flow_data in enumerate(test_flows, 1):
            print(f"\nTEST {i}: {flow_data['name']}")
            print("-" * 50)
            
            try:
                # Convert the mermaid diagram
                result = self.converter.convert_mermaid_to_ivr(flow_data['mermaid'])
                
                # Validate structure
                validation = self.validate_developer_structure(result, flow_data)
                
                self.test_results.append({
                    'test_name': flow_data['name'],
                    'flow_type': flow_data['type'],
                    'result': result,
                    'validation': validation,
                    'timestamp': time.time()
                })
                
                # Report validation results
                if validation['structure_issues']:
                    self.validation_issues.extend(validation['structure_issues'])
                    print(f"STRUCTURE ISSUES FOUND: {len(validation['structure_issues'])}")
                    for issue in validation['structure_issues']:
                        print(f"   - {issue}")
                else:
                    print("✓ STRUCTURE VALIDATION PASSED")
                    
                print(f"Generated {validation['node_count']} nodes")
                print(f"Production features: {validation['production_features']}")
                
            except Exception as e:
                print(f"TEST FAILED: {e}")
                self.validation_issues.append(f"Test {i} failed with error: {e}")
        
        # Generate comprehensive report
        self.generate_validation_report()
        
        return len(self.validation_issues) == 0

    def test_script8_inbound(self) -> Dict:
        """REU Notification Script - Inbound"""
        return {
            'name': 'Script8 - REU Notification (Inbound)',
            'type': 'inbound',
            'description': 'Simple notification with confirmation',
            'expected_patterns': ['notification', 'confirmation', 'accept/replay', 'custom message'],
            'mermaid': '''flowchart TD
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
J --> F'''
        }

    def test_script5_inbound(self) -> Dict:
        """PIN Change Script - Inbound"""
        return {
            'name': 'Script5 - PIN Change (Inbound)',
            'type': 'inbound',
            'description': 'PIN change with validation and name recording',
            'expected_patterns': ['PIN validation', 'confirmation', 'name recording', 'retry logic'],
            'mermaid': '''flowchart TD
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
I -->|yes| K'''
        }

    def test_script11_inbound(self) -> Dict:
        """Test Contact Numbers - Inbound"""
        return {
            'name': 'Script11 - Test Contact Numbers (Inbound)',
            'type': 'inbound',
            'description': 'Contact number testing with multiple options',
            'expected_patterns': ['menu navigation', 'number testing', 'conditional logic', 'star key'],
            'mermaid': '''flowchart TD
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
M -->|invalid input - no input| F'''
        }

    def test_script6ob_outbound(self) -> Dict:
        """Fill Shift Pre-Arranged Callout - Outbound"""
        return {
            'name': 'Script6ob - Fill Shift Pre-Arranged (Outbound)',
            'type': 'outbound',
            'description': 'Pre-arranged callout with employee verification and confirmation',
            'expected_patterns': ['employee verification', 'PIN entry', 'callout details', 'confirmation patterns'],
            'mermaid': '''flowchart TD
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
O --> P'''
        }

    def test_script7ob_outbound(self) -> Dict:
        """REU Callout with Answering Machine - Outbound"""
        return {
            'name': 'Script7ob - REU Callout with Answering Machine (Outbound)',
            'type': 'outbound',
            'description': 'Callout with multiple types and answering machine detection',
            'expected_patterns': ['multiple callout types', 'answering machine', 'callback options', 'loop logic'],
            'mermaid': '''flowchart TD
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
G --> K["input – 1, 3, 7, or 9<br/>If 1, go to Employee Enter PIN on page 2.<br/>If 3, go to need more time on page 2.<br/>If 7, go to Employee Not Home on page 2.<br/>If 9, go to Repeat Message on page 2."]'''
        }

    def test_script11ob_outbound(self) -> Dict:
        """Automated TEST Callout - Outbound"""
        return {
            'name': 'Script11ob - Automated TEST Callout (Outbound)',
            'type': 'outbound',
            'description': 'Test callout with employee verification and PIN validation',
            'expected_patterns': ['test callout', 'employee verification', 'PIN validation', 'confirmation'],
            'mermaid': '''flowchart TD
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

    def validate_developer_structure(self, result: Any, flow_data: Dict) -> Dict:
        """Validate generated code against developer structure patterns"""
        if not result or len(result) < 2:
            return {
                'node_count': 0,
                'structure_issues': ['Conversion failed or returned empty result'],
                'production_features': []
            }
        
        ivr_flow = result[0] if isinstance(result, tuple) else result
        js_code = result[1] if isinstance(result, tuple) and len(result) > 1 else ""
        
        structure_issues = []
        production_features = []
        
        # Check for essential developer structure patterns
        self._validate_node_structure(ivr_flow, structure_issues, production_features)
        self._validate_flow_patterns(ivr_flow, flow_data, structure_issues)
        self._validate_production_features(ivr_flow, structure_issues, production_features)
        
        return {
            'node_count': len(ivr_flow),
            'structure_issues': structure_issues,
            'production_features': production_features,
            'js_code_length': len(js_code)
        }

    def _validate_node_structure(self, ivr_flow: List, structure_issues: List, production_features: List):
        """Validate basic node structure against developer patterns"""
        
        required_fields = ['label', 'playPrompt', 'playLog']
        node_types_found = set()
        
        for i, node in enumerate(ivr_flow):
            if not isinstance(node, dict):
                structure_issues.append(f"Node {i+1} is not a dictionary structure")
                continue
                
            # Check for required fields
            missing_fields = [field for field in required_fields if field not in node]
            if missing_fields:
                structure_issues.append(f"Node {i+1} missing required fields: {missing_fields}")
            
            # Identify node types
            if 'branch' in node:
                node_types_found.add('decision')
                if 'getDigits' in node:
                    production_features.append('Input collection with DTMF')
            elif 'goto' in node:
                node_types_found.add('goto')
            elif 'gosub' in node:
                node_types_found.add('gosub')
                production_features.append('Gosub calls for result saving')
                
            # Check for production-level features
            if 'maxLoop' in node:
                production_features.append('Loop control with maxLoop')
            if 'nobarge' in node:
                production_features.append('No-barge protection')
            if 'guard' in node:
                production_features.append('Conditional logic with guards')
            if 'branchOn' in node:
                production_features.append('Dynamic branching with branchOn')
                
        # Ensure we have diverse node types
        if len(node_types_found) < 2:
            structure_issues.append("Flow lacks diverse node types (decision, goto, gosub)")

    def _validate_flow_patterns(self, ivr_flow: List, flow_data: Dict, structure_issues: List):
        """Validate flow-specific patterns based on type"""
        
        flow_type = flow_data['type']
        expected_patterns = flow_data.get('expected_patterns', [])
        
        # Get all node labels and logs for pattern matching
        all_text = []
        for node in ivr_flow:
            if isinstance(node, dict):
                all_text.extend(node.get('playLog', []))
                if node.get('label'):
                    all_text.append(node.get('label'))
        
        combined_text = ' '.join(all_text).lower()
        
        # Check for expected patterns
        for pattern in expected_patterns:
            if pattern.lower() not in combined_text:
                structure_issues.append(f"Missing expected pattern '{pattern}' for {flow_type} flow")
        
        # Flow-specific validations
        if flow_type == 'outbound':
            # Outbound flows should have employee verification
            if not any('employee' in text.lower() for text in all_text):
                structure_issues.append("Outbound flow missing employee verification pattern")
                
            # Should have PIN entry for most outbound flows
            if 'pin' not in combined_text:
                structure_issues.append("Outbound flow missing PIN entry pattern")
                
        elif flow_type == 'inbound':
            # Inbound flows should have menu navigation patterns
            if not any('press' in text.lower() for text in all_text):
                structure_issues.append("Inbound flow missing menu navigation patterns")

    def _validate_production_features(self, ivr_flow: List, structure_issues: List, production_features: List):
        """Validate production-level features match developer expectations"""
        
        # Check for template variables (production feature)
        template_vars_found = False
        for node in ivr_flow:
            if isinstance(node, dict):
                prompts = node.get('playPrompt', [])
                if isinstance(prompts, list):
                    for prompt in prompts:
                        if '{{' in str(prompt) and '}}' in str(prompt):
                            template_vars_found = True
                            break
        
        if template_vars_found:
            production_features.append('Template variables ({{var}})')
        else:
            structure_issues.append("Missing template variables - not matching production patterns")
            
        # Check for proper error handling
        has_error_handling = any('Invalid Entry' in node.get('label', '') for node in ivr_flow if isinstance(node, dict))
        if has_error_handling:
            production_features.append('Error handling with Invalid Entry nodes')
        else:
            structure_issues.append("Missing proper error handling patterns")
            
        # Check for proper goodbye/disconnect pattern
        has_goodbye = any('goodbye' in node.get('label', '').lower() for node in ivr_flow if isinstance(node, dict))
        has_disconnect = any('disconnect' in node.get('label', '').lower() or 'hangup' in str(node.get('goto', '')).lower() for node in ivr_flow if isinstance(node, dict))
        
        if has_goodbye and has_disconnect:
            production_features.append('Proper goodbye/disconnect pattern')
        else:
            structure_issues.append("Missing proper goodbye/disconnect flow termination")

    def generate_validation_report(self):
        """Generate comprehensive validation report"""
        report_path = "developer_structure_validation_report.json"
        
        summary = {
            'total_tests': len(self.test_results),
            'tests_passed': len([t for t in self.test_results if not t['validation']['structure_issues']]),
            'tests_failed': len([t for t in self.test_results if t['validation']['structure_issues']]),
            'total_structure_issues': len(self.validation_issues),
            'structure_issues': self.validation_issues,
            'test_results': self.test_results,
            'timestamp': time.time()
        }
        
        with open(report_path, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"\nDEVELOPER STRUCTURE VALIDATION SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {summary['total_tests']}")
        print(f"Passed: {summary['tests_passed']}")
        print(f"Failed: {summary['tests_failed']}")
        print(f"Structure Issues: {summary['total_structure_issues']}")
        
        if self.validation_issues:
            print(f"\nSTRUCTURE ISSUES TO FIX:")
            for i, issue in enumerate(self.validation_issues, 1):
                print(f"   {i}. {issue}")
        
        print(f"\nFull validation report saved to: {report_path}")
        
        return summary

if __name__ == "__main__":
    validator = DeveloperStructureValidator()
    success = validator.run_developer_structure_tests()
    
    if success:
        print("\nSUCCESS: ALL DEVELOPER STRUCTURE VALIDATIONS PASSED!")
        print("Converter generates code matching developer expectations.")
    else:
        print("\nFAILED: STRUCTURE VALIDATION ISSUES FOUND!")
        print("Review the report and fix structural inconsistencies.")