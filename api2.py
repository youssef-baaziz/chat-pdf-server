from flask import Flask, request, jsonify
import os
import json
from PyPDF2 import PdfReader
from dotenv import load_dotenv
from langchain.text_splitter import CharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import FAISS
from langchain.chat_models import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain
import mysql.connector
import asyncio
import aiofiles
from flask_cors import CORS
from datetime import datetime
import random
import string

app = Flask(__name__)
CORS(app, origins=["http://localhost:5173"])
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['DATA_JSON_FOLDER'] = 'data_json'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['DATA_JSON_FOLDER'], exist_ok=True)

# Load environment variables
load_dotenv()
openai_key = os.getenv("OPENAI_API_KEY")

# Initialize session state variables
session_state = {
    "history": {"id": [], "question": [], "answer": []},
    "hold_descriptions": [],
    "hold_files": [],
    "file_names": '',
    "conversation": [],
}

def get_text_from_doc(docs, description):
    text = ""
    if description:
        text += description + "\n"
    for doc in docs:
        if doc.endswith(".pdf"):
            pdf_reader = PdfReader(doc)
            for page in pdf_reader.pages:
                text += doc + " "
                text += page.extract_text() or ""
        else:
            with open(doc, 'r') as file:
                text += file.read()
    return text

def process_text(text, do_split=True):
    if not do_split:
        return [text]
    text_splitter = CharacterTextSplitter(
        separator="\n", chunk_size=1000, chunk_overlap=200, length_function=len
    )
    chunks = text_splitter.split_text(text)
    return chunks

def get_vectorstore(text_chunks, model_name):
    embeddings = OpenAIEmbeddings(model=model_name)
    vectorstore = FAISS.from_texts(texts=text_chunks, embedding=embeddings)
    return vectorstore

def get_conversation_chain(vectorstore, model_name="gpt-4-turbo"):
    llm = ChatOpenAI(temperature=0.2, model_name=model_name, openai_api_key=openai_key)
    memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
    conversation_chain = ConversationalRetrievalChain.from_llm(
        llm=llm, retriever=vectorstore.as_retriever(), memory=memory
    )
    return conversation_chain

def connect_to_db():
    return mysql.connector.connect(
            host="172.30.1.200",
            user="remote",
            password="snomone2014",
            port=3306,
            database="240109_voice_bot"
        )

def stock_in_file2(question,answer):
    fileJson = session_state["file_names"]
    file_path = os.path.join(app.config['DATA_JSON_FOLDER'], fileJson)
    datafile = {'question':question,'answer':answer}
    
    if os.path.isfile(file_path):
        content_file = read_json_file(app.config['DATA_JSON_FOLDER'], fileJson)
        content_file.append(datafile)
        print("exist")
        with open(file_path, 'w') as file:
            json.dump(content_file, file, indent=4)
    else:
        print("not exist")
        with open(file_path, 'w') as file:
            json.dump([], file, indent=4)
            
# def stock_in_file3():
#     fileJson = session_state["file_names"]+'.json'
#     file_path = os.path.join(app.config['DATA_JSON_FOLDER'], fileJson)
#     # if os.path.isfile(file_path):
#     content_file = read_json_file(app.config['DATA_JSON_FOLDER'], fileJson)
#     data = session_state["history"]
#     print("data history")
#     print(data)
#     history_data = [
#         {
#             "question": q,
#             "answer": r
#         }
#         for q, r in zip(data["question"], data["answer"])
#     ]
#     with open(app.config['DATA_JSON_FOLDER']+'/'+fileJson+'.json', 'w') as file:
#         json.dump(history_data, file)
#     # else:
#     #     data = session_state["history"]
#     #     history_data = [
#     #         {
#     #             "question": q,
#     #             "answer": r
#     #         }
#     #         for q, r in zip(data["question"], data["answer"])
#     #     ]
#     #     with open(app.config['DATA_JSON_FOLDER']+'/'+fileJson+'.json', 'w') as file:
#     #         json.dump(history_data, file)
            
# def stock_in_file(fileJson):
#     print('data')
#     print(session_state["history"])
#     file_exist = check_file_if_exist(fileJson)
    
#     print("history_data")
#     print(history_data)
#     if file_exist:
#         content_file = read_json_file(app.config['DATA_JSON_FOLDER'], fileJson)
#         data = session_state["history"]
#         history_data = [
#             {
#                 "question": q,
#                 "answer": r
#             }
#             for q, r in zip(data["question"], data["answer"])
#         ]
#         with open(app.config['DATA_JSON_FOLDER']+'/'+fileJson+'.json', 'w') as file:
#             json.dump(history_data, file)
#     else:
#         data = session_state["history"]
#         history_data = [
#             {
#                 "question": q,
#                 "answer": r
#             }
#             for q, r in zip(data["question"], data["answer"])
#         ]
#         with open(app.config['DATA_JSON_FOLDER']+'/'+fileJson+'.json', 'w') as file:
#             json.dump(history_data, file)

def get_files_name():
    connection = connect_to_db()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM chatpdf_history")
    data = cursor.fetchall()
    connection.close()
    return data

def check_file_if_exist(file_json):
    connection = connect_to_db()
    cursor = connection.cursor()
    file = file_json
    cursor.execute("SELECT * FROM chatpdf_history WHERE file_stock_json = %s", (file_json,))
    file_json = cursor.fetchall()
    connection.close()
    if file_json:
        return True
    else:
        return False
    
def get_file_id(file):
    connection = connect_to_db()
    cursor = connection.cursor()
    cursor.execute("SELECT id FROM chatpdf_files WHERE file = %s", (file,))
    result = cursor.fetchone()
    connection.close()
    return result[0] if result else None

def get_file_by_id(history_id):
    connection = connect_to_db()
    cursor = connection.cursor()
    cursor.execute("""SELECT f.file FROM chatpdf_files f
    JOIN chatpdf_history_files h ON f.id = h.chatpdf_file_id
    WHERE h.chatpdf_history_id = %s""", (history_id,))
    files = cursor.fetchall()
    connection.close()
    return [item[0] for item in files]

def insert_file(file):
    connection = connect_to_db()
    cursor = connection.cursor()
    cursor.execute("INSERT INTO chatpdf_files (file) VALUES (%s)", (file,))
    connection.commit()
    file_id = cursor.lastrowid
    connection.close()
    return file_id

def process_files_and_history(files, file_stock_json):    
    file_exist = check_file_if_exist(file_stock_json)
    if not file_exist:
        file_ids = []
        for file in files:
            file_id = get_file_id(file)
            if not file_id:
                file_id = insert_file(file)
            file_ids.append(file_id)
            
        connection = connect_to_db()
        cursor = connection.cursor()
        
        now = datetime.now()
        random_string = ''.join(random.choices(string.ascii_letters + string.digits, k=5))
        identifiant = 'file_'+random_string+'_'+ now.strftime("%Y-%m-%d %H:%M:%S")
        # Insert chat history
        cursor.execute("INSERT INTO chatpdf_history (identifiant, file_stock_json) VALUES (%s, %s)", (identifiant, file_stock_json))
        history_id = cursor.lastrowid
        
        # Associate files with chat history
        for file_id in file_ids:
            cursor.execute("INSERT INTO chatpdf_history_files (chatpdf_history_id, chatpdf_file_id) VALUES (%s, %s)", (history_id, file_id))
        
        connection.commit()
        connection.close()
    
        print("add successfuly")
    else:
        print("file already exist")


# def check_file_exist(file):
#     connection = connect_to_db()
#     cursor = connection.cursor()
#     cursor.execute("SELECT file FROM chatpdf_files WHERE file = %s", (file,))
#     exists = cursor.fetchone()
#     if not exists:
#         sql_insert = "INSERT INTO chatpdf_files (file) VALUES (%s)"
#         cursor.execute(sql_insert, (file,))
#         connection.commit()
#         print(f"Inserted file: {file}")
#     else:
#         print(f"file already exists: {file}")

def initialize_data():
    session_state['hold_files'] = []
    session_state['conversation'] = []
    session_state['hold_descriptions'] = []
    session_state['file_names'] = ''
    session_state["history"] = {'id': [], 'question': [], 'answer': []}

def read_json_file(directory, filename):
    file_path = os.path.join(directory, filename)
    
    # Check if the file exists
    if os.path.isfile(file_path):
        print(f"Found file: {file_path}")
        # Open and read the JSON file
        with open(file_path, 'r') as file:
            data = json.load(file)
            return data
    else:
        return None

async def save_file(file):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    try:
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(file.read())
        print(f"File saved: {file_path}")
    except Exception as e:
        print(f"Error saving file: {e}")
        return None
    return file_path

# start the APIs
@app.route('/files', methods=['POST'])
def get_data_files():
    data = get_files_name()
    return jsonify(data)

@app.route('/history', methods=['POST'])
def get_data_history():
    history_file = request.json.get('history_file_json')
    history_id = request.json.get('history_id')
    file_labels = get_file_by_id(history_id)
    
    print("history_file")
    print(history_file)
    print("file_labels")
    print(file_labels)   
        
    file_path = []
    
    for file_label in file_labels:
        file_path.append(os.path.join(app.config['UPLOAD_FOLDER'], file_label))
        # if not os.path.isfile(file_path):
        #     file_path = None
        
        
    print("file_path")
    print(file_path)
    session_state['file_names'] = '__'.join([os.path.basename(f)[:-4] for f in file_path])+'.json'
    
    if not file_path:
        return jsonify({"error": "file path not found"}), 404
    
    new_description = ""
    raw_text = get_text_from_doc(file_path, new_description)
    
    if not raw_text:
        return jsonify({"error": "No text extracted from the files"}), 400

    do_split = False
    text_chunks = process_text(raw_text, do_split=do_split)

    vectorstore = get_vectorstore(text_chunks, "gpt-4-turbo")
    session_state["conversation"] = get_conversation_chain(vectorstore)
    
    content_file = read_json_file(app.config['DATA_JSON_FOLDER'], history_file)
    if content_file is None:
        return jsonify({"error": "History file not found"}), 404
    elif content_file == []:
        return [] 
    
    return jsonify(content_file)

@app.route('/upload', methods=['POST'])
async def upload_files():
    description = ''
    initialize_data()
    files = request.files.getlist('files')

    if not files:
        return jsonify({"error": "No files provided"}), 400
    file_stock = []
    file_paths = await asyncio.gather(*[save_file(file) for file in files])
    print("file_paths")
    print(file_paths)
    for file_path in file_paths:
        if os.path.isfile(file_path):
            file_name = os.path.basename(file_path)
            file_stock.append(file_name)
    
    file_name_json = '__'.join([os.path.basename(f)[:-4] for f in file_paths])+'.json'
    session_state['file_names'] = '__'.join([os.path.basename(f)[:-4] for f in file_paths])+'.json'
    process_files_and_history(file_stock, file_name_json)
    stock_in_file2("","")
    
    session_state['hold_descriptions'].append(description)
    session_state['hold_files'].extend(file_paths)

    if not session_state['hold_files']:
        return jsonify({"error": "No files to process"}), 400

    new_description = " ".join(session_state['hold_descriptions'])
    raw_text = get_text_from_doc(session_state['hold_files'], new_description)

    if not raw_text:
        return jsonify({"error": "No text extracted from the files"}), 400

    do_split = False
    text_chunks = process_text(raw_text, do_split=do_split)

    vectorstore = get_vectorstore(text_chunks, "gpt-4-turbo")
    session_state["conversation"] = get_conversation_chain(vectorstore)

    return jsonify({"message": "Files uploaded and processed successfully"}), 200

@app.route('/response', methods=['POST'])
def query_model():
    user_question = request.json.get('question', '')
    if not user_question:
        return jsonify({"error": "No question provided"}), 400

    if not session_state["conversation"]:
        return jsonify({"error": "Conversation not initialized"}), 400

    try:
        response = session_state["conversation"]({"question": user_question})
        question = response['question']
        answer = response['answer']
        stock_in_file2(question,answer)
        get_data_files()
        return jsonify({"question": question, "answer": answer}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.config["JSON_AS_ASCII"] = False
    app.config["JSONIFY_PRETTYPRINT_REGULAR"] = True
    app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024
    app.run(host="0.0.0.0", port=5055)
