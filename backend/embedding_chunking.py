from transformers import AutoTokenizer, AutoModel
import torch
from typing import List, Dict

# Load tokenizer and model for embeddings
tokenizer = AutoTokenizer.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")
model = AutoModel.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")

# Chunking parameters
CHUNK_SIZE = 1000
OVERLAP = 150

# Function to chunk text
def chunk_text(text: str) -> List[str]:
    tokens = tokenizer.tokenize(text)
    chunks = []
    for i in range(0, len(tokens), CHUNK_SIZE - OVERLAP):
        chunk = tokens[i:i + CHUNK_SIZE]
        chunks.append(tokenizer.convert_tokens_to_string(chunk))
    return chunks

# Function to generate embeddings
def generate_embeddings(chunks: List[str]) -> List[List[float]]:
    inputs = tokenizer(chunks, padding=True, truncation=True, return_tensors="pt")
    with torch.no_grad():
        outputs = model(**inputs)
    embeddings = outputs.last_hidden_state.mean(dim=1).tolist()
    return embeddings

# Example usage
if __name__ == "__main__":
    text = "Your long document text here."
    chunks = chunk_text(text)
    embeddings = generate_embeddings(chunks)
    for i, chunk in enumerate(chunks):
        print(f"Chunk {i+1}: {chunk}")
        print(f"Embedding {i+1}: {embeddings[i]}")