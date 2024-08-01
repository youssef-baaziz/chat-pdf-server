
from PyPDF2 import PdfReader
from flask import Flask, request, jsonify
from langchain.text_splitter import CharacterTextSplitter
from app import data_data, get_responses, uploadFile
import os

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_text_from_doc(docs):
    text = ""
    for doc in docs:
        if doc.content_type == "application/pdf":
            pdf_reader = PdfReader(doc)
            for page in pdf_reader.pages:
                text += page.extract_text() or ""
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
    from langchain.embeddings import OpenAIEmbeddings
    from langchain.vectorstores import FAISS
    embeddings = OpenAIEmbeddings(model=model_name)
    vectorstore = FAISS.from_texts(texts=text_chunks, embedding=embeddings)
    return vectorstore

def get_conversation_chain(vectorstore, model_name="gpt-4-turbo"):
    from langchain.chat_models import ChatOpenAI
    from langchain.memory import ConversationBufferMemory
    from langchain.chains import ConversationalRetrievalChain
    llm = ChatOpenAI(temperature=0.2, model_name=model_name, openai_api_key=os.getenv("OPENAI_API_KEY"))
    memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
    conversation_chain = ConversationalRetrievalChain.from_llm(
        llm=llm, retriever=vectorstore.as_retriever(), memory=memory
    )
    return conversation_chain
@app.route('/gett', methods=['GET'])
def get_get():
    return "data"

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if file and allowed_file(file.filename):
        filename = file.filename
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        return uploadFile(file_path)
        file.save(file_path)
        
        # raw_text = get_text_from_doc([file])
        # text_chunks = process_text(raw_text, do_split=True)
        # vectorstore = get_vectorstore(text_chunks, "gpt-4-turbo")
        # data = get_conversation_chain(vectorstore, model_name="gpt-4-turbo")
        # print(data["chat_history"]);
        
        return jsonify({'filename': filename, 'message': 'File processed successfully'}), 200
    return jsonify({'error': 'File not allowed'}), 400

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_file(os.path.join(app.config['UPLOAD_FOLDER'], filename))


@app.route('/response', methods=['POST'])
def answer():
    if "text" not in request.get_json():
        return jsonify({"error": "Text parameter is missing"}), 400
    text = request.get_json()["text"]
    print("*******"+text)
    reponse = get_responses(text)
    print(reponse);
    return reponse

if __name__ == "__main__":
    app.config["JSON_AS_ASCII"] = False
    app.config["JSONIFY_PRETTYPRINT_REGULAR"] = True
    app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024
    app.run(host="0.0.0.0", port=5055)
