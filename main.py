import os
import warnings
import streamlit as st
from dotenv import load_dotenv
from src.RAG.bot import RAGChatBot

# Suppress deprecation warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

# Disable Streamlit file watcher to avoid PyTorch errors
os.environ["STREAMLIT_SERVER_WATCH_FILE_SYSTEM"] = "false"

# Load environment variables
load_dotenv()

# Load API key from .env file
api_key = os.getenv("GROQ_API_KEY")
if api_key:
    os.environ["GROQ_API_KEY"] = api_key

# Initialize session state for the RAG chatbot
if "rag_bot" not in st.session_state:
    with st.spinner("Initializing RAG chatbot..."):
        try:
            st.session_state["rag_bot"] = RAGChatBot(
                model_name="llama3-70b-8192",
                verbose=False
            )
            st.success("Chatbot initialized with llama3-70b-8192!")
        except Exception as e:
            st.error(f"Error initializing chatbot: {str(e)}")

# Sidebar for configuration
with st.sidebar:
    st.title("Alltius Customer Care")
    
    # Clear chat history button
    if st.button("Clear Chat History"):
        if st.session_state.get("rag_bot"):
            st.session_state["rag_bot"].clear_chat_history()
        if "messages" in st.session_state:
            st.session_state["messages"] = [{"role": "assistant", "content": "Chat history cleared. How can I help you?"}]
        st.success("Chat history cleared!")

# Main chat interface
st.title("💬 Alltius Customer Care Chatbot")
st.caption("🚀 Powered by RAG and Groq LLM (llama3-70b-8192)")

# Initialize messages in session state if not already there
if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "assistant", "content": "Welcome to Alltius Customer Care! How can I help you today?"}]

# Display chat messages
for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

# Chat input
if prompt := st.chat_input():
    # Check if chatbot is initialized
    if not st.session_state.get("rag_bot"):
        # This should rarely happen since we initialize on startup,
        # but just in case there was an error during initialization
        st.error("Chatbot initialization failed. Please refresh the page to try again.")
        st.stop()
    
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)
    
    # Get response from RAG chatbot
    with st.spinner("Thinking..."):
        result = st.session_state["rag_bot"].answer_question(prompt)
        answer = result.get("answer", "I'm sorry, I encountered an issue processing your question.")
        sources = result.get("sources", [])
        elapsed_time = result.get("elapsed_time", "")
    
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": answer})
    
    # Display response with sources if available
    response_container = st.chat_message("assistant")
    response_container.write(answer)
    
    # Show sources if available
    if sources:
        with response_container.expander("Sources"):
            for i, source in enumerate(sources, 1):
                if source.get("title") and source.get("title") != "Unknown":
                    st.markdown(f"**{i}. {source['title']}**")
                    if source.get("url"):
                        st.markdown(f"URL: {source['url']}")
    
    # Show response time
    if elapsed_time:
        st.caption(f"Response time: {elapsed_time}")