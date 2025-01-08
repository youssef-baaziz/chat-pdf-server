import os
import json
from PyPDF2 import PdfReader
from dotenv import load_dotenv

from langchain.text_splitter import CharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import FAISS
from langchain.chat_models import ChatOpenAI
from langchain.memory import ConversationBufferMemory,ConversationSummaryMemory
from langchain.chains import ConversationalRetrievalChain
import mysql.connector
import aiofiles
from datetime import datetime
import random
import string
import asyncio
# from docx import Document
import fitz
from data_section_files import section_files

from PIL import Image
import pytesseract
from io import BytesIO
                    
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

# def read_docx(file_path):
#     with zipfile.ZipFile(file_path, 'r') as docx:
#         # Open the document.xml file within the .docx archive
#         xml_content = docx.read('word/document.xml')

#         # Parse the XML content
#         tree = ET.XML(xml_content)

#         # Extract text from XML
#         namespace = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
#         paragraphs = []
#         for paragraph in tree.iter(f'{namespace}p'):
#             texts = [node.text for node in paragraph.iter(f'{namespace}t') if node.text]
#             paragraphs.append(''.join(texts))

#         return '\n'.join(paragraphs)
    
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

def get_text_from_image(images,page_num,doc):
    text_image = ""
    print(f"Page {page_num + 1} contains images.")
                        
    for img_index, img in enumerate(images):
        xref = img[0]  # The image XREF index
        base_image = doc.extract_image(xref)
        image_bytes = base_image["image"]  # Raw image data
        image_ext = base_image["ext"]  # Image file extension (e.g., 'png')

        try:
            # Create an image object from the extracted image bytes
            image = Image.open(BytesIO(image_bytes))

            # Save the image temporarily
            image_filename = f"extracted_image_page{page_num+1}_img{img_index+1}.{image_ext}"
            image.save(image_filename)
            
            # Use Tesseract to extract text from the image
            text = pytesseract.image_to_string(image)
            
            # Print the extracted text
            # print(f"Extracted Text from Page {page_num + 1}, Image {img_index + 1}:")
            text_image += text + "\n"

        finally:
            image.close()

            if os.path.exists(image_filename):
                os.remove(image_filename)
                print(f"Deleted image: {image_filename}")
            else:
                print(f"Failed to delete")
                    
    return text_image             
                    
def get_text_from_doc2(docs, descriptions=None):
    text = ""
    
    for i, doc in enumerate(docs):
        file_content = ""
        file_name = os.path.basename(doc)
        description = descriptions[i] if descriptions and i < len(descriptions) else "No description provided"
        
        file_content += f"Name of the file: {file_name}\n"
        file_content += f"Description: {description}\n"
        file_content += "Content:\n"
        pytesseract.pytesseract.tesseract_cmd = r'C:\Users\ybaaziz\AppData\Local\Programs\Tesseract-OCR\tesseract.exe'
        
        try:
            # Handle PDF files
            if doc.endswith(".pdf"):
                pdf_document = fitz.open(doc)
                print(f"le nom de fichier : {os.path.basename(doc)}")
                # Loop through all the pages
                for page_num in range(len(pdf_document)):
                    page = pdf_document.load_page(page_num)
                    images = page.get_images(full=True)
                    
                    if images:
                        text_image = get_text_from_image(images,page_num,pdf_document)
                        file_content += text_image + "\n"
                    else:
                        page_text = page.get_text()
                        if page_text:
                            file_content += page_text + "\n"
                            
                # Close the PDF file
                pdf_document.close()

            # Handle plain text (.txt) files
            elif doc.endswith(".txt"):
                with open(doc, 'r', encoding="utf-8") as f:
                    file_content += f.read()
            
            # Handle .docx (Word) files
            elif doc.endswith(".docx"):
                word_document = fitz.open(doc)

                for page_num in range(word_document.page_count):
                    page = word_document.load_page(page_num)

                    images = page.get_images(full=True)
                    if images:
                        text_image = get_text_from_image(images,page_num,word_document)
                        file_content += text_image + "\n"
                    else:
                        # If no images, read normal text
                        page_text = page.get_text()
                        if page_text:
                            file_content += page_text + "\n"
                            
                # Close the WORD file
                word_document.close()
        
            # Handle other generic file types like .rtf or others
            else:
                with open(doc, 'r', encoding='utf-8') as file:
                    file_content += file.read()
                    
        except Exception as e:
            file_content += f"\nError reading file: {e}\n"
        
        # Append this file's content to the main text
        text += file_content + "\n" + "-" * 80 + "\n"

    return text



# def get_text_from_doc2(docs, descriptions=None):
#     text = ""
    
#     for i, doc in enumerate(docs):
        
#         file_content = ""
#         file_name = os.path.basename(doc)
#         description = descriptions[i] if descriptions and i < len(descriptions) else "No description provided"
        
#         file_content += f"Name of the file: {file_name}\n"
#         file_content += f"Description: {description}\n"
#         file_content += "Content:\n"
        
#         try:
            
#             # Add description if available
#             # if descriptions and i < len(descriptions):
#             #     text += descriptions[i] + "\n"
        
#             # Handle PDF files
#             if doc.endswith(".pdf"):
#                 pdf_reader = PdfReader(doc)
#                 for page in pdf_reader.pages:
#                     file_content += page.extract_text() or ""
            
#             # Handle plain text (.txt) files
#             elif doc.endswith(".txt"):
#                 # file_content += doc.read().decode("utf-8")
#                 with open(doc, 'r', encoding="utf-8") as f:
#                     file_content += f.read()
            
#             # Handle .docx (Word) files
#             elif doc.endswith(".docx"):
#                 doc = fitz.open(doc)

#                 # Extract text from each page of the document
#                 for page_num in range(doc.page_count):
#                     page = doc.load_page(page_num)
#                     file_content = page.get_text()
#                     print(file_content)
                
#                 # docx = Document(doc)
#                 # for para in docx.paragraphs:
#                 #     file_content += para.text + "\n"
        
#             # Handle generic file types like .rtf or others by opening
#             else:
#                 with open(doc, 'r', encoding='utf-8') as file:
#                     file_content += file.read()
                    
#         except Exception as e:
#             file_content += f"\nError reading file: {e}\n"
        
#         # Append this file's content to the main text
#         text += file_content + "\n" + "-" * 80 + "\n"

#     return text


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

def get_conversation_chain(vectorstore, model_name="gpt-4"):
    # model_name="gpt-3.5-turbo-0125"
    llm = ChatOpenAI(temperature=0.5, model_name=model_name, openai_api_key=openai_key)
    # llm = ChatOpenAI(temperature=0.2, model_name=model_name, openai_api_key=openai_key)
    memory = ConversationSummaryMemory(memory_key="chat_history", return_messages=True,llm=llm)
    # memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
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
    file_path = os.path.join(upload_json, file_json)
    datafile = {'question': question, 'answer': answer}
    
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


def get_files_name(user_id):
    connection = connect_to_db()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM chatpdf_history WHERE user_id = %s ORDER BY created_at DESC;",(user_id,))
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
            print("History updated successfully.")
            return True
        else:
            print("History update failed or no changes were made.")
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
                print("File updated successfully.")
                return True
            else:
                print("File update failed or no changes were made.")
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
                print("File added successfully.")
                return True
            else:
                print("File addition failed or no changes were made.")
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
            print("History deleted successfully.")
            return True
        else:
            print("History deletion failed or record not found.")
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
            print("File deleted successfully.")
            return True
        else:
            print("File deletion failed or record not found.")
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
    if description is None or description == 'undefined':
        description = ""
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
    
        print("History added successfuly")
    else:
        print("History already exists")
        
def process_insert_into_other_files_history(files, history_id, descriptions):
    file_labels = get_file_by_id(history_id)
    if file_labels:
        file_ids = []
        for file, description in zip(files, descriptions):
            file_id = get_file_id(file)
            if not file_id:
                file_id = insert_in_table_files(file,description)
            file_ids.append(file_id)
            
        connection = connect_to_db()
        cursor = connection.cursor()
        
        # Associate files with chat history
        for file_id in file_ids:
            cursor.execute("INSERT INTO chatpdf_history_files (chatpdf_history_id, chatpdf_file_id) VALUES (%s, %s)", (history_id, file_id))
        
        connection.commit()
        connection.close()
        print("Other files added with success")
    else:
        print("Error adding files to history.")
        
def process_insert_into_files_and_history(files, file_stock_json,descriptions,identifiant,user_id):    
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
        
        # Insert chat history
        cursor.execute("INSERT INTO chatpdf_history (identifiant, file_stock_json, user_id) VALUES (%s, %s, %s)", (identifiant, file_stock_json, user_id))
        history_id = cursor.lastrowid
        
        # Associate files with chat history
        for file_id in file_ids:
            cursor.execute("INSERT INTO chatpdf_history_files (chatpdf_history_id, chatpdf_file_id) VALUES (%s, %s)", (history_id, file_id))
        
        connection.commit()
        connection.close()
    
        print("History added successfuly.")
    else:
        print("History already exists.")
        
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
        # async with aiofiles.open(file_path, mode='r') as file:
        #     data = await file.read()
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

def traiter_file_have_history(history_id,history_file,upload_folder):
    file_labels = get_file_by_id(history_id)
    file_path = []
    descriptions = []
    
    for file_label in file_labels:
        descriptions.append(file_label[2])
        file_path.append(os.path.join(upload_folder, file_label[1]))
    
    session_state['file_names'] = history_file
    process_file2(file_path,descriptions)
    
def data_history(history_file,folder_json):
    # file_labels = get_file_by_id(history_id)       
    # file_path = []
    # descriptions = []
    
    # for file_label in file_labels:
    #     descriptions.append(file_label[2])
    #     file_path.append(os.path.join(upload_folder, file_label[1]))
    
    # session_state['file_names'] = history_file
    # print("descriptions",descriptions)
    # process_file2(file_path,descriptions)
    content_file = []
    if os.path.exists(os.path.join(folder_json, history_file)):
        content_file = read_json_file(folder_json, history_file)
        if content_file is None:
            return {"error": "History file not found"}
        elif content_file == []:
            return [] 
    
    return content_file

def data_history(history_file,folder_json):
    # file_labels = get_file_by_id(history_id)       
    # file_path = []
    # descriptions = []
    
    # for file_label in file_labels:
    #     descriptions.append(file_label[2])
    #     file_path.append(os.path.join(upload_folder, file_label[1]))
    
    # session_state['file_names'] = history_file
    # print("descriptions",descriptions)
    # process_file2(file_path,descriptions)
    content_file = []
    if os.path.exists(os.path.join(folder_json, history_file)):
        content_file = read_json_file(folder_json, history_file)
        if content_file is None:
            return {"error": "History file not found"}
        elif content_file == []:
            return [] 
    
    return content_file

async def upload_other_files(files,upload_folder,identifiant,descriptions,user_id):
    initialize_data()
    if not files:
        return {"error": "No files provided"}
    file_stock = []
    
    file_name_json = identifiant + word_json
    
    file_paths = await asyncio.gather(*[save_file(file,upload_folder) for file in files])
    
    for file_path in file_paths:
        if os.path.isfile(file_path):
            file_name = os.path.basename(file_path)
            file_stock.append(file_name)
            
    session_state['hold_descriptions'] = descriptions
    
    session_state['file_names'] = file_name_json
    process_insert_into_files_and_history(file_stock, file_name_json,session_state['hold_descriptions'],identifiant,user_id)

    session_state['hold_files'].extend(file_paths)
    process_file2(session_state['hold_files'],session_state['hold_descriptions']);

    return {"message": "Files uploaded and processed successfully"}

async def upload_file(files,upload_json,upload_folder,descriptions,user_id):
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
    process_insert_into_files_and_history(file_stock, file_name_json,session_state['hold_descriptions'],identifiant,user_id)
    stock_in_file('','',upload_json)
    
    
    # session_state['hold_descriptions'].append(description)
    session_state['hold_files'].extend(file_paths)
    process_file2(session_state['hold_files'],session_state['hold_descriptions']);

    return {"message": "Files uploaded and processed successfully"}


def process_file2(file_paths, descriptions):
    if not file_paths or not descriptions or len(file_paths) != len(descriptions):
        return {"error": "Mismatch between file paths and descriptions"}

    raw_text = get_text_from_doc2(file_paths, descriptions)
    if not raw_text:
        return {"error": "No text extracted from the files"}
    
    text_size = len(raw_text)  # Use len(raw_text) for characters or tokenize it for word/token count
    if text_size < 500:
        do_split = False  # Small text
    elif 500 <= text_size <= 2000:
        do_split = True  # Medium text
    else:
        do_split = True  # Large text
   
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
    user_question_fr = f"{user_question}\nRépondez uniquement en français, peu importe la langue de la question."
    try:
        response = session_state["conversation"]({"question": user_question_fr})
        question = response['question']
        answer = response['answer']
        stock_in_file(question,answer,upload_json)
        return {"question": question, "answer": answer}

    except Exception as e:
        return {"error": str(e)}
    

async def upload_and_process_files(new_files,upload_folder,history_id,new_descriptions):
    initialize_data()
    history_id = history_id
    
    file_labels = get_file_by_id(history_id)
    old_file_paths = []
    new_file_stock = []
    old_descriptions = []
    if not new_files:
        return {"error": "No files provided"}  
    
    # Save the new files to the upload folder
    new_file_paths = await asyncio.gather(*[save_file(file, upload_folder) for file in new_files])
    # Process new file paths, add them to file stock
    for file_path in new_file_paths:
        if os.path.isfile(file_path):
            file_name = os.path.basename(file_path)
            new_file_stock.append(file_name)
    # Insert new files and descriptions into database
    process_insert_into_other_files_history(new_file_stock, history_id, new_descriptions)
    
    for file_label in file_labels:
        old_descriptions.append(file_label[2])
        old_file_paths.append(os.path.join(upload_folder, file_label[1]))
        
    file_paths = old_file_paths + new_file_paths
    descriptions = old_descriptions + new_descriptions
    session_state['hold_files'].extend(file_paths)
    session_state['hold_descriptions'].extend(descriptions)
    process_file2(session_state['hold_files'], session_state['hold_descriptions'])

    return {"message": "Other files uploaded and processed successfully"}

def get_section_by_user(user_id):
    connection = connect_to_db()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM sections WHERE user_id = %s", (user_id,))
    result = cursor.fetchall()
    connection.close()
    return result

def get_file_by_section(section_label):
    connection = connect_to_db()
    cursor = connection.cursor()
    cursor.execute("""SELECT f.id,f.file,f.description FROM sections_files sf
    JOIN sections s ON s.id = sf.section_id
    JOIN chatpdf_files f ON f.id = sf.file_id
    WHERE s.label = %s""", (section_label,))
    result = cursor.fetchall()
    connection.close()
    return result

def get_new_conversation_by_section(section_label,upload_json,upload_folder,user_id):
    initialize_data()
    if not section_label:
        return {"error": "No section provided"}
    else:
        file_labels = get_file_by_section(section_label)
        file_paths = []
        descriptions = []

        if file_labels:
            for file_label in file_labels:
                descriptions.append(file_label[2])
                file_paths.append(file_label[1])
             
        session_state['hold_descriptions'] = descriptions
        
        # for section in section_files[section_label]:
        #     print("section",section)
            
            
            
        
        now = datetime.now()
        random_string = ''.join(random.choices(string.ascii_letters + string.digits, k=5))
        identifiant = 'file_'+random_string+'_'+ now.strftime("%Y-%m-%d %H:%M:%S")
        file_name_json = 'file_'+random_string+'_'+ now.strftime("%Y-%m-%d %H-%M-%S") + '.json'
        session_state['file_names'] = file_name_json
        
        process_insert_into_files_and_history(file_paths, file_name_json,session_state['hold_descriptions'],identifiant,user_id)
        stock_in_file('','',upload_json)
        
        session_state['hold_files'].extend(file_paths)
        process_file2(session_state['hold_files'],session_state['hold_descriptions']);

    return {"message": "Files section uploaded and processed successfully"}
    