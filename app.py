import streamlit as st
from dotenv import load_dotenv
from PyPDF2 import PdfReader
from langchain.text_splitter import CharacterTextSplitter
from htmlTemplates import css, bot_template, user_template
# from langchain.llms import HuggingFaceHub
import os
import json
import asyncio
import aiofiles
import mysql.connector


openai_key = os.getenv("OPENAI_API_KEY")

def initialiserData(initialier):
    if initialier == True:
        listHistory = []
        hold_descriptions = []
        hold_files = []
        file_names = []

if "history_label" not in st.session_state:
    st.session_state.history_label = ''

if "show_history" not in st.session_state:
    st.session_state.show_history = False
    
if "history" not in st.session_state:
    try:
        with open("history.json", "r") as file:
            st.session_state.history = json.load(file)
    except Exception as e:
        st.session_state.history = {"questions": [], "responses": []}

history = st.session_state.history

if "history_label" not in st.session_state:
    st.session_state.history_label = ''

if "show_history" not in st.session_state:
    st.session_state.show_history = False

if "hold_descriptions" not in st.session_state and "hold_files" not in st.session_state:
    st.session_state.hold_descriptions = []
    st.session_state.hold_files = []
    st.session_state.file_names = [] 

if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

if 'user_question' not in st.session_state:
    st.session_state.user_question = ''


def load_tasks():
    try:
        with open("tasks.json", "r") as f:
            tasks = json.load(f)
    except FileNotFoundError:
        tasks = []
    return tasks


def save_tasks(tasks):
    with open("tasks.json", "w") as f:
        json.dump(tasks, f)


def get_text_from_doc(docs, description):
    text = ""
    ##### description
    if description:
        text += description + "\n"
    ######
    for doc in docs:
        if doc.type == "application/pdf":
            pdf_reader = PdfReader(doc)
            for page in pdf_reader.pages:
                # nom du fichier
                text += doc.name + " "
                text += page.extract_text() or ""
        elif doc.type in ["text/plain", "application/rtf", "text/rtf"]:
            text += doc.read().decode("utf-8")

    return text


def add_description(descriptions, new_description):
    if new_description:
        descriptions.append(new_description)
        # st.success("Description added successfully!")
    else:
        descriptions.append("")


def display_descriptions(descriptions):
    st.write(f"descriptions {descriptions}")


def get_text_chunks(text):
    text_splitter = CharacterTextSplitter(
        separator="\n", chunk_size=1000, chunk_overlap=200, length_function=len
    )
    chunks = text_splitter.split_text(text)
    return chunks


def process_text(text, do_split=True):
    if not do_split:
        return [text]  # Return the entire text without splitting

    text_splitter = CharacterTextSplitter(
        separator="\n", chunk_size=1000, chunk_overlap=200, length_function=len
    )
    chunks = text_splitter.split_text(text)
    return chunks


def get_vectorstore(text_chunks, model_name):
    from langchain.embeddings import OpenAIEmbeddings
    from langchain.vectorstores import FAISS
    embeddings = OpenAIEmbeddings(model=model_name)
    # embeddings = HuggingFaceInstructEmbeddings(model_name="hkunlp/instructor-xl")
    vectorstore = FAISS.from_texts(texts=text_chunks, embedding=embeddings)
    return vectorstore


def get_conversation_chain(vectorstore, model_name="gpt-4-turbo"):
    from langchain.chat_models import ChatOpenAI
    from langchain.memory import ConversationBufferMemory
    from langchain.chains import ConversationalRetrievalChain
    llm = ChatOpenAI(temperature=0.2, model_name=model_name, openai_api_key=openai_key)

    # llm = HuggingFaceHub(repo_id="google/flan-t5-xxl", model_kwargs={"temperature":0.5, "max_length":512})

    memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
    conversation_chain = ConversationalRetrievalChain.from_llm(
        llm=llm, retriever=vectorstore.as_retriever(), memory=memory
    )
    print("----------")
    print(conversation_chain)
    return conversation_chain

def connect_to_db():
    return mysql.connector.connect(
            host="172.30.1.200",
            user="remote",
            password="snomone2014",
            port=3306,
            database="240109_voice_bot"
        )

    
def get_files_name():
    connection = connect_to_db()
    cursor = connection.cursor()
    cursor.execute("SELECT file_name FROM history_doc group by file_name")
    data = cursor.fetchall()
    connection.close()
    return [item[0] for item in data]


def get_history_by_file_name(label):
    connection = connect_to_db()
    cursor = connection.cursor()
    cursor.execute("SELECT question,response FROM history_doc WHERE file_name=%s", (label,))
    data = cursor.fetchall()
    connection.close()
    return data


def get_history(label):
    responses = get_history_by_file_name(label)
    for item in responses:
        question, response = item
        st.markdown(
            user_template.replace("{MSG}", question),
            unsafe_allow_html=True,
        )
        st.markdown(
            bot_template.replace("{MSG}", response),
            unsafe_allow_html=True,
        )      

def insert_data_to_history(question, response, filename):
    try:
        conn = connect_to_db()
        
        if conn.is_connected():
            print("Connected to the database")
            
        with conn.cursor() as cursor:
            sql_insert = "INSERT INTO history_doc (question, response, file_name) VALUES (%s, %s, %s)"
            cursor.execute(sql_insert, (question, response, filename))
            conn.commit()
        st.success('History added successfully')
        
    except mysql.connector.Error as e:
        print(f"Error inserting data into MySQL: {e}")
        st.error(f"Failed to insert history: {e}")
        
    finally:
        if conn.is_connected():
            conn.close()
            print("Database connection closed")
        

def handle_userinput(user_question):            
    try:
        response = st.session_state.conversation({"question": user_question})
        st.session_state.chat_history = response["chat_history"]
        question= ''
        answer= ''
        for i, message in enumerate(st.session_state.chat_history):
            if i % 2 == 0:
                # Replace {{MSG}} with the actual message content for the user
                st.markdown(
                    user_template.replace("{MSG}", message.content),
                    unsafe_allow_html=True,
                )
                history['questions'].append(message.content)
                question = message.content
            else:
                # Replace {{MSG}} with the actual message content for the bot
                st.markdown(
                    bot_template.replace("{MSG}", message.content),
                    unsafe_allow_html=True,
                )
                history['responses'].append(message.content)
                answer = message.content
                
        with open('history.json', 'w') as file:
            json.dump(history, file)
            
        insert_data_to_history(question,answer,st.session_state.file_names)
                
    except Exception as e:
        st.error("Veuillez d'abord charger le fichier puis cliquer sur 'Traiter'.")


async def get_audio_text(audio_path):
    # Define dynamic output file name based on audio file name
    output_file_name = audio_path.rsplit(".", 1)[0] + ".json"

    # Execute insanely-fast-whisper command with dynamic output file name asynchronously
    command = [
        "insanely-fast-whisper",
        "--file-name",
        audio_path,
        "--device-id",
        "mps",
        "--language",
        "fr",
        "--transcript-path",
        output_file_name,
    ]
    await asyncio.create_subprocess_exec(*command)

    # Asynchronously read the dynamically named output file
    async with aiofiles.open(output_file_name, "r") as f:
        output = json.loads(await f.read())

    # Optionally remove the audio and output files
    # os.remove(audio_path)
    # os.remove(output_file_name)

    return output["chunks"]


def render_checkbox(checkbox_state):
    checkbox_state = st.checkbox("Découper le contenu", value=checkbox_state)
    return checkbox_state


def calculate_result(checkbox_state):
    return True if checkbox_state else False


# Define a function to perform some action when a file is uploaded
def process_uploaded_files(uploaded_files, new_description):
    if uploaded_files is not None:
        for i, val in enumerate(uploaded_files):
            if i > (len(st.session_state.descriptions) - 1):
                # add description next to the file
                add_description(st.session_state.descriptions, new_description)

                # st.write(st.session_state.descriptions)


def check_if_lists_empty(list_of_lists):
    for sublist in list_of_lists:
        if sublist:
            return True
    return False

def deleteStorageFiles(self):
    storage_path  = os.getcwd()+"/sgd/storage/"+self.product
    for filename in os.listdir(storage_path):
        file_path = os.path.join(storage_path, filename)
        if os.path.isfile(file_path):
            os.remove(file_path)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

    
def uploadFilee(files,description,model):
    UPLOAD_FOLDER = 'uploads'
    ALLOWED_EXTENSIONS = {'pdf'}
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)

    # app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    new_description = " ".join(map(str, description))
    doc_files = [item for sublist in files for item in sublist]
    raw_text = get_text_from_doc(doc_files, new_description)
    model_choice = model
    text_chunks = process_text(raw_text, do_split=do_split)
    vectorstore = get_vectorstore(text_chunks, model_choice)

    get_conversation_chain(vectorstore, model_name=model_choice) 

def uploads():
    if st.button("Ajouter vos documents"):
        st.session_state.hold_descriptions.append("")
        st.session_state.hold_files.append("")

    # Input field for users to type in a description
    for i, value in enumerate(
        zip(st.session_state.hold_descriptions, st.session_state.hold_files)
    ):
        col1, col2 = st.columns([0.9, 0.1])
        if st.session_state.hold_descriptions[i] == None:
            continue
        if col2.button("X", key=f"delete_button_{i}"):
            st.write("heeeeeeeeeeeeeeeee")
            st.session_state.hold_descriptions[i] = None
            st.session_state.hold_files[i] = None
            # st.experimental_rerun()
            # continue
        st.session_state.hold_descriptions[i] = col1.text_input(
            "Entrer la description :", "", key=f"descr{i}"
        )
        st.session_state.hold_files[i] = col1.file_uploader(
            "Chargez vos documents ici,", accept_multiple_files=True, key=f"file{i}"
        )
        
def traiter():
    checkbox_state = False
    checkbox_state = render_checkbox(checkbox_state)
    do_split = calculate_result(checkbox_state)
    
    if not check_if_lists_empty(
        st.session_state.hold_files
    ) and not check_if_lists_empty(st.session_state.hold_descriptions):
        return "Aucun document n'a été sélectionné et aucune description"
    else:
        new_description = " ".join(map(str, st.session_state.hold_descriptions))
        doc_files = [
            item for sublist in st.session_state.hold_files for item in sublist
        ]
        for i, message in enumerate(st.session_state.hold_files):
            for item in message:
                st.session_state.file_names = item.name
        raw_text = get_text_from_doc(doc_files, new_description)
        if not raw_text:
            return "Aucun texte n'a été extrait des fichiers"
        else:
            st.empty()
        text_chunks = process_text(raw_text, do_split=do_split)
        
                    
        with open("output.txt", "w") as file:
            if isinstance(text_chunks, list):
                file.write("\n".join(text_chunks))
            else:
                file.write(text_chunks)
        vectorstore = get_vectorstore(text_chunks, selected_model_value)

        st.session_state.conversation = get_conversation_chain(
            vectorstore, model_name=selected_model_value
        )
def initialize_conversation():
    return lambda x: {"answer": "response based on " + x["question"]}


def uploadFile(files,model="gpt-4-turbo"):
    if "conversation" not in st.session_state:
        st.session_state.conversation = None
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = None
    if 'user_question' not in st.session_state:
        st.session_state.user_question = ''
    if 'show_history' not in st.session_state:
        st.session_state.show_history = False
    if 'clicked_item' not in st.session_state:
        st.session_state.clicked_item = None
        
    print(st.session_state.conversation)
    print(st.session_state.hold_files)
    print(st.session_state.chat_history)
    print(st.session_state.hold_descriptions)
    
    for i, value in enumerate(zip(st.session_state.hold_descriptions, st.session_state.hold_files)):
        if st.session_state.hold_descriptions[i] == None:
            continue
        
        st.session_state.hold_files[i] = files

        checkbox_state = False
        checkbox_state = render_checkbox(checkbox_state)
        do_split = calculate_result(checkbox_state)
        
        if not check_if_lists_empty(st.session_state.hold_files) and not check_if_lists_empty(st.session_state.hold_descriptions):
            new_description = " ".join(map(str, st.session_state.hold_descriptions))
            doc_files = [item for sublist in st.session_state.hold_files for item in sublist]
            raw_text = get_text_from_doc(doc_files, new_description)
            if not raw_text:
                print("Aucun texte n'a été extrait des fichiers")
            else:
                print('text vide')
            text_chunks = process_text(raw_text, do_split=do_split)
            with open("outputt.txt", "w") as file:
                if isinstance(text_chunks, list):
                    file.write("\n".join(text_chunks))
                else:
                    file.write(text_chunks)
                    
            vectorstore = get_vectorstore(text_chunks, model)

            st.session_state.conversation = get_conversation_chain(vectorstore, model_name=model)
    

def data_data(file=""):
    load_dotenv()
    st.set_page_config(page_title="Interroger vos documents")
    st.write(css, unsafe_allow_html=True)

    # if "conversation" not in st.session_state:
    #     st.session_state.conversation = initialize_conversation()
    # if "chat_history" not in st.session_state:
    #     st.session_state.chat_history = None
    # if 'user_question' not in st.session_state:
    #     st.session_state.user_question = ''
    # if 'show_history' not in st.session_state:
    #     st.session_state.show_history = False
    # if 'clicked_item' not in st.session_state:
    #     st.session_state.clicked_item = None   

    for i, value in enumerate(
        zip(st.session_state.hold_descriptions, st.session_state.hold_files)
    ):
        col1, col2 = st.columns([0.9, 0.1])
        if st.session_state.hold_descriptions[i] == None:
            continue
        if col2.button("X", key=f"delete_button_{i}"):
            # st.write(i)
            st.session_state.hold_descriptions[i] = None
            st.session_state.hold_files[i] = None
            st.experimental_rerun()
        st.session_state.hold_descriptions[i] = col1.text_input(
            "Entrer la description :", "", key=f"descr{i}"
        )
        st.session_state.hold_files[i] = file

        checkbox_state = False
        checkbox_state = render_checkbox(checkbox_state)
        do_split = calculate_result(checkbox_state)
        
        st.write(st.session_state.hold_files)
        if not check_if_lists_empty(
            st.session_state.hold_files
        ) and not check_if_lists_empty(st.session_state.hold_descriptions):
        
            new_description = " ".join(map(str, st.session_state.hold_descriptions))
            doc_files = [
                item for sublist in st.session_state.hold_files for item in sublist
            ]
            for i, message in enumerate(st.session_state.hold_files):
                for item in message:
                    st.session_state.file_names = item.name
            raw_text = get_text_from_doc(doc_files, new_description)
            if not raw_text:
                return
            else:
                st.empty()
            print(f"do_split = {do_split}")
            text_chunks = process_text(raw_text, do_split=do_split)
                        
            with open("output.txt", "w") as file:
                if isinstance(text_chunks, list):
                    file.write("\n".join(text_chunks))
                else:
                    file.write(text_chunks)
            vectorstore = get_vectorstore(text_chunks, "gpt-4-turbo")
            st.session_state.conversation = get_conversation_chain(
                vectorstore, model_name="gpt-4-turbo"
            )
        
    return "treated"

def get_responses(user_question):  
        response = st.session_state.conversation({"question": user_question})
        return response
        st.session_state.chat_history = response["chat_history"]
        question= ''
        answer= ''
        for i, message in enumerate(st.session_state.chat_history):
            if i % 2 == 0:
                history['questions'].append(message.content)
                question = message.content
            else:
                history['responses'].append(message.content)
                answer = message.content
                
        return response["chat_history"]
        
def main():
    load_dotenv()
    st.set_page_config(page_title="Interroger vos documents")
    st.write(css, unsafe_allow_html=True)

    if "conversation" not in st.session_state:
        st.session_state.conversation = None
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = None
    if 'user_question' not in st.session_state:
        st.session_state.user_question = ''

    st.header("Interroger plusieurs documents")

    user_question = st.text_input("Entrez votre question relative aux documents :")
    model_choice = st.selectbox(
        "Modèle à utiliser",
        options=[
            ("GPT 4 - 128k", "gpt-4-turbo"),
            ("GPT 3.5 - 16k", "gpt-3.5-turbo-0125"),
        ],
        format_func=lambda x: x[0],
        index=0,
    )
    selected_model_value = model_choice[1]
    if user_question  :
        handle_userinput(user_question)
        st.session_state.user_question = ''
        

    with st.sidebar:
        # st.subheader("Vos documents")
        ##### descriptions

        if st.button("Ajouter vos documents"):
            st.session_state.hold_descriptions.append("")
            st.session_state.hold_files.append("")

        # Input field for users to type in a description
        for i, value in enumerate(
            zip(st.session_state.hold_descriptions, st.session_state.hold_files)
        ):
            col1, col2 = st.columns([0.9, 0.1])
            if st.session_state.hold_descriptions[i] == None:
                continue
            if col2.button("X", key=f"delete_button_{i}"):
                # st.write(i)
                st.session_state.hold_descriptions[i] = None
                st.session_state.hold_files[i] = None
                st.experimental_rerun()
                # continue
            st.session_state.hold_descriptions[i] = col1.text_input(
                "Entrer la description :", "", key=f"descr{i}"
            )
            # display_descriptions(st.session_state.descriptions)

            ####### end description
            st.session_state.hold_files[i] = col1.file_uploader(
                "Chargez vos documents ici,", accept_multiple_files=True, key=f"file{i}"
            )

        ### option
        checkbox_state = False
        checkbox_state = render_checkbox(checkbox_state)
        do_split = calculate_result(checkbox_state)
        # st.write('Result:', do_split)
        ### end option

        if st.button("Traiter"):
            # st.write(st.session_state.hold_files)
            if not check_if_lists_empty(
                st.session_state.hold_files
            ) and not check_if_lists_empty(st.session_state.hold_descriptions):
                st.error("Aucun document n'a été sélectionné et aucune description.")
                return
            with st.spinner("Traitement en cours"):
                # Get audio text
                new_description = " ".join(map(str, st.session_state.hold_descriptions))
                doc_files = [
                    item for sublist in st.session_state.hold_files for item in sublist
                ]
                for i, message in enumerate(st.session_state.hold_files):
                    for item in message:
                        st.session_state.file_names = item.name
                        print(st.session_state.file_names)
                        print('ffffff')
                raw_text = get_text_from_doc(doc_files, new_description)
                if not raw_text:
                    st.error("Aucun texte n'a été extrait des fichiers.")
                    return
                else:
                    st.empty()
                # Get the text chunks
                print(f"do_split = {do_split}")
                text_chunks = process_text(raw_text, do_split=do_split)
                # add_to_history(f"do_split = {do_split}")
                
                            
                with open("output.txt", "w") as file:
                    if isinstance(text_chunks, list):
                        # If text_chunks is a list of strings
                        file.write("\n".join(text_chunks))
                    else:
                        # If text_chunks is a single string
                        file.write(text_chunks)
                # Create vector store
                vectorstore = get_vectorstore(text_chunks, "gpt-4-turbo")

                # Create conversation chain
                st.session_state.conversation = get_conversation_chain(
                    vectorstore, model_name="gpt-4-turbo"
                )
                print("hererererreer")
                print(st.session_state.conversation)
        questions = reversed(history['questions'])
        responses = reversed(history['responses'])
        for question, response in zip(questions, responses):
            with st.expander(question):
                st.write(response)
            
        
        
if __name__ == "__main__":
    main()
