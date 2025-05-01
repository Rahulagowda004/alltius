from langgraph.graph import START, StateGraph
from typing_extensions import List, TypedDict
from langchain_groq import ChatGroq
from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.prompts import ChatPromptTemplate
import os

load_dotenv()

# Initialize the LLM with proper parameters
llm = ChatGroq(model_name="llama3-70b-8192", api_key="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")

embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-mpnet-base-v2")

vector_store = FAISS.load_local("src/RAG/angleone_data/index.faiss", embeddings=embedding_model)

class State(TypedDict):
    question: str
    context: List[Document]
    answer: str

# Define the prompt template
prompt = ChatPromptTemplate.from_template("""
Answer the following question based on the context provided:

Context: {context}
Question: {question}

Answer:
""")

# Define application steps
def retriever(state: State):
    retrieved_docs = vector_store.similarity_search(state["question"])
    return {"context": retrieved_docs}

def generate(state: State):
    docs_content = "\n\n".join(doc.page_content for doc in state["context"])
    messages = prompt.invoke({"question": state["question"], "context": docs_content})
    response = llm.invoke(messages)
    return {"answer": response.content}

graph_builder = StateGraph(State)

graph_builder.add_node("retriever", retriever)
graph_builder.add_node("generate", generate)

graph_builder.add_edge(START, "retriever")
graph_builder.add_edge("retriever", "generate")
graph = graph_builder.compile()

from IPython.display import Image, display

display(Image(graph.get_graph().draw_mermaid_png()))