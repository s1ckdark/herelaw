from flask import Flask, request, jsonify
import openai
import os
from dotenv import load_dotenv
from flask_cors import CORS
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
from bson import ObjectId
import speech_recognition as sr
import os
from werkzeug.utils import secure_filename
import subprocess
from io import BytesIO
from flask import send_file
from bson.errors import InvalidId

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": ["http://172.30.1.41:3000", "http://localhost:3000"]}})
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'your-secret-key')  # 실제 배포 시에는 반드시 환경 변수로 설정해야 합니다
app.config['UPLOAD_FOLDER'] = './uploads'

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
        self.logs = self.db['logs']  # Add logs collection
        
        print(f"MongoDB 연결 정보:")
        print(f"Database: {self.db.name}")
        print(f"Collections: {self.db.list_collection_names()}")
        
        # Create indexes
        self.documents.create_index([("chunk_hash", 1)], unique=True)
        self.feedback.create_index([("session_id", 1)])
        self.users.create_index([("username", 1)], unique=True)
        self.users.create_index([("email", 1)], unique=True)
        self.sessions.create_index([("user_id", 1)])
        self.logs.create_index([("user_id", 1)])  # Add logs index
    
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
                "last_login": None,
                "role": "user",  # Default role
                "level": 1,      # Default level
                "status": "active"
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
            "created_at": datetime.utcnow(),
            "rating": None,
            "feedback": None
        })
        return session_id
    
    def get_user_sessions(self, user_id: str) -> List[dict]:
        """사용자의 모든 세션을 조회합니다."""
        return list(self.sessions.find(
            {"user_id": user_id},
            {"_id": 0}
        ).sort("created_at", -1))
    
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
                "created_at": datetime.now()
            })
    
    def save_conversation(self, session_id: str, user_input: str, generated_content: Dict):
        conversation = {
            "session_id": session_id,
            "created_at": datetime.now(),
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

    def save_log(self, log_data):
        """로그를 저장합니다."""
        try:
            result = self.logs.insert_one(log_data)
            if result.inserted_id:
                print(f"로그 저장 성공: {result.inserted_id}")
                return result.inserted_id
            else:
                raise Exception("로그 저장 실패")
                
        except Exception as e:
            print(f"로그 저장 중 오류: {str(e)}")
            raise e

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

# Admin required decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'Token is missing'}), 401
        
        try:
            payload = jwt_manager.verify_token(token.split(' ')[1])
            user = mongodb_manager.users.find_one({'_id': ObjectId(payload['user_id'])})
            if not user or user.get('role') != 'admin':
                return jsonify({'message': 'Admin privileges required'}), 403
        except:
            return jsonify({'message': 'Invalid token'}), 401
        
        return f(*args, **kwargs)
    return decorated_function

# Admin routes
@app.route('/api/admin/users', methods=['GET'])
@admin_required
def get_users():
    users = list(mongodb_manager.users.find({}, {'password': 0}))
    for user in users:
        user['_id'] = str(user['_id'])
    return jsonify(users)

@app.route('/api/admin/users/<user_id>', methods=['PUT'])
@admin_required
def update_user(user_id):
    try:
        data = request.json
        allowed_fields = ['email', 'role', 'status', 'level']
        update_data = {k: v for k, v in data.items() if k in allowed_fields}
        
        if not update_data:
            return jsonify({'message': 'No valid fields to update'}), 400
        
        result = mongodb_manager.users.update_one(
            {'_id': ObjectId(user_id)},
            {'$set': update_data}
        )
        
        if result.modified_count:
            return jsonify({'message': 'User updated successfully'})
        return jsonify({'message': 'User not found'}), 404
        
    except InvalidId:
        return jsonify({'message': 'Invalid user ID'}), 400

@app.route('/api/admin/users/<user_id>/reset-password', methods=['POST'])
@admin_required
def reset_user_password(user_id):
    try:
        new_password = request.json.get('new_password')
        if not new_password:
            return jsonify({'message': 'New password is required'}), 400
            
        hashed_password = generate_password_hash(new_password)
        result = mongodb_manager.users.update_one(
            {'_id': ObjectId(user_id)},
            {'$set': {'password': hashed_password}}
        )
        
        if result.modified_count:
            return jsonify({'message': 'Password reset successfully'})
        return jsonify({'message': 'User not found'}), 404
        
    except InvalidId:
        return jsonify({'message': 'Invalid user ID'}), 400

@app.route('/api/admin/users/<user_id>/logs', methods=['GET'])
@admin_required
def get_user_logs(user_id):
    try:
        # Get logs from MongoDB (assuming we store logs in a 'logs' collection)
        logs = list(mongodb_manager.db.logs.find({'user_id': user_id}))
        for log in logs:
            log['_id'] = str(log['_id'])
        return jsonify(logs)
    except InvalidId:
        return jsonify({'message': 'Invalid user ID'}), 400

# Modify the existing register route to include user level
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

@app.route('/api/sessions/<session_id>', methods=['GET'])
@jwt_required()
def get_session_details(session_id):
    """특정 세션의 상세 정보를 반환합니다."""
    try:
        # 세션 ID 유효성 검사
        if not session_id or session_id == 'undefined':
            return jsonify({"error": "유효하지 않은 세션 ID입니다."}), 400
        
        # 세션 조회 쿼리 준비
        query = {
            'user_id': request.user_id
        }
        
        # ObjectId 형식인지 확인
        try:
            # ObjectId로 변환 시도
            object_id = ObjectId(session_id)
            query['_id'] = object_id
        except (InvalidId, TypeError):
            # ObjectId가 아니면 session_id로 검색
            query['session_id'] = session_id
        
        # 세션 조회
        session = mongodb_manager.sessions.find_one(query)
        
        if not session:
            return jsonify({"error": "세션을 찾을 수 없습니다."}), 404
        
        # 날짜 처리 함수
        def parse_date(date_obj):
            if isinstance(date_obj, dict) and '$date' in date_obj:
                return date_obj['$date']
            elif isinstance(date_obj, datetime):
                return date_obj
            else:
                return datetime.now()
        
        # 세션 데이터 준비 (MongoDB ObjectId를 문자열로 변환)
        session_data = {
            '_id': str(session['_id']),
            'session_id': session.get('session_id', str(session['_id'])),
            'created_at': parse_date(session.get('created_at', datetime.now())),
            'summary': session.get('summary', ''),
            'consultation_text': session.get('consultation_text', []),
            'complaint': session.get('generated_content', ''),
            'rating': session.get('rating')
        }
        
        return jsonify(session_data), 200
    
    except Exception as e:
        print(f"세션 상세 정보 조회 중 오류: {str(e)}")
        return jsonify({"error": f"세션 정보를 불러오는 중 오류가 발생했습니다: {str(e)}"}), 500

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
            
            try:
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
            except Exception as db_error:
                print(f"데이터베이스 저장 오류: {str(db_error)}")
                # 데이터베이스 오류가 발생해도 사용자에게는 생성된 응답을 반환
            
            return jsonify({
                "response": assistant_response,
                "complaint": generated_complaint,
                "session_id": session_id
            }), 200
            
        except openai.error.OpenAIError as e:
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
            "created_at": datetime.utcnow()
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

@app.route('/api/summarize-text', methods=['POST'])
@jwt_required()
def summarize_text():
    data = request.get_json()
    text = data.get('text', '')
    model = data.get('model', 'gpt-4-turbo')
    
    try:
        client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "당신은 전문적이고 간결한 텍스트 요약을 제공하는 AI 어시스턴트입니다. 핵심 포인트를 명확하고 간결하게 요약해주세요."},
                {"role": "user", "content": f"다음 텍스트를 간결하고 명확하게 요약해주세요:\n\n{text}"}
            ],
            max_tokens=300
        )
        
        summary = response.choices[0].message.content.strip()
        
        return jsonify({
            'summary': summary,
            'status': 'success'
        }), 200
    
    except Exception as e:
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500

@app.route('/api/summarize-consultation', methods=['POST'])
@jwt_required()
def summarize_consultation():
    """
    상담 내역을 요약하고 중요한 법적 고려사항을 추출합니다.
    
    요청 본문 예시:
    {
        "text": "상담 내용 전체 텍스트",
        "model": "gpt-4o"  # 선택적
    }
    
    반환 예시:
    {
        "summary": "상담 내용 요약",
        "key_points": ["법적 고려사항 1", "법적 고려사항 2"]
    }
    """
    try:
        # 요청 데이터 검증
        data = request.get_json()
        if not data or 'text' not in data:
            return jsonify({"error": "텍스트가 제공되지 않았습니다."}), 400
        
        consultation_text = data['text']
        model = data.get('model', 'gpt-4o')
        
        # OpenAI 클라이언트 초기화
        client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        # 상담 내역 요약을 위한 프롬프트
        system_prompt = """
        당신은 전문 법률 상담 요약 전문가입니다. 다음 지침에 따라 상담 내용을 분석하고 요약하세요:

        1. 상담 내용의 핵심 쟁점을 명확하게 식별하세요.
        2. 법적 관점에서 중요한 세부사항을 강조하세요.
        3. 잠재적인 법적 해결책이나 고려사항을 제시하세요.
        4. 전문적이고 간결한 언어를 사용하세요.
        5. 요약은 3-4문단을 넘지 않도록 하세요.

        출력 형식:
        - 상담 내용 전체 요약
        - 주요 법적 고려사항 목록
        """
        
        # OpenAI API 호출
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": consultation_text}
            ],
            max_tokens=300,
            temperature=0.7
        )
        
        # 요약 추출
        summary = response.choices[0].message.content.strip()
        
        # 세션에 요약 정보 저장
        session_id = str(uuid.uuid4())  # 새 세션 ID 생성
        mongodb_manager.save_session(
            user_id=request.user_id, 
            consultation_text=consultation_text, 
            generated_content={"summary": summary}
        )
        
        return jsonify({
            "summary": summary,
            "session_id": session_id
        }), 200
    
    except openai.OpenAIError as e:
        # OpenAI API 관련 오류 처리
        print(f"OpenAI API 오류: {str(e)}")
        return jsonify({
            "error": f"AI 요약 생성 중 오류 발생: {str(e)}",
            "details": str(e)
        }), 500
    
    except Exception as e:
        # 기타 예외 처리
        print(f"상담 요약 중 예외 발생: {str(e)}")
        return jsonify({
            "error": "상담 요약 중 예기치 않은 오류가 발생했습니다.",
            "details": str(e)
        }), 500

@app.route('/api/upload-audio', methods=['POST'])
@jwt_required()
def upload_audio():
    if 'audio' not in request.files:
        return jsonify({"error": "No audio file uploaded"}), 400
    
    audio_file = request.files['audio']
    
    # 안전한 파일명 생성
    input_filename = secure_filename(audio_file.filename)
    input_filepath = os.path.join(app.config['UPLOAD_FOLDER'], input_filename)
    audio_file.save(input_filepath)
    
    try:
        # 오디오 파일을 WAV 16kHz mono로 변환
        converted_filepath = convert_audio_to_wav(input_filepath)
        
        if not converted_filepath:
            # 변환 실패 시 원본 파일 삭제
            os.remove(input_filepath)
            return jsonify({"error": "오디오 파일 변환에 실패했습니다."}), 400
        
        # 변환된 파일로 음성 인식 수행
        recognizer = sr.Recognizer()
        with sr.AudioFile(converted_filepath) as source:
            audio_data = recognizer.record(source)
            text = recognizer.recognize_google(audio_data, language='ko-KR')
        
        # 임시 파일들 삭제
        os.remove(input_filepath)
        os.remove(converted_filepath)
        
        return jsonify({"text": text}), 200
    
    except sr.UnknownValueError:
        # 음성 인식 불가능한 경우
        # 임시 파일들 삭제
        if os.path.exists(input_filepath):
            os.remove(input_filepath)
        if 'converted_filepath' in locals() and os.path.exists(converted_filepath):
            os.remove(converted_filepath)
        
        return jsonify({"error": "음성을 인식할 수 없습니다."}), 400
    
    except sr.RequestError:
        # 음성 인식 서비스 오류
        # 임시 파일들 삭제
        if os.path.exists(input_filepath):
            os.remove(input_filepath)
        if 'converted_filepath' in locals() and os.path.exists(converted_filepath):
            os.remove(converted_filepath)
        
        return jsonify({"error": "음성 인식 서비스에 문제가 있습니다."}), 500
    
    except Exception as e:
        # 기타 예외 처리
        # 임시 파일들 삭제
        if os.path.exists(input_filepath):
            os.remove(input_filepath)
        if 'converted_filepath' in locals() and os.path.exists(converted_filepath):
            os.remove(converted_filepath)
        
        return jsonify({"error": str(e)}), 500

@app.route('/api/rate-session', methods=['POST'])
@jwt_required()
def rate_session():
    """세션에 대한 평가를 처리합니다."""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        rating = data.get('rating')
        feedback = data.get('feedback', '')
        
        # 필수 필드 검증
        if not all([session_id, rating]):
            return jsonify({"error": "세션 ID와 평점은 필수입니다."}), 400
        
        # 세션 존재 여부 확인
        session = mongodb_manager.sessions.find_one({
            'session_id': session_id,
            'user_id': request.user_id
        })
        
        if not session:
            return jsonify({"error": "해당 세션을 찾을 수 없습니다."}), 404
        
        # 이미 평가했는지 확인
        existing_rating = mongodb_manager.feedback.find_one({
            'session_id': session_id,
            'user_id': request.user_id
        })
        
        if existing_rating:
            return jsonify({"error": "이미 이 세션에 대해 평가하셨습니다."}), 400
        
        # 피드백 저장
        feedback_doc = {
            'session_id': session_id,
            'user_id': request.user_id,
            'rating': rating,
            'feedback': feedback,
            'created_at': datetime.now()
        }
        
        # 세션에 평가 정보 업데이트
        mongodb_manager.sessions.update_one(
            {'session_id': session_id},
            {'$set': {
                'rating': rating,
                'has_feedback': True
            }}
        )
        
        # 피드백 저장
        mongodb_manager.feedback.insert_one(feedback_doc)
        
        return jsonify({
            "message": "평가가 성공적으로 제출되었습니다.",
            "rating": rating
        }), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/generate-document', methods=['POST'])
@jwt_required()
def generate_document():
    data = request.get_json()
    transcription = data.get('transcription', '')
    summary = data.get('summary', '')
    
    try:
        # Create a new Document
        doc = Document()
        
        # Title
        title = doc.add_heading('음성 녹음 기반 소장', 0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # Transcription Section
        doc.add_heading('원본 녹음 내용', level=1)
        transcription_para = doc.add_paragraph(transcription)
        transcription_para.style.font.size = Pt(11)
        
        # Summary Section
        doc.add_heading('대화 요약', level=1)
        summary_para = doc.add_paragraph(summary)
        summary_para.style.font.size = Pt(11)
        
        # Save document to a BytesIO object
        doc_bytes = BytesIO()
        doc.save(doc_bytes)
        doc_bytes.seek(0)
        
        return send_file(
            doc_bytes, 
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            as_attachment=True,
            download_name='소장.docx'
        )
    
    except Exception as e:
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500

@app.route('/api/update_complaint', methods=['POST'])
@jwt_required()
def update_complaint():
    """
    사용자의 소장을 업데이트합니다.
    
    요청 본문 예시:
    {
        "complaint": "수정된 소장 내용",
        "session_id": "세션 ID (선택적)"
    }
    
    반환 예시:
    {
        "message": "소장이 성공적으로 업데이트되었습니다.",
        "updated_complaint": "수정된 소장 내용"
    }
    """
    try:
        # 요청 데이터 검증
        data = request.get_json()
        if not data or 'complaint' not in data:
            return jsonify({"error": "소장 내용이 제공되지 않았습니다."}), 400
        
        updated_complaint = data['complaint']
        session_id = data.get('session_id')
        
        # 세션 ID가 제공된 경우 해당 세션 업데이트
        if session_id:
            update_result = mongodb_manager.sessions.update_one(
                {"session_id": session_id, "user_id": request.user_id},
                {"$set": {"generated_content.complaint": updated_complaint}}
            )
            
            if update_result.modified_count == 0:
                # 세션을 찾지 못하거나 업데이트 실패
                return jsonify({
                    "error": "해당 세션을 찾을 수 없거나 업데이트 권한이 없습니다.",
                    "details": f"Session ID: {session_id}, User ID: {request.user_id}"
                }), 403
        
        # 추가적인 로깅 또는 처리
        print(f"소장 업데이트 - 사용자 ID: {request.user_id}, 세션 ID: {session_id}")
        
        return jsonify({
            "message": "소장이 성공적으로 업데이트되었습니다.",
            "updated_complaint": updated_complaint
        }), 200
    
    except Exception as e:
        # 예외 처리
        print(f"소장 업데이트 중 오류 발생: {str(e)}")
        return jsonify({
            "error": "소장 업데이트 중 예기치 않은 오류가 발생했습니다.",
            "details": str(e)
        }), 500

@app.route('/api/start-consultation', methods=['POST'])
@jwt_required()
def start_consultation():
    """
    새 상담 세션을 시작하고 초기 대화 내용을 저장합니다.
    
    요청 본문 예시:
    {
        "consultation_text": "상담 내용",
        "conversation": "상담 내용 (대화 기록용)"
    }
    
    반환 예시:
    {
        "session_id": "새로 생성된 세션 ID",
        "consultation_text": "상담 내용",
        "created_at": "세션 생성 시간"
    }
    """
    try:
        # 요청 데이터 파싱
        data = request.get_json()
        consultation_text = data.get('consultation_text')
        conversation = data.get('conversation', consultation_text)
        
        # 입력 검증
        if not consultation_text:
            return jsonify({"error": "상담 내용이 필요합니다."}), 400
        
        # 세션 생성
        session_id = str(uuid.uuid4())
        
        # 세션 저장
        session_data = {
            "_id": session_id,
            "user_id": request.user_id,
            "consultation_text": consultation_text,
            "conversation": conversation,
            "created_at": datetime.utcnow(),
            "status": "in_progress"
        }
        
        # MongoDB에 세션 저장
        mongodb_manager.sessions.insert_one(session_data)
        
        # 응답 생성
        return jsonify({
            "session_id": session_id,
            "consultation_text": consultation_text,
            "created_at": session_data['created_at'].isoformat()
        }), 201
    
    except Exception as e:
        print(f"상담 시작 중 오류 발생: {str(e)}")
        return jsonify({"error": "상담 시작 중 오류가 발생했습니다.", "details": str(e)}), 500

def convert_audio_to_wav(input_file):
    """
    Convert input audio file to WAV 16kHz mono using FFmpeg
    
    Args:
        input_file (str): Path to the input audio file
    
    Returns:
        str: Path to the converted WAV file, or None if conversion fails
    """
    try:
        # Generate a unique filename for the converted file
        output_filename = f"{uuid.uuid4()}.wav"
        output_file = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)
        
        # FFmpeg command to convert audio to WAV 16kHz mono
        ffmpeg_command = [
            'ffmpeg', 
            '-i', input_file,  # Input file
            '-acodec', 'pcm_s16le',  # 16-bit PCM
            '-ar', '16000',  # Sample rate 16kHz
            '-ac', '1',  # Mono audio
            output_file
        ]
        
        # Run FFmpeg conversion
        result = subprocess.run(ffmpeg_command, capture_output=True, text=True)
        
        # Check if conversion was successful
        if result.returncode == 0 and os.path.exists(output_file):
            return output_file
        else:
            # Log FFmpeg error output
            print(f"FFmpeg conversion error: {result.stderr}")
            return None
    
    except Exception as e:
        print(f"Audio conversion error: {e}")
        return None

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)