import streamlit as st
from dotenv import load_dotenv
from PyPDF2 import PdfReader
from langchain.text_splitter import CharacterTextSplitter
import os
import json
import asyncio
import aiofiles
import streamlit as st

openai_key = os.getenv("OPENAI_API_KEY")
    
if "history" not in st.session_state:
    try:
        with open("history.json", "r") as file:
            st.session_state.history = json.load(file)
    except Exception as e:
        st.session_state.history = {"questions": [], "responses": []}

history = st.session_state.history

if "hold_files" not in st.session_state:
    st.session_state.hold_files = []
    st.session_state.file_names = [] 
    
if "conversation" not in st.session_state:
    st.session_state.conversation = []
        
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
    
if not hasattr(st, 'session_state'):
    st.session_state = {}

def get_text_from_doc(docs, description):
    text = ""
    if description:
        text += description + "\n"
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
        return [text]

    text_splitter = CharacterTextSplitter(
        separator="\n", chunk_size=1000, chunk_overlap=200, length_function=len
    )
    chunks = text_splitter.split_text(text)
    return chunks


def get_vectorstore(text_chunks, model_name):
    from langchain.embeddings import OpenAIEmbeddings
    from langchain.vectorstores import FAISS
    embeddings = OpenAIEmbeddings(model=model_name)
    vectorstore = FAISS.from_texts(texts=text_chunks, embedding=embeddings)
    return vectorstore


def get_conversation_chain(vectorstore, model_name="gpt-4-turbo"):
    from langchain.chat_models import ChatOpenAI
    from langchain.memory import ConversationBufferMemory
    from langchain.chains import ConversationalRetrievalChain
    llm = ChatOpenAI(temperature=0.2, model_name=model_name, openai_api_key=openai_key)

    memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
    conversation_chain = ConversationalRetrievalChain.from_llm(
        llm=llm, retriever=vectorstore.as_retriever(), memory=memory
    )
    
    return conversation_chain


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

    return output["chunks"]


def render_checkbox(checkbox_state):
    checkbox_state = st.checkbox("Découper le contenu", value=checkbox_state)
    return checkbox_state


def calculate_result(checkbox_state):
    return True if checkbox_state else False


def check_if_lists_empty(list_of_lists):
    for sublist in list_of_lists:
        if sublist:
            return True
    return False

def get_responses(user_question):
    if st.session_state.conversation is None:
        return {"error": "Conversation not initialized. Please upload files first."}
        
    response = st.session_state.conversation
    return st.session_state.conversation
    st.session_state.chat_history = response["chat_history"]

    history = {"questions": [], "responses": []}
    question = ''
    answer = ''
    for i, message in enumerate(st.session_state.chat_history):
        if i % 2 == 0:
            history['questions'].append(message['content'])
            question = message['content']
        else:
            history['responses'].append(message['content'])
            answer = message['content']
            
    return history
def trated():
    checkbox_state = False
    checkbox_state = render_checkbox(checkbox_state)
    do_split = calculate_result(checkbox_state)
    print("---------st.session_state.hold_files---------")
    print(st.session_state.hold_files)
    if not check_if_lists_empty(st.session_state.hold_files):
        doc_files = [item for sublist in st.session_state.hold_files for item in sublist]
        raw_text = get_text_from_doc(doc_files, '')
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
                
        print('97978979789797677489')
        vectorstore = get_vectorstore(text_chunks, "gpt-4-turbo")
        st.session_state.conversation = get_conversation_chain(vectorstore, model_name="gpt-4-turbo") 
    
def uploadFile(files):
    if "conversation" not in st.session_state:
        st.session_state.conversation = []
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if 'hold_files' not in st.session_state:
        st.session_state.hold_files = []
        
    for i, value in enumerate(zip(st.session_state.hold_files)):
        st.session_state.hold_files[i] = files
    
def main():
    load_dotenv()
    if "conversation" not in st.session_state:
        st.session_state.conversation = []
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if 'hold_files' not in st.session_state:
        st.session_state.hold_files = []
        
    print(st.session_state.conversation)
    print(st.session_state.hold_files)
    print(st.session_state.chat_history)
    
    
if __name__ == "__main__":
    main()