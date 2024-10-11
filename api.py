import chatpdf
from flask import Flask, request, jsonify
import os
import asyncio
from flask_cors import CORS

app = Flask(__name__)

CORS(app, resources={r"/*": {"origins": "*"}})
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['DATA_JSON_FOLDER'] = 'data_json'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['DATA_JSON_FOLDER'], exist_ok=True)
word_json = ".json"

# start the APIs
@app.route('/files', methods=['POST'])
def get_data_files():
    data = chatpdf.get_files_name()
    return jsonify(data)

@app.route('/history', methods=['POST'])
def get_data_history():
    history_file = request.json.get('history_file_json')
    history_id = request.json.get('history_id')
    history = chatpdf.data_history(history_id,history_file,app.config['DATA_JSON_FOLDER'],app.config['UPLOAD_FOLDER'])
    files = chatpdf.get_file_by_id(history_id)
    return jsonify({"history": history, "files": files})

@app.route('/edit-description', methods=['POST'])
def edit_add_description():
    file = request.json.get('filename')
    description = request.json.get('description')
    
    data = chatpdf.updateDescription(file,description) 
    return jsonify(data)

@app.route('/upload', methods=['POST'])
async def upload_files():
    files = request.files.getlist('files')
    description = request.form.getlist('description')
    data =  await chatpdf.upload_file(files,app.config['DATA_JSON_FOLDER'],app.config['UPLOAD_FOLDER'],description)
    return jsonify(data)

@app.route('/response', methods=['POST'])
def query_model():
    user_question = request.json.get('question', '')
    data = chatpdf.get_response(user_question,app.config['DATA_JSON_FOLDER'])
    return jsonify(data)

@app.route('/files-select', methods=['POST'])
def get_files_selected():
    history_id = request.json.get('history_id')
    files = chatpdf.get_file_by_id(history_id)
    return jsonify(files)

@app.route('/rename', methods=['POST'])
def rename_identifiant():
    history_identifiant = request.json.get('identifiant')
    history_id = request.json.get('history_id')
    data = chatpdf.rename_identifiant_in_table_chatpdf_history(history_identifiant,history_id)
    return jsonify(data)

@app.route('/delete', methods=['POST'])
def delete_conversation():
    history_id = request.json.get('history_id')
    data = chatpdf.delete_record_from_chatpdf_history(history_id)
    return jsonify(data)

@app.route('/delete-file', methods=['POST'])
def delete_file():
    file_id = request.json.get('file_id')
    print(file_id)
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
