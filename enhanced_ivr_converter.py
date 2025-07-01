"""
Enhanced IVR Converter with Intelligent Audio Mapping
Replaces placeholder system with data-driven audio ID mapping
Integrates with AudioMapper to generate real IVR configurations
"""

import re
import json
from typing import List, Dict, Any, Optional, Tuple
import logging

from audio_database_manager import AudioDatabaseManager
from audio_mapper import AudioMapper, AudioMapping
from parse_mermaid import MermaidParser, Node, Edge
from segment_parser import SegmentParser

class EnhancedIVRConverter:
    """
    Enhanced IVR converter that generates real audio IDs instead of placeholders
    Implements the complete workflow: Mermaid → Text Analysis → Audio Mapping → IVR Code
    """
    
    def __init__(self, audio_database_path: str, config: Optional[Dict[str, Any]] = None):
        # Initialize components
        self.db_manager = AudioDatabaseManager(audio_database_path)
        self.audio_mapper = AudioMapper(self.db_manager)
        self.mermaid_parser = MermaidParser()
        self.logger = logging.getLogger(__name__)
        
        # Configuration
        self.config = {
            'defaultMaxTries': 3,
            'defaultMaxTime': 7,
            'defaultErrorPrompt': "callflow:1009",
            'defaultTimeoutPrompt': "callflow:1010",
            'defaultTimeout': 5000,
            'company': 'arcos',  # Default company
            'schema': None       # Default schema
        }
        if config:
            self.config.update(config)
        
        # Standard IVR response mappings (from openai_ivr_converter.py)
        self.standard_responses = {
            'accept': {'code': 1001, 'text': 'Accept'},
            'decline': {'code': 1002, 'text': 'Decline'},
            'not_home': {'code': 1006, 'text': 'NotHome'},
            'qualified_no': {'code': 1145, 'text': 'QualNo'},
            'error': {'code': 1198, 'text': 'Error Out'}
        }
        
        # Node type mappings for IVR generation
        self.ivr_node_generators = {
            'START': self._generate_start_node,
            'END': self._generate_end_node,
            'ACTION': self._generate_action_node,
            'DECISION': self._generate_decision_node,
            'INPUT': self._generate_input_node,
            'TRANSFER': self._generate_transfer_node,
            'MENU': self._generate_menu_node,
            'PROMPT': self._generate_prompt_node,
            'ERROR': self._generate_error_node
        }
    
    def convert_mermaid_to_ivr(self, mermaid_code: str, company: str = None, schema: str = None) -> Tuple[str, Dict]:
        """
        Convert Mermaid diagram to IVR JavaScript configuration
        
        Args:
            mermaid_code: Mermaid diagram text
            company: Company context for audio mapping
            schema: Schema context for audio mapping
            
        Returns:
            Tuple of (IVR JavaScript code, conversion report)
        """
        self.logger.info("Starting Mermaid to IVR conversion")
        
        # Use provided context or defaults
        conversion_company = company or self.config['company']
        conversion_schema = schema or self.config['schema']
        
        try:
            # Parse Mermaid diagram
            parsed_diagram = self.mermaid_parser.parse(mermaid_code)
            nodes = parsed_diagram['nodes']
            edges = parsed_diagram['edges']
            
            self.logger.info(f"Parsed {len(nodes)} nodes and {len(edges)} edges")
            
            # Convert nodes to IVR format
            ivr_nodes = []
            conversion_report = {
                'total_nodes': len(nodes),
                'successful_mappings': 0,
                'failed_mappings': 0,
                'missing_audio': [],
                'node_reports': {}
            }
            
            for node_id, node in nodes.items():
                try:
                    ivr_node, node_report = self._convert_node_to_ivr(
                        node, edges, conversion_company, conversion_schema
                    )
                    
                    if ivr_node:
                        ivr_nodes.append(ivr_node)
                        conversion_report['successful_mappings'] += 1
                        
                        # Track missing audio
                        if 'audio_mapping' in node_report and node_report['audio_mapping'].missing_segments:
                            conversion_report['missing_audio'].extend(node_report['audio_mapping'].missing_segments)
                    else:
                        conversion_report['failed_mappings'] += 1
                    
                    conversion_report['node_reports'][node_id] = node_report
                    
                except Exception as e:
                    self.logger.error(f"Failed to convert node {node_id}: {e}")
                    conversion_report['failed_mappings'] += 1
                    conversion_report['node_reports'][node_id] = {'error': str(e)}
            
            # Generate JavaScript code
            js_code = self._generate_javascript_module(ivr_nodes)
            
            # Summary
            conversion_report['unique_missing_audio'] = list(set(conversion_report['missing_audio']))
            conversion_report['overall_success_rate'] = (
                conversion_report['successful_mappings'] / conversion_report['total_nodes']
                if conversion_report['total_nodes'] > 0 else 0.0
            )
            
            self.logger.info(f"Conversion complete: {conversion_report['successful_mappings']}/{conversion_report['total_nodes']} nodes successful")
            
            return js_code, conversion_report
            
        except Exception as e:
            self.logger.error(f"Conversion failed: {e}")
            raise
    
    def _convert_node_to_ivr(self, node: Node, edges: List[Edge], company: str, schema: str) -> Tuple[Optional[Dict], Dict]:
        """Convert a single Mermaid node to IVR format"""
        node_type = node.node_type.name if hasattr(node.node_type, 'name') else str(node.node_type)
        
        # Get node connections
        outgoing_edges = [e for e in edges if e.from_id == node.id]
        
        # Map text to audio
        audio_mapping = self.audio_mapper.map_text_to_audio(node.raw_text, company, schema)
        
        # Generate IVR node based on type
        generator = self.ivr_node_generators.get(node_type, self._generate_action_node)
        ivr_node = generator(node, outgoing_edges, audio_mapping)
        
        # Report
        node_report = {
            'node_id': node.id,
            'node_type': node_type,
            'original_text': node.raw_text,
            'audio_mapping': audio_mapping,
            'success': ivr_node is not None
        }
        
        return ivr_node, node_report
    
    def _generate_start_node(self, node: Node, edges: List[Edge], audio_mapping: AudioMapping) -> Dict:
        """Generate start node"""
        return {
            'label': node.id,
            'log': ' '.join(audio_mapping.play_log),
            'playPrompt': audio_mapping.play_prompt,
            'goto': edges[0].to_id if edges else 'End'
        }
    
    def _generate_end_node(self, node: Node, edges: List[Edge], audio_mapping: AudioMapping) -> Dict:
        """Generate end node"""
        return {
            'label': node.id,
            'log': ' '.join(audio_mapping.play_log) or 'End of call',
            'playPrompt': audio_mapping.play_prompt or ['callflow:1029'],  # Default goodbye
            'nobarge': '1'
        }
    
    def _generate_action_node(self, node: Node, edges: List[Edge], audio_mapping: AudioMapping) -> Dict:
        """Generate action/prompt node"""
        base_node = {
            'label': node.id,
            'log': ' '.join(audio_mapping.play_log),
            'playPrompt': audio_mapping.play_prompt
        }
        
        # Add navigation
        if edges:
            if len(edges) == 1:
                base_node['goto'] = edges[0].to_id
            else:
                # Multiple edges, might need branching
                base_node.update(self._create_branching_logic(edges))
        
        return base_node
    
    def _generate_decision_node(self, node: Node, edges: List[Edge], audio_mapping: AudioMapping) -> Dict:
        """Generate decision node with input handling"""
        base_node = {
            'label': node.id,
            'log': ' '.join(audio_mapping.play_log),
            'playPrompt': audio_mapping.play_prompt
        }
        
        # Add input collection
        input_config = self._create_input_config(node, edges)
        if input_config:
            base_node.update(input_config)
        
        # Add branching logic
        branching_logic = self._create_branching_logic(edges)
        if branching_logic:
            base_node.update(branching_logic)
        
        return base_node
    
    def _generate_input_node(self, node: Node, edges: List[Edge], audio_mapping: AudioMapping) -> Dict:
        """Generate input collection node"""
        return self._generate_decision_node(node, edges, audio_mapping)
    
    def _generate_menu_node(self, node: Node, edges: List[Edge], audio_mapping: AudioMapping) -> Dict:
        """Generate menu node"""
        return self._generate_decision_node(node, edges, audio_mapping)
    
    def _generate_prompt_node(self, node: Node, edges: List[Edge], audio_mapping: AudioMapping) -> Dict:
        """Generate prompt node"""
        return self._generate_action_node(node, edges, audio_mapping)
    
    def _generate_transfer_node(self, node: Node, edges: List[Edge], audio_mapping: AudioMapping) -> Dict:
        """Generate transfer node"""
        return {
            'label': node.id,
            'log': ' '.join(audio_mapping.play_log),
            'playPrompt': audio_mapping.play_prompt,
            'transfer': True,
            'goto': edges[0].to_id if edges else 'End'
        }
    
    def _generate_error_node(self, node: Node, edges: List[Edge], audio_mapping: AudioMapping) -> Dict:
        """Generate error handling node"""
        return {
            'label': node.id,
            'log': ' '.join(audio_mapping.play_log) or "Error handler",
            'playPrompt': audio_mapping.play_prompt or ['callflow:1351'],
            'nobarge': '1',
            'goto': edges[0].to_id if edges else 'End'
        }
    
    def _create_input_config(self, node: Node, edges: List[Edge]) -> Dict:
        """Create getDigits configuration"""
        # Analyze edges to determine expected inputs
        valid_choices = []
        
        for edge in edges:
            if edge.label:
                # Extract digit from label
                digit_match = re.search(r'\b(\d+)\b', edge.label)
                if digit_match:
                    valid_choices.append(digit_match.group(1))
        
        if valid_choices:
            return {
                'getDigits': {
                    'numDigits': 1,
                    'maxTries': self.config['defaultMaxTries'],
                    'maxTime': self.config['defaultMaxTime'],
                    'validChoices': '|'.join(sorted(set(valid_choices))),
                    'errorPrompt': self.config['defaultErrorPrompt'],
                    'timeoutPrompt': self.config['defaultTimeoutPrompt']
                }
            }
        
        return {}
    
    def _create_branching_logic(self, edges: List[Edge]) -> Dict:
        """Create branch configuration from edges"""
        if not edges:
            return {}
        
        branch = {}
        
        for edge in edges:
            if edge.label:
                # Parse edge label for conditions
                condition = self._parse_edge_condition(edge.label)
                if condition:
                    branch[condition] = edge.to_id
                else:
                    # Default fallback
                    if 'error' not in branch:
                        branch['error'] = edge.to_id
            else:
                # Unlabeled edge - use as default
                if 'none' not in branch:
                    branch['none'] = edge.to_id
        
        # Add standard error handling if not present
        if 'error' not in branch and edges:
            branch['error'] = 'Problems'
        
        if branch:
            return {'branch': branch}
        
        return {}
    
    def _parse_edge_condition(self, label: str) -> Optional[str]:
        """Parse edge label to extract condition"""
        if not label:
            return None
        
        label_lower = label.lower().strip()
        
        # Digit conditions
        digit_match = re.search(r'\b(\d+)\b', label)
        if digit_match:
            return digit_match.group(1)
        
        # Special conditions
        if any(keyword in label_lower for keyword in ['yes', 'accept', 'available']):
            return '1'
        elif any(keyword in label_lower for keyword in ['no', 'decline', 'unavailable']):
            return '2'
        elif any(keyword in label_lower for keyword in ['not home', 'absent']):
            return '7'
        elif any(keyword in label_lower for keyword in ['repeat', 'again']):
            return '9'
        elif any(keyword in label_lower for keyword in ['more time', 'wait']):
            return '3'
        elif any(keyword in label_lower for keyword in ['error', 'invalid', 'timeout']):
            return 'error'
        elif any(keyword in label_lower for keyword in ['no input', 'none']):
            return 'none'
        
        return None
    
    def _generate_javascript_module(self, ivr_nodes: List[Dict]) -> str:
        """Generate JavaScript module from IVR nodes"""
        if not ivr_nodes:
            return self._generate_empty_module()
        
        # Convert to formatted JSON
        try:
            json_str = json.dumps(ivr_nodes, indent=2, ensure_ascii=False)
            
            # Format as JavaScript module
            js_code = f"module.exports = {json_str};"
            
            # Add header comment
            header = '''/**
 * IVR Configuration - Generated by Enhanced IVR Converter
 * This file contains the call flow logic with real audio file mappings
 * Audio IDs are mapped from the transcription database
 */

'''
            
            return header + js_code
            
        except Exception as e:
            self.logger.error(f"Failed to generate JavaScript: {e}")
            return self._generate_empty_module()
    
    def _generate_empty_module(self) -> str:
        """Generate empty/error module"""
        return '''/**
 * IVR Configuration - Error Handler
 */

module.exports = [
  {
    "label": "Problems",
    "log": "Error in call flow generation",
    "playPrompt": ["callflow:1351"],
    "nobarge": "1",
    "goto": "End"
  },
  {
    "label": "End",
    "log": "End of call",
    "playPrompt": ["callflow:1029"],
    "nobarge": "1"
  }
];'''
    
    def generate_conversion_report(self, report_data: Dict) -> str:
        """Generate human-readable conversion report"""
        lines = []
        lines.append("=== IVR Conversion Report ===")
        lines.append(f"Total Nodes: {report_data['total_nodes']}")
        lines.append(f"Successful: {report_data['successful_mappings']}")
        lines.append(f"Failed: {report_data['failed_mappings']}")
        lines.append(f"Success Rate: {report_data['overall_success_rate']:.1%}")
        lines.append("")
        
        if report_data['unique_missing_audio']:
            lines.append("Missing Audio Segments (need recording):")
            for segment in report_data['unique_missing_audio']:
                lines.append(f"  - '{segment}'")
            lines.append("")
        
        lines.append("Node Details:")
        for node_id, node_report in report_data['node_reports'].items():
            lines.append(f"  {node_id}:")
            if 'error' in node_report:
                lines.append(f"    ERROR: {node_report['error']}")
            else:
                lines.append(f"    Type: {node_report['node_type']}")
                lines.append(f"    Text: '{node_report['original_text']}'")
                if 'audio_mapping' in node_report:
                    mapping = node_report['audio_mapping']
                    lines.append(f"    Success Rate: {mapping.success_rate:.1%}")
                    if mapping.play_prompt:
                        lines.append(f"    Audio: {mapping.play_prompt}")
                    if mapping.missing_segments:
                        lines.append(f"    Missing: {mapping.missing_segments}")
            lines.append("")
        
        return '\n'.join(lines)
    
    def validate_ivr_output(self, js_code: str) -> Dict[str, Any]:
        """Validate generated IVR JavaScript"""
        validation_result = {
            'valid': False,
            'errors': [],
            'warnings': [],
            'node_count': 0
        }
        
        try:
            # Extract JSON from module.exports
            json_match = re.search(r'module\.exports\s*=\s*(\[.*\]);', js_code, re.DOTALL)
            if not json_match:
                validation_result['errors'].append("No valid module.exports found")
                return validation_result
            
            # Parse JSON
            json_str = json_match.group(1)
            nodes = json.loads(json_str)
            
            if not isinstance(nodes, list):
                validation_result['errors'].append("Module should export an array")
                return validation_result
            
            validation_result['node_count'] = len(nodes)
            
            # Validate each node
            for i, node in enumerate(nodes):
                if not isinstance(node, dict):
                    validation_result['errors'].append(f"Node {i} is not an object")
                    continue
                
                # Check required fields
                if 'label' not in node:
                    validation_result['errors'].append(f"Node {i} missing 'label' field")
                
                # Check playPrompt format
                if 'playPrompt' in node:
                    if isinstance(node['playPrompt'], str):
                        validation_result['warnings'].append(f"Node {node.get('label', i)}: playPrompt should be array")
                    elif isinstance(node['playPrompt'], list):
                        for prompt in node['playPrompt']:
                            if not isinstance(prompt, str):
                                validation_result['warnings'].append(f"Node {node.get('label', i)}: invalid playPrompt item")
            
            validation_result['valid'] = len(validation_result['errors']) == 0
            
        except json.JSONDecodeError as e:
            validation_result['errors'].append(f"Invalid JSON: {e}")
        except Exception as e:
            validation_result['errors'].append(f"Validation error: {e}")
        
        return validation_result


def convert_mermaid_to_ivr_enhanced(mermaid_code: str, audio_database_path: str, 
                                   company: str = None, schema: str = None) -> Tuple[str, Dict]:
    """
    Convenience function for enhanced Mermaid to IVR conversion
    
    Args:
        mermaid_code: Mermaid diagram text
        audio_database_path: Path to audio transcription CSV
        company: Company context
        schema: Schema context
        
    Returns:
        Tuple of (IVR JavaScript code, conversion report)
    """
    converter = EnhancedIVRConverter(audio_database_path)
    return converter.convert_mermaid_to_ivr(mermaid_code, company, schema)