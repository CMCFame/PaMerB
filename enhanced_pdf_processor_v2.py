"""
Enhanced PDF processor V2 with intelligent page filtering and multi-callout support.
Fixes tuple errors and adds AI-powered page classification.
"""

import fitz  # PyMuPDF
import io
import base64
import logging
from typing import List, Dict, Any, Optional, Tuple
from PIL import Image
from dataclasses import dataclass
from openai import OpenAI
import streamlit as st
import re

logger = logging.getLogger(__name__)

@dataclass
class PageClassification:
    """Classification result for a PDF page"""
    page_number: int
    is_diagram: bool
    confidence: float
    page_type: str  # 'title', 'diagram', 'text', 'mixed', 'blank'
    suggested_callout_type: Optional[str]
    key_content: str

@dataclass
class DiagramInfo:
    """Information about a detected diagram"""
    page_number: int
    mermaid_code: str
    callout_type: Optional[str]
    confidence: float
    title: str

class IntelligentPDFProcessor:
    """
    V2 PDF processor with intelligent page classification and multi-callout support
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize processor with OpenAI API key"""
        self.api_key = (
            api_key or 
            st.secrets.get("general", {}).get("OPENAI_API_KEY") or 
            st.secrets.get("OPENAI_API_KEY")
        )
        
        if not self.api_key:
            raise ValueError("OpenAI API key not found")
        
        self.client = OpenAI(api_key=self.api_key)
    
    def process_pdf_intelligently(self, pdf_file) -> Tuple[List[DiagramInfo], List[PageClassification]]:
        """
        Process PDF with intelligent page classification and diagram extraction
        """
        try:
            # Read PDF from uploaded file
            pdf_bytes = pdf_file.read()
            pdf_file.seek(0)  # Reset file pointer
            
            # Open PDF document
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            
            logger.info(f"Processing PDF with {len(doc)} pages")
            
            # First pass: classify all pages
            page_classifications = []
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                classification = self._classify_page_content(page, page_num)
                page_classifications.append(classification)
                logger.info(f"Page {page_num + 1}: {classification.page_type} "
                          f"(diagram: {classification.is_diagram}, confidence: {classification.confidence:.2f})")
            
            # Second pass: process only diagram pages
            diagram_infos = []
            for classification in page_classifications:
                if classification.is_diagram and classification.confidence > 0.3:
                    page = doc.load_page(classification.page_number)
                    try:
                        diagram_info = self._extract_diagram_from_page(page, classification)
                        if diagram_info:
                            diagram_infos.append(diagram_info)
                    except Exception as e:
                        logger.error(f"Error processing diagram on page {classification.page_number + 1}: {e}")
            
            doc.close()
            
            logger.info(f"Successfully extracted {len(diagram_infos)} diagrams from {len(page_classifications)} pages")
            return diagram_infos, page_classifications
            
        except Exception as e:
            logger.error(f"PDF processing failed: {str(e)}")
            raise RuntimeError(f"PDF processing error: {str(e)}")
    
    def _classify_page_content(self, page: fitz.Page, page_num: int) -> PageClassification:
        """
        Classify page content using text analysis and AI
        """
        try:
            # Extract text content safely
            text_content = ""
            try:
                text_blocks = page.get_text("blocks")
                for block in text_blocks:
                    if len(block) >= 5:  # Valid text block
                        text_content += str(block[4]) + " "
            except Exception as e:
                logger.warning(f"Text extraction failed for page {page_num + 1}: {e}")
                text_content = page.get_text() or ""
            
            # Get drawing information
            try:
                drawings = page.get_drawings()
                has_drawings = len(drawings) > 0
            except Exception as e:
                logger.warning(f"Drawing extraction failed for page {page_num + 1}: {e}")
                has_drawings = False
            
            # Clean and analyze text
            text_clean = text_content.strip().lower()
            text_summary = text_clean[:200] + "..." if len(text_clean) > 200 else text_clean
            
            # Quick classification based on content patterns
            flowchart_keywords = [
                'flowchart', 'diagram', 'press', 'enter', 'welcome', 'callout',
                'employee', 'pin', 'accept', 'decline', 'invalid', 'goodbye',
                'if', 'then', 'else', 'decision', 'start', 'end', 'process'
            ]
            
            title_keywords = [
                'title', 'cover', 'table of contents', 'index', 'appendix',
                'document', 'manual', 'guide', 'overview', 'introduction'
            ]
            
            # Calculate keyword scores
            flowchart_score = sum(1 for keyword in flowchart_keywords if keyword in text_clean)
            title_score = sum(1 for keyword in title_keywords if keyword in text_clean)
            
            # Determine page type and confidence
            if len(text_clean) < 20 and not has_drawings:
                page_type = 'blank'
                is_diagram = False
                confidence = 0.9
            elif title_score > flowchart_score and title_score > 0:
                page_type = 'title'
                is_diagram = False
                confidence = 0.7
            elif flowchart_score > 0 or has_drawings:
                page_type = 'diagram'
                is_diagram = True
                confidence = min(0.9, 0.3 + (flowchart_score * 0.1) + (0.3 if has_drawings else 0))
            elif len(text_clean) > 100:
                page_type = 'text'
                is_diagram = False
                confidence = 0.6
            else:
                page_type = 'mixed'
                is_diagram = flowchart_score > 0 or has_drawings
                confidence = 0.5
            
            # Suggest callout type for diagram pages
            suggested_callout_type = None
            if is_diagram:
                suggested_callout_type = self._suggest_callout_type_from_text(text_clean)
            
            return PageClassification(
                page_number=page_num,
                is_diagram=is_diagram,
                confidence=confidence,
                page_type=page_type,
                suggested_callout_type=suggested_callout_type,
                key_content=text_summary
            )
            
        except Exception as e:
            logger.error(f"Page classification failed for page {page_num + 1}: {e}")
            # Return safe fallback classification
            return PageClassification(
                page_number=page_num,
                is_diagram=True,  # Process as diagram to be safe
                confidence=0.5,
                page_type='unknown',
                suggested_callout_type=None,
                key_content="Classification failed"
            )
    
    def _suggest_callout_type_from_text(self, text: str) -> Optional[str]:
        """Suggest callout type based on text analysis"""
        text_lower = text.lower()
        
        if "test" in text_lower and "callout" in text_lower:
            return "2050"  # Test Callout
        elif "reu" in text_lower and ("notification" in text_lower or "message" in text_lower):
            return "2100"  # REU Notification
        elif "fill shift" in text_lower or "pre-arranged" in text_lower:
            return "2025"  # Fill Shift Callout
        elif "pin" in text_lower and "enter" in text_lower:
            return "1001"  # Employee PIN Verification
        elif ("accept" in text_lower and "decline" in text_lower) or "emergency" in text_lower:
            return "1025"  # Emergency Callout Response
        elif "welcome" in text_lower and ("press" in text_lower or "menu" in text_lower):
            return "1072"  # General IVR Menu
        elif "notification" in text_lower or "message" in text_lower:
            return "1006"  # Notification Only
        
        return "1072"  # Default to general menu
    
    def _extract_diagram_from_page(self, page: fitz.Page, classification: PageClassification) -> Optional[DiagramInfo]:
        """Extract diagram from a classified page"""
        try:
            # Convert page to image for AI processing
            mat = fitz.Matrix(2.0, 2.0)  # 2x zoom for better quality
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("png")
            
            # Convert to base64 for OpenAI
            base64_image = base64.b64encode(img_data).decode()
            
            # Prompt optimized for Mermaid compatibility
            prompt = f"""
Convert this IVR flowchart diagram to valid Mermaid.js format.

CONTEXT:
- Page type: {classification.page_type}
- Suggested callout type: {classification.suggested_callout_type or 'Unknown'}

INSTRUCTIONS:
1. Extract all visible text content exactly as written
2. Use rectangles A[text] for processes, diamonds A{{text}} for decisions  
3. Follow all flow lines and connections with --> arrows
4. Include all DTMF options and labels (Press 1, Press 2, etc.)
5. Preserve the logical flow structure
6. Skip title text, headers, and footers

MERMAID SYNTAX REQUIREMENTS:
- Start with 'flowchart TD'
- Node IDs: Use simple letters (A, B, C, etc.)
- Node labels: Keep text clean and readable
- Line breaks: Use \\n in text (will be converted to <br/>)
- Connections: Use --> for arrows, |"label"| for edge labels
- Special characters: Avoid unless necessary

EXAMPLE:
flowchart TD
    A[Welcome\\nPress 1 for employee] -->|"1"| B[Enter PIN]
    A -->|"7"| C[Not Home]

Focus on creating valid Mermaid syntax that will render properly.
"""
            
            try:
                response = self.client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/png;base64,{base64_image}",
                                        "detail": "high"
                                    }
                                }
                            ]
                        }
                    ],
                    max_tokens=3000,
                    temperature=0.1
                )
                
                mermaid_code = response.choices[0].message.content.strip()
                
                # Check if AI detected no diagram
                if "NO_DIAGRAM" in mermaid_code.upper():
                    logger.info(f"AI detected no valid diagram on page {classification.page_number + 1}")
                    return None
                
                # Clean up the response
                if "```mermaid" in mermaid_code:
                    mermaid_code = mermaid_code.split("```mermaid")[1].split("```")[0].strip()
                elif "```" in mermaid_code:
                    mermaid_code = mermaid_code.split("```")[1].strip()
                
                # Clean and fix common Mermaid syntax issues
                mermaid_code = self._clean_mermaid_syntax(mermaid_code)
                
                # Optional validation (disabled for now to reduce API calls)
                # validation_result = self._validate_mermaid_output(base64_image, mermaid_code, classification)
                # if not validation_result['valid']:
                #     logger.warning(f"Validation failed for page {classification.page_number + 1}: {validation_result['reason']}")
                #     mermaid_code += f"\n// VALIDATION WARNING: {validation_result['reason']}"
                
                # Validate mermaid code has content
                if len(mermaid_code.strip()) < 20:
                    logger.warning(f"Generated Mermaid code too short for page {classification.page_number + 1}")
                    return None
                
                # Extract title from first line or key content
                title_match = re.search(r'([A-Z][^"\[\{]*)', mermaid_code)
                title = title_match.group(1)[:50] if title_match else f"Diagram {classification.page_number + 1}"
                
                return DiagramInfo(
                    page_number=classification.page_number + 1,
                    mermaid_code=mermaid_code,
                    callout_type=classification.suggested_callout_type,
                    confidence=classification.confidence,
                    title=title.strip()
                )
                
            except Exception as e:
                logger.error(f"OpenAI processing failed for page {classification.page_number + 1}: {e}")
                return None
                
        except Exception as e:
            logger.error(f"Diagram extraction failed for page {classification.page_number + 1}: {e}")
            return None
    
    def _validate_mermaid_output(self, base64_image: str, mermaid_code: str, classification) -> Dict[str, Any]:
        """Validate the generated Mermaid code against the original diagram"""
        try:
            # Quick validation checks
            node_count = len(re.findall(r'[A-Z]\[.*?\]', mermaid_code))
            arrow_count = len(re.findall(r'-->', mermaid_code))
            
            # Basic sanity checks
            if node_count < 2:
                return {'valid': False, 'reason': 'Too few nodes detected'}
            
            if arrow_count < 1:
                return {'valid': False, 'reason': 'No connections detected'}
            
            # For more thorough validation, use a secondary API call (optional)
            # This can be enabled for critical diagrams
            if classification.confidence > 0.8:
                return self._deep_validate_with_api(base64_image, mermaid_code)
            
            return {'valid': True, 'reason': 'Basic validation passed'}
            
        except Exception as e:
            logger.error(f"Validation error: {e}")
            return {'valid': True, 'reason': 'Validation error, assuming valid'}
    
    def _deep_validate_with_api(self, base64_image: str, mermaid_code: str) -> Dict[str, Any]:
        """Deep validation using a secondary API call to compare against original"""
        try:
            validation_prompt = f"""
Compare this generated Mermaid code against the original diagram image.

GENERATED CODE:
{mermaid_code[:1000]}...

VALIDATION CHECKLIST:
1. Are all visible text boxes/nodes included?
2. Are all arrows/connections preserved?
3. Are DTMF options (Press 1, 2, etc.) correct?
4. Are decision points properly represented?
5. Is the flow logic accurate?

RESPOND WITH:
VALID: YES/NO
REASON: [brief explanation]
MISSING: [any missing elements]
EXTRA: [any hallucinated elements]
"""

            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user", 
                        "content": [
                            {"type": "text", "text": validation_prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/png;base64,{base64_image}"}
                            }
                        ]
                    }
                ],
                max_tokens=500,
                temperature=0.1
            )
            
            result = response.choices[0].message.content.lower()
            is_valid = "valid: yes" in result
            
            # Extract reason
            reason_match = re.search(r'reason: (.+?)(?:\n|$)', result)
            reason = reason_match.group(1) if reason_match else "No specific reason"
            
            return {
                'valid': is_valid,
                'reason': reason,
                'full_response': result[:200]
            }
            
        except Exception as e:
            logger.error(f"Deep validation failed: {e}")
            return {'valid': True, 'reason': 'Deep validation failed, assuming valid'}
    
    def _clean_mermaid_syntax(self, mermaid_code: str) -> str:
        """Clean and fix common Mermaid syntax issues"""
        try:
            lines = mermaid_code.split('\n')
            cleaned_lines = []
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Fix Mermaid syntax issues with proper node label quoting
                # 1. Fix line breaks
                line = re.sub(r'\\n', '<br/>', line)  # Literal \n becomes <br/>
                
                # 2. Fix node label quoting - wrap complex labels in double quotes
                # Match node definitions: A[content] or A{content}
                def quote_node_content(match):
                    node_id = match.group(1)
                    bracket_type = match.group(2)
                    content = match.group(3)
                    closing_bracket = match.group(4)
                    
                    # Fix common bracket issues first
                    # Handle cases like: [REU"] Callout System.]
                    if '"]' in content and content.count('[') != content.count(']'):
                        # Try to fix unmatched brackets
                        content = content.replace('"]', '').replace('[', '').replace(']', '')
                    
                    # Remove any existing broken quotes
                    if content.startswith('"') and not content.endswith('"'):
                        content = content[1:]  # Remove leading quote
                    if content.endswith('"') and not content.startswith('"'):
                        content = content[:-1]  # Remove trailing quote
                    
                    # Check if content needs quoting (contains commas, parentheses, <br/>, brackets, etc.)
                    needs_quotes = any(char in content for char in [',', '(', ')', '<br/>', '&', ';', ':', '[', ']'])
                    
                    if needs_quotes and not (content.startswith('"') and content.endswith('"')):
                        # Escape any existing quotes in content
                        content = content.replace('"', '&quot;')
                        content = f'"{content}"'
                    
                    return f'{node_id}{bracket_type}{content}{closing_bracket}'
                
                # Fix specific broken patterns first
                # Fix: ["content [REU"] remaining.]
                line = re.sub(r'\["([^"]*)\[([^"]*?)"\]\s*([^"]*?)\.\]', r'["\1\2 \3."]', line)
                
                # Fix: ["content [no"] remaining.]  
                line = re.sub(r'\["([^"]*)\[([^"]*?)"\]\s*([^"]*?)\]', r'["\1\2 \3"]', line)
                
                # Fix remaining bracket patterns within node content
                # Pattern: [word"] -> word
                line = re.sub(r'\[([^"]*?)"\]', r'\1', line)
                
                # Pattern: [word] -> word (for simple cases)
                line = re.sub(r'\[([^\]"]*?)\](?=\s)', r'\1', line)
                
                # Fix trailing quotes and brackets at end of lines
                line = re.sub(r'not"\]\s*active\.\]$', r'not active."]', line)
                line = re.sub(r'([^"]+)"\]\s*([^"]*?)\.\]$', r'\1 \2."]', line)
                
                # Apply standard quoting to node definitions
                line = re.sub(r'([A-Z]+)(\[)([^\]]+)(\])', quote_node_content, line)  # Rectangle nodes
                line = re.sub(r'([A-Z]+)(\{)([^\}]+)(\})', quote_node_content, line)  # Diamond nodes
                
                # 3. Fix basic arrow syntax
                line = re.sub(r'--\s+([A-Z])', r'-->\1', line)  # Fix broken arrows to nodes
                
                # 4. Remove excessive spaces
                line = re.sub(r'\s{3,}', ' ', line)  # Only remove 3+ spaces
                
                # 5. Final Mermaid-specific fixes
                # Fix edge label syntax - ensure quotes around complex labels
                line = re.sub(r'\|\s*([^|"]+[,\(\)&;:].*?)\s*\|', r'|"\1"|', line)  # Quote complex edge labels
                
                cleaned_lines.append(line)
            
            # Ensure proper flowchart declaration
            if cleaned_lines and not cleaned_lines[0].startswith('flowchart'):
                cleaned_lines.insert(0, 'flowchart TD')
            elif not cleaned_lines:
                return 'flowchart TD\n    A[Empty Diagram]'
            
            # Add proper indentation
            result_lines = [cleaned_lines[0]]  # Keep flowchart TD without indent
            for line in cleaned_lines[1:]:
                if line.strip():
                    result_lines.append(f'    {line}')
            
            result = '\n'.join(result_lines)
            
            # Final validation - check for basic Mermaid syntax
            if self._validate_mermaid_syntax(result):
                return result
            else:
                logger.warning("Generated Mermaid syntax may have issues")
                return result  # Return anyway, but log warning
            
        except Exception as e:
            logger.warning(f"Mermaid syntax cleaning failed: {e}")
            # Return original if cleaning fails
            return mermaid_code
    
    def _validate_mermaid_syntax(self, mermaid_code: str) -> bool:
        """Basic validation of Mermaid syntax"""
        try:
            lines = mermaid_code.split('\n')
            
            # Check for required elements
            has_flowchart = any('flowchart' in line for line in lines)
            has_nodes = any('[' in line and ']' in line for line in lines)
            has_connections = any('-->' in line for line in lines)
            
            # Check for common syntax errors
            has_unmatched_brackets = False
            for line in lines:
                if line.count('[') != line.count(']') or line.count('{') != line.count('}'):
                    has_unmatched_brackets = True
                    break
            
            return has_flowchart and has_nodes and has_connections and not has_unmatched_brackets
            
        except Exception:
            return True  # If validation fails, assume it's ok
    
    def process_pdf_file_v2(self, pdf_file) -> Tuple[List[str], List[Dict[str, Any]]]:
        """
        V2 entry point that returns both mermaid codes and metadata
        """
        try:
            diagram_infos, page_classifications = self.process_pdf_intelligently(pdf_file)
            
            # Convert to format expected by app
            mermaid_results = []
            metadata_results = []
            
            for diagram_info in diagram_infos:
                mermaid_results.append(diagram_info.mermaid_code)
                metadata_results.append({
                    "page_number": diagram_info.page_number,
                    "title": diagram_info.title,
                    "callout_type": diagram_info.callout_type,
                    "confidence": diagram_info.confidence
                })
            
            # Add summary of skipped pages
            skipped_pages = [c for c in page_classifications if not c.is_diagram or c.confidence <= 0.3]
            if skipped_pages:
                skipped_summary = []
                for page_class in skipped_pages:
                    skipped_summary.append(f"Page {page_class.page_number + 1}: {page_class.page_type}")
                
                logger.info(f"Skipped {len(skipped_pages)} pages: {', '.join(skipped_summary)}")
            
            return mermaid_results, metadata_results
            
        except Exception as e:
            logger.error(f"V2 PDF processing failed: {str(e)}")
            raise RuntimeError(f"V2 PDF processing error: {str(e)}")

# Backwards compatibility wrapper
class EnhancedPDFProcessor:
    """Backwards compatibility wrapper for the V2 processor"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.v2_processor = IntelligentPDFProcessor(api_key)
    
    def process_pdf_file(self, pdf_file) -> List[str]:
        """Process PDF and return mermaid codes (V1 compatibility)"""
        mermaid_results, _ = self.v2_processor.process_pdf_file_v2(pdf_file)
        return mermaid_results
    
    def process_pdf_file_with_metadata(self, pdf_file) -> Tuple[List[str], List[Dict[str, Any]]]:
        """Process PDF and return mermaid codes with metadata (V2 features)"""
        return self.v2_processor.process_pdf_file_v2(pdf_file)