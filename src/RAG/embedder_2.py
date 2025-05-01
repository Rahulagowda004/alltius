"""
Embedder module for processing PDF content from JSON files and creating vector embeddings for RAG.
This module handles loading PDF content from JSON, chunking, embedding, and storing the vectors in FAISS.
"""

import os
import logging
import json
from typing import List, Dict, Any, Optional
from pathlib import Path
from tqdm import tqdm
import torch

# LangChain imports
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PDFJsonEmbedder:
    """Class for handling PDF content embedding operations from JSON files."""
    
    def __init__(self, 
                 embedding_model_name: str = "sentence-transformers/all-mpnet-base-v2",
                 chunk_size: int = 1000,
                 chunk_overlap: int = 200,
                 vector_store_path: str = "artifacts/vector_store/pdf_vectors",
                 use_gpu: bool = None):
        """
        Initialize the PDFJsonEmbedder.
        
        Args:
            embedding_model_name (str): Name of the HuggingFace embedding model
            chunk_size (int): Size of text chunks for splitting
            chunk_overlap (int): Overlap between chunks
            vector_store_path (str): Path to store the vector database
            use_gpu (bool, optional): Whether to use GPU acceleration. If None, automatically detect.
        """
        self.embedding_model_name = embedding_model_name
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.vector_store_path = vector_store_path
        
        # Check GPU availability if not explicitly set
        if use_gpu is None:
            use_gpu = torch.cuda.is_available()
        
        device = "cuda" if use_gpu else "cpu"
        logger.info(f"Initializing PDF embedder with model: {embedding_model_name} on device: {device}")
        
        # Initialize embeddings with GPU support if available
        self.embeddings = HuggingFaceEmbeddings(
            model_name=embedding_model_name,
            model_kwargs={"device": device}
        )
        
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len
        )
        
        # Log GPU information if available
        if use_gpu:
            logger.info(f"Using GPU acceleration: {torch.cuda.get_device_name(0)}")
            logger.info(f"CUDA Version: {torch.version.cuda}")
        else:
            logger.info("Running on CPU. GPU not available or not enabled.")
        
        # Initialize vectorstore to None at first
        self.vectorstore = None
    
    def read_pdf_json(self, json_file_path: str) -> Dict[str, Dict[str, Any]]:
        """
        Read PDF content from a JSON file.
        
        Args:
            json_file_path (str): Path to the JSON file containing PDF content
            
        Returns:
            Dict[str, Dict[str, Any]]: Dictionary containing PDF data
        """
        logger.info(f"Reading PDF content from JSON file: {json_file_path}")
        try:
            with open(json_file_path, 'r', encoding='utf-8') as file:
                return json.load(file)
        except Exception as e:
            logger.error(f"Error reading PDF content from JSON file: {e}")
            raise
    
    def process_pdf_content(self, pdf_data: Dict[str, Dict[str, Any]]) -> List[Document]:
        """
        Process PDF content from JSON data and convert to documents.
        
        Args:
            pdf_data (Dict[str, Dict[str, Any]]): Dictionary containing PDF data
            
        Returns:
            List[Document]: List of document chunks
        """
        logger.info(f"Processing PDF content from {len(pdf_data)} PDF entries")
        all_documents = []
        
        for pdf_id, pdf_info in tqdm(pdf_data.items(), desc="Processing PDF entries"):
            if not pdf_info.get("content"):
                logger.warning(f"No content found for PDF ID {pdf_id}, skipping.")
                continue
                
            # Extract content and metadata
            content = pdf_info["content"]
            metadata = {
                "source": f"pdf_{pdf_id}",
                "filename": pdf_info.get("filename", f"pdf_{pdf_id}.pdf"),
                "page_count": pdf_info.get("page_count", 0)
            }
            
            # Create a document
            document = Document(page_content=content, metadata=metadata)
            
            # Split into chunks
            chunks = self.text_splitter.split_documents([document])
            
            # Add source ID to each chunk for tracking
            for chunk in chunks:
                chunk.metadata["source_id"] = pdf_id
                chunk.metadata["chunk_type"] = "pdf"
            
            all_documents.extend(chunks)
            
        logger.info(f"Created {len(all_documents)} chunks from all PDF content")
        return all_documents
    
    def create_embeddings(self, documents: List[Document]) -> FAISS:
        """
        Create vector embeddings for documents.
        
        Args:
            documents (List[Document]): List of document chunks
            
        Returns:
            FAISS: Vector store with embeddings
        """
        logger.info(f"Creating embeddings for {len(documents)} document chunks using {self.embedding_model_name}")
        self.vectorstore = FAISS.from_documents(documents, self.embeddings)
        return self.vectorstore
    
    def save_vector_store(self, vectorstore: Optional[FAISS] = None, store_name: str = "pdf_vectors") -> str:
        """
        Save vector store to disk.
        
        Args:
            vectorstore (FAISS, optional): Vector store to save. If None, uses self.vectorstore
            store_name (str): Name for the vector store
            
        Returns:
            str: Path to saved vector store
        """
        if vectorstore is None:
            if self.vectorstore is None:
                raise ValueError("No vector store available to save.")
            vectorstore = self.vectorstore
            
        # Create directory if it doesn't exist
        os.makedirs(self.vector_store_path, exist_ok=True)
        
        # Save the vector store
        save_path = os.path.join(self.vector_store_path, store_name)
        vectorstore.save_local(save_path)
        logger.info(f"Vector store saved to {save_path}")
        
        return save_path
    
    def load_vector_store(self, store_name: str = "pdf_vectors") -> FAISS:
        """
        Load vector store from disk.
        
        Args:
            store_name (str): Name of the vector store
            
        Returns:
            FAISS: Loaded vector store
        """
        load_path = os.path.join(self.vector_store_path, store_name)
        if not os.path.exists(load_path):
            raise FileNotFoundError(f"Vector store not found at {load_path}")
            
        logger.info(f"Loading vector store from {load_path}")
        self.vectorstore = FAISS.load_local(load_path, self.embeddings)
        return self.vectorstore
    
    def process_pdf_json_file(self, json_file_path: str, store_name: str = "pdf_vectors") -> str:
        """
        Process a JSON file containing PDF content and create/save embeddings.
        
        Args:
            json_file_path (str): Path to the JSON file
            store_name (str): Name for the vector store
            
        Returns:
            str: Path to saved vector store
        """
        # Read the PDF content from the JSON file
        pdf_data = self.read_pdf_json(json_file_path)
        
        # Process the PDF content
        documents = self.process_pdf_content(pdf_data)
        
        # Create embeddings
        vectorstore = self.create_embeddings(documents)
        
        # Save the vector store
        save_path = self.save_vector_store(vectorstore, store_name)
        
        return save_path


def main():
    """Main function to demonstrate usage."""
    # Check for GPU availability
    gpu_available = torch.cuda.is_available()
    if gpu_available:
        logger.info(f"GPU detected: {torch.cuda.get_device_name(0)}")
        logger.info("Running embedding with GPU acceleration")
    else:
        logger.warning("No GPU detected. Running on CPU which may be slower.")
    
    # Initialize the embedder with GPU support
    embedder = PDFJsonEmbedder(
        chunk_size=1000,
        chunk_overlap=200,
        vector_store_path="artifacts/vector_store",
        use_gpu=True  # Explicitly request GPU usage (will fallback to CPU if unavailable)
    )
    
    # Path to the PDF content JSON file
    json_file_path = "src/RAG/artifacts/pdfs/pdf_contents.json"
    
    if os.path.exists(json_file_path):
        # Process the JSON file
        store_path = embedder.process_pdf_json_file(json_file_path, "pdf_vectors")
        logger.info(f"PDF embeddings created and saved to {store_path}")
    else:
        logger.error(f"JSON file not found: {json_file_path}")


if __name__ == "__main__":
    main()