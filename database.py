import mysql.connector
from mysql.connector import Error

class database:
    def connect_to_db():
        return mysql.connector.connect(
                host="127.0.0.1",
                user="root",
                password="",
                port=3306,
                database="ask_multi_documents"
            )
        
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
            