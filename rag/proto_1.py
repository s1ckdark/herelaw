import openai
import os
from dotenv import load_dotenv
import docx
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import FAISS
from langchain.text_splitter import CharacterTextSplitter

# Load environment variables
load_dotenv()
openai.api_key = os.getenv("HERELAW_OPENAI_API_KEY")

# Function to load .docx files
def load_docx(file_path):
    doc = docx.Document(file_path)
    text = ""
    for paragraph in doc.paragraphs:
        text += paragraph.text + "\n"
    return text

# Function to load and embed reference documents
def load_and_embed_documents(file_paths):
    documents = []
    for file_path in file_paths:
        text = load_docx(file_path)
        documents.append(text)
    
    # Split text into chunks (1000 characters each)
    text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    texts = text_splitter.create_documents(documents)

    # Create embeddings and vector store
    embeddings = OpenAIEmbeddings()
    vectorstore = FAISS.from_documents(texts, embeddings)
    return vectorstore

# Function to retrieve relevant reference texts based on consultation data
def retrieve_relevant_texts(data_text, vectorstore, k=3):
    # Embed the query text
    query_embedding = OpenAIEmbeddings().embed_query(data_text)
    # Retrieve top similar documents
    results = vectorstore.similarity_search_with_score_by_vector(query_embedding, k=k)
    # Combine the content of the retrieved documents
    reference_texts = "\n".join([doc.page_content for doc, score in results])
    return reference_texts

# Function to generate divorce petition
def generate_divorce_petition(data_text, reference_texts):
    # Define the messages for the chat model
    messages = [
        {"role": "system", "content": "당신은 이혼 소장을 작성하는 법률 보조 시스템입니다."},
        {"role": "user", "content": f"상담 데이터:\n{data_text}\n\n참고 문서:\n{reference_texts}\n\n제공된 상담 데이터와 참고 문서를 바탕으로 이혼 소장을 작성해 주세요. 소장에는 다음과 같은 항목을 포함하고, 각 항목을 명확하게 구분하여 법적 문서 형식으로 작성해 주세요:\n\n1. 원고 정보\n2. 피고 정보\n3. 청구 취지\n4. 청구 원인\n5. 첨부 서류\n6. 대리인 정보\n\n각 항목에 상담 데이터를 바탕으로 필요한 내용을 작성해 주세요. 만약 정보가 부족하면 ‘추후 기재’라고 표시해 주세요. 제출용 법적 문서 형식을 갖추어 전문적이고 깔끔하게 작성해 주세요."}
    ]

    
    # Call the chat completion endpoint
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.7
    )
    
    # Extract the assistant's reply
    petition = response.choices[0].message.content
    return petition

# Main execution
if __name__ == "__main__":
    # Load consultation data
    data_text = load_docx("../data/data.docx")
    
    # Load and embed reference documents
    reference_files = ["../data/claim.docx", "../data/relief.docx", "../data/result.docx"]
    vectorstore = load_and_embed_documents(reference_files)
    
    # Retrieve relevant reference texts
    reference_texts = retrieve_relevant_texts(data_text, vectorstore)
    
    # Generate the divorce petition
    petition = generate_divorce_petition(data_text, reference_texts)
    print("Generated Divorce Petition:\n", petition)
