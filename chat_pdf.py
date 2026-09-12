import os
import tempfile
import streamlit as st
from embedchain import App
from streamlit_chat import message

def embedchain_bot(db_path, api_key):
    os.environ["OPENAI_API_KEY"] = api_key
    return App.from_config(
        config={
            "llm": {"provider": "openai", "config": {"api_key": api_key}},
            "vectordb": {"provider": "chroma", "config": {"dir": db_path}},
            "embedder": {"provider": "openai", "config": {"api_key": api_key}},
        }
    )

st.set_page_config(page_title="Chat with PDF", page_icon="📄")
st.title("📄 Chat with PDF")

openai_access_token = st.sidebar.text_input("OpenAI API Key", type="password")

if not openai_access_token:
    st.info("Please enter your OpenAI API Key in the sidebar to get started.")
else:
    os.environ["OPENAI_API_KEY"] = openai_access_token

    if "db_path" not in st.session_state:
        st.session_state.db_path = tempfile.mkdtemp()
    
    if "app" not in st.session_state or st.session_state.get("api_key") != openai_access_token:
        st.session_state.app = embedchain_bot(st.session_state.db_path, openai_access_token)
        st.session_state.api_key = openai_access_token

    if "messages" not in st.session_state:
        st.session_state.messages = []

    with st.sidebar:
        st.header("Upload PDF")
        pdf_file = st.file_uploader("Upload a PDF file", type="pdf")

        if pdf_file:
            if st.button("Add to Knowledge Base"):
                with st.spinner("Processing PDF..."):
                    try:
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as f:
                            f.write(pdf_file.getvalue())
                            temp_path = f.name
                        
                        st.session_state.app.add(temp_path, data_type="pdf_file")
                        if os.path.exists(temp_path):
                            os.remove(temp_path)
                        st.success(f"Added '{pdf_file.name}' to knowledge base!")
                    except Exception as e:
                        st.error(f"Error processing PDF: {str(e)}")

    # Display chat messages
    for i, msg in enumerate(st.session_state.messages):
        message(msg["content"], is_user=msg["role"] == "user", key=str(i))

    if prompt := st.chat_input("Ask a question about the PDF"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        message(prompt, is_user=True)

        with st.spinner("Thinking..."):
            try:
                answer = st.session_state.app.chat(prompt)
                st.session_state.messages.append({"role": "assistant", "content": answer})
                message(answer)
            except Exception as e:
                err_msg = str(e)
                if "APIStatusError" in err_msg or "AuthenticationError" in err_msg or "401" in err_msg:
                    st.error("❌ **Invalid OpenAI API Key or Missing Quota!**\n\n"
                             "OpenAI ne request reject kar diya hai. Kripya check karein:\n"
                             "1. Aapne sahi OpenAI API Key (`sk-proj-...`) enter ki hai ya nahi.\n"
                             "2. Aapke OpenAI account par Billing/Credits active hain ya nahi (https://platform.openai.com/account/billing).\n\n"
                             "*(Nayi API Key enter karne ke baad page refresh karein)*")
                else:
                    st.error(f"❌ Error: {err_msg}")


        