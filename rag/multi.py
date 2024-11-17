import streamlit as st
import openai
import os
from dotenv import load_dotenv
from langchain.vectorstores import FAISS
from langchain.text_splitter import CharacterTextSplitter
from langsmith import Client
from langchain.embeddings import OpenAIEmbeddings
from langchain.callbacks.tracers import LangChainTracer
from langchain.callbacks.manager import CallbackManager
from typing import List, Dict
import json
from datetime import datetime
from pymongo import MongoClient
import uuid
import hashlib

# .env 파일 로드
load_dotenv()

class MongoDBManager:
    def __init__(self, uri):
        if not uri:
            raise ValueError("MongoDB URI is required")
        self.client = MongoClient(uri)
        self.db = self.client['divorce_db']
        self.conversations = self.db['conversations']
        self.documents = self.db['document_chunks']
        
        # 인덱스 생성
        self.documents.create_index([("chunk_hash", 1)], unique=True)
    
    def save_chunk(self, content: str, doc_type: str, embedding: List[float]):
        """문서 청크 저장"""
        chunk_hash = hashlib.md5(content.encode()).hexdigest()
        if not self.documents.find_one({"chunk_hash": chunk_hash}):
            self.documents.insert_one({
                "content": content,
                "doc_type": doc_type,
                "chunk_hash": chunk_hash,
                "embedding": embedding,
                "timestamp": datetime.now()
            })
    
    def save_conversation(self, session_id: str, user_input: str, generated_content: Dict):
        """대화 내용 저장"""
        self.conversations.insert_one({
            "session_id": session_id,
            "timestamp": datetime.now(),
            "user_input": user_input,
            "generated_content": generated_content
        })

    def get_similar_chunks(self, query_embedding: List[float], doc_type: str, k: int = 3):
        """유사한 청크 검색"""
        raise NotImplementedError("Vector search not implemented in this example.")

class SessionManager:
    def __init__(self):
        if 'session_id' not in st.session_state:
            st.session_state.session_id = str(uuid.uuid4())
        if 'conversation_history' not in st.session_state:
            st.session_state.conversation_history = []
    
    def get_session_id(self) -> str:
        return st.session_state.session_id
    
    def add_to_history(self, user_input: str, generated_content: Dict):
        st.session_state.conversation_history.append({
            'timestamp': datetime.now(),
            'user_input': user_input,
            'generated_content': generated_content
        })

class DivorceComplaintGenerator:
    def __init__(self):
        # 환경 변수에서 값 로드
        api_key = os.getenv("OPENAI_API_KEY")
        mongo_uri = os.getenv("MONGO_URI")
        endpoint = os.getenv("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com")
        langchain_api_key = os.getenv("LANGCHAIN_API_KEY")
        self.project_name = os.getenv("LANGCHAIN_PROJECT", "default_project")  # 기본값 설정

        # LangSmith 설정
        if langchain_api_key:  # API 키가 있을 때만 LangSmith 초기화
            print("LangSmith 클라이언트 초기화")
            self.langsmith_client = Client(
                api_url=endpoint,  # base_url로 변경
                api_key=langchain_api_key,
            )
        else:
            self.langsmith_client = None
            print("LangSmith 클라이언트가 초기화되지 않았습니다. 트레이싱이 비활성화됩니다.")

        # OpenAI Embeddings 초기화
        self.embeddings = OpenAIEmbeddings(api_key=api_key)
        
        # MongoDB 연결
        self.mongo_db = MongoDBManager(mongo_uri)
        self.session_manager = SessionManager()
    
    def generate_complaint(self, consultation_text: str) -> dict:
        """소장 생성"""
        run_id = None

        if self.langsmith_client:  # LangSmith가 설정된 경우 실행 생성
            # 실행 생성 (name 및 run_type 포함)
            run_id = self.langsmith_client.create_run(
                name="generate_complaint",  # 실행 이름
                run_type="tool",            # 실행 유형 (예: 'tool', 'chain', 'llm' 등)
                project_name=self.project_name,  # 프로젝트 이름
                inputs={"consultation_text": consultation_text}  # 입력 데이터
            )

        try:
            # 내부 로직 실행
            result = self._generate_complaint_internal(consultation_text)

            # 실행 결과 업데이트
            if self.langsmith_client and run_id:
                self.langsmith_client.update_run(
                    run_id=run_id,
                    outputs=result,
                    status="completed"
                )
            return result
        except Exception as e:
            # 실행 오류 처리
            if self.langsmith_client and run_id:
                self.langsmith_client.update_run(
                    run_id=run_id,
                    error=str(e),
                    status="failed"
                )
            raise e


    def _generate_complaint_internal(self, consultation_text: str) -> dict:
        """실제 소장 생성 로직 (임의로 대체 가능)"""
        claim_chunks = ["Claim data placeholder"]
        relief_chunks = ["Relief data placeholder"]

        return self._generate_with_gpt(consultation_text, claim_chunks, relief_chunks)

    def _generate_with_gpt(self, consultation_text: str, claim_chunks: List[str], relief_chunks: List[str]) -> dict:
        """GPT로 소장 생성"""
        prompt = (
            "다음 상담 내용과 참고 문서를 바탕으로 이혼 소장을 작성해주세요.\n\n"
            f"[상담 내용]\n{consultation_text}\n\n"
            f"[청구취지 참고문서]\n{' '.join(claim_chunks)}\n\n"
            f"[청구원인 참고문서]\n{' '.join(relief_chunks)}\n\n"
            "아래 형식으로 작성해주세요:\n\n"
            "소    장\n\n"
            "원 고: [원고정보]\n"
            "피 고: [피고정보]\n\n"
            "청 구 취 지\n"
            "1. 이혼 청구\n"
            "2. 위자료 청구 (해당되는 경우)\n"
            "3. 재산분할 청구 (해당되는 경우)\n"
            "4. 양육권 및 양육비 청구 (해당되는 경우)\n"
            "5. 소송비용 청구\n"
            "6. 가집행 신청 (위자료나 양육비 청구가 있는 경우)\n\n"
            "청 구 원 인\n"
            "1. 당사자의 지위\n"
            "2. 재판상 이혼사유\n"
            "3. 위자료 청구 사유 (해당되는 경우)\n"
            "4. 재산분할 청구 사유 (해당되는 경우)\n"
            "5. 양육권 및 양육비 청구 사유 (해당되는 경우)\n\n"
            "입 증 방 법\n"
            "첨 부 서 류"
        )
        
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system", 
                    "content": "당신은 전문 법률 문서 작성 시스템입니다. 이혼 소장을 작성해주세요."
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            temperature=0.3
        )
        
        return response.choices[0].message.content

def main():
    st.set_page_config(page_title="이혼 소장 자동 생성 시스템", layout="wide")
    
    st.title("이혼 소장 자동 생성 시스템")
    
    generator = DivorceComplaintGenerator()
    
    consultation_text = st.text_area(
        "상담 내용을 입력하세요",
        height=300,
        key="consultation_input"
    )
    if st.button("소장 생성", type="primary"):
        if not consultation_text:
            st.error("상담 내용을 입력해주세요.")
            return
            
        with st.spinner("소장 생성 중..."):
            try:
                # 소장 생성
                complaint = generator.generate_complaint(consultation_text)
                
                # 결과 표시
                st.subheader("생성된 소장")
                st.markdown(complaint)
                
            except Exception as e:
                st.error(f"오류가 발생했습니다: {str(e)}")
    
    # 대화 기록 표시
    if st.session_state.conversation_history:
        st.subheader("상담 기록")
        for idx, conv in enumerate(st.session_state.conversation_history):
            with st.expander(f"상담 {idx + 1} - {conv['timestamp']}"):
                st.text("상담 내용:")
                st.text(conv["user_input"])
                st.text("생성된 소장:")
                st.json(conv["generated_content"])

if __name__ == "__main__":
    main()