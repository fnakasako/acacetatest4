from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from opensearchpy import OpenSearch
from sentence_transformers import SentenceTransformer
from pinecone import Pinecone, ServerlessSpec
import os

db = SQLAlchemy()
bcrypt = Bcrypt()
jwt = JWTManager()
migrate = Migrate()
client = None
index = None
model = None

def create_app():
    global client, index, model

    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://yourusername:yourpassword@localhost/acacetatest1'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JWT_SECRET_KEY'] = '65cfcceb68809ac908b79a160b4885a73b46124c4fbf31d0'

    db.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)

    # Initialize OpenSearch
    client = OpenSearch(
        hosts=[{'host': 'localhost', 'port': 9200}],
        http_compress=True,
    )

    # Initialize Pinecone
    pc = Pinecone(api_key="690b186d-635a-4e09-b0f2-41d57a9cc07c")
    index_name = "document-embeddings"
    if index_name not in [index.name for index in pc.list_indexes()]:
        pc.create_index(
            name=index_name,
            dimension=1536,
            metric='cosine',
            spec=ServerlessSpec(
                cloud='aws',
                region='us-east-1'
            )
        )
    index = pc.Index(index_name)

    # Load model
    model = SentenceTransformer('all-MiniLM-L6-v2')

    # Ensure the data/pdfs directory exists
    os.makedirs('data/pdfs', exist_ok=True)

    with app.app_context():
        from backend.routes import register_routes
        register_routes(app)

    return app

