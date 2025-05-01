import os
import json
import glob
import time
from typing import List, Dict, Any, Optional
from tqdm import tqdm
import re
import numpy as np
from pathlib import Path

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
BASE_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
RAG_DATA_DIR = BASE_DIR / "rag_data"
INDEX_DIR = BASE_DIR / "vector_index"
BATCH_SIZE = 100  # Number of documents to process at once

# Embedding model config
DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DEVICE = "cpu"  # Set to "cuda" if GPU is available


class DocumentEmbedder:
    """Handles document loading, preprocessing and embedding for RAG applications"""

    def __init__(
        self,
        embedding_model: str = DEFAULT_EMBEDDING_MODEL,
        device: str = EMBEDDING_DEVICE,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ):
        self.embedding_model = embedding_model
        self.device = device
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.embeddings = HuggingFaceEmbeddings(
            model_name=embedding_model,
            model_kwargs={"device": device},
            encode_kwargs={"normalize_embeddings": True}
        )
        self.vectorstore = None
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        
        print(f"Initialized DocumentEmbedder with model: {embedding_model} on {device}")

    def _get_document_batches(self, json_files):
        """Process document files in batches to avoid memory issues"""
        
        total_processed = 0
        print(f"Processing {len(json_files)} files in batches of {BATCH_SIZE}")
        
        for i in range(0, len(json_files), BATCH_SIZE):
            batch_files = json_files[i:i+BATCH_SIZE]
            batch_documents = []
            
            for file_path in tqdm(batch_files, desc=f"Batch {i//BATCH_SIZE + 1}"):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    
                    metadata = data.get("metadata", {})
                    structured_content = data.get("structured_content", {})
                    
                    # Process each chunk as a separate document
                    for j, chunk in enumerate(structured_content.get("chunks", [])):
                        # Find which section this chunk belongs to (if any)
                        section_heading = ""
                        for section in structured_content.get("sections", []):
                            if chunk in section.get("content", ""):
                                section_heading = section.get("heading", "")
                                break
                        
                        # Create document with rich metadata
                        doc_metadata = {
                            "url": metadata.get("url", ""),
                            "title": metadata.get("title", ""),
                            "source": metadata.get("source", "Angel One Support"),
                            "section": section_heading,
                            "chunk_id": j,
                            "file_path": file_path
                        }
                        
                        batch_documents.append(Document(page_content=chunk, metadata=doc_metadata))
                
                except Exception as e:
                    print(f"Error processing {file_path}: {str(e)}")
            
            total_processed += len(batch_documents)
            print(f"Processed {total_processed} document chunks in total")
            yield batch_documents

    def process_pdf_files(self, pdf_dir: str) -> List[Document]:
        """Process PDF files from a directory"""
        try:
            from langchain_community.document_loaders import PyPDFLoader
            from langchain_community.document_loaders import DirectoryLoader
        except ImportError:
            print("PyPDF loader not available. Install with 'pip install pypdf langchain-community'")
            return []
            
        print(f"Processing PDF files from {pdf_dir}")
        
        # Load all PDFs from directory
        loader = DirectoryLoader(
            pdf_dir, 
            glob="**/*.pdf",
            loader_cls=PyPDFLoader
        )
        
        documents = loader.load()
        print(f"Loaded {len(documents)} pages from PDF files")
        
        # Split into chunks
        chunked_documents = self.text_splitter.split_documents(documents)
        print(f"Split into {len(chunked_documents)} chunks")
        
        return chunked_documents

    def process_docx_files(self, docx_dir: str) -> List[Document]:
        """Process DOCX files from a directory"""
        try:
            from langchain_community.document_loaders import Docx2txtLoader
            from langchain_community.document_loaders import DirectoryLoader
        except ImportError:
            print("DOCX loader not available. Install with 'pip install docx2txt langchain-community'")
            return []
            
        print(f"Processing DOCX files from {docx_dir}")
        
        # Load all DOCX files from directory
        loader = DirectoryLoader(
            docx_dir, 
            glob="**/*.docx",
            loader_cls=Docx2txtLoader
        )
        
        documents = loader.load()
        print(f"Loaded {len(documents)} pages from DOCX files")
        
        # Split into chunks
        chunked_documents = self.text_splitter.split_documents(documents)
        print(f"Split into {len(chunked_documents)} chunks")
        
        return chunked_documents

    def load_documents(self, force_reload: bool = False) -> None:
        """Load RAG documents from processed crawled data"""
        # Check if vector index already exists
        if os.path.exists(INDEX_DIR) and os.path.isdir(INDEX_DIR) and not force_reload:
            try:
                print(f"Loading existing vector index from {INDEX_DIR}")
                self.vectorstore = FAISS.load_local(INDEX_DIR, self.embeddings)
                print(f"Successfully loaded existing vector index with {self.vectorstore.index.ntotal} vectors")
                return
            except Exception as e:
                print(f"Failed to load existing vector index: {str(e)}. Creating new index.")
        
        print(f"Loading documents from {RAG_DATA_DIR}")
        
        # Get all JSON files in the RAG data directory
        json_files = glob.glob(os.path.join(RAG_DATA_DIR, "*.json"))
        print(f"Found {len(json_files)} document files")
        
        if len(json_files) == 0:
            print("No document files found. Run the scrapper first.")
            return
        
        # Process files in batches
        self.vectorstore = None
        documents_loaded = 0
        
        start_time = time.time()
        
        for batch_documents in self._get_document_batches(json_files):
            documents_loaded += len(batch_documents)
            
            print(f"Creating/updating vector index with batch of {len(batch_documents)} documents...")
            
            if self.vectorstore is None:
                # Create new vectorstore with first batch
                self.vectorstore = FAISS.from_documents(batch_documents, self.embeddings)
            else:
                # Add subsequent batches to existing vectorstore
                self.vectorstore.add_documents(batch_documents)
        
        elapsed_time = time.time() - start_time
        print(f"Vector index creation completed in {elapsed_time:.2f} seconds")
        print(f"Total documents loaded: {documents_loaded}")
        
        # Save the index for future use
        if self.vectorstore:
            os.makedirs(INDEX_DIR, exist_ok=True)
            self.vectorstore.save_local(INDEX_DIR)
            print(f"Vector index saved to {INDEX_DIR}")

    def load_external_documents(self, documents_dir: str) -> None:
        """Process external documents (PDFs, DOCXs) and add them to the vector store"""
        if not os.path.exists(documents_dir):
            print(f"Directory {documents_dir} does not exist")
            return
            
        # Process PDF files
        pdf_docs = self.process_pdf_files(documents_dir)
        
        # Process DOCX files
        docx_docs = self.process_docx_files(documents_dir)
        
        # Combine all documents
        all_docs = pdf_docs + docx_docs
        
        if not all_docs:
            print("No external documents were processed")
            return
            
        print(f"Adding {len(all_docs)} external document chunks to vector index...")
        
        # Make sure we have a vector store
        if self.vectorstore is None:
            self.load_documents()
            
        if self.vectorstore is None:
            # If still None, create a new one
            self.vectorstore = FAISS.from_documents(all_docs, self.embeddings)
        else:
            # Add to existing vector store
            self.vectorstore.add_documents(all_docs)
            
        # Save the updated index
        os.makedirs(INDEX_DIR, exist_ok=True)
        self.vectorstore.save_local(INDEX_DIR)
        print(f"Vector index updated and saved with external documents")

    def get_retriever(self, k: int = 5):
        """Get a retriever for the vectorstore"""
        if self.vectorstore is None:
            self.load_documents()
            
        if self.vectorstore is None:
            raise ValueError("No documents have been loaded yet")
            
        return self.vectorstore.as_retriever(
            search_type="similarity",
            search_kwargs={"k": k}
        )

    def similarity_search(self, query: str, k: int = 5) -> List[Document]:
        """Perform a similarity search on the vector store"""
        if self.vectorstore is None:
            self.load_documents()
            
        if self.vectorstore is None:
            raise ValueError("No documents have been loaded yet")
            
        return self.vectorstore.similarity_search(query, k=k)

    def clear_index(self) -> None:
        """Delete the existing vector index"""
        if os.path.exists(INDEX_DIR):
            import shutil
            try:
                shutil.rmtree(INDEX_DIR)
                print(f"Vector index at {INDEX_DIR} has been deleted")
            except Exception as e:
                print(f"Error deleting vector index: {str(e)}")
                
        self.vectorstore = None


def main():
    """Run a simple demo of the document embedder"""
    print("Initializing document embedder...")
    embedder = DocumentEmbedder()
    
    # Load documents from rag_data
    embedder.load_documents()
    
    # Add any document files from artifacts directory
    artifacts_dir = os.path.abspath(os.path.join(BASE_DIR, "..", "..", "artifacts"))
    if os.path.exists(artifacts_dir):
        print(f"Processing external documents from {artifacts_dir}")
        embedder.load_external_documents(artifacts_dir)
    
    # Test a similarity search
    if embedder.vectorstore:
        query = "How to add funds in Angel One?"
        print(f"\nPerforming similarity search for: '{query}'")
        docs = embedder.similarity_search(query, k=2)
        
        for i, doc in enumerate(docs, 1):
            print(f"\nResult {i}:")
            print(f"Source: {doc.metadata.get('title', 'Unknown')}")
            print(f"Section: {doc.metadata.get('section', 'Unknown')}")
            print(f"Content: {doc.page_content[:200]}...")


if __name__ == "__main__":
    main()