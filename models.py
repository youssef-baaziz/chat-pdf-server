import mysql.connector
from mysql.connector import Error
from werkzeug.security import generate_password_hash, check_password_hash
import bcrypt # type: ignore

class User:
    def __init__(self, username, password=None, firstname=None, lastname=None):
        self.username = username
        self.firstname = firstname if firstname else None
        self.lastname = lastname if lastname else None
        salt = bcrypt.gensalt()
        self.password = bcrypt.hashpw(password.encode('utf-8'), salt) if password else None
        # self.password = generate_password_hash(password) if password else None

    @staticmethod
    def connect_db():
        """Establishes a connection to the MySQL database."""
        try:
            connection = mysql.connector.connect(
                host="127.0.0.1",
                user="root",
                password="",
                port=3306,
                database="ask_multi_documents"
            )
            if connection.is_connected():
                return connection
        except Error as e:
            print(f"Error: {e}")
            return None

    def save(self):
        """Saves the user to the database."""
        connection = self.connect_db()
        if connection:
            cursor = connection.cursor()
            print(self.username, self.password, self.firstname, self.lastname)
            try:
                cursor.execute("INSERT INTO users (username, password, firstname, lastname) VALUES (%s, %s, %s, %s)", 
                               (self.username, self.password, self.firstname, self.lastname))
                connection.commit()
            except Error as e:
                print(f"Error: {e}")
            finally:
                cursor.close()
                connection.close()

    @staticmethod
    def verify(username, password):
        """Verifies user credentials."""
        connection = User.connect_db()
        if connection:
            cursor = connection.cursor(dictionary=True)
            try:
                cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
                user = cursor.fetchone()
                print('users:', user)
                print('hash:', password)
                print('stored password:', user['password'])

                # Ensure that the password from the database is converted to bytes
                stored_password_bytes = user['password'].encode('utf-8') if isinstance(user['password'], str) else user['password']

                is_password_correct = bcrypt.checkpw(password.encode('utf-8'), stored_password_bytes)
                if is_password_correct:
                    print("Password is correct")
                    return user
                else:
                    print('Password is incorrect')
                    return None
            except Error as e:
                print(f"Error: {e}")
            finally:
                cursor.close()
                connection.close()
                
    def getDataUser(username, password):
        connection = User.connect_db()
        if connection:
            cursor = connection.cursor(dictionary=True)
            try:
                cursor.execute("SELECT username,firstname,lastname FROM users WHERE username = %s", (username,))
                user = cursor.fetchone()
                stored_password_bytes = user['password'].encode('utf-8') if isinstance(user['password'], str) else user['password']
                is_password_correct = bcrypt.checkpw(password.encode('utf-8'), stored_password_bytes)
                if is_password_correct:
                    return user
                else:
                    return None
            except Error as e:
                print(f"Error: {e}")
            finally:
                cursor.close()
                connection.close()

    @staticmethod
    def get_by_username(username):
        """Fetch user details by username."""
        connection = User.connect_db()
        if connection:
            cursor = connection.cursor(dictionary=True)
            try:
                cursor.execute("SELECT id ,username, firstname, lastname FROM users WHERE username = %s", (username,))
                user = cursor.fetchone()
                return user
            except Error as e:
                print(f"Error: {e}")
            finally:
                cursor.close()
                connection.close()
        return None

# Usage example:
# Create a new user
# new_user = User(username='example_user', password='your_secure_password')
# new_user.save()

# # Verify user credentials
# verified_user = User.verify('example_user', 'your_secure_password')
# if verified_user:
#     print("User verified:", verified_user)
# else:
#     print("Invalid credentials.")
