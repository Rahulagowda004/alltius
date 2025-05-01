from langgraph.graph import START, StateGraph
from typing_extensions import List, TypedDict
from langchain_groq import ChatGroq
from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain.embeddings import HuggingFaceEmbeddings
import os

load_dotenv()

llm = ChatGroq("llama3-70b-8192",api_key=os.getenv("GROQ_API_KEY"))

embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-mpnet-base-v2")

vector_store1 = FAISS.load_local("src/RAG/angleone_data/index.faiss", embeddings=embedding_model)

vector_store2 = FAISS.load_local("src/RAG/pdfs_data/index.faiss", embeddings=embedding_model)

class State(TypedDict):
    question: str
    context: List[Document]
    answer: str

# Define application steps
def angleone(state: State):
    retrieved_docs = vector_store1.similarity_search(state["question"])
    return {"context": retrieved_docs}

def pdf(state: State):
    retrieved_docs = vector_store2.similarity_search(state["question"])
    return {"context": retrieved_docs}

def generate(state: State):
    docs_content = "\n\n".join(doc.page_content for doc in state["context"])
    messages = prompt.invoke({"question": state["question"], "context": docs_content})
    response = llm.invoke(messages)
    return {"answer": response.content}

# Compile application and test
graph_builder = StateGraph(State).add_sequence([angleone, generate])
graph_builder.add_edge(START, "angleone")
graph_builder.add_edge("angleone", "pdf")
graph_builder.add_edge("pdf", "generate")
graph = graph_builder.compile()