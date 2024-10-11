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
import aiofiles
from datetime import datetime
import random
import string
import asyncio


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
word_json = ".json"

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

def get_text_from_doc2(docs, descriptions=None):
    text = ""
    for i, doc in enumerate(docs):
        if descriptions and i < len(descriptions):
            text += descriptions[i] + "\n"
        if doc.endswith(".pdf"):
            pdf_reader = PdfReader(doc)
            for page in pdf_reader.pages:
                text += doc + " "
                text += page.extract_text() or ""
        else:
            with open(doc, 'r') as file:
                text += file.read()
    return text

def process_text(text, do_split=False):
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

def get_conversation_chain(vectorstore, model_name="gpt-3.5-turbo-0125"):
    llm = ChatOpenAI(temperature=0.2, model_name=model_name, openai_api_key=openai_key)
    memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
    conversation_chain = ConversationalRetrievalChain.from_llm(
        llm=llm, retriever=vectorstore.as_retriever(), memory=memory
    )
    return conversation_chain

def connect_to_db():
    return mysql.connector.connect(
            host="127.0.0.1",
            user="root",
            password="",
            port=3306,
            database="ask_multi_documents"
        )

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


def get_files_name():
    connection = connect_to_db()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM chatpdf_history ORDER BY created_at DESC;")
    data = cursor.fetchall()
    connection.close()
    return data

def check_file_if_exist(file_json):
    connection = connect_to_db()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM chatpdf_history WHERE file_stock_json = %s", (file_json,))
    file_json = cursor.fetchall()
    connection.close()
    if file_json:
        return True
    else:
        return False

def rename_identifiant_in_table_chatpdf_history(identifiant, id):
    connection = connect_to_db()
    cursor = connection.cursor()
    
    try:
        cursor.execute("UPDATE chatpdf_history SET identifiant = %s WHERE id = %s", (identifiant, id))
        connection.commit()
        
        if cursor.rowcount > 0:
            print("Updated successfully.")
            return True
        else:
            print("Update failed or no changes made.")
            return False
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        return False
    finally:
        cursor.close()
        connection.close()
        
def updateDescription(filename, description):
    connection = connect_to_db()
    cursor = connection.cursor()
    cursor.execute("SELECT id FROM chatpdf_files WHERE file = %s", (filename,))
    result = cursor.fetchone()
    if result:
        try:
            cursor.execute("UPDATE chatpdf_files SET description = %s WHERE file = %s", (description, filename))
            connection.commit()
            
            if cursor.rowcount > 0:
                print("Updated successfully.")
                return True
            else:
                print("Update failed or no changes made.")
                return False
        except mysql.connector.Error as err:
            print(f"Error: {err}")
            return False
        finally:
            cursor.close()
            connection.close()
    else:
        cursor1 = connection.cursor()
        try:
            cursor1.execute("INSERT INTO chatpdf_files (file,description) VALUES (%s,%s)", (filename,description,))
            connection.commit()
            if cursor1.rowcount > 0:
                print("Added successfully.")
                return True
            else:
                print("Update failed or no changes made.")
                return False
        except mysql.connector.Error as err:
            print(f"Error: {err}")
            return False
        finally:
            cursor.close()
            connection.close()
    
def delete_record_from_chatpdf_history(id):
    connection = connect_to_db()
    cursor = connection.cursor()
    
    if not connection.is_connected():
        print("Failed to connect to the database.")
        return False

    try:
        cursor.execute("DELETE FROM chatpdf_history_files WHERE chatpdf_history_id = %s", (id,))
        cursor.execute("DELETE FROM chatpdf_history WHERE id = %s", (id,))
        connection.commit()
        
        if cursor.rowcount > 0:
            print("Deleted successfully.")
            return True
        else:
            print("Delete failed or record not found.")
            return False
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        connection.rollback()
        return False
    finally:
        cursor.close()
        connection.close()
    
def delete_file(id):
    connection = connect_to_db()
    cursor = connection.cursor()
    
    if not connection.is_connected():
        print("Failed to connect to the database.")
        return False

    try:
        cursor.execute("DELETE FROM chatpdf_history_files WHERE chatpdf_file_id = %s", (id,))
        connection.commit()
        
        if cursor.rowcount > 0:
            print("Deleted successfully.")
            return True
        else:
            print("Delete failed or record not found.")
            return False
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        connection.rollback()
        return False
    finally:
        cursor.close()
        connection.close()
        
                   
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
    cursor.execute("""SELECT * FROM chatpdf_files f
    JOIN chatpdf_history_files h ON f.id = h.chatpdf_file_id
    WHERE h.chatpdf_history_id = %s""", (history_id,))
    files = cursor.fetchall()
    connection.close()
    return [item for item in files]

def insert_file(file):
    connection = connect_to_db()
    cursor = connection.cursor()
    cursor.execute("INSERT INTO chatpdf_files (file) VALUES (%s)", (file,))
    connection.commit()
    file_id = cursor.lastrowid
    connection.close()
    return file_id

def insert_in_table_files(file,description):
    connection = connect_to_db()
    cursor = connection.cursor()
    cursor.execute("INSERT INTO chatpdf_files (file,description) VALUES (%s,%s)", (file,description))
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

def process_insert_into_files_and_history(files, file_stock_json,descriptions,identifiant):    
    file_exist = check_file_if_exist(file_stock_json)
    if not file_exist:
        file_ids = []
        for file, description in zip(files, descriptions):
            file_id = get_file_id(file)
            if not file_id:
                file_id = insert_in_table_files(file,description)
            file_ids.append(file_id)
            
        connection = connect_to_db()
        cursor = connection.cursor()
        
        # now = datetime.now()
        # random_string = ''.join(random.choices(string.ascii_letters + string.digits, k=5))
        # identifiant = 'file_'+random_string+'_'+ now.strftime("%Y-%m-%d %H:%M:%S")
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

async def save_file(file,upload_folder):
    file_path = os.path.join(upload_folder, file.filename)
    try:
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(file.read())
        print(f"File saved: {file_path}")
    except Exception as e:
        print(f"Error saving file: {e}")
        return None
    return file_path

def data_history(history_id,history_file,folder_json,upload_folder):
    file_labels = get_file_by_id(history_id)       
    file_path = []
    descriptions = []
    
    for file_label in file_labels:
        descriptions.append(file_label[2])
        file_path.append(os.path.join(upload_folder, file_label[1]))
        
    # session_state['file_names'] = '__'.join([os.path.basename(f)[:-4] for f in file_path])+word_json
    session_state['file_names'] = history_file
    print("descriptions",descriptions)
    process_file2(file_path,descriptions)
    
    if os.path.exists(os.path.join(folder_json, history_file)):
        content_file = read_json_file(folder_json, history_file)
        if content_file is None:
            return {"error": "History file not found"}
        elif content_file == []:
            return [] 
    
    return content_file


async def upload_file(files,upload_json,upload_folder,descriptions):
    # description = ''
    initialize_data()
    if not files:
        return {"error": "No files provided"}
    file_stock = []
    
    now = datetime.now()
    random_string = ''.join(random.choices(string.ascii_letters + string.digits, k=5))
    identifiant = 'file_'+random_string+'_'+ now.strftime("%Y-%m-%d %H:%M:%S")
    file_name_json = 'file_'+random_string+'_'+ now.strftime("%Y-%m-%d %H-%M-%S")+word_json
    
    file_paths = await asyncio.gather(*[save_file(file,upload_folder) for file in files])
    
    for file_path in file_paths:
        if os.path.isfile(file_path):
            file_name = os.path.basename(file_path)
            file_stock.append(file_name)
            
    session_state['hold_descriptions'] = descriptions
    
    # file_name_json = '__'.join([os.path.basename(f)[:-4] for f in file_paths])+word_json
    # session_state['file_names'] = '__'.join([os.path.basename(f)[:-4] for f in file_paths])+word_json
    
    session_state['file_names'] = file_name_json
    process_insert_into_files_and_history(file_stock, file_name_json,session_state['hold_descriptions'],identifiant)
    stock_in_file('','',upload_json)
    
    
    # session_state['hold_descriptions'].append(description)
    session_state['hold_files'].extend(file_paths)
    process_file2(session_state['hold_files'],session_state['hold_descriptions']);

    return {"message": "Files uploaded and processed successfully"}


def process_file2(file_paths, descriptions):
    if not file_paths:
        return {"error": "No files to process"}
    
    if not descriptions or len(descriptions) != len(file_paths):
        return {"error": "Descriptions count does not match files count"}

    raw_text = get_text_from_doc2(file_paths, descriptions)
    
    if not raw_text:
        return {"error": "No text extracted from the files"}

    do_split = False
    text_chunks = process_text(raw_text, do_split=do_split)

    vectorstore = get_vectorstore(text_chunks, "gpt-4-turbo")
    session_state["conversation"] = get_conversation_chain(vectorstore)

def process_file(file_paths,description):
    if not file_paths:
        return {"error": "No files to process"}

    new_description = " ".join(description)
    raw_text = get_text_from_doc(file_paths, new_description)

    if not raw_text:
        return {"error": "No text extracted from the files"}

    do_split = False
    text_chunks = process_text(raw_text, do_split=do_split)

    vectorstore = get_vectorstore(text_chunks, "gpt-4-turbo")
    session_state["conversation"] = get_conversation_chain(vectorstore)
    
    
def get_response(user_question,upload_json):
    if not user_question:
        return {"error": "No question provided"}

    if not session_state["conversation"]:
        return {"error": "Conversation not initialized"}

    try:
        response = session_state["conversation"]({"question": user_question})
        question = response['question']
        answer = response['answer']
        stock_in_file(question,answer,upload_json)
        return {"question": question, "answer": answer}

    except Exception as e:
        return {"error": str(e)}