from flask import request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from backend import db, bcrypt
from backend.models import User, Subscription, Chat, Document
from backend.utils.pdf_indexing import index_documents
from backend.utils.embedding_indexing import index_embeddings

def register_routes(app):

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
        user = User.query.filter_by(email=data['email']).first()
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
