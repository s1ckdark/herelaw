from pymongo import MongoClient
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import MongoDBAtlasVectorSearch
from langchain.document_loaders import DirectoryLoader
from langchain.llms import OpenAI
from langchain.chains import RetrievalQA
import gradio as gr
from gradio.themes.base import Base
import os
from dotenv import load_dotenv
from pymongo.server_api import ServerApi

load_dotenv()

# MongoDB 연결 설정
uri = os.getenv("MONGODB_URI")  # .env 파일에서 URI를 가져오도록 수정
client = MongoClient(uri, server_api=ServerApi('1'))
dbName = "langchain_demo"
collectionName = "collection_of_text_blobs"
collection = client[dbName][collectionName]

# OpenAI API 키 설정
openai_api_key = os.getenv("OPENAI_API_KEY")  # .env 파일에서 API 키를 가져오도록 수정

# 임베딩 모델 초기화
embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key)

# 벡터 스토어 초기화
vectorStore = MongoDBAtlasVectorSearch(
    collection=collection,
    embedding=embeddings,
    index_name="default"  # Atlas Search 인덱스 이름 지정
)

def query_data(query):
    # Vector Search 실행
    docs = vectorStore.similarity_search(query, k=1)
    as_output = docs[0].page_content

    # LLM 초기화
    llm = OpenAI(openai_api_key=openai_api_key, temperature=0)
    
    # Retriever 설정
    retriever = vectorStore.as_retriever()
    
    # QA 체인 설정
    qa = RetrievalQA.from_chain_type(llm=llm, chain_type="stuff", retriever=retriever)
    
    # 쿼리 실행
    retriever_output = qa.run(query)
    
    return as_output, retriever_output

# Gradio 인터페이스 설정
with gr.Blocks(theme=Base(), title="Question Answering App using Vector Search + RAG") as demo:
    gr.Markdown(
        """
        # Question Answering App using Atlas Vector Search + RAG Architecture
        """)
    textbox = gr.Textbox(label="Enter your Question:")
    with gr.Row():
        button = gr.Button("Submit", variant="primary")
    with gr.Column():
        output1 = gr.Textbox(lines=1, max_lines=10, label="Atlas Vector Search Output:")
        output2 = gr.Textbox(lines=1, max_lines=10, label="RAG Output:")

    button.click(query_data, textbox, outputs=[output1, output2])

if __name__ == "__main__":
    demo.launch()

