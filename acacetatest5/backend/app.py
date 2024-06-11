import sys
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

print(sys.path)

from backend import db, bcrypt, jwt, migrate

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://yourusername:yourpassword@localhost/acacetatest1'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JWT_SECRET_KEY'] = '65cfcceb68809ac908b79a160b4885a73b46124c4fbf31d0'

    db.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)
    CORS(app, resources={r"/*": {"origins": "http://localhost:3000"}})  # Enable CORS for the specific frontend origin

    # Initialize Pinecone
    pc = Pinecone(api_key="690b186d-635a-4e09-b0f2-41d57a9cc07c")
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
    index = pc.Index(index_name)

    # Load model
    model = SentenceTransformer('all-MiniLM-L6-v2')

    with app.app_context():
        db.create_all()
        index_documents('data/pdfs')  # Index documents on the first request
        index_embeddings('data/pdfs')  # Index embeddings on the first request

    from backend.models import User, Subscription, Chat, Document

    @app.before_request
    def handle_options_request():
        if request.method == 'OPTIONS':
            response = make_response()
            response.headers.add("Access-Control-Allow-Origin", "http://localhost:3000")
            response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
            response.headers.add("Access-Control-Allow-Methods", "GET,POST,PUT,DELETE,OPTIONS")
            response.headers.add("Access-Control-Allow-Credentials", "true")
            return response

    @app.after_request
    def add_cors_headers(response):
        response.headers.add("Access-Control-Allow-Origin", "http://localhost:3000")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
        response.headers.add("Access-Control-Allow-Methods", "GET,POST,PUT,DELETE,OPTIONS")
        response.headers.add("Access-Control-Allow-Credentials", "true")
        return response

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
        return jsonify(message="User registered successfully"), 201

    @app.route('/login', methods=['POST'])
    def login():
        data = request.get_json()
        app.logger.info('Login data received: %s', data)
        user = User.query.filter_by(email=data['email']).first()
        app.logger.info('User found: %s', user)
        if user and bcrypt.check_password_hash(user.password, data['password']):
            access_token = create_access_token(identity=user.id)
            return jsonify(access_token=access_token), 200
        return jsonify(message="Invalid credentials"), 401

    @app.route('/subscribe', methods=['POST'])
    @jwt_required()
    def subscribe():
        user_id = get_jwt_identity()
        new_subscription = Subscription(user_id=user_id, active=True)
        db.session.add(new_subscription)
        db.session.commit()
        return jsonify(message="Subscription activated"), 200

    @app.route('/chat', methods=['POST'])
    @jwt_required()
    def chat():
        user_id = get_jwt_identity()
        data = request.get_json()
        new_chat = Chat(user_id=user_id, message=data['message'], response="Sample response")
        db.session.add(new_chat)
        db.session.commit()
        return jsonify(message="Chat stored successfully"), 200

    @app.route('/document', methods=['POST'])
    def upload_document():
        data = request.get_json()
        new_document = Document(filename=data['filename'], content=data['content'])
        db.session.add(new_document)
        db.session.commit()
        # Index the new document in Pinecone
        index_documents('data/pdfs')
        index_embeddings('data/pdfs')
        return jsonify(message="Document uploaded and indexed successfully"), 201

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
        return jsonify(response['hits']['hits'])

    @app.route('/semantic_search', methods=['POST'])
    def semantic_search():
        query = request.get_json().get('query')
        query_embedding = model.encode(query)
        results = index.query(queries=[query_embedding], top_k=5)
        return jsonify(results['matches'])

    @app.route('/test_db')
    def test_db():
        try:
            user = User.query.first()
            return jsonify(user.username), 200
        except Exception as e:
            return jsonify(error=str(e)), 500

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
