import os
import warnings
import streamlit as st
from dotenv import load_dotenv
from src.RAG.bot import RAGChatBot
import traceback
import sys

warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

os.environ["STREAMLIT_SERVER_WATCH_FILE_SYSTEM"] = "false"

load_dotenv()

api_key = os.getenv("GROQ_API_KEY")
if api_key:
    os.environ["GROQ_API_KEY"] = api_key
else:
    st.error("GROQ_API_KEY not found in environment variables. Please check your .env file.")

if "rag_bot" not in st.session_state:
    with st.spinner("Initializing RAG chatbot..."):
        try:
            embedded_data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                             "src", "RAG", "embedded_data")
            if not os.path.exists(embedded_data_path):
                st.warning(f"Embedded data directory not found at: {embedded_data_path}")
                
            st.session_state["rag_bot"] = RAGChatBot(
                model_name="llama3-70b-8192",
                verbose=True
            )
            st.success("Chatbot initialized with llama3-70b-8192!")
        except Exception as e:
            error_msg = f"Error initializing chatbot: {str(e)}"
            st.error(error_msg)
            exc_type, exc_value, exc_traceback = sys.exc_info()
            tb_str = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
            st.code(tb_str, language="python")

with st.sidebar:
    st.title("Alltius Customer Care")
    
    if st.button("Clear Chat History"):
        if st.session_state.get("rag_bot"):
            st.session_state["rag_bot"].clear_chat_history()
        if "messages" in st.session_state:
            st.session_state["messages"] = [{"role": "assistant", "content": "Chat history cleared. How can I help you?"}]
        st.success("Chat history cleared!")

st.title("💬 Alltius Customer Care Chatbot")
st.caption("🚀 Powered by RAG and Groq LLM (llama3-70b-8192)")

if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "assistant", "content": "Welcome to Alltius Customer Care! How can I help you today?"}]

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

if prompt := st.chat_input():
    if not st.session_state.get("rag_bot"):
        st.error("Chatbot initialization failed. Please refresh the page to try again.")
        st.stop()
    
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)
    
    with st.spinner("Thinking..."):
        result = st.session_state["rag_bot"].answer_question(prompt)
        answer = result.get("answer", "I'm sorry, I encountered an issue processing your question.")
        sources = result.get("sources", [])
        elapsed_time = result.get("elapsed_time", "")
    
    st.session_state.messages.append({"role": "assistant", "content": answer})
    
    response_container = st.chat_message("assistant")
    response_container.write(answer)
    
    if sources:
        with response_container.expander("Sources"):
            for i, source in enumerate(sources, 1):
                if source.get("title") and source.get("title") != "Unknown":
                    st.markdown(f"**{i}. {source['title']}**")
                    if source.get("url"):
                        st.markdown(f"URL: {source['url']}")
    
    if elapsed_time:
        st.caption(f"Response time: {elapsed_time}")