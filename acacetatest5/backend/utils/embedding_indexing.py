import os
import fitz  # PyMuPDF
from sentence_transformers import SentenceTransformer

def index_embeddings(pdf_directory):
    if not os.path.exists(pdf_directory):
        print(f"Directory {pdf_directory} does not exist.")
        return

    model = SentenceTransformer('all-MiniLM-L6-v2')

    for filename in os.listdir(pdf_directory):
        if filename.endswith('.pdf'):
            filepath = os.path.join(pdf_directory, filename)
            with fitz.open(filepath) as doc:
                text = ""
                for page in doc:
                    text += page.get_text()
                # Create embedding for the document
                embedding = model.encode(text)
                # Here you would insert the embedding into your Pinecone index
                # Assuming `index` is your Pinecone index object
                index.upsert(vectors=[(filename, embedding)])
