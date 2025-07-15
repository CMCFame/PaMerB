"""
FIXED VERSION - mermaid_ivr_converter.py
This version fixes the NodeType.INPUT error and ensures proper IVR code generation
"""

import re
import csv
import json
import requests
import streamlit as st
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from difflib import SequenceMatcher

class NodeType(Enum):
    WELCOME = "welcome"
    DECISION = "decision" 
    ACTION = "action"
    PIN_ENTRY = "pin_entry"
    RESPONSE = "response"
    GOODBYE = "goodbye"
    ERROR = "error"
    SLEEP = "sleep"
    AVAILABILITY = "availability"
    INPUT = "input"  # FIXED: Added missing INPUT type

@dataclass
class VoiceFile:
    company: str
    folder: str
    file_name: str
    transcript: str
    callflow_id: str

class ProductionIVRConverter:
    def __init__(self, uploaded_csv_file=None):
        # Real voice file database (8,555 entries)
        self.voice_files: List[VoiceFile] = []
        self.transcript_index: Dict[str, List[VoiceFile]] = {}
        self.exact_match_index: Dict[str, VoiceFile] = {}
        
        # Load the database - either from uploaded file or fallback
        if uploaded_csv_file:
            self._load_database_from_upload(uploaded_csv_file)
        else:
            self._load_real_database()

    def _load_database_from_upload(self, uploaded_file):
        """Load database from uploaded cf_general_structure.csv file"""
        try:
            print(f"📥 Loading database from uploaded file: {uploaded_file.name}")
            
            # Read the uploaded CSV file
            import io
            content = uploaded_file.read()
            
            # Handle both bytes and string content
            if isinstance(content, bytes):
                content = content.decode('utf-8')
            
            # Parse CSV content
            csv_reader = csv.DictReader(io.StringIO(content))
            
            # Debug: Check column names
            fieldnames = csv_reader.fieldnames
            print(f"📋 CSV columns found: {fieldnames}")
            
            row_count = 0
            
            for row in csv_reader:
                row_count += 1
                
                # Extract callflow ID from file name (remove .ulaw extension)
                file_name = row.get('File Name', '')
                callflow_id = file_name.replace('.ulaw', '') if file_name else f"{row_count}"
                
                voice_file = VoiceFile(
                    company=row.get('Company', ''),
                    folder=row.get('Folder', ''),
                    file_name=file_name,
                    transcript=row.get('Transcript', ''),
                    callflow_id=callflow_id
                )
                
                self.voice_files.append(voice_file)
                
                # Index by transcript for exact matching
                transcript_clean = voice_file.transcript.lower().strip()
                if transcript_clean:
                    self.exact_match_index[transcript_clean] = voice_file
                    
                    # Also index individual words
                    words = transcript_clean.split()
                    for word in words:
                        if word not in self.transcript_index:
                            self.transcript_index[word] = []
                        self.transcript_index[word].append(voice_file)
            
            print(f"✅ Successfully loaded {row_count} voice files from uploaded CSV")
            
        except Exception as e:
            print(f"❌ Error loading database: {e}")
            self._load_fallback_database()

    def _load_real_database(self):
        """Load fallback database with common phrases"""
        fallback_data = [
            ("Welcome", "This is an automated callout", "1186"),
            ("Press", "Press", "PRESSNEU"),
            ("Thank you", "Thank you.", "MSG023"),
            ("Goodbye", "Goodbye.", "MSG003"),
            ("Invalid", "I'm sorry. That is an invalid entry. Please try again.", "MSG028"),
            ("Available", "All available.", "1111"),
        ]
        
        for company, transcript, callflow_id in fallback_data:
            voice_file = VoiceFile(
                company=company,
                folder="",
                file_name=f"{callflow_id}.ulaw",
                transcript=transcript,
                callflow_id=callflow_id
            )
            self.voice_files.append(voice_file)
            self.exact_match_index[transcript.lower().strip()] = voice_file

    def _load_fallback_database(self):
        """Load minimal fallback when CSV fails"""
        self._load_real_database()

    def _parse_mermaid_diagram(self, mermaid_code: str) -> Tuple[List[Dict], List[Dict]]:
        """Parse Mermaid diagram into nodes and connections"""
        nodes = []
        connections = []
        
        # Extract nodes with improved regex
        node_pattern = r'([A-Z]+)\s*\[\s*"([^"]+)"\s*\]|([A-Z]+)\s*\{\s*"([^"]+)"\s*\}'
        
        # Extract rectangular nodes (actions/prompts)
        for match in re.finditer(r'([A-Z]+)\s*\[\s*"([^"]+)"\s*\]', mermaid_code):
            node_id = match.group(1)
            node_text = match.group(2).replace('<br/>', '\n').replace('\\n', '\n')
            nodes.append({
                'id': node_id,
                'text': node_text,
                'type': self._determine_node_type(node_text),
                'shape': 'rectangle'
            })
            print(f"📦 Found rectangular node: {node_id} = '{node_text[:50]}...'")
        
        # Extract diamond nodes (decisions)
        for match in re.finditer(r'([A-Z]+)\s*\{\s*"([^"]+)"\s*\}', mermaid_code):
            node_id = match.group(1)
            node_text = match.group(2).replace('<br/>', '\n').replace('\\n', '\n')
            nodes.append({
                'id': node_id,
                'text': node_text,
                'type': NodeType.DECISION,
                'shape': 'diamond'
            })
            print(f"💎 Found diamond node: {node_id} = '{node_text[:50]}...'")
        
        # Extract connections with improved parsing
        connection_patterns = [
            r'([A-Z]+)\s*-->\s*\|"([^"]+)"\|\s*([A-Z]+)',  # A -->|"label"| B
            r'([A-Z]+)\s*-->\s*([A-Z]+)',                   # A --> B
            r'([A-Z]+)\s*-->\s*\|([^|]+)\|\s*([A-Z]+)',     # A -->|label| B
        ]
        
        for pattern in connection_patterns:
            for match in re.finditer(pattern, mermaid_code):
                source = match.group(1)
                if len(match.groups()) == 3:
                    if pattern.count('"') > 0:
                        label = match.group(2)
                        target = match.group(3)
                    else:
                        label = match.group(2) if '|' in pattern else ''
                        target = match.group(3) if '|' in pattern else match.group(2)
                else:
                    label = ''
                    target = match.group(2)
                
                connections.append({
                    'source': source,
                    'target': target,
                    'label': label
                })
                print(f"🔗 Found connection: {source} -> {target} ('{label}')")
        
        print(f"✅ Parsed {len(nodes)} nodes and {len(connections)} connections")
        return nodes, connections

    def _determine_node_type(self, text: str) -> NodeType:
        """Determine node type from text content"""
        text_lower = text.lower()
        
        # Welcome nodes - typically first nodes with greeting
        if any(phrase in text_lower for phrase in ["welcome", "this is an", "this is a", "automated"]):
            return NodeType.WELCOME
        
        # PIN entry nodes
        if any(phrase in text_lower for phrase in ["pin", "enter", "digits"]) and not "invalid" in text_lower:
            return NodeType.PIN_ENTRY
        
        # Availability questions - specific pattern
        if "available" in text_lower and any(phrase in text_lower for phrase in ["work", "callout", "press 1", "press 3"]):
            return NodeType.AVAILABILITY
        
        # Response/action nodes
        if any(phrase in text_lower for phrase in ["accepted", "decline", "response", "recorded"]):
            return NodeType.RESPONSE
        
        # Goodbye/disconnect nodes
        if any(phrase in text_lower for phrase in ["goodbye", "thank you", "disconnect"]):
            return NodeType.GOODBYE
        
        # Error/problem nodes
        if any(phrase in text_lower for phrase in ["invalid", "error", "problem", "try again"]):
            return NodeType.ERROR
        
        # Sleep/wait nodes
        if any(phrase in text_lower for phrase in ["more time", "continue", "press any key"]):
            return NodeType.SLEEP
        
        # Decision nodes - contain questions or simple yes/no choices
        if any(phrase in text_lower for phrase in ["?", "yes", "no", "correct"]) or len(text.split()) <= 5:
            return NodeType.DECISION
        
        # Default to action
        return NodeType.ACTION

    def _generate_meaningful_label(self, node_text: str, node_type: NodeType, node_id: str, all_nodes: List[Dict] = None) -> str:
        """Generate meaningful labels like allflows LITE (NOT A, B, C)"""
        
        if node_text:
            text_lower = node_text.lower()
            
            # Welcome/greeting nodes
            if "welcome" in text_lower or "this is" in text_lower or node_type == NodeType.WELCOME:
                return "Live Answer"
            
            # PIN entry
            if "pin" in text_lower and ("enter" in text_lower or "type" in text_lower or "digits" in text_lower):
                return "Enter PIN"
            
            # Availability questions
            if "available" in text_lower and "work" in text_lower:
                return "Offer"
            
            # Response actions
            if "accepted" in text_lower and ("response" in text_lower or "recorded" in text_lower):
                return "Accept"
            elif "decline" in text_lower and ("response" in text_lower or "recorded" in text_lower):
                return "Decline"
            elif "not home" in text_lower:
                return "Not Home"
            elif "qualified" in text_lower:
                return "Qualified No"
            
            # Sleep/wait
            if ("more time" in text_lower or "continue" in text_lower or "press any key" in text_lower):
                return "Sleep"
            
            # Goodbye
            if "goodbye" in text_lower:
                return "Goodbye"
            elif "disconnect" in text_lower:
                return "Disconnect"
            
            # Error/problems
            if "invalid" in text_lower and "entry" in text_lower:
                return "Invalid Entry"
            elif "problem" in text_lower or "error" in text_lower:
                return "Problems"
            
            # Callout information nodes
            if "electric callout" in text_lower:
                return "Live Answer 1"
            elif "callout reason" in text_lower:
                return "Callout Reason"
            elif "trouble location" in text_lower:
                return "Trouble Location"
            elif "custom message" in text_lower:
                return "Custom Message"
            
            # Decision nodes (short questions)
            if node_type == NodeType.DECISION or "?" in node_text:
                if "correct" in text_lower and "pin" in text_lower:
                    return "Check PIN"
                elif "this is employee" in text_lower or "employee" in text_lower:
                    return "Live Answer 2"
                elif len(node_text.split()) <= 4:
                    # Capitalize first letter of each word
                    return ' '.join(word.capitalize() for word in node_text.split())

            # Fallback: Generate from first few meaningful words
            words = re.findall(r'\b[A-Za-z]+\b', node_text)
            if words:
                meaningful_words = [w for w in words[:3] if len(w) > 2 and w.lower() not in ['the', 'and', 'for', 'you', 'this', 'that', 'is', 'a']]
                if meaningful_words:
                    return ' '.join(word.capitalize() for word in meaningful_words)
        
        # Last resort: Use node type and ID
        return f"{node_type.value.replace('_', ' ').title()}_{node_id}"

    def _create_ivr_node(self, node: Dict, connections: List[Dict], label: str, node_id_to_label: Dict[str, str] = None) -> Dict[str, Any]:
        """Create IVR node following allflows LITE patterns"""
        text = node['text']
        node_type = node['type']
        
        # Create base node following allflows property order
        ivr_node = {'label': label}
        
        # Add log based on text content
        ivr_node['log'] = text.replace('\n', ' ').strip()
        
        # Add playPrompt - use callflow:node_id for now
        ivr_node['playPrompt'] = f"callflow:{node['id']}"
        
        # Add interaction logic based on node type
        if node_type in [NodeType.WELCOME, NodeType.AVAILABILITY, NodeType.DECISION, NodeType.PIN_ENTRY]:
            # FIXED: Removed NodeType.INPUT from this check since it was causing the error
            self._add_input_logic(ivr_node, connections, node, node_id_to_label)
        elif node_type == NodeType.RESPONSE:
            self._add_response_logic(ivr_node, label)
        
        # Add goto for nodes with a single, unconditional path
        if len(connections) == 1 and not ivr_node.get('branch'):
            target_id = connections[0]['target']
            target_label = node_id_to_label.get(target_id, self._generate_meaningful_label("", NodeType.ACTION, target_id))
            ivr_node['goto'] = target_label

        return ivr_node

    def _add_input_logic(self, ivr_node: Dict, connections: List[Dict], node: Dict, node_id_to_label: Dict[str, str] = None):
        """Add getDigits and branch logic"""
        if not connections:
            return
        
        # Determine valid choices from connection labels
        valid_choices = []
        branch_map = {}
        
        for conn in connections:
            label = conn.get('label', '').lower()
            target = conn['target']
            target_label = node_id_to_label.get(target, self._generate_meaningful_label("", NodeType.ACTION, target))
            
            print(f"🔀 Processing connection label: '{label}' -> {target} ({target_label})")
            
            # Extract digit from various label formats
            digit_match = re.search(r'\b(\d+)\b', label)
            if digit_match:
                choice = digit_match.group(1)
                valid_choices.append(choice)
                branch_map[choice] = target_label
            elif any(phrase in label for phrase in ['no input', 'timeout', 'none']):
                branch_map['none'] = target_label
            elif any(phrase in label for phrase in ['invalid', 'error', 'retry', 'no']):
                branch_map['error'] = target_label
            elif 'yes' in label:
                # Direct connection for PIN verification, etc.
                ivr_node['goto'] = target_label
                return
        
        # Only add getDigits if we found valid numeric choices
        if valid_choices:
            ivr_node['getDigits'] = {
                'numDigits': 1,
                'maxTime': 7,
                'maxTries': 3,
                'validChoices': '|'.join(sorted(set(valid_choices))),
                'errorPrompt': 'callflow:1009',
                'nonePrompt': 'callflow:1009',
            }
            
            # Add error/none handling if not already specified
            if 'error' not in branch_map:
                branch_map['error'] = 'Problems'
            if 'none' not in branch_map:
                branch_map['none'] = branch_map['error']
            
            ivr_node['branch'] = branch_map
            print(f"✅ Added input logic: choices={valid_choices}, branches={branch_map}")

    def _add_response_logic(self, ivr_node: Dict, label: str):
        """Add gosub for response handling like allflows LITE"""
        label_lower = label.lower()
        if 'accept' in label_lower:
            ivr_node['gosub'] = ['SaveCallResult', 1001, 'Accept']
        elif 'decline' in label_lower:
            ivr_node['gosub'] = ['SaveCallResult', 1002, 'Decline']
        elif 'not home' in label_lower:
            ivr_node['gosub'] = ['SaveCallResult', 1006, 'NotHome']
        elif 'qualified' in label_lower:
            ivr_node['gosub'] = ['SaveCallResult', 1145, 'QualNo']
        else:
            # If it's a response node without a clear action, just go to Goodbye
            ivr_node['goto'] = 'Goodbye'

    def convert_mermaid_to_ivr(self, mermaid_code: str, uploaded_csv_file=None) -> Tuple[List[Dict[str, Any]], List[str]]:
        """Main conversion method - PRODUCTION READY WITH DEBUGGING"""
        notes = []
        
        try:
            print(f"🚀 Starting conversion of Mermaid diagram...")
            print(f"📝 Input length: {len(mermaid_code)} characters")
            
            # Parse Mermaid diagram
            nodes, connections = self._parse_mermaid_diagram(mermaid_code)
            notes.append(f"Parsed {len(nodes)} nodes and {len(connections)} connections")
            
            if not nodes:
                notes.append("❌ No nodes found in diagram - check Mermaid syntax")
                print("❌ PARSING FAILED - No nodes extracted")
                return self._create_fallback_flow(), notes
            
            print(f"✅ Successfully parsed {len(nodes)} nodes")
            
            # Create a mapping of node IDs to meaningful labels
            node_id_to_label = {}
            used_labels = set()
            
            for node in nodes:
                base_label = self._generate_meaningful_label(node['text'], node['type'], node['id'], nodes)
                
                # Handle duplicate labels by adding suffix
                final_label = base_label
                counter = 1
                while final_label in used_labels:
                    final_label = f"{base_label} {counter}"
                    counter += 1
                
                node_id_to_label[node['id']] = final_label
                used_labels.add(final_label)
                print(f"🏷️ {node['id']} -> '{final_label}' ({node['type'].value})")
            
            # Generate IVR nodes with meaningful labels
            ivr_nodes = []
            
            for node in nodes:
                print(f"\n🔄 Processing node {node['id']}: {node['text'][:50]}...")
                
                # Get the meaningful label
                label = node_id_to_label[node['id']]
                
                # Get connections for this node
                node_connections = [c for c in connections if c['source'] == node['id']]
                print(f"🔗 Found {len(node_connections)} outgoing connections")
                
                # Create IVR node with node mapping for better branch labels
                ivr_node = self._create_ivr_node(node, node_connections, label, node_id_to_label)
                ivr_nodes.append(ivr_node)
                
                notes.append(f"Generated node: {label}")
                print(f"✅ Generated IVR node: {label}")
            
            # Add standard termination nodes if not present
            if not any(node.get('label') == 'Problems' for node in ivr_nodes):
                ivr_nodes.append({
                    'label': 'Problems',
                    'log': 'Error handler - invalid input or system error',
                    'playPrompt': 'callflow:1351',
                    'goto': 'Goodbye'
                })
                notes.append("Added standard 'Problems' error handler")
            
            if not any(node.get('label') == 'Goodbye' for node in ivr_nodes):
                ivr_nodes.append({
                    'label': 'Goodbye',
                    'log': 'Thank you goodbye',
                    'playPrompt': 'callflow:1029',
                    'goto': 'hangup'
                })
                notes.append("Added standard 'Goodbye' termination")
            
            notes.append(f"✅ Generated {len(ivr_nodes)} production-ready IVR nodes")
            print(f"🎉 CONVERSION SUCCESSFUL - Generated {len(ivr_nodes)} nodes")
            
            return ivr_nodes, notes
            
        except Exception as e:
            error_msg = f"❌ Conversion failed: {str(e)}"
            notes.append(error_msg)
            print(error_msg)
            import traceback
            traceback.print_exc()
            return self._create_fallback_flow(), notes

    def _create_fallback_flow(self) -> List[Dict[str, Any]]:
        """Create fallback flow for errors"""
        return [
            {
                'label': 'Problems',
                'log': 'Error handler',
                'playPrompt': 'callflow:1351',
                'goto': 'Goodbye'
            },
            {
                'label': 'Goodbye',
                'log': 'Thank you goodbye',
                'playPrompt': 'callflow:1029',
                'goto': 'hangup'
            }
        ]

# Main function for the app
def convert_mermaid_to_ivr(mermaid_code: str, uploaded_csv_file=None) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Production-ready conversion function with optional CSV upload"""
    converter = ProductionIVRConverter(uploaded_csv_file)
    return converter.convert_mermaid_to_ivr(mermaid_code)