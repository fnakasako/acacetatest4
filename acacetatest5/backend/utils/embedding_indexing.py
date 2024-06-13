import os
import fitz  # PyMuPDF
from sentence_transformers import SentenceTransformer
from pinecone import Pinecone, ServerlessSpec
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def index_embeddings(pdf_directory):
    if not os.path.exists(pdf_directory):
        print(f"Directory {pdf_directory} does not exist.")
        return

    model = SentenceTransformer('all-MiniLM-L6-v2')

    pinecone_api_key = os.getenv("PINECONE_API_KEY")
    if not pinecone_api_key:
        print("Pinecone API key not found in environment variables.")
        return

    # Initialize Pinecone
    pc = Pinecone(api_key=pinecone_api_key)
    index_name = "document-embeddings"
    if index_name not in pc.list_indexes().names():
        pc.create_index(
            name=index_name,
            dimension=384,
            metric='cosine',
            spec=ServerlessSpec(
                cloud='aws',
                region='us-east-1'
            )
        )
    pinecone_index = pc.Index(index_name)

    for filename in os.listdir(pdf_directory):
        if filename.endswith('.pdf'):
            filepath = os.path.join(pdf_directory, filename)
            with fitz.open(filepath) as doc:
                text = ""
                for page in doc:
                    text += page.get_text()
                # Create embedding for the document
                embedding = model.encode(text)
                # Insert the embedding into Pinecone index
                pinecone_index.upsert(vectors=[(filename, embedding)])
