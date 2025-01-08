from dotenv import load_dotenv
import mysql.connector
from datetime import datetime
import random
import string

load_dotenv()

def connect_to_db():
    return mysql.connector.connect(
            host="127.0.0.1",
            user="root",
            password="",
            port=3306,
            database="ask_multi_documents"
        )

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

    