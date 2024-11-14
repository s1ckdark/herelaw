from docx import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
import os

def extract_text_from_docx(file_path):
    doc = Document(file_path)
    full_text = []
    for para in doc.paragraphs:
        full_text.append(para.text)
    return '\n'.join(full_text)

def create_chunks(text, chunk_size=1000, chunk_overlap=200):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len
    )
    chunks = text_splitter.split_text(text)
    return chunks

def process_docx_files(directory):
    all_chunks = []
    for filename in os.listdir(directory):
        if filename.endswith('.docx'):
            file_path = os.path.join(directory, filename)
            text = extract_text_from_docx(file_path)
            chunks = create_chunks(text)
            all_chunks.extend(chunks)
    return all_chunks

# Example usage
directory = 'path/to/your/docx/files'
chunks = process_docx_files(directory)

# Print the first few chunks as an example
for i, chunk in enumerate(chunks[:5]):
    print(f"Chunk {i + 1}:")
    print(chunk)
    print("-" * 50)

print(f"Total number of chunks: {len(chunks)}")
