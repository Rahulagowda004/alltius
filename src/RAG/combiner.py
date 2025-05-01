import os
import json
from typing import Dict, Any

def combine_json_files(input_dir: str, output_dir: str) -> None:
    """Combine all JSON files from input directory into a single file"""
    
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Dictionary to store combined data
    combined_data = {}
    
    # Get all JSON files
    json_files = [f for f in os.listdir(input_dir) if f.endswith('.json')]
    
    print(f"Found {len(json_files)} JSON files to process")
    
    # Process each JSON file
    for json_file in json_files:
        print(f"Processing {json_file}...")
        # Fixed the path join syntax
        file_path = os.path.join(input_dir, json_file)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Use filename without extension as key
            file_key = os.path.splitext(json_file)[0]
            combined_data[file_key] = {
                "source_file": json_file,
                "content": data
            }
        except Exception as e:
            print(f"Error processing {json_file}: {str(e)}")
    
    # Save combined data
    output_path = os.path.join(output_dir, "combined_rag_data.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(combined_data, f, ensure_ascii=False, indent=2)
    
    print(f"Successfully combined {len(json_files)} files into {output_path}")

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Update path to point to the correct rag_data directory
    rag_data_dir = os.path.join(current_dir, "artifacts", "rag_data")
    artifacts_dir = os.path.join(current_dir, "artifacts")
    
    # Ensure the input directory exists
    if not os.path.exists(rag_data_dir):
        print(f"Error: Directory not found: {rag_data_dir}")
        print("Please ensure the rag_data directory exists in the artifacts folder.")
        exit(1)
    
    combine_json_files(rag_data_dir, artifacts_dir)
