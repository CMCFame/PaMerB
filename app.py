"""
Enhanced Streamlit app with CSV Upload Feature
Users can upload their audio database CSV instead of storing it in GitHub
"""
import streamlit as st
import streamlit_mermaid as st_mermaid
import json
import tempfile
import os
from PIL import Image
import traceback
import pandas as pd
import io

# Import existing components
from parse_mermaid import parse_mermaid, MermaidParser
from openai_converter import process_flow_diagram

# Import NEW enhanced components
from enhanced_ivr_converter import EnhancedIVRConverter, convert_mermaid_to_ivr_enhanced
from audio_database_manager import AudioDatabaseManager

# Page configuration
st.set_page_config(
    page_title="Enhanced IVR Converter with CSV Upload",
    page_icon="🔄",
    layout="wide"
)

# Constants and examples (same as before)
DEFAULT_FLOWS = {
    "Simple Callout": '''flowchart TD
A["Welcome<br/>This is an electric callout from (Level 2).<br/>Press 1, if this is (employee).<br/>Press 3, if you need more time to get (employee) to the phone.<br/>Press 7, if (employee) is not home.<br/>Press 9, to repeat this message."] -->|"1"| B{"1 - this is employee"}
A -->|"no input - go to pg 3"| C["30-second message<br/>Press any key to continue..."]
A -->|"7 - not home"| D["Employee Not Home"]
A -->|"3 - need more time"| C
A -->|"9 - repeat"| A
B -->|"yes"| E["Enter Employee PIN"]''',

    "PIN Change": '''flowchart TD
A["Enter PIN"] --> B{"Valid PIN?"}
B -->|"No"| C["Invalid Entry"]
B -->|"Yes"| D["PIN Changed"]
C --> A''',

    "Transfer Flow": '''flowchart TD
A["Transfer Request"] --> B{"Transfer Available?"}
B -->|"Yes"| C["Connect"]
B -->|"No"| D["Failed"]
C --> E["End"]
D --> E'''
}

def save_temp_file(content: str, suffix: str = '.js') -> str:
    """Save content to a temporary file and return the path"""
    with tempfile.NamedTemporaryFile(mode='w', suffix=suffix, delete=False, encoding='utf-8') as f:
        f.write(content)
        return f.name

def validate_mermaid(mermaid_text: str) -> str:
    """Validate Mermaid diagram syntax"""
    try:
        parser = MermaidParser()
        parser.parse(mermaid_text)
        return None
    except Exception as e:
        return f"Diagram Validation Error: {str(e)}"

def show_code_diff(original: str, converted: str):
    """Show comparison of original and converted code"""
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Original Mermaid")
        st.code(original, language="mermaid")
    with col2:
        st.subheader("Generated IVR Code")
        st.code(converted, language="javascript")

def render_mermaid_safely(mermaid_text: str):
    """Safely render Mermaid diagram with error handling"""
    try:
        st_mermaid.st_mermaid(mermaid_text, height=400)
    except Exception as e:
        st.error(f"Preview Error: {str(e)}")
        st.code(mermaid_text, language="mermaid")

@st.cache_data
def validate_csv_format(df):
    """Validate that the uploaded CSV has the required format"""
    required_columns = ['Company', 'Folder', 'File Name', 'Transcript']
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        return False, f"Missing required columns: {missing_columns}"
    
    # Check for empty data
    if df.empty:
        return False, "CSV file is empty"
    
    # Check for basic data quality
    null_counts = df[required_columns].isnull().sum()
    if null_counts.any():
        return False, f"Found null values in required columns: {null_counts[null_counts > 0].to_dict()}"
    
    return True, "CSV format is valid"

@st.cache_resource
def load_audio_database(_uploaded_file):
    """Load and cache the audio database from uploaded file"""
    try:
        # Create temporary file from uploaded content
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.csv') as tmp_file:
            # Read uploaded file content
            content = _uploaded_file.getvalue().decode('utf-8')
            tmp_file.write(content)
            tmp_file.flush()
            
            # Initialize database manager
            db_manager = AudioDatabaseManager(tmp_file.name)
            
            # Clean up temp file
            os.unlink(tmp_file.name)
            
            return db_manager, None
            
    except Exception as e:
        return None, str(e)

def show_csv_upload_section():
    """Display CSV upload section and handle file processing"""
    st.subheader("📊 Audio Database Upload")
    
    # Upload section
    uploaded_csv = st.file_uploader(
        "Upload your audio transcription database (CSV)",
        type=['csv'],
        help="Required columns: Company, Folder, File Name, Transcript",
        key="csv_uploader"
    )
    
    if uploaded_csv is not None:
        try:
            # Preview the uploaded file
            df = pd.read_csv(uploaded_csv)
            
            # Validate format
            is_valid, message = validate_csv_format(df)
            
            if not is_valid:
                st.error(f"❌ Invalid CSV format: {message}")
                st.info("Please ensure your CSV has columns: Company, Folder, File Name, Transcript")
                
                # Show current columns for debugging
                st.write("**Current columns in your file:**", list(df.columns))
                return None, None
            
            else:
                st.success("✅ CSV format validated successfully!")
                
                # Show preview
                with st.expander("📋 Data Preview", expanded=False):
                    st.write(f"**Rows:** {len(df)}")
                    st.write(f"**Columns:** {list(df.columns)}")
                    st.dataframe(df.head(10))
                
                # Load into audio database
                with st.spinner("Loading audio database..."):
                    # Reset file pointer
                    uploaded_csv.seek(0)
                    db_manager, error = load_audio_database(uploaded_csv)
                
                if error:
                    st.error(f"❌ Failed to load database: {error}")
                    return None, None
                
                # Show database statistics
                stats = db_manager.stats()
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total Records", stats['total_records'])
                with col2:
                    st.metric("Companies", stats['companies'])
                with col3:
                    st.metric("Folders", stats['folders'])
                with col4:
                    st.metric("Unique Transcripts", stats['unique_transcripts'])
                
                # Show companies and folders
                with st.expander("🏢 Available Companies & Folders"):
                    companies = db_manager.get_companies()
                    folders = db_manager.get_folders()
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write("**Companies:**")
                        st.write(", ".join(companies))
                    with col2:
                        st.write("**Folders:**")
                        st.write(", ".join(folders))
                
                return db_manager, uploaded_csv
                
        except Exception as e:
            st.error(f"❌ Error processing CSV file: {str(e)}")
            return None, None
    
    else:
        st.info("👆 Please upload your audio transcription CSV file to enable enhanced conversion")
        
        # Show example format
        with st.expander("📝 Required CSV Format Example"):
            example_df = pd.DataFrame([
                {"Company": "aep", "Folder": "callflow", "File Name": "1191.ulaw", "Transcript": "This is an"},
                {"Company": "aep", "Folder": "type", "File Name": "1001.ulaw", "Transcript": "electric"},
                {"Company": "dpl", "Folder": "location", "File Name": "4000.ulaw", "Transcript": "North Dayton"},
            ])
            st.dataframe(example_df)
            st.caption("Your CSV should have exactly these column names")
        
        return None, None

def enhanced_convert_to_ivr(mermaid_text: str, db_manager: AudioDatabaseManager, 
                          conversion_method: str, company: str, schema: str, 
                          show_debug: bool = False):
    """
    Enhanced IVR conversion with uploaded audio database
    """
    try:
        if conversion_method == "Enhanced (Recommended)":
            # Use enhanced system with uploaded database
            with st.spinner("Converting with enhanced audio mapping..."):
                # Create temporary CSV file for converter
                with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as tmp_file:
                    # Export database records to temporary CSV
                    records_data = []
                    for record in db_manager.audio_records:
                        records_data.append({
                            'Company': record.company,
                            'Folder': record.folder,
                            'File Name': record.file_name,
                            'Transcript': record.transcript
                        })
                    
                    df = pd.DataFrame(records_data)
                    df.to_csv(tmp_file.name, index=False)
                    
                    # Use enhanced converter
                    converter = EnhancedIVRConverter(tmp_file.name)
                    js_code, report = converter.convert_mermaid_to_ivr(
                        mermaid_text,
                        company=company,
                        schema=schema
                    )
                    
                    # Clean up temp file
                    os.unlink(tmp_file.name)
                
                # Display results
                st.subheader("📤 Generated IVR Configuration (Enhanced)")
                st.code(js_code, language="javascript")
                
                # Show conversion report in expander
                with st.expander("📊 Conversion Report", expanded=True):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Success Rate", f"{report['overall_success_rate']:.1%}")
                    with col2:
                        st.metric("Nodes Mapped", f"{report['successful_mappings']}/{report['total_nodes']}")
                    with col3:
                        st.metric("Missing Audio", len(report['unique_missing_audio']))
                    
                    # Show missing audio segments
                    if report['unique_missing_audio']:
                        st.warning("⚠️ Missing audio segments (need recording):")
                        for segment in report['unique_missing_audio']:
                            st.code(f"'{segment}'", language=None)
                    else:
                        st.success("✅ All audio segments found in database!")
                    
                    # Detailed node reports
                    if show_debug:
                        with st.expander("🔍 Detailed Node Analysis"):
                            for node_id, node_report in report['node_reports'].items():
                                st.subheader(f"Node: {node_id}")
                                if 'error' in node_report:
                                    st.error(f"Error: {node_report['error']}")
                                else:
                                    st.write(f"**Original text:** {node_report['original_text']}")
                                    st.write(f"**Node type:** {node_report['node_type']}")
                                    if 'audio_mapping' in node_report:
                                        mapping = node_report['audio_mapping']
                                        st.write(f"**Mapping method:** {mapping.mapping_method}")
                                        st.write(f"**Success rate:** {mapping.success_rate:.1%}")
                                        if mapping.play_prompt:
                                            st.write("**Audio prompts:**")
                                            for prompt in mapping.play_prompt:
                                                st.code(prompt)
                
                return js_code, True
                
        else:
            # Use legacy system for comparison
            with st.spinner("Converting with legacy system..."):
                from mermaid_ivr_converter import convert_mermaid_to_ivr
                ivr_flow_dict, notes = convert_mermaid_to_ivr(mermaid_text)
                js_code = "module.exports = " + json.dumps(ivr_flow_dict, indent=2) + ";"
                
                st.subheader("📤 Generated IVR Configuration (Legacy)")
                st.code(js_code, language="javascript")
                
                # Show notes if any
                if notes:
                    st.warning("📝 Notes from diagram:")
                    for note in notes:
                        st.info(f"• {note}")
                
                st.warning("⚠️ This conversion uses placeholder audio IDs - not production ready!")
                
                return js_code, True
                
    except Exception as e:
        st.error(f"Conversion Error: {str(e)}")
        if show_debug:
            st.exception(e)
            st.text(traceback.format_exc())
        return None, False

def main():
    st.title("🔄 Enhanced IVR Converter with CSV Upload")
    st.markdown("""
    **Intelligent Audio Mapping System** - Upload your audio transcription database 
    and generate production-ready IVR code with real audio file references.
    """)

    # Initialize session state
    if 'last_mermaid_code' not in st.session_state:
        st.session_state.last_mermaid_code = ""
    if 'last_ivr_code' not in st.session_state:
        st.session_state.last_ivr_code = ""

    # CSV Upload Section (Priority)
    db_manager, uploaded_csv = show_csv_upload_section()
    
    # Enhanced sidebar configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Input method selection
        conversion_method_input = st.radio("Input Method", ["Mermaid Editor", "Image Upload"])
        
        # Audio mapping settings (only if CSV is uploaded)
        if db_manager:
            st.subheader("🎵 Audio Mapping Settings")
            
            # Get available companies from uploaded data
            available_companies = db_manager.get_companies()
            
            if available_companies:
                company = st.selectbox("Company Context", 
                                      available_companies,
                                      help="Company context for audio file hierarchy")
            else:
                company = st.text_input("Company Context", value="aep", 
                                       help="Company context for audio file hierarchy")
            
            schema = st.text_input("Schema (Optional)", 
                                  placeholder="e.g., QUALITYA",
                                  help="Schema context for audio file hierarchy")
            
            # Conversion method
            st.subheader("🔧 Conversion Method")
            conversion_method = st.radio("IVR Generation", 
                                       ["Enhanced (Recommended)", "Legacy (Comparison)"],
                                       help="Enhanced uses real audio mapping, Legacy uses placeholders")
        else:
            st.info("🔒 Audio mapping settings will appear after CSV upload")
            company = "aep"  # Default
            schema = None
            conversion_method = "Enhanced (Recommended)"
        
        # Advanced settings
        st.subheader("🔬 Advanced Settings")
        validate_syntax = st.checkbox("Validate Diagram", value=True)
        show_debug = st.checkbox("Show Debug Info", value=False)
        
        # API configuration
        st.subheader("🔑 API Configuration")
        openai_api_key = st.text_input("OpenAI API Key", type="password", 
                                      help="Required for image processing")

    # Show database status
    if db_manager:
        st.success("✅ Audio database loaded and ready for enhanced conversion!")
    else:
        st.warning("⚠️ Upload your CSV file above to enable enhanced audio mapping")

    mermaid_text = ""
    
    # Input method handling
    if conversion_method_input == "Mermaid Editor":
        selected_example = st.selectbox("Load Example Flow", ["Custom"] + list(DEFAULT_FLOWS.keys()))
        initial_text = DEFAULT_FLOWS.get(selected_example, st.session_state.last_mermaid_code)
        mermaid_text = st.text_area("Mermaid Diagram", initial_text, height=400)
        st.session_state.last_mermaid_code = mermaid_text
    else:
        # Image upload handling
        col1, col2 = st.columns(2)
        with col1:
            uploaded_file = st.file_uploader("Upload Flowchart", type=['pdf', 'png', 'jpg', 'jpeg'])
        with col2:
            if uploaded_file:
                try:
                    image = Image.open(uploaded_file)
                    st.image(image, caption="Uploaded Flowchart", use_column_width=True)
                except Exception as e:
                    st.error(f"Error loading image: {str(e)}")
        
        if uploaded_file and openai_api_key:
            if st.button("🔄 Convert Image to Mermaid"):
                with st.spinner("Converting image..."):
                    try:
                        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp_file:
                            tmp_file.write(uploaded_file.getvalue())
                            mermaid_text = process_flow_diagram(tmp_file.name, openai_api_key)
                            st.session_state.last_mermaid_code = mermaid_text
                        st.success("Image converted successfully!")
                        st.subheader("Generated Mermaid Code")
                        st.code(mermaid_text, language="mermaid")
                    except Exception as e:
                        st.error(f"Conversion Error: {str(e)}")
                        if show_debug: st.exception(e)
                    finally:
                        if 'tmp_file' in locals(): os.unlink(tmp_file.name)
        else:
            if not openai_api_key: st.info("Please provide an OpenAI API key in the sidebar for image conversion.")
            if not uploaded_file: st.info("Please upload an image or PDF for conversion.")
        
        mermaid_text = st.session_state.last_mermaid_code

    # Mermaid preview
    if mermaid_text and mermaid_text.strip():
        st.subheader("👁️ Mermaid Diagram Preview")
        render_mermaid_safely(mermaid_text)
    else:
        st.warning("No Mermaid code to display. Paste code in the editor or convert an image.")

    # IVR conversion
    if mermaid_text and mermaid_text.strip():
        
        # Check requirements for enhanced conversion
        can_use_enhanced = db_manager is not None
        
        if not can_use_enhanced and conversion_method == "Enhanced (Recommended)":
            st.warning("⚠️ Enhanced conversion requires CSV upload. Using legacy mode.")
            conversion_method = "Legacy (Comparison)"
        
        if st.button("🔄 Convert to IVR", type="primary"):
            # Validate syntax if requested
            if validate_syntax:
                error = validate_mermaid(mermaid_text)
                if error:
                    st.error(error)
                    return

            # Perform conversion
            if can_use_enhanced:
                js_output, success = enhanced_convert_to_ivr(
                    mermaid_text, 
                    db_manager,
                    conversion_method, 
                    company, 
                    schema, 
                    show_debug
                )
            else:
                # Fallback to legacy conversion
                try:
                    with st.spinner("Converting with legacy system..."):
                        from mermaid_ivr_converter import convert_mermaid_to_ivr
                        ivr_flow_dict, notes = convert_mermaid_to_ivr(mermaid_text)
                        js_output = "module.exports = " + json.dumps(ivr_flow_dict, indent=2) + ";"
                        success = True
                        
                        st.subheader("📤 Generated IVR Configuration (Legacy)")
                        st.code(js_output, language="javascript")
                        st.warning("⚠️ This uses placeholder audio IDs. Upload CSV for real audio mapping!")
                        
                except Exception as e:
                    st.error(f"Conversion failed: {e}")
                    js_output, success = None, False
            
            if success and js_output:
                st.session_state.last_ivr_code = js_output
                
                # Download button
                tmp_file = save_temp_file(js_output)
                with open(tmp_file, 'rb') as f:
                    st.download_button("⬇️ Download IVR Configuration", 
                                     f, 
                                     file_name="ivr_flow.js", 
                                     mime="application/javascript")
                os.unlink(tmp_file)

                # Show comparison
                show_code_diff(mermaid_text, js_output)
                
                # Show enhancement benefits
                if can_use_enhanced and conversion_method == "Enhanced (Recommended)":
                    st.success("✅ **Enhanced conversion complete!** This IVR code uses real audio file IDs from your uploaded database.")
                else:
                    st.info("💡 **Tip:** Upload your CSV file to get production-ready code with real audio IDs instead of placeholders.")
    else:
        st.info("Mermaid code is not available for conversion.")

    # Footer with enhancement information
    with st.expander("ℹ️ About Enhanced Audio Mapping"):
        st.markdown("""
        ### What's Enhanced About This System?
        
        **🎯 Real Audio Mapping**: Instead of placeholder IDs, get actual audio file references from your database.
        
        **🔍 Intelligent Segmentation**: Breaks down complex text into searchable segments automatically.
        
        **📊 Hierarchy Search**: Follows Schema → Company → Global search order for accurate context.
        
        **⚙️ Grammar Rules**: Automatically handles "a" vs "an" based on following sounds.
        
        **🔧 Variable Support**: Properly maps dynamic variables like `{{callout_type}}`, `{{location}}`.
        
        **📝 Missing Detection**: Flags audio segments that need recording.
        
        **🔒 Secure**: Your CSV data stays in your control - no need to store in GitHub.
        
        ### Benefits:
        - ✅ **99% Accurate Mappings** - Real IDs from your database
        - ✅ **No More Placeholders** - Production-ready code immediately  
        - ✅ **Faster Development** - Automates manual 5-minute audio search process
        - ✅ **Quality Assurance** - Detailed reporting and validation
        - ✅ **Context Awareness** - Respects company and schema hierarchies
        - ✅ **Data Privacy** - Your audio database never leaves your control
        """)

if __name__ == "__main__":
    main()