#!/usr/bin/env python3
"""
Automated Test Suite for IVR Converter
Tests multiple call flow scenarios until we get proper code structure
"""

import os
import json
import time
from typing import Dict, List, Any
from mermaid_ivr_converter import FlexibleARCOSConverter

class IVRTestSuite:
    def __init__(self):
        self.converter = FlexibleARCOSConverter()
        self.test_results = []
        self.critical_issues = []
        
    def run_automated_tests(self):
        """Run automated tests on multiple call flow scenarios"""
        print("STARTING AUTOMATED IVR TEST SUITE")
        print("=" * 60)
        
        test_scenarios = [
            self.test_electric_callout_flow(),
            self.test_emergency_callout_flow(),
            self.test_maintenance_callout_flow(), 
            self.test_supervisor_notification_flow(),
            self.test_simple_inbound_flow()
        ]
        
        for i, scenario in enumerate(test_scenarios, 1):
            print(f"\nTEST {i}: {scenario['name']}")
            print("-" * 40)
            
            try:
                # Convert the mermaid diagram
                result = self.converter.convert_mermaid_to_ivr(scenario['mermaid'])
                
                # Analyze the result
                analysis = self.analyze_conversion_result(result, scenario)
                
                self.test_results.append({
                    'test_name': scenario['name'],
                    'scenario': scenario,
                    'result': result,
                    'analysis': analysis,
                    'timestamp': time.time()
                })
                
                # Check for critical issues
                if analysis['critical_issues']:
                    self.critical_issues.extend(analysis['critical_issues'])
                    print(f"CRITICAL ISSUES FOUND: {len(analysis['critical_issues'])}")
                    for issue in analysis['critical_issues']:
                        print(f"   - {issue}")
                else:
                    print("NO CRITICAL ISSUES DETECTED")
                    
                print(f"Generated {analysis['node_count']} nodes")
                print(f"DTMF mappings: {analysis['dtmf_mappings']}")
                print(f"gosub calls: {analysis['gosub_count']}")
                
            except Exception as e:
                print(f"TEST FAILED: {e}")
                self.critical_issues.append(f"Test {i} failed with error: {e}")
        
        # Generate comprehensive report
        self.generate_test_report()
        
        return len(self.critical_issues) == 0
    
    def test_electric_callout_flow(self) -> Dict:
        """Test the electric callout flow from user's example"""
        return {
            'name': 'Electric Callout Flow',
            'description': 'Standard electric callout with employee verification',
            'expected_features': ['PIN verification', 'DTMF choices 1,3,7,9', 'Accept/Decline flow'],
            'mermaid': '''flowchart TD
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
L -->|"1 - accept"| M["Accepted Response<br/>An accepted response has<br/>been recorded."]
L -->|"3 - decline"| N["Callout Decline<br/>Your response is being recorded as a decline."]
L -->|"9 - call back"| O["Qualified No<br/>You may be called again on this<br/>callout if no one accepts."]
M --> P["Goodbye<br/>Thank you.<br/>Goodbye."]
N --> P
O --> P
P --> Q["Disconnect"]
D --> Q'''
        }
    
    def test_emergency_callout_flow(self) -> Dict:
        """Test emergency callout flow"""
        return {
            'name': 'Emergency Callout Flow',
            'description': 'High-priority emergency callout with immediate response',
            'expected_features': ['Immediate response', 'No PIN required', 'Accept only'],
            'mermaid': '''flowchart TD
A["EMERGENCY CALLOUT<br/>This is an EMERGENCY callout.<br/>Press 1 to accept immediately.<br/>Press 9 to repeat this message."] -->|"1 - immediate accept"| B["Emergency Accept<br/>You have accepted this emergency callout.<br/>Report immediately."]
A -->|"9 - repeat"| A
A -->|"no response"| C["No Response<br/>No response recorded for emergency callout."]
B --> D["Goodbye<br/>Thank you.<br/>Goodbye."]
C --> D
D --> E["Disconnect"]'''
        }
    
    def test_maintenance_callout_flow(self) -> Dict:
        """Test maintenance callout flow"""
        return {
            'name': 'Maintenance Callout Flow', 
            'description': 'Scheduled maintenance callout with time options',
            'expected_features': ['Time selection', 'Maintenance specific prompts', 'Scheduling'],
            'mermaid': '''flowchart TD
A["Maintenance Callout<br/>Scheduled maintenance required.<br/>Press 1 if available now.<br/>Press 2 if available in 2 hours.<br/>Press 3 to decline."] -->|"1 - now"| B["Accept Now<br/>You will perform maintenance now."]
A -->|"2 - later"| C["Accept Later<br/>You will perform maintenance in 2 hours."]
A -->|"3 - decline"| D["Decline<br/>Maintenance declined."]
B --> E["Goodbye<br/>Thank you.<br/>Goodbye."]
C --> E
D --> E
E --> F["Disconnect"]'''
        }
    
    def test_supervisor_notification_flow(self) -> Dict:
        """Test supervisor notification flow"""
        return {
            'name': 'Supervisor Notification Flow',
            'description': 'Supervisor acknowledgment with escalation options',
            'expected_features': ['Supervisor acknowledgment', 'Escalation paths', 'Authority checks'],
            'mermaid': '''flowchart TD
A["Supervisor Notification<br/>Critical situation requires supervisor attention.<br/>Press 1 to acknowledge.<br/>Press 2 to escalate to upper management.<br/>Press 3 for more information."] -->|"1 - acknowledge"| B["Acknowledged<br/>Supervisor acknowledgment recorded."]
A -->|"2 - escalate"| C["Escalation<br/>Escalating to upper management."]
A -->|"3 - info"| D["More Info<br/>Additional information about the situation."]
D -->|"return"| A
B --> E["Goodbye<br/>Thank you.<br/>Goodbye."]
C --> E
E --> F["Disconnect"]'''
        }
    
    def test_simple_inbound_flow(self) -> Dict:
        """Test simple inbound flow"""
        return {
            'name': 'Simple Inbound Flow',
            'description': 'Basic inbound call handling',
            'expected_features': ['Employee login', 'PIN verification', 'Main menu'],
            'mermaid': '''flowchart TD
A["Welcome<br/>Welcome to the callout system.<br/>Please enter your employee ID."] -->|"id entered"| B["Enter PIN<br/>Please enter your 4-digit PIN."]
A -->|"invalid id"| C["Invalid ID<br/>Invalid employee ID. Please try again."]
C -->|"retry"| A
B -->|"correct pin"| D["Main Menu<br/>Press 1 for current callouts.<br/>Press 2 for availability status.<br/>Press 3 to exit."]
B -->|"incorrect pin"| C
D -->|"1 - callouts"| E["Current Callouts<br/>You have no active callouts."]
D -->|"2 - status"| F["Availability Status<br/>You are currently available."]
D -->|"3 - exit"| G["Goodbye<br/>Thank you.<br/>Goodbye."]
E --> D
F --> D
G --> H["Disconnect"]'''
        }
    
    def analyze_conversion_result(self, result: Any, scenario: Dict) -> Dict:
        """Analyze conversion result for critical issues"""
        if not result or len(result) < 2:
            return {
                'node_count': 0,
                'critical_issues': ['Conversion failed or returned empty result'],
                'dtmf_mappings': {},
                'gosub_count': 0
            }
        
        ivr_flow = result[0] if isinstance(result, tuple) else result
        js_code = result[1] if isinstance(result, tuple) and len(result) > 1 else ""
        
        critical_issues = []
        dtmf_mappings = {}
        gosub_count = 0
        
        # Analyze nodes
        for node in ivr_flow:
            if isinstance(node, dict):
                # Check for gosub calls
                if 'gosub' in node:
                    gosub_count += 1
                
                # Check for DTMF mappings
                if 'branch' in node:
                    for key, value in node['branch'].items():
                        if key.isdigit():
                            dtmf_mappings[key] = value
                
                # Check for critical mapping issues
                label = node.get('label', '')
                if 'Live Answer' in label or 'Welcome' in label:
                    branch = node.get('branch', {})
                    if '1' in branch:
                        target = branch['1']
                        # Check if choice 1 leads to proper verification
                        verification_keywords = ['pin', 'verify', 'enter', 'employee', 'check']
                        if not any(keyword in target.lower() for keyword in verification_keywords):
                            critical_issues.append(f"Choice 1 maps to '{target}' instead of verification flow")
        
        # Check for missing essential flows
        node_labels = [node.get('label', '') for node in ivr_flow if isinstance(node, dict)]
        
        if scenario['name'] == 'Electric Callout Flow':
            # Electric callout specific checks - trace the actual flow path
            has_employee_verification = any('employee' in label.lower() and 'verification' in node.get('log', '').lower() for node in ivr_flow if isinstance(node, dict))
            has_pin_entry = any(('pin' in label.lower() and 'enter' in label.lower()) or 
                           ('pin' in node.get('log', '').lower() and 'enter' in label.lower()) for node in ivr_flow if isinstance(node, dict) for label in [node.get('label', '')])
            
            # Check if welcome node correctly maps choice 1 to Employee
            welcome_node = None
            employee_node = None
            
            for node in ivr_flow:
                if isinstance(node, dict):
                    label = node.get('label', '').lower()
                    if 'live answer' in label or 'welcome' in label:
                        welcome_node = node
                    elif 'employee' in label and 'branch' in node:
                        employee_node = node
            
            # Verify the flow path
            if welcome_node and 'branch' in welcome_node:
                choice_1_target = welcome_node['branch'].get('1', '')
                if choice_1_target.lower() != 'employee':
                    critical_issues.append(f"Welcome node choice 1 should map to 'Employee', but maps to '{choice_1_target}'")
            
            if employee_node:
                # Employee node should be a decision node with yes/no branches
                branch = employee_node.get('branch', {})
                if 'yes' not in branch:
                    critical_issues.append("Employee verification node missing 'yes' branch")
                elif 'enter' not in branch['yes'].lower():
                    critical_issues.append(f"Employee verification 'yes' should lead to PIN entry, but leads to '{branch['yes']}'")
            else:
                critical_issues.append("Missing employee verification decision node")
            
            if not has_pin_entry:
                critical_issues.append("Missing PIN entry node")
            
            # The flow is correct if: Welcome(1)->Employee(yes)->Enter(PIN)->...->Accept
            # We should NOT flag this as bypassing verification anymore
        
        return {
            'node_count': len(ivr_flow),
            'critical_issues': critical_issues,
            'dtmf_mappings': dtmf_mappings,
            'gosub_count': gosub_count,
            'node_labels': node_labels
        }
    
    def generate_test_report(self):
        """Generate comprehensive test report"""
        report_path = "automated_test_report.json"
        
        summary = {
            'total_tests': len(self.test_results),
            'tests_passed': len([t for t in self.test_results if not t['analysis']['critical_issues']]),
            'tests_failed': len([t for t in self.test_results if t['analysis']['critical_issues']]),
            'total_critical_issues': len(self.critical_issues),
            'critical_issues': self.critical_issues,
            'test_results': self.test_results,
            'timestamp': time.time()
        }
        
        with open(report_path, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"\nAUTOMATED TEST SUITE SUMMARY")
        print("=" * 50)
        print(f"Total Tests: {summary['total_tests']}")
        print(f"Passed: {summary['tests_passed']}")
        print(f"Failed: {summary['tests_failed']}")
        print(f"Critical Issues: {summary['total_critical_issues']}")
        
        if self.critical_issues:
            print(f"\nCRITICAL ISSUES TO FIX:")
            for i, issue in enumerate(self.critical_issues, 1):
                print(f"   {i}. {issue}")
        
        print(f"\nFull report saved to: {report_path}")
        
        return summary

if __name__ == "__main__":
    test_suite = IVRTestSuite()
    success = test_suite.run_automated_tests()
    
    if success:
        print("\nALL TESTS PASSED! Converter is working correctly.")
    else:
        print("\nTESTS REVEALED ISSUES. Check the report for details.")