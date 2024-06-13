import logging
from flask import Flask, request, jsonify, render_template, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_migrate import Migrate
from flask_cors import CORS
from sentence_transformers import SentenceTransformer
from pinecone import Pinecone, ServerlessSpec
from backend.utils.pdf_indexing import index_documents
from backend.utils.embedding_indexing import index_embeddings
from PyPDF2 import PdfReader
import os
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

from backend import db, bcrypt, jwt, migrate

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://yourusername:yourpassword@localhost/acacetatest1'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JWT_SECRET_KEY'] = '65cfcceb68809ac908b79a160b4885a73b46124c4fbf31d0'
    app.config['UPLOAD_FOLDER'] = 'uploads'
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    db.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)
    CORS(app, supports_credentials=True, resources={r"/*": {"origins": "http://localhost:3000"}})

    # Print environment variables for debugging
    print(f"AWS_ACCESS_KEY_ID: {os.getenv('AWS_ACCESS_KEY_ID')}")
    print(f"AWS_SECRET_ACCESS_KEY: {os.getenv('AWS_SECRET_ACCESS_KEY')}")
    print(f"PINECONE_API_KEY: {os.getenv('PINECONE_API_KEY')}")

    # Initialize Pinecone and model
    pinecone_api_key = os.getenv("PINECONE_API_KEY")
    if not pinecone_api_key:
        raise ValueError("Pinecone API key not found in environment variables")

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
    pinecone_index = pc.Index(index_name)  # Ensure pinecone_index is used correctly
    model = SentenceTransformer('all-MiniLM-L6-v2')

    with app.app_context():
        db.create_all()
        index_documents('data/pdfs')
        index_embeddings('data/pdfs')

    from backend.models import User, Subscription, Chat, Document

    @app.route('/')
    def home():
        return render_template('index.html')

    @app.route('/register', methods=['POST'])
    def register():
        data = request.get_json()
        hashed_password = bcrypt.generate_password_hash(data['password']).decode('utf-8')
        new_user = User(username=data['username'], email=data['email'], password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        response = jsonify(message="User registered successfully")
        response.headers.add("Access-Control-Allow-Origin", "http://localhost:3000")
        response.headers.add("Access-Control-Allow-Credentials", "true")
        return response

    @app.route('/login', methods=['POST'])
    def login():
        data = request.get_json()
        app.logger.info('Login data received: %s', data)
        user = User.query.filter_by(email=data['email']).first()
        app.logger.info('User found: %s', user)
        if user and bcrypt.check_password_hash(user.password, data['password']):
            access_token = create_access_token(identity=user.id)
            response = jsonify(access_token=access_token)
            response.headers.add("Access-Control-Allow-Origin", "http://localhost:3000")
            response.headers.add("Access-Control-Allow-Credentials", "true")
            return response
        response = jsonify(message="Invalid credentials")
        response.status_code = 401
        response.headers.add("Access-Control-Allow-Origin", "http://localhost:3000")
        response.headers.add("Access-Control-Allow-Credentials", "true")
        return response

    @app.route('/subscribe', methods=['POST'])
    @jwt_required()
    def subscribe():
        user_id = get_jwt_identity()
        new_subscription = Subscription(user_id=user_id, active=True)
        db.session.add(new_subscription)
        db.session.commit()
        response = jsonify(message="Subscription activated")
        response.headers.add("Access-Control-Allow-Origin", "http://localhost:3000")
        response.headers.add("Access-Control-Allow-Credentials", "true")
        return response

    @app.route('/chat', methods=['POST'])
    @jwt_required()
    def chat():
        user_id = get_jwt_identity()
        data = request.get_json()
        new_chat = Chat(user_id=user_id, message=data['message'], response="Sample response")
        db.session.add(new_chat)
        db.session.commit()
        response = jsonify(message="Chat stored successfully")
        response.headers.add("Access-Control-Allow-Origin", "http://localhost:3000")
        response.headers.add("Access-Control-Allow-Credentials", "true")
        return response

    @app.route('/document', methods=['POST'])
    def upload_document():
        data = request.get_json()
        new_document = Document(filename=data['filename'], content=data['content'])
        db.session.add(new_document)
        db.session.commit()
        # Index the new document in Pinecone
        index_documents('data/pdfs')
        index_embeddings('data/pdfs')
        response = jsonify(message="Document uploaded and indexed successfully")
        response.headers.add("Access-Control-Allow-Origin", "http://localhost:3000")
        response.headers.add("Access-Control-Allow-Credentials", "true")
        return response

    @app.route('/upload', methods=['POST'])
    def upload_file():
        if 'file' not in request.files:
            logging.error("No file part in the request.")
            response = jsonify({"error": "No file part"})
            response.status_code = 400
            response.headers.add("Access-Control-Allow-Origin", "http://localhost:3000")
            response.headers.add("Access-Control-Allow-Credentials", "true")
            return response
        file = request.files['file']
        if file.filename == '':
            logging.error("No selected file.")
            response = jsonify({"error": "No selected file"})
            response.status_code = 400
            response.headers.add("Access-Control-Allow-Origin", "http://localhost:3000")
            response.headers.add("Access-Control-Allow-Credentials", "true")
            return response
        if file and not file.filename.endswith('.pdf'):
            logging.error("Invalid file type.")
            response = jsonify({"error": "Invalid file type"})
            response.status_code = 400
            response.headers.add("Access-Control-Allow-Origin", "http://localhost:3000")
            response.headers.add("Access-Control-Allow-Credentials", "true")
            return response
        
        try:
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filepath)
            logging.debug(f"File saved to {filepath}")

            pdf_reader = PdfReader(filepath)
            text = ""
            for page in range(len(pdf_reader.pages)):
                text += pdf_reader.pages[page].extract_text()
            
            logging.debug("PDF text extracted.")

            existing_document = Document.query.filter_by(filename=file.filename).first()
            if existing_document:
                logging.error(f"File with name {file.filename} already exists.")
                response = jsonify({"error": "File with this name already exists"})
                response.status_code = 400
                response.headers.add("Access-Control-Allow-Origin", "http://localhost:3000")
                response.headers.add("Access-Control-Allow-Credentials", "true")
                return response

            pdf_data = Document(filename=file.filename, content=text)
            db.session.add(pdf_data)
            db.session.commit()
            logging.debug("PDF data committed to database.")

            index_documents(app.config['UPLOAD_FOLDER'])
            index_embeddings(app.config['UPLOAD_FOLDER'])
            logging.debug("PDF data indexed.")

            response = jsonify({"message": "File uploaded and processed successfully"})
            response.status_code = 200
            response.headers.add("Access-Control-Allow-Origin", "http://localhost:3000")
            response.headers.add("Access-Control-Allow-Credentials", "true")
            return response
        except Exception as e:
            logging.error(f"Unexpected error: {e}")
            response = jsonify({"error": "An error occurred during file upload."})
            response.status_code = 500
            response.headers.add("Access-Control-Allow-Origin", "http://localhost:3000")
            response.headers.add("Access-Control-Allow-Credentials", "true")
            return response

    @app.route('/search', methods=['POST'])
    def search():
        query = request.get_json().get('query')
        response = client.search(
            index="documents",
            body={
                "query": {
                    "match": {
                        "content": query
                    }
                }
            }
        )
        response = jsonify(response['hits']['hits'])
        response.headers.add("Access-Control-Allow-Origin", "http://localhost:3000")
        response.headers.add("Access-Control-Allow-Credentials", "true")
        return response

    @app.route('/semantic_search', methods=['POST'])
    def semantic_search():
        query = request.get_json().get('query')
        query_embedding = model.encode(query)
        results = pinecone_index.query(queries=[query_embedding], top_k=5)
        response = jsonify(results['matches'])
        response.headers.add("Access-Control-Allow-Origin", "http://localhost:3000")
        response.headers.add("Access-Control-Allow-Credentials", "true")
        return response

    @app.route('/test_db')
    def test_db():
        try:
            user = User.query.first()
            response = jsonify(user.username)
            response.status_code = 200
            response.headers.add("Access-Control-Allow-Origin", "http://localhost:3000")
            response.headers.add("Access-Control-Allow-Credentials", "true")
            return response
        except Exception as e:
            response = jsonify(error=str(e))
            response.status_code = 500
            response.headers.add("Access-Control-Allow-Origin", "http://localhost:3000")
            response.headers.add("Access-Control-Allow-Credentials", "true")
            return response

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
