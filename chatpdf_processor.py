from langchain.text_splitter import CharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import FAISS
from langchain.chat_models import ChatOpenAI
from langchain.memory import ConversationBufferMemory,ConversationSummaryMemory
from langchain.chains import ConversationalRetrievalChain
# from langchain.llms import ChatOpenAI
from callbacks import CustomStreamingCallbackHandler
import os
openai_key = os.getenv("OPENAI_API_KEY")

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

# def get_conversation_chain(vectorstore, model_name="gpt-4"):
#     # model_name="gpt-3.5-turbo-0125"
#     llm = ChatOpenAI(temperature=0.5, model_name=model_name, openai_api_key=openai_key)
#     # llm = ChatOpenAI(temperature=0.2, model_name=model_name, openai_api_key=openai_key)
#     memory = ConversationSummaryMemory(memory_key="chat_history", return_messages=True,llm=llm)
#     # memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
#     # memory.chat_memory.add_user_message("Répondez à toutes les questions uniquement en français, même si elles sont posées en anglais.")
#     conversation_chain = ConversationalRetrievalChain.from_llm(
#         llm=llm, retriever=vectorstore.as_retriever(), memory=memory
#     )
#     return conversation_chain

# from flask_socketio import emit

def get_conversation_chain(vectorstore, model_name="gpt-4"):
    # Initialize the LLM with streaming enabled
    llm = ChatOpenAI(
        temperature=0.3,
        model_name=model_name,
        openai_api_key=openai_key,
        streaming=True,  # Enable streaming
        callbacks=[],  # Stream to custom handler
    )

    system_message_language = "Répondez à toutes les questions uniquement en français, même si elles sont posées en anglais."
    system_message_behavior = "You are a good assistant that can answer the user's question using provided tools."
    
    # Use ConversationSummaryMemory for summarizing the chat history
    # memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
    memory = ConversationSummaryMemory(memory_key="chat_history", return_messages=True, llm=llm)
    
    memory.chat_memory.add_user_message(system_message_behavior)
    memory.chat_memory.add_user_message(system_message_language)
    
    # Create the ConversationalRetrievalChain with streaming enabled
    conversation_chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=vectorstore.as_retriever(),
        memory=memory,
        verbose=True,
    )

    return conversation_chain