"""
Simple test script to isolate the AxiosError 400 issue
Run this to test if the basic Streamlit file uploader works
"""

import streamlit as st

st.title("🔬 File Upload Test")
st.info("This is a minimal test to isolate the AxiosError 400 issue")

# Basic file uploader test
uploaded_file = st.file_uploader(
    "Test file upload:", 
    type=['pdf', 'png', 'jpg', 'jpeg']
)

if uploaded_file:
    st.success(f"✅ File uploaded successfully!")
    st.write(f"**Name**: {uploaded_file.name}")
    st.write(f"**Type**: {uploaded_file.type}")
    st.write(f"**Size**: {uploaded_file.size:,} bytes")
    
    # Try to read the file
    try:
        file_data = uploaded_file.read()
        st.success(f"✅ File read successfully: {len(file_data):,} bytes")
        uploaded_file.seek(0)  # Reset pointer
    except Exception as e:
        st.error(f"❌ Error reading file: {str(e)}")
else:
    st.info("👆 Upload a file to test")

st.markdown("---")
st.info("If this test works but the main app doesn't, the issue is in the main app logic.")
st.info("If this test also fails with AxiosError 400, it's a Streamlit/browser issue.")