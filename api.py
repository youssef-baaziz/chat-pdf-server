import chatpdf
import database
from models import User
from flask import Flask, request, jsonify
import os
import asyncio
import jwt
from flask_jwt_extended import create_access_token,create_refresh_token, jwt_required, get_jwt, JWTManager, get_jwt_identity
from flask_cors import CORS
from datetime import timedelta  # Import timedelta for token expiration
from flask_socketio import SocketIO, emit
import threading
            
app = Flask(__name__)
         
socketio = SocketIO(app, cors_allowed_origins="*", supports_credentials=True)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['DATA_JSON_FOLDER'] = 'data_json'
app.config['JWT_SECRET_KEY'] = 'chatpdf'  # Change this to a random secret key

# Set token expiration to 1 hour
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(minutes=15)
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=2)

jwt = JWTManager(app)

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['DATA_JSON_FOLDER'], exist_ok=True)
    
# Start the APIs
@app.route('/files', methods=['POST'])
def get_data_files():
    user_id = request.json.get('user_id')
    data = database.get_files_name(user_id)
    return jsonify(data)

@app.route('/files-by-history', methods=['POST'])
async def get_data_files_by_history():
    history_id = request.json.get('history_id')
    loop = asyncio.get_running_loop()
    files = await loop.run_in_executor(None, database.get_file_by_id, history_id)
    return jsonify({"files": files})

@app.route('/history', methods=['POST'])
async def get_data_history():
    history_file = request.json.get('history_file_json')
    
    # Run the synchronous function in a thread pool
    loop = asyncio.get_running_loop()
    history = await loop.run_in_executor(None, chatpdf.data_history, history_file, app.config['DATA_JSON_FOLDER'])
    
    return jsonify({"history": history})

@app.route('/section', methods=['POST'])
def new_conversation_by_section():
    section_label = request.json.get('section_label')
    user_id = request.json.get('user_id')
    data = chatpdf.get_new_conversation_by_section(section_label,app.config['DATA_JSON_FOLDER'],app.config['UPLOAD_FOLDER'],user_id)
    
    return jsonify({"data": data})

@app.route('/list-section', methods=['POST'])
@jwt_required()
def get_section():
    user_id = request.json.get('user_id')
    data = database.get_section_by_user(user_id)
    
    return jsonify(data)

@app.route('/treated-file', methods=['POST'])
def treated_file():
    history_file = request.json.get('history_file_json')
    history_id = request.json.get('history_id')
    
    treated = chatpdf.traiter_file_have_history(history_id, history_file, app.config['UPLOAD_FOLDER'])
    
    return jsonify(treated)

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
        access_token = create_access_token(identity=user['username'])
        refresh_token = create_refresh_token(identity=user['username'])
        return jsonify(access_token=access_token, refresh_token=refresh_token), 200
    return jsonify({"msg": "Invalid credentials"}), 401

# Refresh route to renew access token using the refresh token
@app.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """Endpoint to refresh the access token."""
    current_user = get_jwt_identity()
    new_access_token = create_access_token(identity=current_user)
    return jsonify(access_token=new_access_token), 200

@app.route('/user', methods=['GET'])
@jwt_required()
def get_user():
    """Get logged-in user's info."""
    current_user = get_jwt_identity()
    user = User.get_by_username(current_user)
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
    data = database.updateDescription(file, description)
    return jsonify(data)

@app.route('/upload', methods=['POST'])
@jwt_required()
async def upload_files():
    files = request.files.getlist('files')
    descriptions = request.form.getlist('description')
    user_id = request.form.get('user_id')
    data = await chatpdf.upload_file(files, app.config['DATA_JSON_FOLDER'], app.config['UPLOAD_FOLDER'], descriptions, user_id)
    # file_check_thread = threading.Thread(target=chatpdf.delete_record_from_chatpdf_history_if_stay_vide, args=(data['history_id'],app.config['DATA_JSON_FOLDER']))
    # file_check_thread.daemon = True  # Ensures the thread exits when the main program exits
    # file_check_thread.start()
    return jsonify(data)

# @app.route('/delete-vide-history', methods=['POST'])
# @jwt_required()
# def delete_vide_history():
#     history_id = request.json.get('history_id')
#     # data = chatpdf.delete_record_from_chatpdf_history_if_stay_vide(history_id,app.config['DATA_JSON_FOLDER'])
#     data = []
#     return jsonify(data)

@socketio.on('start_stream')
def handle_message(data):
    question = data.get('question', '')
    print(f"Received question: {question}")
    
    # Call get_response with an emit function that streams chunks
    chatpdf.get_response(
        user_question=question, 
        upload_json=app.config['DATA_JSON_FOLDER'], 
        emit_func=emit
    )

@app.route('/files-select', methods=['POST'])
@jwt_required()
def get_files_selected():
    history_id = request.json.get('history_id')
    files = database.get_file_by_id(history_id)
    return jsonify(files)

@app.route('/rename', methods=['POST'])
@jwt_required()
def rename_identifiant():
    history_identifiant = request.json.get('identifiant')
    history_id = request.json.get('history_id')
    data = database.rename_identifiant_in_table_chatpdf_history(history_identifiant, history_id)
    return jsonify(data)

@app.route('/delete', methods=['POST'])
@jwt_required()
def delete_conversation():
    history_id = request.json.get('history_id')
    data = database.delete_record_from_chatpdf_history(history_id)
    return jsonify(data)

@app.route('/delete-file', methods=['POST'])
@jwt_required()
def delete_file():
    file_id = request.json.get('file_id')
    data = database.delete_file(file_id)
    return jsonify(data)


@app.route('/upload-other-files', methods=['POST'])
@jwt_required()
async def upload_other_files():
    history_id = request.form.get('history_id')
    new_files = request.files.getlist('new_files')
    descriptions = request.form.getlist('new_descriptions')
    data = await chatpdf.upload_and_process_files(new_files, app.config['UPLOAD_FOLDER'], history_id, descriptions)
    return jsonify(data)

@app.route('/ping', methods=['GET'])
def ping():
    return 'hello'

if __name__ == "__main__":
    app.config["JSON_AS_ASCII"] = False
    app.config["JSONIFY_PRETTYPRINT_REGULAR"] = True
    app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024
    socketio.run(app, host="0.0.0.0", port=5052, debug=True)
