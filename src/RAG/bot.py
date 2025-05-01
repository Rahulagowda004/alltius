import os
import sys
import torch
from typing import List, Dict, Any, Optional
from pathlib import Path
import time
from dotenv import load_dotenv

from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_groq import ChatGroq
from langchain_community.vectorstores import FAISS
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferWindowMemory

from .embedder import DocumentEmbedder

load_dotenv()

BASE_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
INDEX_DIR = BASE_DIR / "embedded_data"
FALLBACK_INDEX_DIR = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))) / "old_ones" / "embedded_data"

if not os.getenv("GROQ_API_KEY"):
    print("Error: GROQ_API_KEY is not set in environment variables or .env file")
    print("Please set your Groq API key and try again")
    sys.exit(1)

class RAGChatBot:
    def __init__(
        self,
        model_name: str = "llama3-70b-8192",
        temperature: float = 0.5,
        top_k: int = 6,
        embedding_model_name: str = "sentence-transformers/all-mpnet-base-v2",
        verbose: bool = False
    ):
        self.model_name = model_name
        self.temperature = temperature
        self.top_k = top_k
        self.verbose = verbose
        
        print(f"Initializing RAG Chatbot with Groq model: {model_name}")
        
        self.embedder = DocumentEmbedder(
            embedding_model_name=embedding_model_name,
            chunk_size=512,
            chunk_overlap=128,
            use_gpu=torch.cuda.is_available()
        )
        
        self.llm = ChatGroq(
            model_name=model_name,
            temperature=temperature
        )
        
        self.memory = ConversationBufferWindowMemory(
            memory_key="chat_history",
            return_messages=True,
            k=5,
            output_key="answer"
        )
        
        self._setup_rag_chain()
        
    def _setup_rag_chain(self):
        print("Loading FAISS embeddings...")
        try:
            self.vectorstore = None
            index_locations = [INDEX_DIR, FALLBACK_INDEX_DIR]
            
            for location in index_locations:
                if os.path.exists(location) and os.path.isdir(location):
                    print(f"Looking for FAISS index in: {location}")
                    
                    if os.path.exists(location / "index.faiss") and os.path.exists(location / "index.pkl"):
                        try:
                            self.vectorstore = FAISS.load_local(
                                location, 
                                self.embedder.embeddings,
                                allow_dangerous_deserialization=True
                            )
                            print(f"Successfully loaded embeddings from {location} with {self.vectorstore.index.ntotal} vectors")
                            break
                        except Exception as e:
                            print(f"Error loading embeddings from {location}: {str(e)}")
                            continue
            
            if not self.vectorstore:
                print("Error: Could not load embeddings from any location.")
                return
            
        except Exception as e:
            print(f"Error loading embeddings: {str(e)}")
            import traceback
            traceback.print_exc()
            return
            
        self.retriever = self.vectorstore.as_retriever(
            search_type="mmr",
            search_kwargs={
                "k": self.top_k,
                "fetch_k": self.top_k * 2,
                "score_threshold": 0.3
            }
        )
        
        template = """You are an intelligent assistant for Alltius customer care, answering questions based on the provided context.
        
        Context information for your answer:
        {context}
        
        Chat History:
        {chat_history}
        
        Question: {question}
        
        Instructions:
        - Answer the user's question based ONLY on the provided context.
        - If the context doesn't contain the answer, say "I don't have enough information to answer that question." Do NOT make up information.
        - Keep your answers helpful, concise, and accurate.
        - Always maintain a professional and friendly tone.
        - Be specific in your answers using exact details from the context.
        - Include all relevant details to completely answer the question.
        - If the context has multiple potential answers, present the most relevant one first.
        
        Answer: """
        
        self.prompt = PromptTemplate(
            template=template,
            input_variables=["context", "chat_history", "question"]
        )
        
        self.chain = ConversationalRetrievalChain.from_llm(
            llm=self.llm,
            retriever=self.retriever,
            memory=self.memory,
            combine_docs_chain_kwargs={
                "prompt": self.prompt
            },
            return_source_documents=True,
            verbose=self.verbose
        )
        
        print("RAG chain setup complete with Groq LLM")
    
    def answer_question(self, question: str) -> Dict[str, Any]:
        if not hasattr(self, 'chain') or not self.chain:
            return {"answer": "System is not initialized properly. Please check if embeddings are loaded."}
        
        start_time = time.time()
        
        try:
            result = self.chain.invoke({"question": question})
            
            answer = result.get("answer", "")
            source_docs = result.get("source_documents", [])
            
            sources = []
            for i, doc in enumerate(source_docs):
                source_info = {
                    "content": doc.page_content[:200] + "...",
                    "title": doc.metadata.get("title", "Unknown"),
                    "section": doc.metadata.get("section", ""),
                    "url": doc.metadata.get("url", ""),
                    "source": doc.metadata.get("source", ""),
                    "filename": doc.metadata.get("filename", "")
                }
                sources.append(source_info)
            
            elapsed_time = time.time() - start_time
            
            return {
                "answer": answer,
                "sources": sources,
                "elapsed_time": f"{elapsed_time:.2f} seconds",
                "retrieved_docs": len(source_docs)
            }
            
        except Exception as e:
            print(f"Error processing question: {str(e)}")
            return {"answer": f"An error occurred: {str(e)}"}
    
    def clear_chat_history(self):
        self.memory.clear()
        print("Chat history cleared")

    def load_external_documents(self, documents_dir: str) -> None:
        if not self.vectorstore:
            self._setup_rag_chain()
        
        if not self.vectorstore:
            print("Error: Vector store not initialized. Cannot load external documents.")
            return
            
        try:
            path = Path(documents_dir)
            docs = []
            
            for json_file in path.glob("*.json"):
                try:
                    docs.extend(self.embedder.process_json_file(str(json_file)))
                except AttributeError:
                    print(f"Warning: process_json_file method not available. Skipping {json_file}")
            
            docx_files = list(path.glob("*.docx"))
            if docx_files:
                docs.extend(self.embedder.process_docx_files(str(documents_dir)))
            
            if docs:
                if self.vectorstore:
                    self.vectorstore.add_documents(docs)
                else:
                    self.vectorstore = FAISS.from_documents(docs, self.embedder.embeddings)
                
                self.retriever = self.vectorstore.as_retriever(
                    search_type="similarity",
                    search_kwargs={"k": self.top_k}
                )
                print(f"External documents from {documents_dir} added to RAG system")
            else:
                print(f"No documents found or processed from {documents_dir}")
            
        except Exception as e:
            print(f"Error loading external documents: {str(e)}")

def interactive_chat():
    print("\n==== Alltius Customer Care RAG Chatbot ====")
    print("Initializing chatbot with Groq LLM and FAISS embeddings...")
    
    print(f"\nInitializing with model: llama3-70b-8192")
    bot = RAGChatBot(model_name="llama3-70b-8192", verbose=True)
    
    if not hasattr(bot, 'vectorstore') or not bot.vectorstore:
        print("\nError: Could not load FAISS embeddings. Please ensure the 'embedded data' directory contains valid index files.")
        print("You may need to run the json embedding process first with: python -m src.RAG.run_json_embedding")
        return
    
    print("\nChat is ready! Type your questions or 'exit' to quit.")
    print("Type 'clear' to clear chat history.")
    print("\nYou can ask questions about Angel One support documents and files in the artifacts directory.")
    
    while True:
        user_input = input("\nYou: ").strip()
        
        if user_input.lower() in ["exit", "quit", "bye"]:
            print("Chatbot: Goodbye!")
            break
            
        if user_input.lower() == "clear":
            bot.clear_chat_history()
            print("Chatbot: Chat history cleared.")
            continue
            
        if not user_input:
            continue
            
        print("\nChatbot is thinking...")
        result = bot.answer_question(user_input)
        
        print(f"\nChatbot: {result['answer']}")
        
        if result.get("sources"):
            print("\nSources:")
            for i, source in enumerate(result["sources"], 1):
                if source.get("title") and source.get("title") != "Unknown":
                    print(f"  {i}. {source['title']}")
                    if source.get("url"):
                        print(f"     URL: {source['url']}")
                elif source.get("filename"):
                    print(f"  {i}. File: {source['filename']}")
        
        if result.get("elapsed_time"):
            print(f"\nResponse time: {result['elapsed_time']}")

if __name__ == "__main__":
    interactive_chat()