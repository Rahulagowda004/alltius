import os
import json
from pypdf import PdfReader
from docx import Document
from typing import List, Dict

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from a PDF file"""
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    return text

def save_text_to_docx(text: str, output_path: str) -> None:
    """Save text to a DOCX file"""
    doc = Document()
    doc.add_paragraph(text)
    doc.save(output_path)

def process_pdfs(input_dir: str, output_dir: str, save_docx: bool = False) -> None:
    """Process all PDFs and save content to JSON and optionally to DOCX"""
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Dictionary to store all PDF contents
    pdf_contents = {}
    
    # Get all PDF files
    pdf_files = [f for f in os.listdir(input_dir) if f.endswith('.pdf')]
    
    for pdf_file in pdf_files:
        print(f"Processing {pdf_file}...")
        pdf_path = os.path.join(input_dir, pdf_file)
        
        # Extract text
        text = extract_text_from_pdf(pdf_path)
        
        # Store in dictionary
        pdf_contents[os.path.splitext(pdf_file)[0]] = {
            "filename": pdf_file,
            "content": text,
            "page_count": len(PdfReader(pdf_path).pages)
        }
        
        # Optionally save as DOCX
        if save_docx:
            output_filename = os.path.splitext(pdf_file)[0] + '.docx'
            output_path = os.path.join(output_dir, output_filename)
            save_text_to_docx(text, output_path)
            print(f"Saved {output_filename}")
    
    # Save all contents to JSON file
    json_path = os.path.join(output_dir, "pdf_contents.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(pdf_contents, f, ensure_ascii=False, indent=2)
    print(f"Saved all contents to {json_path}")

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    pdf_dir = os.path.join(current_dir, "artifacts", "pdfs")
    output_dir = os.path.join(current_dir, "artifacts", "output")
    
    # Process the PDFs (set save_docx=True if you also want DOCX files)
    process_pdfs(pdf_dir, output_dir, save_docx=False)
    print("All PDFs have been processed!")
