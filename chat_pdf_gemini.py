import os
import tempfile
import streamlit as st
from dotenv import load_dotenv
from google import genai
from pypdf import PdfReader
import pdfplumber

# Load environment variables from .env file
load_dotenv()

# -----------------------------------------------------------------------------
# 1. Page Configuration
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Chat with PDF",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# API Key configuration (loads from .env file)
API_KEY = os.getenv("GEMINI_API_KEY", "")





# -----------------------------------------------------------------------------
# 2. Custom Clean CSS (Hide Deploy Button & Header Completely)
# -----------------------------------------------------------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        color: #0f172a !important;
    }
    
    /* Hide Streamlit Header, Deploy Button, Status Widget, Stop Icon, and Toolbar completely */
    header, 
    [data-testid="stHeader"], 
    [data-testid="stAppDeployButton"], 
    .stDeployButton, 
    [data-testid="stToolbar"], 
    [data-testid="stStatusWidget"], 
    [data-testid="stDecoration"],
    [data-testid="stActionButtonIcon"],
    [data-testid="stHeaderActionElements"],
    .stActionButton,
    #MainMenu, 
    footer {
        display: none !important;
        visibility: hidden !important;
        height: 0 !important;
        width: 0 !important;
        opacity: 0 !important;
        pointer-events: none !important;
    }

    /* Main Container Padding */
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 2rem !important;
        max-width: 900px !important;
    }

    /* App Background */
    .stApp {
        background: #f8fafc !important;
    }

    /* Center Upload Box */
    .upload-container {
        background: #ffffff;
        border: 2px dashed #cbd5e1;
        border-radius: 16px;
        padding: 2.5rem 1.5rem;
        text-align: center;
        margin-top: 1.5rem;
        margin-bottom: 2rem;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03);
    }

    /* Document Status Bar */
    .doc-bar {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 0.85rem 1.25rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 1.5rem;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
    }

    /* Clean Buttons */
    .stButton>button {
        border-radius: 10px !important;
        background: #2563eb !important;
        color: #ffffff !important;
        font-weight: 600 !important;
        border: none !important;
        padding: 0.5rem 1rem !important;
        transition: all 0.2s ease !important;
    }

    .stButton>button:hover {
        background: #1d4ed8 !important;
        transform: translateY(-1px);
    }

    /* Chat Messages styling */
    [data-testid="stChatMessage"] {
        background-color: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 12px !important;
        padding: 12px 16px !important;
        margin-bottom: 12px !important;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 3. Helper Functions
# -----------------------------------------------------------------------------
def extract_text_from_pdf(uploaded_file):
    """Dual extraction engine using pdfplumber with pypdf fallback."""
    extracted_text = ""
    page_count = 0
    
    try:
        bytes_data = uploaded_file.getvalue()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(bytes_data)
            tmp_path = tmp_file.name
            
        with pdfplumber.open(tmp_path) as pdf:
            page_count = len(pdf.pages)
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    extracted_text += t + "\n"
        os.remove(tmp_path)
    except Exception:
        pass

    if not extracted_text.strip():
        try:
            uploaded_file.seek(0)
            pdf_reader = PdfReader(uploaded_file)
            page_count = len(pdf_reader.pages)
            for page in pdf_reader.pages:
                t = page.extract_text()
                if t:
                    extracted_text += t + "\n"
        except Exception as e:
            st.error(f"PDF Extraction Error: {str(e)}")

    word_count = len(extracted_text.split())
    return extracted_text.strip(), page_count, word_count

def ask_gemini(document_text, conversation_history, new_user_prompt):
    """Generate answer from Gemini 3.6 Flash based on PDF context."""
    client = genai.Client(api_key=API_KEY)
    
    # Build prompt payload
    prompt_payload = f"""[DOCUMENT CONTEXT]
File Name: {st.session_state.get('current_file_name', 'PDF Document')}
Content:
{document_text[:100000]}

[INSTRUCTION]
Answer the user's question accurately based ONLY on the document context above. 
If the answer is not mentioned in the document, politely inform the user.
Format your answer clearly using Markdown with bold points, headings, or lists where helpful.

[USER QUESTION]
{new_user_prompt}
"""
    
    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt_payload,
        config={
            "system_instruction": "You are a helpful AI assistant that answers questions accurately based on uploaded PDF documents."
        }
    )
    return response.text

# -----------------------------------------------------------------------------
# 4. Session State Initialization
# -----------------------------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []
if "pdf_text" not in st.session_state:
    st.session_state.pdf_text = ""
if "file_key" not in st.session_state:
    st.session_state.file_key = ""

# -----------------------------------------------------------------------------
# 5. Header Title
# -----------------------------------------------------------------------------
st.markdown("<h1 style='text-align: center; margin-bottom: 4px; font-weight: 700; color: #0f172a;'>📄 Chat with PDF</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #64748b; margin-bottom: 1.5rem;'>Upload any PDF document and ask questions instantly</p>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 6. Main Center Stage Uploader vs Chatbot Logic
# -----------------------------------------------------------------------------
if not st.session_state.pdf_text:
    # Center PDF Upload Card
    st.markdown("""
    <div style="background: #ffffff; border: 2px dashed #cbd5e1; border-radius: 16px; padding: 2rem; text-align: center; margin-bottom: 1rem;">
        <div style="font-size: 2.5rem; margin-bottom: 0.5rem;">📁</div>
        <h3 style="margin-bottom: 0.25rem; font-weight: 600;">Upload PDF Document</h3>
        <p style="color: #64748b; font-size: 0.9rem; margin-bottom: 1rem;">Select or drop your PDF file below to start chatting</p>
    </div>
    """, unsafe_allow_html=True)

    uploaded_file = st.file_uploader(
        "Choose a PDF file",
        type=["pdf"],
        label_visibility="collapsed"
    )

    if uploaded_file:
        with st.spinner("Processing PDF document..."):
            text, pages, words = extract_text_from_pdf(uploaded_file)
            if text:
                st.session_state.pdf_text = text
                st.session_state.current_file_name = uploaded_file.name
                st.session_state.pages = pages
                st.session_state.words = words
                st.session_state.file_key = f"{uploaded_file.name}_{uploaded_file.size}"
                st.session_state.messages = [
                    {"role": "assistant", "content": f"Hello! I have read **{uploaded_file.name}** ({pages} pages, ~{words:,} words). What would you like to know about this PDF?"}
                ]
                st.rerun()
            else:
                st.error("⚠️ Could not extract text from this PDF. It might be scanned or password protected.")

else:
    # PDF Info Header & Upload New PDF Button
    col_doc_info, col_reset = st.columns([3, 1])
    with col_doc_info:
        st.markdown(f"""
        <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 10px; padding: 10px 16px; font-weight: 600; color: #2563eb; font-size: 0.95rem;">
            📌 {st.session_state.current_file_name} <span style="color: #64748b; font-weight: 400; margin-left: 8px;">({st.session_state.pages} pages, ~{st.session_state.words:,} words)</span>
        </div>
        """, unsafe_allow_html=True)
    with col_reset:
        if st.button("➕ Upload New PDF", use_container_width=True):
            st.session_state.pdf_text = ""
            st.session_state.messages = []
            st.session_state.file_key = ""
            st.rerun()

    st.markdown("<hr style='margin: 1rem 0 1.5rem 0; border: none; border-top: 1px solid #e2e8f0;'>", unsafe_allow_html=True)

    # Render Chat Messages
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"], avatar="👤" if msg["role"] == "user" else "🤖"):
            st.markdown(msg["content"])

    # Chat Input Box
    if prompt := st.chat_input(f"Ask anything about {st.session_state.current_file_name}..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt)

        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Analyzing PDF..."):
                try:
                    answer = ask_gemini(st.session_state.pdf_text, st.session_state.messages, prompt)
                    st.markdown(answer)
                    st.session_state.messages.append({"role": "assistant", "content": answer})
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")




