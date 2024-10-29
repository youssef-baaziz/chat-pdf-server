import chatpdf
from models import User
from flask import Flask, request, jsonify
import os
import asyncio
import jwt
from flask_jwt_extended import create_access_token, jwt_required, JWTManager, get_jwt_identity
from flask_cors import CORS
from datetime import timedelta  # Import timedelta for token expiration

app = Flask(__name__)

CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['DATA_JSON_FOLDER'] = 'data_json'
app.config['JWT_SECRET_KEY'] = 'test2024'  # Change this to a random secret key

# Set token expiration to 1 hour
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(minutes=2)

jwt = JWTManager(app)

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['DATA_JSON_FOLDER'], exist_ok=True)

# Start the APIs
@app.route('/files', methods=['POST'])
def get_data_files():
    user_id = request.json.get('user_id')
    data = chatpdf.get_files_name(user_id)
    return jsonify(data)

@app.route('/history', methods=['POST'])
def get_data_history():
    history_file = request.json.get('history_file_json')
    history_id = request.json.get('history_id')
    history = chatpdf.data_history(history_id, history_file, app.config['DATA_JSON_FOLDER'], app.config['UPLOAD_FOLDER'])
    files = chatpdf.get_file_by_id(history_id)
    return jsonify({"history": history, "files": files})

@app.route('/register', methods=['POST'])
def register():
    """User registration endpoint."""
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    firstname = data.get('firstName')
    lastname = data.get('lastName')

    # Create user and hash password (make sure to hash the password in your User model)
    new_user = User(username=username, password=password, firstname=firstname, lastname=lastname)
    new_user.save()
    return jsonify({"msg": "User registered successfully"}), 201    

@app.route('/login', methods=['POST'])
def login():
    """User login endpoint."""
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    user = User.verify(username, password)
    if user:
        # Create JWT token
        token = create_access_token(identity=user['username'])
        return jsonify(access_token=token), 200
    return jsonify({"msg": "Invalid credentials"}), 401

@app.route('/user', methods=['GET'])
@jwt_required()
def get_user():
    """Get logged-in user's info."""
    current_user = get_jwt_identity()
    user = User.get_by_username(current_user)  # Implement this method to get user info from the DB
    print('user ---------')
    print(user['id'])
    return jsonify(user), 200

@app.route('/logout', methods=['POST'])
@jwt_required()
def logout_user():
    """User logout endpoint."""
    return jsonify({"msg": "Logged out successfully"}), 200

@app.route('/edit-description', methods=['POST'])
@jwt_required()
def edit_add_description():
    file = request.json.get('filename')
    description = request.json.get('description')
    data = chatpdf.updateDescription(file, description) 
    return jsonify(data)

@app.route('/upload', methods=['POST'])
@jwt_required()
async def upload_files():
    files = request.files.getlist('files')
    descriptions = request.form.getlist('description')
    print(files)
    print(descriptions)
    user_id = request.form.get('user_id')
    data = await chatpdf.upload_file(files, app.config['DATA_JSON_FOLDER'], app.config['UPLOAD_FOLDER'], descriptions, user_id)
    return jsonify(data)

@app.route('/response', methods=['POST'])
@jwt_required()
def query_model():
    user_question = request.json.get('question', '')
    data = chatpdf.get_response(user_question, app.config['DATA_JSON_FOLDER'])
    return jsonify(data)

@app.route('/files-select', methods=['POST'])
@jwt_required()
def get_files_selected():
    history_id = request.json.get('history_id')
    files = chatpdf.get_file_by_id(history_id)
    return jsonify(files)

@app.route('/rename', methods=['POST'])
@jwt_required()
def rename_identifiant():
    history_identifiant = request.json.get('identifiant')
    history_id = request.json.get('history_id')
    data = chatpdf.rename_identifiant_in_table_chatpdf_history(history_identifiant, history_id)
    return jsonify(data)

@app.route('/delete', methods=['POST'])
@jwt_required()
def delete_conversation():
    history_id = request.json.get('history_id')
    data = chatpdf.delete_record_from_chatpdf_history(history_id)
    return jsonify(data)

@app.route('/delete-file', methods=['POST'])
@jwt_required()
def delete_file():
    file_id = request.json.get('file_id')
    data = chatpdf.delete_file(file_id)
    return jsonify(data)

@app.route('/ping', methods=['GET'])
def ping():
    return 'hello'

if __name__ == "__main__":
    app.config["JSON_AS_ASCII"] = False
    app.config["JSONIFY_PRETTYPRINT_REGULAR"] = True
    app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024
    app.run(host="0.0.0.0", port=5054)
