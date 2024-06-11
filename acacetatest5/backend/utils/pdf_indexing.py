import os
import fitz  # PyMuPDF
from opensearchpy import OpenSearch

def index_documents(pdf_directory):
    if not os.path.exists(pdf_directory):
        print(f"Directory {pdf_directory} does not exist.")
        return
    
    client = OpenSearch(
        hosts=[{'host': 'localhost', 'port': 9200}],
        http_compress=True,
    )
    
    for filename in os.listdir(pdf_directory):
        if filename.endswith('.pdf'):
            filepath = os.path.join(pdf_directory, filename)
            with fitz.open(filepath) as doc:
                text = ""
                for page in doc:
                    text += page.get_text()
                document = {
                    'filename': filename,
                    'content': text
                }
                client.index(index="documents", document=document)
