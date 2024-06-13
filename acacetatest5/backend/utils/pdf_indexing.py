import os
import fitz  # PyMuPDF
import boto3
from requests_aws4auth import AWS4Auth
from opensearchpy import OpenSearch, RequestsHttpConnection
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def index_documents(pdf_directory):
    if not os.path.exists(pdf_directory):
        print(f"Directory {pdf_directory} does not exist.")
        return

    # Fetch AWS credentials from environment variables
    aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
    aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
    aws_session_token = os.getenv('AWS_SESSION_TOKEN')  # Add this line if using session token
    region = 'us-east-2'  # Change to your AWS region

    if not aws_access_key or not aws_secret_key:
        print("AWS credentials not found in environment variables.")
        return

    print(f"Using AWS_ACCESS_KEY_ID: {aws_access_key}")
    print(f"Using AWS_SECRET_ACCESS_KEY: {aws_secret_key}")
    
    session = boto3.Session(
        aws_access_key_id=aws_access_key,
        aws_secret_access_key=aws_secret_key,
        aws_session_token=aws_session_token,  # Add this line if using session token
        region_name=region
    )
    credentials = session.get_credentials()
    credentials = credentials.get_frozen_credentials()
    awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, region, 'es', session_token=credentials.token)

    # OpenSearch client initialization
    host = 'search-acacetatest2-77yosy27xlgngbjtxtonysvjai.aos.us-east-2.on.aws'  # Your OpenSearch domain endpoint
    client = OpenSearch(
        hosts=[{'host': host, 'port': 443}],
        http_auth=awsauth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
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
                try:
                    response = client.index(index="documents", body=document)  # Use 'body' instead of 'document'
                    print(f"Indexed document {filename}: {response}")
                except Exception as e:
                    print(f"Error indexing document {filename}: {e}")

# Example usage:
# index_documents('/path/to/pdf/directory')
