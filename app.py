"""
Complete Unified Mermaid-to-IVR Converter
Features:
- Image/PDF to Mermaid conversion (OpenAI)
- ARCOS-integrated voice file matching
- Robust, flexible converter for any customer
- Production-ready IVR code generation
"""
import streamlit as st
import streamlit_mermaid as st_mermaid
import json
import tempfile
import os
from PIL import Image
import traceback
import base64
import io
import logging

# Import the converters
from mermaid_ivr_converter import convert_mermaid_to_ivr
from openai import OpenAI

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="🎯 Unified IVR Converter",
    page_icon="🔄",
    layout="wide"
)

# Constants and examples
DEFAULT_FLOWS = {
    "Electric Callout": '''flowchart TD
A["Welcome<br/>This is an electric callout from (Level 2).<br/>Press 1, if this is (employee).<br/>Press 3, if you need more time to get (employee) to the phone.<br/>Press 7, if (employee) is not home.<br/>Press 9, to repeat this message."] -->|"input"| B{"1 - this is employee"}
A -->|"no input - go to pg 3"| C["30-second message<br/>Press any key to continue..."]
A -->|"7 - not home"| D["Employee Not Home<br/>Please have<br/>(employee) call the<br/>(Level 2) Callout<br/>System at<br/>866-502-7267."]
A -->|"3 - need more time"| C
A -->|"9 - repeat"| A
B -->|"yes"| E["Enter Employee PIN<br/>Please enter your 4 digit PIN<br/>followed by the pound key."]
E --> F{"Correct PIN?"}
F -->|"yes"| G["Electric Callout<br/>This is an electric callout."]
F -->|"no"| H["Invalid PIN<br/>Please try again."]
H --> E
G --> I["Callout Reason<br/>The callout reason is (callout reason)."]
I --> J["Trouble Location<br/>The trouble location is (trouble location)."]
J --> K["Custom Message<br/>(Play custom message, if selected.)"]
K --> L{"Available For Callout<br/>Are you available to work this callout?<br/>If yes, press 1. If no, press 3.<br/>If no one else accepts, and you want to be called again, press 9."}
L -->|"1 - accept"| M["Accepted Response<br/>An accepted response has been recorded."]
L -->|"3 - decline"| N["Callout Decline<br/>Your response is being recorded as a decline."]
L -->|"9 - call back"| O["Qualified No<br/>You may be called again on this callout if no one accepts."]
M --> P["Goodbye<br/>Thank you.<br/>Goodbye."]
N --> P
O --> P
P --> Q["Disconnect"]
D --> Q''',

    "PIN Change": '''flowchart TD
A["Enter Current PIN<br/>Please enter your current 4 digit PIN followed by the pound key."] --> B{"Valid PIN?"}
B -->|"No"| C["Invalid Entry<br/>Invalid PIN. Please try again."]
B -->|"Yes"| D["New PIN<br/>Please enter your new 4 digit PIN followed by the pound key."]
C --> A
D --> E["Confirm PIN<br/>Please confirm your new PIN by entering it again."]
E --> F{"PIN Match?"}
F -->|"No"| D
F -->|"Yes"| G["PIN Changed<br/>Your PIN has been successfully updated."]
G --> H["Goodbye<br/>Thank you."]''',

    "Simple Availability": '''flowchart TD
A["Available For Callout<br/>Are you available to work this callout?<br/>Press 1 for yes, press 3 for no."] -->|"1"| B["Accept<br/>Thank you. Your response has been recorded."]
A -->|"3"| C["Decline<br/>Your decline has been recorded."]
A -->|"no input"| D["Problems<br/>I'm sorry you are having problems."]
B --> E["Goodbye<br/>Thank you."]
C --> E
D --> E'''
}

class ImageToMermaidConverter:
    """OpenAI-powered image to Mermaid converter"""
    
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
        
    def convert_image_to_mermaid(self, image_file) -> str:
        """Convert uploaded image to Mermaid diagram"""
        try:
            # Process image
            image = Image.open(image_file)
            
            # Convert to RGB if necessary
            if image.mode not in ('RGB', 'L'):
                image = image.convert('RGB')
            
            # Resize if too large
            max_size = (1000, 1000)
            if image.size[0] > max_size[0] or image.size[1] > max_size[1]:
                image.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # Convert to base64
            buffered = io.BytesIO()
            image.save(buffered, format="PNG")
            base64_image = base64.b64encode(buffered.getvalue()).decode()
            
            # Create prompt for IVR diagram conversion
            system_prompt = """You are a specialized converter focused on creating EXACT Mermaid.js flowchart representations of IVR call flow diagrams. 

CRITICAL REQUIREMENTS:
1. Text Content: Copy ALL text exactly as written, including punctuation and capitalization
2. Node Types: Use {"text"} for decisions, ["text"] for processes
3. Connections: Preserve ALL connection labels exactly as written
4. Include all retry loops, self-references, and connection directions
5. Maintain exact node shapes and flow structure

FORMAT: Always start with "flowchart TD" and use correct Mermaid syntax.

EXAMPLE:
flowchart TD
    A["Exact Node Text<br/>With line breaks"] -->|"Exact Label"| B{"Decision Text"}
    B -->|"1 - option"| C["Next Step"]
    B -->|"retry"| A

Focus on exact text reproduction and maintain all connections precisely."""
            
            # Make API call
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Convert this IVR flow diagram to Mermaid syntax EXACTLY as shown. Maintain all text, connections, and formatting precisely."
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=4096,
                temperature=0.1
            )
            
            # Extract and clean Mermaid code
            mermaid_text = response.choices[0].message.content
            
            # Clean up the response
            import re
            code_match = re.search(r'```(?:mermaid)?\n(.*?)```', mermaid_text, re.DOTALL)
            if code_match:
                mermaid_text = code_match.group(1)
            
            # Ensure proper flowchart definition
            if not mermaid_text.strip().startswith('flowchart TD'):
                mermaid_text = f'flowchart TD\n{mermaid_text}'
            
            # Clean up whitespace
            lines = [line.strip() for line in mermaid_text.splitlines() if line.strip()]
            return '\n'.join(lines)
            
        except Exception as e:
            logger.error(f"Image conversion failed: {str(e)}")
            raise RuntimeError(f"Image conversion error: {str(e)}")

def show_database_status(cf_general_csv, arcos_csv):
    """Show database loading status"""
    st.subheader("📊 Voice Database Status")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if arcos_csv:
            st.success("✅ ARCOS Foundation Database")
            st.info(f"📁 {arcos_csv.name} ({arcos_csv.size:,} bytes)")
            st.caption("🏗️ Core callflow recordings (1191, 1274, etc.)")
        else:
            st.warning("⚠️ ARCOS Fallback Database")
            st.caption("🔧 Limited to basic patterns")
    
    with col2:
        if cf_general_csv:
            st.success("✅ Client Database")
            st.info(f"📁 {cf_general_csv.name} ({cf_general_csv.size:,} bytes)")
            st.caption("🎯 Client-specific voice files")
        else:
            st.info("ℹ️ No Client Database")
            st.caption("🏗️ ARCOS foundation only")

def analyze_conversion_results(ivr_flow: list):
    """Analyze conversion results"""
    st.subheader("🔍 Conversion Analysis")
    
    # Critical fix verification
    welcome_node = next((node for node in ivr_flow if 'Live Answer' in node.get('label', '') or 'Welcome' in node.get('label', '')), None)
    
    if welcome_node:
        st.success("✅ Welcome node found")
        
        # Check branch mapping
        branch_map = welcome_node.get('branch', {})
        if '1' in branch_map:
            st.success(f"✅ **CRITICAL FIX VERIFIED**: Choice '1' maps to '{branch_map['1']}'")
        else:
            st.error("❌ **CRITICAL ISSUE**: Choice '1' mapping missing!")
        
        # Show branch mappings
        if branch_map:
            st.write("**Branch Mappings:**")
            for choice, target in branch_map.items():
                icon = "✅" if choice.isdigit() else "🔧"
                st.write(f"{icon} Choice '{choice}' → {target}")
    
    # Voice file analysis
    col1, col2, col3, col4 = st.columns(4)
    
    arcos_prompts = 0
    client_prompts = 0
    variable_prompts = 0
    missing_prompts = 0
    
    for node in ivr_flow:
        play_prompts = node.get('playPrompt', [])
        if isinstance(play_prompts, list):
            for prompt in play_prompts:
                if isinstance(prompt, str):
                    if prompt.startswith('callflow:'):
                        callflow_id = prompt.replace('callflow:', '')
                        if callflow_id.isdigit() and len(callflow_id) == 4:
                            arcos_prompts += 1
                        else:
                            client_prompts += 1
                    elif ':{{' in prompt:
                        variable_prompts += 1
                    elif '[VOICE FILE NEEDED]' in prompt:
                        missing_prompts += 1
    
    with col1:
        st.metric("🏗️ ARCOS", arcos_prompts)
    with col2:
        st.metric("🎯 Client", client_prompts)
    with col3:
        st.metric("🔧 Variables", variable_prompts)
    with col4:
        st.metric("❓ Missing", missing_prompts)
    
    total_prompts = arcos_prompts + client_prompts + variable_prompts + missing_prompts
    if total_prompts > 0:
        coverage = ((arcos_prompts + client_prompts + variable_prompts) / total_prompts) * 100
        st.metric("📊 Coverage", f"{coverage:.1f}%")

def show_code_diff(mermaid_text: str, js_output: str):
    """Show before/after comparison"""
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📝 Input: Mermaid Diagram")
        st.code(mermaid_text, language="mermaid")
        
        # Show Mermaid visualization
        try:
            st.markdown("### 🎨 Mermaid Visualization")
            st_mermaid.st_mermaid(mermaid_text, height="400px")
        except Exception as e:
            st.info(f"Mermaid visualization not available: {str(e)}")
    
    with col2:
        st.markdown("### ⚡ Output: Production IVR Code")
        st.code(js_output, language="javascript")

def main():
    st.title("🎯 Unified IVR Converter")
    st.markdown("**Complete Solution**: Image-to-Mermaid + ARCOS-Integrated IVR Generation")
    
    # Sidebar configuration
    with st.sidebar:
        st.header("📁 Voice Databases")
        
        # ARCOS Foundation Database
        st.markdown("### 🏗️ ARCOS Foundation")
        arcos_csv = st.file_uploader(
            "Upload ARCOS Database", 
            type=['csv'],
            key="arcos_upload",
            help="ARCOS foundation recordings (arcos_general_structure.csv)"
        )
        
        # Client Database
        st.markdown("### 🎯 Client Database")
        cf_general_csv = st.file_uploader(
            "Upload Client Database", 
            type=['csv'],
            key="client_upload",
            help="Client-specific recordings (cf_general_structure.csv)"
        )
        
        st.markdown("### 🔧 API Configuration")
        openai_api_key = st.text_input(
            "OpenAI API Key", 
            type="password",
            help="Required for image-to-Mermaid conversion"
        )
        
        st.markdown("### ⚙️ Settings")
        show_debug = st.checkbox("Show Debug Info", value=False)
        show_analysis = st.checkbox("Show Analysis", value=True)
    
    # Show database status
    show_database_status(cf_general_csv, arcos_csv)
    
    st.markdown("""
    **🚀 Unified Features:**
    - 📷 **Image-to-Mermaid**: Convert flowchart images/PDFs to Mermaid code
    - 🏗️ **ARCOS Foundation**: Core voice file patterns for any customer
    - 🎯 **Client Integration**: Company-specific voice file overrides
    - ✅ **Production Ready**: Generates deployable IVR JavaScript
    - 🔧 **Flexible**: Works for existing and new customers
    """)

    # Initialize session state
    if 'mermaid_code' not in st.session_state:
        st.session_state.mermaid_code = ""
    if 'ivr_code' not in st.session_state:
        st.session_state.ivr_code = ""

    # Input method selection
    st.subheader("📝 Input Method")
    input_method = st.radio(
        "Choose input method:", 
        ["🖊️ Mermaid Editor", "📷 Image Upload"],
        horizontal=True
    )
    
    mermaid_text = ""
    
    if input_method == "🖊️ Mermaid Editor":
        # Mermaid editor mode
        st.markdown("### 📝 Mermaid Code Editor")
        
        # Example selector
        selected_example = st.selectbox(
            "Load Example Flow", 
            ["Custom"] + list(DEFAULT_FLOWS.keys())
        )
        
        initial_text = DEFAULT_FLOWS.get(selected_example, st.session_state.mermaid_code)
        
        mermaid_text = st.text_area(
            "Mermaid Diagram Code", 
            initial_text, 
            height=400,
            help="Paste your Mermaid flowchart code here or select an example above"
        )
        
        st.session_state.mermaid_code = mermaid_text
        
        # Show preview
        if mermaid_text.strip():
            st.markdown("### 🎨 Mermaid Preview")
            try:
                st_mermaid.st_mermaid(mermaid_text, height="300px")
            except Exception as e:
                st.warning(f"Preview not available: {str(e)}")
    
    else:
        # Image upload mode
        st.markdown("### 📷 Image Upload")
        
        if not openai_api_key:
            st.error("❌ OpenAI API key required for image conversion")
            st.info("Please enter your OpenAI API key in the sidebar")
            return
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            uploaded_file = st.file_uploader(
                "Upload Flowchart Image/PDF", 
                type=['pdf', 'png', 'jpg', 'jpeg'],
                help="Upload a flowchart image or PDF for conversion"
            )
        
        with col2:
            if uploaded_file:
                try:
                    # Show uploaded image
                    if uploaded_file.type.startswith('image/'):
                        image = Image.open(uploaded_file)
                        st.image(image, caption="Uploaded Flowchart", use_column_width=True)
                    else:
                        st.info("📄 PDF uploaded successfully")
                        
                except Exception as e:
                    st.error(f"Error loading file: {str(e)}")
        
        if uploaded_file:
            if st.button("🔄 Convert Image to Mermaid", type="primary"):
                with st.spinner("Converting image to Mermaid..."):
                    try:
                        # Convert image to Mermaid
                        converter = ImageToMermaidConverter(openai_api_key)
                        mermaid_text = converter.convert_image_to_mermaid(uploaded_file)
                        
                        st.session_state.mermaid_code = mermaid_text
                        st.success("✅ Image converted to Mermaid successfully!")
                        
                        # Show generated Mermaid code
                        st.markdown("### 📝 Generated Mermaid Code")
                        st.code(mermaid_text, language="mermaid")
                        
                        # Show preview
                        st.markdown("### 🎨 Mermaid Preview")
                        try:
                            st_mermaid.st_mermaid(mermaid_text, height="300px")
                        except Exception as e:
                            st.warning(f"Preview not available: {str(e)}")
                        
                    except Exception as e:
                        st.error(f"❌ Image conversion failed: {str(e)}")
                        if show_debug:
                            st.exception(e)
        else:
            st.info("📷 Upload an image or PDF to begin conversion")
            return
    
    # IVR Conversion Section
    if mermaid_text.strip():
        st.markdown("---")
        st.subheader("🔄 IVR Code Generation")
        
        if st.button("🚀 Generate IVR Code", type="primary", use_container_width=True):
            with st.spinner("Generating production IVR code..."):
                try:
                    # Convert using ARCOS-integrated converter
                    ivr_flow_dict, js_output = convert_mermaid_to_ivr(
                        mermaid_text, 
                        cf_general_csv=cf_general_csv, 
                        arcos_csv=arcos_csv
                    )
                    
                    st.session_state.ivr_code = js_output
                    
                    # Show success
                    st.success(f"✅ **IVR CODE GENERATED!** {len(ivr_flow_dict)} nodes created")
                    
                    # Critical fix verification
                    welcome_node = next((node for node in ivr_flow_dict if 'Live Answer' in node.get('label', '') or 'Welcome' in node.get('label', '')), None)
                    if welcome_node and welcome_node.get('branch', {}).get('1'):
                        st.success(f"🎯 **CRITICAL FIX VERIFIED**: Choice '1' → '{welcome_node['branch']['1']}'")
                    
                    # Show results
                    st.markdown("### 📋 Generated IVR Code")
                    
                    # Download button
                    st.download_button(
                        label="💾 Download IVR Code",
                        data=js_output,
                        file_name="production_ivr_flow.js",
                        mime="application/javascript"
                    )
                    
                    # Display JavaScript output
                    st.code(js_output, language="javascript")
                    
                    # Show analysis if requested
                    if show_analysis:
                        analyze_conversion_results(ivr_flow_dict)
                    
                    # Show comparison
                    if st.checkbox("📊 Show Before & After Comparison", value=True):
                        st.markdown("### 🔍 Before & After Comparison")
                        show_code_diff(mermaid_text, js_output)
                    
                    # Debug information
                    if show_debug:
                        st.markdown("### 🐛 Debug Information")
                        for i, node in enumerate(ivr_flow_dict):
                            with st.expander(f"Node {i+1}: {node.get('label', 'Unknown')}"):
                                st.json(node)
                
                except Exception as e:
                    st.error(f"❌ IVR generation failed: {str(e)}")
                    if show_debug:
                        st.exception(e)
                        st.text(traceback.format_exc())
    
    else:
        st.info("👈 Please enter Mermaid code or upload an image to begin")

    # Footer
    st.markdown("---")
    st.markdown("""
    **🎯 Complete Solution Features:**
    - 📷 **Image-to-Mermaid**: OpenAI-powered conversion of flowchart images
    - 🏗️ **ARCOS Foundation**: Core voice recordings for universal compatibility
    - 🎯 **Client Integration**: Company-specific voice file overrides
    - ✅ **Production Ready**: Generates deployable JavaScript following allflows LITE patterns
    - 🔧 **Flexible Design**: Works for existing and new customers without configuration
    - 🚀 **Complete Workflow**: From image upload to production code in minutes
    """)

if __name__ == "__main__":
    main()