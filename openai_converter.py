"""
UPDATED openai_ivr_converter.py - NO MORE HARD-CODED AUDIO IDs
Integrates with enhanced audio mapping system instead of using hard-coded mappings
"""
from typing import Dict, List, Any
from openai import OpenAI
import json
import logging
import base64
import os

# Import enhanced components
from enhanced_ivr_converter import EnhancedIVRConverter

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def process_flow_diagram(image_path: str, api_key: str) -> str:
    """
    Convert a flowchart image to Mermaid diagram using GPT-4 Vision
    
    Args:
        image_path: Path to the flowchart image file
        api_key: OpenAI API key
        
    Returns:
        Mermaid diagram code as string
    """
    try:
        # Initialize OpenAI client
        client = OpenAI(api_key=api_key)
        
        # Encode the image
        with open(image_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode('utf-8')
        
        # Prepare the prompt for GPT-4 Vision
        prompt = """You are an expert at converting flowcharts to Mermaid diagram syntax.

        Analyze this flowchart image and convert it to a Mermaid diagram following these rules:
        1. Use flowchart TD (top-down) syntax
        2. Identify node types:
           - Rectangles = action nodes (use ["text"])
           - Diamonds = decision nodes (use {"text"})
           - Rounded rectangles = start/end nodes (use (["text"]))
        3. Label edges with decision outcomes (yes/no, 1/2/3, etc.)
        4. Preserve all text exactly as shown in the image
        5. Use <br/> for line breaks within nodes
        6. Maintain the flow logic precisely

        Example format:
        flowchart TD
        A["Welcome<br/>Press 1 for yes"] -->|"1"| B{"Decision"}
        B -->|"yes"| C["Action"]
        B -->|"no"| D["Other Action"]

        Generate ONLY the Mermaid code, no explanations."""

        # Call GPT-4 Vision
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=2000
        )
        
        # Extract the Mermaid code
        mermaid_code = response.choices[0].message.content.strip()
        
        # Clean up the response if needed
        if mermaid_code.startswith("```"):
            # Remove code blocks if present
            lines = mermaid_code.split('\n')
            if lines[0].strip() in ['```', '```mermaid']:
                lines = lines[1:]
            if lines[-1].strip() == '```':
                lines = lines[:-1]
            mermaid_code = '\n'.join(lines)
        
        logger.info("Successfully converted image to Mermaid diagram")
        return mermaid_code
        
    except Exception as e:
        logger.error(f"Failed to process flow diagram: {str(e)}")
        raise Exception(f"Image conversion failed: {str(e)}")


class OpenAIIVRConverter:
    """
    ENHANCED OpenAI IVR Converter that uses real audio database instead of hard-coded IDs
    """
    
    def __init__(self, api_key: str, audio_database_path: str = "cf_general_structure.csv"):
        self.client = OpenAI(api_key=api_key)
        self.audio_database_path = audio_database_path
        
        # Initialize enhanced converter for final processing
        try:
            self.enhanced_converter = EnhancedIVRConverter(audio_database_path)
            self.enhanced_available = True
            logger.info("Enhanced audio mapping available")
        except Exception as e:
            logger.warning(f"Enhanced audio mapping not available: {e}")
            self.enhanced_available = False

    def convert_to_ivr(self, mermaid_code: str, company: str = "arcos", schema: str = None) -> str:
        """
        Convert Mermaid diagram to IVR configuration using GPT-4 + Enhanced Audio Mapping
        
        This method now uses a two-step process:
        1. GPT-4 generates the logical flow structure 
        2. Enhanced audio mapper provides real audio IDs
        """
        
        if self.enhanced_available:
            # NEW APPROACH: Use enhanced converter directly
            return self._convert_with_enhanced_mapping(mermaid_code, company, schema)
        else:
            # FALLBACK: Use GPT-4 with generic guidance
            return self._convert_with_gpt4_fallback(mermaid_code)
    
    def _convert_with_enhanced_mapping(self, mermaid_code: str, company: str, schema: str) -> str:
        """Convert using enhanced audio mapping (RECOMMENDED)"""
        try:
            logger.info("Using enhanced audio mapping for conversion")
            
            # Use enhanced converter directly - this gives us real audio IDs
            js_code, report = self.enhanced_converter.convert_mermaid_to_ivr(
                mermaid_code, 
                company=company, 
                schema=schema
            )
            
            # Log success metrics
            logger.info(f"Enhanced conversion: {report['overall_success_rate']:.1%} success rate")
            if report['unique_missing_audio']:
                logger.warning(f"Missing audio segments: {report['unique_missing_audio']}")
            
            return js_code
            
        except Exception as e:
            logger.error(f"Enhanced conversion failed: {e}")
            return self._convert_with_gpt4_fallback(mermaid_code)
    
    def _convert_with_gpt4_fallback(self, mermaid_code: str) -> str:
        """Fallback GPT-4 conversion (when enhanced mapping not available)"""
        
        # UPDATED PROMPT: No more hard-coded audio IDs
        prompt = f"""You are an expert IVR system developer. Convert this Mermaid flowchart into a complete IVR JavaScript configuration.

        IMPORTANT: DO NOT use hard-coded audio IDs. Instead, generate logical flow structure and use descriptive placeholders.

        Requirements:
        1. Node Structure:
           - Each node must have a unique "label" (node identifier)
           - "log" property for documentation/logging
           - "playPrompt" should use descriptive placeholders like ["WELCOME_MESSAGE"] or ["ERROR_PROMPT"]
           - Include appropriate control flow (getDigits, branch, goto, etc.)

        2. Flow Control:
           - Use "branch" for conditional paths based on user input
           - Use "goto" for direct transitions
           - Include proper error handling with "error" and "none" branches
           - Add timeout handling where appropriate

        3. Input Handling:
           For nodes requiring user input, include:
           {{
             "getDigits": {{
               "numDigits": 1,
               "maxTries": 3,
               "validChoices": "1|2|3|7|9",
               "errorPrompt": ["ERROR_INVALID_INPUT"],
               "timeoutPrompt": ["ERROR_TIMEOUT"]
             }}
           }}

        4. Special Nodes:
           - "Problems" node for error handling
           - "End" or "Disconnect" for call termination
           - Use descriptive labels instead of single letters

        Mermaid diagram to convert:
        {mermaid_code}

        Generate a complete, valid JavaScript module.exports array with IVR configuration objects.
        """

        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=2000
            )
            
            ivr_code = response.choices[0].message.content.strip()
            
            # Clean up response
            if ivr_code.startswith("```"):
                lines = ivr_code.split('\n')
                start_idx = 1
                end_idx = len(lines) - 1
                
                if lines[-1].strip() == "```":
                    end_idx -= 1
                    
                ivr_code = '\n'.join(lines[start_idx:end_idx])
            
            # Add warning comment about placeholders
            warning_comment = '''/**
 * WARNING: This IVR configuration uses placeholder audio IDs.
 * Use enhanced audio mapping to get real audio file IDs.
 * Placeholders like ["WELCOME_MESSAGE"] need to be replaced with actual audio IDs.
 */

'''
            
            return warning_comment + ivr_code

        except Exception as e:
            logger.error(f"GPT-4 IVR conversion failed: {str(e)}")
            return self._generate_error_fallback()

    def _generate_error_fallback(self) -> str:
        """Generate basic error handler when all conversion methods fail"""
        return '''/**
 * IVR Configuration - Error Fallback
 * Generated when conversion failed
 */

module.exports = [
  {
    "label": "Problems",
    "log": "Conversion error - please check input",
    "playPrompt": ["ERROR_CONVERSION_FAILED"],
    "nobarge": "1",
    "goto": "End"
  },
  {
    "label": "End",
    "log": "End of call",
    "playPrompt": ["GOODBYE_MESSAGE"],
    "nobarge": "1"
  }
];'''

    def get_conversion_info(self) -> Dict[str, Any]:
        """Get information about available conversion methods"""
        return {
            "enhanced_mapping_available": self.enhanced_available,
            "audio_database_path": self.audio_database_path,
            "recommended_method": "enhanced" if self.enhanced_available else "gpt4_fallback",
            "capabilities": {
                "real_audio_ids": self.enhanced_available,
                "placeholder_ids": True,
                "logical_flow_generation": True
            }
        }


def convert_mermaid_to_ivr(mermaid_code: str, api_key: str, 
                          audio_database_path: str = "cf_general_structure.csv",
                          company: str = "arcos", schema: str = None) -> str:
    """
    UPDATED wrapper function for Mermaid to IVR conversion
    Now uses enhanced audio mapping when available
    
    Args:
        mermaid_code: Mermaid diagram text
        api_key: OpenAI API key
        audio_database_path: Path to audio transcription database
        company: Company context for audio mapping
        schema: Schema context for audio mapping
    
    Returns:
        JavaScript IVR configuration
    """
    converter = OpenAIIVRConverter(api_key, audio_database_path)
    return converter.convert_to_ivr(mermaid_code, company, schema)


# Helper function for batch conversion
def batch_convert_diagrams(diagrams: List[str], api_key: str, 
                          audio_database_path: str = "cf_general_structure.csv",
                          company: str = "arcos", schema: str = None) -> List[Dict[str, Any]]:
    """
    Convert multiple Mermaid diagrams in batch
    
    Returns list of results with diagram index, success status, and output
    """
    converter = OpenAIIVRConverter(api_key, audio_database_path)
    results = []
    
    for idx, diagram in enumerate(diagrams):
        try:
            ivr_code = converter.convert_to_ivr(diagram, company, schema)
            results.append({
                "index": idx,
                "success": True,
                "output": ivr_code,
                "error": None
            })
        except Exception as e:
            results.append({
                "index": idx,
                "success": False,
                "output": None,
                "error": str(e)
            })
    
    return results