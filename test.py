from data_section_files import section_files
import mysql.connector
import os
from datetime import datetime
import random
import string
from chatpdf import *
session_state = {
    "history": {"id": [], "question": [], "answer": []},
    "hold_descriptions": [],
    "hold_files": [],
    "file_names": '',
    "conversation": [],
}

def initialize_data():
    session_state['hold_files'] = []
    session_state['conversation'] = []
    session_state['hold_descriptions'] = []
    session_state['file_names'] = ''
    session_state["history"] = {'id': [], 'question': [], 'answer': []}
    
def connect_to_db():
    return mysql.connector.connect(
            host="127.0.0.1",
            user="root",
            password="",
            port=3306,
            database="ask_multi_documents"
        )
    
def get_file_by_filename(file):
    connection = connect_to_db()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM chatpdf_files WHERE file = %s", (file,))
    result = cursor.fetchall()
    connection.close()
    return result

def data_section():
    upload_json = 'exemple.json'
    upload_folder = "./uploads"
    
    initialize_data()
    if not section_files:
        return {"error": "No files provided"}
    
    print("file",section_files['section1'])
    
    for section in section_files['section1']:
        print("section",section)
        file_labels = get_file_by_filename(section)
        print("files_labels",file_labels)
        file_paths = []
        descriptions = []
    
        if file_labels:
            for file_label in file_labels:
                descriptions.append(file_label[2])
                file_paths.append(os.path.join(upload_folder, file_label[1]))
    
    print("descriptions",descriptions)        
    session_state['hold_descriptions'] = descriptions
    
    now = datetime.now()
    random_string = ''.join(random.choices(string.ascii_letters + string.digits, k=5))
    identifiant = 'file_'+random_string+'_'+ now.strftime("%Y-%m-%d %H:%M:%S")
    file_name_json = "identifiant" + '.json'
    session_state['file_names'] = file_name_json
    
    process_insert_into_files_and_history(file_paths, file_name_json,session_state['hold_descriptions'],identifiant,6)
    stock_in_file('','',"tester")
    
    session_state['hold_files'].extend(file_paths)
    process_file2(session_state['hold_files'],session_state['hold_descriptions']);

    return {"message": "Files section uploaded and processed successfully"}


def stock_in_file(question,answer,upload_json):
    file_json = session_state['file_names']
    print("hello",file_json)
    file_path = os.path.join(upload_json, file_json)
    print("file_path",file_path)
    datafile = {'question': question, 'answer': answer}

    print("datafile",datafile)
    print("question.strip()",question.strip())
    print("answer.strip()",answer.strip())
    
    if question.strip() and answer.strip():
        if os.path.isfile(file_path):
            content_file = read_json_file(upload_json, file_json)
            content_file.append(datafile)
            with open(file_path, 'w') as file:
                json.dump(content_file, file, indent=4)
        else:
            with open(file_path, 'w') as file:
                json.dump([datafile], file, indent=4)
    else:
        with open(file_path, 'w') as file:
            json.dump([], file, indent=4)
        print("Either 'question' or 'answer' is empty. Please provide both.")
# section_files = [
#     {
#         "id": 1,
#         "files": ["file1.txt","file2.pdf","rb.pdf",],
#     },
#     {
#         "id": 1,
#         "files": ["file1.txt"],
#     },
#     {
#         "id": 1,
#         "files": ["file1.txt"],
#     }
# ]
# print("section_files",section_files[0]['files'])
data_section()

