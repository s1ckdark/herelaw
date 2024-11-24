from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import openai
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
from pymongo import MongoClient
import uuid
import base64
import tempfile
from werkzeug.security import generate_password_hash, check_password_hash

# .env 파일 로드
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'your-secret-key')  # 환경변수에서 시크릿 키 로드

# Flask-Login 설정
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# MongoDB 연결
mongo_client = MongoClient(os.getenv('MONGO_URI'))
db = mongo_client[os.getenv('MONGODB_DB', 'herelaw')]

# User 모델 정의
class User(UserMixin):
    def __init__(self, user_data):
        self.id = str(user_data['_id'])
        self.username = user_data['username']

@login_manager.user_loader
def load_user(user_id):
    user_data = db.users.find_one({'_id': user_id})
    return User(user_data) if user_data else None

# 라우트 정의
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = db.users.find_one({'username': username})
        if user and check_password_hash(user['password'], password):
            login_user(User(user))
            return redirect(url_for('dashboard'))
        
        return render_template('login.html', error='Invalid credentials')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if db.users.find_one({'username': username}):
            return render_template('register.html', error='Username already exists')
        
        hashed_password = generate_password_hash(password)
        db.users.insert_one({
            'username': username,
            'password': hashed_password,
            'created_at': datetime.now()
        })
        
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/dashboard')
@login_required
def dashboard():
    sessions = db.sessions.find({'user_id': current_user.id}).sort('timestamp', -1)
    return render_template('dashboard.html', sessions=sessions)

@app.route('/api/record', methods=['POST'])
@login_required
def record_audio():
    audio_data = request.json.get('audio')
    if not audio_data:
        return jsonify({'error': 'No audio data received'}), 400
    
    try:
        # 오디오 처리 로직
        audio_bytes = base64.b64decode(audio_data)
        with tempfile.NamedTemporaryFile(delete=False, suffix='.webm') as temp_audio:
            temp_audio.write(audio_bytes)
            temp_audio_path = temp_audio.name
        
        # STT 처리
        engine = request.json.get('engine', 'whisper')
        if engine == 'whisper':
            transcriber = AudioTranscriber()
            text = transcriber.transcribe(temp_audio_path)
        else:
            text = gcp_transcribe(temp_audio_path)
        
        os.unlink(temp_audio_path)
        
        return jsonify({'text': text})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/generate-complaint', methods=['POST'])
@login_required
def generate_complaint():
    consultation_text = request.json.get('consultation_text')
    if not consultation_text:
        return jsonify({'error': 'No consultation text provided'}), 400
    
    try:
        generator = DivorceComplaintGenerator()
        complaint = generator.generate_complaint(consultation_text)
        
        # 세션 저장
        session_id = str(uuid.uuid4())
        db.sessions.insert_one({
            'session_id': session_id,
            'user_id': current_user.id,
            'consultation_text': consultation_text,
            'generated_content': complaint,
            'timestamp': datetime.now()
        })
        
        return jsonify({
            'complaint': complaint,
            'session_id': session_id
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/save-feedback', methods=['POST'])
@login_required
def save_feedback():
    session_id = request.json.get('session_id')
    rating = request.json.get('rating')
    feedback = request.json.get('feedback')
    
    if not all([session_id, rating]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    try:
        db.sessions.update_one(
            {'session_id': session_id},
            {'$set': {
                'rating': rating,
                'feedback': feedback
            }}
        )
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)