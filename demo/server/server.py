from flask import Flask, request, jsonify
import openai
import os
from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.text_splitter import CharacterTextSplitter
from langchain.chains import RetrievalQA
from langchain.llms import OpenAI
from pymongo import MongoClient
from datetime import datetime, timedelta
import uuid
import hashlib
from sklearn.preprocessing import StandardScaler
import numpy as np
from docx import Document
from langsmith import Client
from typing import List, Dict, Optional
import json
from moviepy import AudioFileClip
import jwt
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'your-secret-key')  # 실제 배포 시에는 반드시 환경 변수로 설정해야 합니다

class MongoDBManager:
    def __init__(self, uri):
        if not uri:
            raise ValueError("MongoDB URI is required")
        self.client = MongoClient(uri)
        self.db = self.client[os.getenv('MONGODB_DB', 'herelaw')]
        self.conversations = self.db[os.getenv('MONGODB_COLLECTION', 'divorce_complaint')]
        self.documents = self.db['document_chunks']
        self.feedback = self.db['feedback']
        self.users = self.db['users']
        self.sessions = self.db['sessions']
        
        print(f"MongoDB 연결 정보:")
        print(f"Database: {self.db.name}")
        print(f"Collections: {self.db.list_collection_names()}")
        
        # Create indexes
        self.documents.create_index([("chunk_hash", 1)], unique=True)
        self.feedback.create_index([("session_id", 1)])
        self.users.create_index([("username", 1)], unique=True)
        self.users.create_index([("email", 1)], unique=True)
        self.sessions.create_index([("user_id", 1)])
    
    def create_user(self, username: str, password: str, email: str) -> Optional[str]:
        """새 사용자를 생성합니다."""
        try:
            print(f"사용자 생성 시도: {username}")
            user_id = str(uuid.uuid4())
            result = self.users.insert_one({
                "user_id": user_id,
                "username": username,
                "email": email,
                "password": generate_password_hash(password),
                "created_at": datetime.utcnow(),
                "last_login": None
            })
            print(f"사용자 생성 결과: {result.inserted_id}")
            return user_id
        except Exception as e:
            print(f"사용자 생성 중 오류 발생: {str(e)}")
            return None
    
    def get_user_by_username(self, username: str) -> Optional[dict]:
        """사용자명으로 사용자를 조회합니다."""
        return self.users.find_one({"username": username})
    
    def get_user_by_id(self, user_id: str) -> Optional[dict]:
        """사용자 ID로 사용자를 조회합니다."""
        return self.users.find_one({"user_id": user_id})
    
    def verify_user(self, username: str, password: str) -> Optional[dict]:
        """사용자 인증을 수행합니다."""
        user = self.get_user_by_username(username)
        if user and check_password_hash(user["password"], password):
            self.users.update_one(
                {"user_id": user["user_id"]},
                {"$set": {"last_login": datetime.utcnow()}}
            )
            return user
        return None
    
    def save_session(self, user_id: str, consultation_text: str, generated_content: str) -> str:
        """사용자 세션을 저장합니다."""
        session_id = str(uuid.uuid4())
        self.sessions.insert_one({
            "session_id": session_id,
            "user_id": user_id,
            "consultation_text": consultation_text,
            "generated_content": generated_content,
            "timestamp": datetime.utcnow(),
            "rating": None,
            "feedback": None
        })
        return session_id
    
    def get_user_sessions(self, user_id: str) -> List[dict]:
        """사용자의 모든 세션을 조회합니다."""
        return list(self.sessions.find(
            {"user_id": user_id},
            {"_id": 0}
        ).sort("timestamp", -1))
    
    def update_session(self, session_id: str, rating: Optional[int] = None, 
                      feedback: Optional[str] = None) -> bool:
        """세션을 업데이트합니다."""
        update_data = {}
        if rating is not None:
            update_data["rating"] = rating
        if feedback is not None:
            update_data["feedback"] = feedback
        
        if update_data:
            result = self.sessions.update_one(
                {"session_id": session_id},
                {"$set": update_data}
            )
            return result.modified_count > 0
        return False

    def save_chunk(self, content: str, doc_type: str, embedding: List[float]):
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
        conversation = {
            "session_id": session_id,
            "timestamp": datetime.now(),
            "user_input": user_input,
            "generated_content": generated_content
        }
        self.conversations.insert_one(conversation)
        return conversation

    def get_similar_chunks(self, query_embedding: List[float], doc_type: str, k: int = 3):
        raise NotImplementedError("Vector search not implemented in this example.")

    def save_feedback(self, feedback_doc):
        """피드백을 저장합니다."""
        try:
            # 입력값 검증
            if not isinstance(feedback_doc.get('rating'), (int, float)):
                raise ValueError("rating must be a number")
            
            result = self.feedback.insert_one(feedback_doc)
            
            if result.inserted_id:
                print(f"피드백 저장 성공: {result.inserted_id}")
                return result.inserted_id
            else:
                raise Exception("피드백 저장 실패")
                
        except Exception as e:
            print(f"피드백 저장 중 오류: {str(e)}")
            raise e

    def get_feedback_statistics(self):
        pipeline = [
            {
                "$group": {
                    "_id": None,
                    "avg_rating": {"$avg": "$rating"},
                    "count": {"$sum": 1},
                    "ratings": {"$push": "$rating"}
                }
            }
        ]
        
        stats = list(self.feedback.aggregate(pipeline))
        if stats:
            return {
                "average_rating": stats[0]["avg_rating"],
                "total_feedback": stats[0]["count"],
                "rating_distribution": np.histogram(stats[0]["ratings"], bins=5)[0].tolist()
            }
        return None

class ReinforcementLearner:
    def __init__(self, mongo_db):
        self.mongo_db = mongo_db
        self.scaler = StandardScaler()
        self.min_feedback_samples = 10
    
    def extract_features(self, complaint: str) -> List[float]:
        """소장에서 특징 추출"""
        features = []
        
        # 1. 문서 길이
        features.append(len(complaint))
        
        # 2. 섹션 수
        sections = [s for s in complaint.split('\n\n') if s.strip()]
        features.append(len(sections))
        
        # 3. 법률 용어 사용 빈도
        legal_terms = ['청구취지', '청구원인', '입증방법', '첨부서류']
        for term in legal_terms:
            features.append(complaint.count(term))
        
        # 4. 문장의 평균 길이
        sentences = [s.strip() for s in complaint.split('.') if s.strip()]
        avg_sentence_length = sum(len(s) for s in sentences) / len(sentences) if sentences else 0
        features.append(avg_sentence_length)
        
        return features
    
    def calculate_reward(self, user_rating: float, complaint_length: int) -> float:
        """보상 계산"""
        # 기본 보상: 사용자 평가 (1-5점)
        base_reward = user_rating
        
        # 길이 보상: 적정 길이(1000-3000자)일 때 최대
        length_reward = 0
        if 1000 <= complaint_length <= 3000:
            length_reward = 1
        elif complaint_length < 1000:
            length_reward = complaint_length / 1000
        else:
            length_reward = 3000 / complaint_length
        
        # 최종 보상 = 기본 보상 * 0.7 + 길이 보상 * 0.3
        final_reward = base_reward * 0.7 + length_reward * 0.3
        
        return final_reward
    
    def get_best_practices(self) -> Dict:
        """높은 평가를 받은 소장들의 특징을 분석"""
        try:
            # 피드백 데이터 가져오기
            feedback_data = self.mongo_db.get_feedback_statistics()
            
            if not feedback_data or len(feedback_data) < self.min_feedback_samples:
                return None
            
            # 높은 평가를 받은 소장들만 선택 (평점 4점 이상)
            successful_complaints = [
                data for data in feedback_data 
                if data.get('rating', 0) >= 4
            ]
            
            if not successful_complaints:
                return None
            
            # 1. 평균 문서 길이 계산
            avg_length = sum(len(c['complaint']) for c in successful_complaints) / len(successful_complaints)
            
            # 2. 자주 사용된 문구 추출
            common_phrases = self._extract_common_phrases(successful_complaints)
            
            # 3. 섹션 구조 분석
            section_patterns = self._analyze_section_patterns(successful_complaints)
            
            # 4. 성공적인 특징 분석
            successful_features = self._analyze_successful_features(successful_complaints)
            
            return {
                'avg_length': avg_length,
                'common_phrases': common_phrases,
                'section_patterns': section_patterns,
                'successful_features': successful_features
            }
            
        except Exception as e:
            print(f"분석 중 오류 발생: {str(e)}")
            return None
    
    def _extract_common_phrases(self, feedback_data: List[Dict]) -> List[str]:
        """성공적인 소장들에서 자주 사용된 문구 추출"""
        common_phrases = [
            "청구취지", "청구원인", "입증방법", "첨부서류",
            "원고와 피고는", "혼인관계", "파탄", "이혼",
            "판결을 구합니다"
        ]
        return common_phrases
    
    def _analyze_section_patterns(self, feedback_data: List[Dict]) -> str:
        """성공적인 소장들의 섹션 구조 분석"""
        return """
        1. 청구취지 (판결을 구하는 내용)
        2. 청구원인 (구체적인 이혼 사유)
        3. 입증방법 (증거 자료)
        4. 첨부서류 (필요 서류)
        """
    
    def _analyze_successful_features(self, feedback_data: List[Dict]) -> str:
        """성공적인 소장들의 특징 분석"""
        return """
        1. 명확하고 구체적인 사실관계 서술
        2. 적절한 법률 용어 사용
        3. 논리적인 구조와 흐름
        4. 객관적인 증거 자료 제시
        """

class DivorceComplaintGenerator:
    def __init__(self):
        self.mongo_db = mongodb_manager
        self.rl_learner = ReinforcementLearner(self.mongo_db)
        
    def generate_complaint(self, consultation_text: str, conversation_history: list) -> dict:
        """소장 생성"""
        try:
            # 성공적인 소장의 특징 가져오기
            best_practices = self.rl_learner.get_best_practices()
            
            if best_practices:
                # 피드백 기반 프롬프트 최적화
                quality_guidelines = f"""
                다음 기준을 충족하는 고품질 소장을 작성해주세요:
                1. 적정 문서 길이: {int(best_practices.get('avg_length', 2000))} 자 내외
                2. 다음 문구들을 적절히 활용하세요:
                   {', '.join(best_practices.get('common_phrases', [])[:5])}
                3. 성공적인 소장의 섹션 구조를 따르세요:
                   {best_practices.get('section_patterns', '기본 섹션 구조 사용')}
                4. 다음 특징들을 반영하세요:
                   {best_practices.get('successful_features', '기본 특징 사용')}
                """
            else:
                # 기본 가이드라인 사용
                quality_guidelines = """
                다음 기준을 충족하는 고품질 소장을 작성해주세요:
                1. 모든 필수 섹션을 포함할 것
                2. 구체적이고 명확한 법률 용어 사용
                3. 논리적인 구조와 흐름
                4. 적절한 길이와 상세도
                """
            
            # 대화 기록을 포함한 프롬프트 생성
            messages = []
            messages.append({
                "role": "user", 
                "content": """당신은 전문 법률 문서 작성 시스템입니다. 
                과거의 성공적인 소장 작성 경험을 바탕으로 최적화된 이혼 소장을 작성합니다.
                """ + quality_guidelines
            })
            
            # 이전 대화 기록 추가
            for msg in conversation_history:
                messages.append({"role": msg["role"], "content": msg["content"]})
            
            # 현재 상담 내용 추가
            messages.append({"role": "user", "content": consultation_text})
            
            # GPT 모델로 소장 초안 생성
            response = openai.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                temperature=0.3,
                max_tokens=2000
            )
            
            assistant_response = response.choices[0].message.content
            
            # 소장 생성을 위한 두 번째 API 호출
            complaint_prompt = f"""이 대화를 바탕으로 이혼 소장을 작성해주세요. 
            형식은 다음과 같아야 합니다:

            서울가정법원 귀중

            소장

            원고: [이름], [주소]
            피고: [이름], [주소]

            청구취지
            1. 원고와 피고의 이혼을 명한다.
            2. 소송비용은 피고가 부담한다.
            라는 판결을 구합니다.

            청구원인
            [상세 내용]

            입증방법
            1. [입증 자료 목록]

            첨부서류
            1. [첨부 서류 목록]

            [날짜]
            원고 [이름] (인)

            대화 내용: {consultation_text}"""
            
            complaint_response = openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "user", "content": complaint_prompt}
                ],
                temperature=0.3,
                max_tokens=2000
            )
            
            generated_complaint = complaint_response.choices[0].message.content
            
            # 대화 내용 저장
            session_id = self.mongodb_manager.save_session(
                self.user_id,
                consultation_text,
                {
                    "response": assistant_response,
                    "complaint": generated_complaint
                }
            )

            # 청크 저장을 위한 임베딩 생성
            embeddings = OpenAIEmbeddings()
            text_splitter = CharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200
            )
            
            # 소장 내용을 청크로 분할
            chunks = text_splitter.split_text(generated_complaint)
            
            # 각 청크를 저장
            for chunk in chunks:
                embedding = embeddings.embed_query(chunk)
                self.mongodb_manager.save_chunk(
                    content=chunk,
                    doc_type="divorce_complaint",
                    embedding=embedding
                )
            
            # 소장 특징 추출 및 피드백 저장 준비
            features = self.rl_learner.extract_features(generated_complaint)
            
            return {
                "response": assistant_response,
                "complaint": generated_complaint,
                "features": features,
                "session_id": session_id
            }
            
        except Exception as e:
            print(f"소장 생성 중 오류 발생: {str(e)}")
            raise e

class JWTManager:
    def __init__(self, secret_key):
        self.secret_key = secret_key
    
    def generate_token(self, user_id: str) -> str:
        """사용자 ID로 JWT 토큰을 생성합니다."""
        payload = {
            'user_id': user_id,
            'exp': datetime.utcnow() + timedelta(days=1)  # 토큰 만료 시간: 1일
        }
        return jwt.encode(payload, self.secret_key, algorithm='HS256')
    
    def verify_token(self, token: str) -> Optional[dict]:
        """JWT 토큰을 검증하고 페이로드를 반환합니다."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

# JWT 관리자 초기화
jwt_manager = JWTManager(app.config['JWT_SECRET_KEY'])

# MongoDB 매니저 초기화
mongo_uri = os.getenv('MONGO_URI')
if not mongo_uri:
    raise ValueError("MONGO_URI environment variable is not set")
mongodb_manager = MongoDBManager(mongo_uri)

def jwt_required():
    def decorator(func):
        @wraps(func)
        def decorated_function(*args, **kwargs):
            auth_header = request.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                return jsonify({'error': '인증이 필요합니다.'}), 401
            
            token = auth_header.split(' ')[1]
            payload = jwt_manager.verify_token(token)
            if not payload:
                return jsonify({'error': '유효하지 않은 토큰입니다.'}), 401
            
            request.user_id = payload['user_id']
            return func(*args, **kwargs)
        return decorated_function
    return decorator

@app.route('/api/register', methods=['POST'])
def register():
    """새 사용자를 등록합니다."""
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        email = data.get('email', '')  # email은 선택적으로 처리
        
        print(f"회원가입 요청 - 사용자명: {username}")
        
        if not all([username, password]):
            return jsonify({"error": "사용자명과 비밀번호는 필수입니다."}), 400
        
        # 이미 존재하는 사용자인지 확인
        existing_user = mongodb_manager.get_user_by_username(username)
        if existing_user:
            print(f"이미 존재하는 사용자: {username}")
            return jsonify({"error": "이미 존재하는 사용자명입니다."}), 400
        
        # 사용자 생성
        user_id = mongodb_manager.create_user(username, password, email)
        if user_id:
            print(f"사용자 생성 성공 - ID: {user_id}")
            # JWT 토큰 생성
            token = jwt_manager.generate_token(user_id)
            return jsonify({
                "message": "회원가입이 완료되었습니다.",
                "token": token,
                "user_id": user_id,
                "username": username
            })
        else:
            print("사용자 생성 실패")
            return jsonify({"error": "사용자 생성에 실패했습니다."}), 500
    except Exception as e:
        print(f"회원가입 중 오류 발생: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/login', methods=['POST'])
def login():
    """사용자 로그인을 처리합니다."""
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if not all([username, password]):
            return jsonify({"error": "사용자명과 비밀번호를 입력해주세요."}), 400
        
        # 사용자 인증
        user = mongodb_manager.verify_user(username, password)
        if user:
            # JWT 토큰 생성
            token = jwt_manager.generate_token(user['user_id'])
            return jsonify({
                "message": "로그인 성공",
                "token": token,
                "user_id": user['user_id'],
                "username": user['username']
            })
        else:
            return jsonify({"error": "잘못된 사용자명 또는 비밀번호입니다."}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/sessions', methods=['GET'])
@jwt_required()
def get_sessions():
    """사용자의 세션 목록을 반환합니다."""
    try:
        sessions = mongodb_manager.get_user_sessions(request.user_id)
        return jsonify(sessions)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/sessions', methods=['POST'])
@jwt_required()
def create_session():
    """새 세션을 생성합니다."""
    try:
        data = request.get_json()
        consultation_text = data.get('consultation_text')
        generated_content = data.get('generated_content')
        
        if not all([consultation_text, generated_content]):
            return jsonify({"error": "필수 필드가 누락되었습니다."}), 400
        
        session_id = mongodb_manager.save_session(
            request.user_id,
            consultation_text,
            generated_content
        )
        
        return jsonify({
            "message": "세션이 생성되었습니다.",
            "session_id": session_id
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/sessions/<session_id>', methods=['PUT'])
@jwt_required()
def update_session(session_id):
    """세션을 업데이트합니다."""
    try:
        data = request.get_json()
        rating = data.get('rating')
        feedback = data.get('feedback')
        
        if mongodb_manager.update_session(session_id, rating, feedback):
            return jsonify({"message": "세션이 업데이트되었습니다."})
        else:
            return jsonify({"error": "세션 업데이트에 실패했습니다."}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/generate-complaint', methods=['POST'])
@jwt_required()
def generate_complaint():
    try:
        # 요청 데이터 검증
        data = request.get_json()
        if not data:
            return jsonify({"error": "요청 데이터가 없습니다."}), 400
        
        user_input = data.get('user_input')
        conversation_history = data.get('conversation_history', [])
        
        if not user_input:
            return jsonify({"error": "사용자 입력이 없습니다."}), 400
            
        # 현재 사용자 정보 가져오기
        current_user = request.user_id
        
        # OpenAI API를 사용하여 응답 생성
        try:
            # 대화 기록을 포함한 프롬프트 생성
            messages = []
            messages.append({
                "role": "user", 
                "content": """당신은 이혼 소장 작성을 도와주는 법률 전문가입니다. 
                사용자의 상황을 이해하고, 적절한 법적 조언과 함께 이혼 소장 초안을 작성해주세요.
                소장은 한국의 법원 형식에 맞추어 작성되어야 합니다."""
            })
            
            # 이전 대화 기록 추가
            for msg in conversation_history:
                messages.append({"role": msg["role"], "content": msg["content"]})
            
            # 현재 사용자 입력 추가
            messages.append({"role": "user", "content": user_input})
            
            # OpenAI API 호출
            response = openai.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                temperature=0.7,
                max_tokens=2000
            )
            
            # API 응답 처리
            assistant_response = response.choices[0].message.content
            
            # 소장 생성을 위한 두 번째 API 호출
            complaint_prompt = f"""이전 대화를 바탕으로 이혼 소장을 작성해주세요. 
            형식은 다음과 같아야 합니다:

            서울가정법원 귀중

            소장

            원고: [이름], [주소]
            피고: [이름], [주소]

            청구취지
            1. 원고와 피고의 이혼을 명한다.
            2. 소송비용은 피고가 부담한다.
            라는 판결을 구합니다.

            청구원인
            [상세 내용]

            입증방법
            1. [입증 자료 목록]

            첨부서류
            1. [첨부 서류 목록]

            [날짜]
            원고 [이름] (인)

            대화 내용: {user_input}"""
            
            complaint_response = openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "user", "content": complaint_prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            generated_complaint = complaint_response.choices[0].message.content
            
            # 새로 추가: 대화 내용 저장
            session_id = mongodb_manager.save_session(
                request.user_id,
                user_input,
                {
                    "response": assistant_response,
                    "complaint": generated_complaint
                }
            )

            # 새로 추가: 청크 저장을 위한 임베딩 생성
            embeddings = OpenAIEmbeddings()
            text_splitter = CharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200
            )
            
            # 소장 내용을 청크로 분할
            chunks = text_splitter.split_text(generated_complaint)
            
            # 각 청크를 저장
            for chunk in chunks:
                embedding = embeddings.embed_query(chunk)
                mongodb_manager.save_chunk(
                    content=chunk,
                    doc_type="divorce_complaint",
                    embedding=embedding
                )
            
            return jsonify({
                "response": assistant_response,
                "complaint": generated_complaint,
                "session_id": session_id
            }), 200
            
        except Exception as e:
            print(f"OpenAI API 오류: {str(e)}")
            return jsonify({"error": f"응답 생성 중 오류가 발생했습니다: {str(e)}"}), 500
            
    except Exception as e:
        print(f"서버 오류: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/feedback', methods=['POST'])
@jwt_required()
def save_feedback():
    """피드백을 저장하는 엔드포인트"""
    try:
        data = request.get_json()
        
        # 필수 필드 검증
        required_fields = ['session_id', 'complaint', 'rating']
        if not all(field in data for field in required_fields):
            missing_fields = [field for field in required_fields if field not in data]
            return jsonify({
                "error": f"필수 필드가 누락되었습니다: {', '.join(missing_fields)}"
            }), 400

        session_id = data['session_id']
        complaint = data['complaint']
        rating = float(data['rating'])
        feedback_text = data.get('feedback', '')

        print(f"피드백 저장 요청 받음: session_id={session_id}, rating={rating}")

        # 피드백 문서 생성
        feedback_doc = {
            "session_id": session_id,
            "complaint": complaint,
            "rating": rating,
            "feedback": feedback_text,
            "timestamp": datetime.utcnow()
        }

        # MongoDB에 피드백 저장
        feedback_id = mongodb_manager.save_feedback(feedback_doc)

        # 세션 업데이트
        mongodb_manager.update_session(
            session_id=session_id,
            rating=rating,
            feedback=feedback_text
        )

        print(f"피드백 저장 성공: feedback_id={feedback_id}")
        
        return jsonify({
            "message": "피드백이 성공적으로 저장되었습니다",
            "feedback_id": str(feedback_id)
        })

    except ValueError as ve:
        print(f"값 오류 발생: {str(ve)}")
        return jsonify({"error": f"잘못된 입력값: {str(ve)}"}), 400
    except Exception as e:
        print(f"피드백 저장 중 오류 발생: {str(e)}")
        return jsonify({"error": f"피드백 저장 중 오류가 발생했습니다: {str(e)}"}), 500

@app.route('/api/feedback-statistics', methods=['GET'])
@jwt_required()
def get_feedback_statistics():
    try:
        stats = mongodb_manager.get_feedback_statistics()
        if stats:
            return jsonify(stats)
        return jsonify({"error": "No feedback data available"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/upload-audio', methods=['POST'])
@jwt_required()
def upload_audio():
    try:
        if 'audioFile' not in request.files:
            return jsonify({"error": "No audio file provided"}), 400
            
        audio_file = request.files['audioFile']
        
        # Process the audio file and convert to text
        # Implement your audio-to-text conversion logic here
        # This is a placeholder
        text = "Transcribed text would go here"
        
        return jsonify({"text": text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
