from pymongo import MongoClient
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import MongoDBAtlasVectorSearch
from langchain.document_loaders import DirectoryLoader
from langchain.llms import OpenAI
from langchain.chains import RetrievalQA
import gradio as gr
import os
import glob
from gradio.themes.base import Base
import docx import Document
from dotenv import load_dotenv

client = MongoClient(key_param.MONGO_URI)
dbName = "langchain_demo"
collectionName = "collection_of_text_blobs"
collection = client[dbName][collectionName]

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
loader = DirectoryLoader( './embedding', glob="./*.docx", show_progress=True)
data = loader.load()

embeddings = OpenAIEmbeddings(openai_api_key=api_key)

vectorStore = MongoDBAtlasVectorSearch.from_documents( data, embeddings, collection=collection )

