import streamlit as st
import requests
import os
from datetime import datetime
import uuid
import extra_streamlit_components as stx
from datetime import timedelta
import json
import base64
import openai
import ffmpeg
import time
import subprocess

# Constants
API_BASE_URL = "http://localhost:5000/api"

class Session:
    def __init__(self, session_id, conversation_history=None, generated_complaint=None, rating=None, feedback=None, timestamp=None):
        self.session_id = session_id
        self.conversation_history = conversation_history or []
        self.generated_complaint = generated_complaint
        self.rating = rating
        self.feedback = feedback
        self.timestamp = timestamp or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

class UserManager:
    def __init__(self):
        if 'user' not in st.session_state:
            st.session_state.user = None
            
    def _get_auth_headers(self):
        """인증 헤더를 반환합니다."""
        if st.session_state.user and 'token' in st.session_state.user:
            return {"Authorization": f"Bearer {st.session_state.user['token']}"}
        return {}
        
    def _save_session_to_cookie(self):
        """사용자 세션을 쿠키에 저장합니다."""
        if st.session_state.user:
            st.session_state.user_cookie = st.session_state.user
            
    def _restore_session_from_cookie(self):
        """쿠키에서 사용자 세션을 복원합니다."""
        if 'user_cookie' in st.session_state:
            st.session_state.user = st.session_state.user_cookie
            
    def is_logged_in(self):
        """사용자가 로그인되어 있는지 확인합니다."""
        if not st.session_state.user:
            self._restore_session_from_cookie()
        return st.session_state.user is not None
        
    def login(self, username, password):
        """사용자 로그인을 처리합니다."""
        try:
            response = requests.post(
                f"{API_BASE_URL}/login",
                json={"username": username, "password": password}
            )
            
            if response.status_code == 200:
                data = response.json()
                st.session_state.user = {
                    "username": username,
                    "token": data["token"]
                }
                self._save_session_to_cookie()
                return True
            else:
                print(f"Login failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"Error during login: {str(e)}")
            return False
            
    def logout(self):
        """사용자 로그아웃을 처리합니다."""
        st.session_state.user = None
        if 'user_cookie' in st.session_state:
            del st.session_state.user_cookie
            
    def get_current_user(self):
        """현재 로그인된 사용자 정보를 반환합니다."""
        if not st.session_state.user:
            self._restore_session_from_cookie()
        return st.session_state.user or {}
        
    def register(self, username, password):
        """새로운 사용자를 등록합니다."""
        try:
            response = requests.post(
                f"{API_BASE_URL}/register",
                json={"username": username, "password": password}
            )
            
            if response.status_code == 200:
                return True
            else:
                print(f"Register failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"Error during register: {str(e)}")
            return False

class SessionManager:
    def __init__(self):
        if 'sessions' not in st.session_state:
            st.session_state.sessions = []
        if 'current_session_id' not in st.session_state:
            st.session_state.current_session_id = None
            
    def save_session(self, consultation_text, generated_complaint):
        """새로운 세션을 저장합니다."""
        try:
            response = requests.post(
                f"{API_BASE_URL}/sessions",
                headers=st.session_state.user_manager._get_auth_headers(),
                json={
                    "consultation_text": consultation_text,
                    "generated_content": generated_complaint
                }
            )
            
            if response.status_code == 200:
                session_id = response.json().get("session_id")
                session = Session(
                    session_id=session_id,
                    conversation_history=[],
                    generated_complaint=generated_complaint
                )
                st.session_state.sessions.append(session)
                st.session_state.current_session_id = session_id
                return session_id
            else:
                print(f"Failed to save session: {response.status_code}")
                return None
        except Exception as e:
            print(f"Error saving session: {str(e)}")
            return None
    
    def get_sessions(self):
        """사용자의 모든 세션을 가져옵니다."""
        try:
            response = requests.get(
                f"{API_BASE_URL}/sessions",
                headers=st.session_state.user_manager._get_auth_headers()
            )
            
            if response.status_code == 200:
                sessions_data = response.json()
                st.session_state.sessions = [
                    Session(
                        session_id=session["session_id"],
                        conversation_history=session.get("conversation_history", []),
                        generated_complaint=session.get("generated_content"),
                        rating=session.get("rating"),
                        feedback=session.get("feedback"),
                        timestamp=session.get("timestamp")
                    )
                    for session in sessions_data
                ]
                return st.session_state.sessions
            else:
                print(f"Failed to get sessions: {response.status_code}")
                return []
        except Exception as e:
            print(f"Error getting sessions: {str(e)}")
            return []
    
    def update_session(self, session_id, rating=None, feedback=None):
        """세션을 업데이트합니다."""
        if not session_id:
            return False
            
        try:
            # 세션 업데이트 API 호출
            response = requests.put(
                f"{API_BASE_URL}/sessions/{session_id}",
                headers=st.session_state.user_manager._get_auth_headers(),
                json={
                    "rating": rating,
                    "feedback": feedback
                }
            )
            
            if response.status_code == 200:
                # 메모리 상의 세션도 업데이트
                for session in st.session_state.sessions:
                    if session.session_id == session_id:
                        if rating is not None:
                            session.rating = rating
                        if feedback is not None:
                            session.feedback = feedback
                        
                        # 피드백 저장 API 호출
                        feedback_response = requests.post(
                            f"{API_BASE_URL}/save-feedback",
                            headers=st.session_state.user_manager._get_auth_headers(),
                            json={
                                "session_id": session_id,
                                "complaint": session.generated_complaint,
                                "rating": rating,
                                "feedback": feedback
                            }
                        )
                        
                        if feedback_response.status_code != 200:
                            print(f"피드백 저장 실패: {feedback_response.status_code}")
                            print(f"응답 내용: {feedback_response.text}")
                            return False
                        
                        return True
                return False
            else:
                print(f"세션 업데이트 실패: {response.status_code}")
                print(f"응답 내용: {response.text}")
                return False
        except Exception as e:
            print(f"세션 업데이트 중 오류: {str(e)}")
            return False
    
    def save_feedback(self, session_id, complaint, rating):
        """피드백을 저장합니다."""
        try:
            response = requests.post(
                f"{API_BASE_URL}/save-feedback",
                headers=st.session_state.user_manager._get_auth_headers(),
                json={
                    "session_id": session_id,
                    "complaint": complaint,
                    "rating": rating
                }
            )
            
            if response.status_code == 200:
                return response.json().get("feedback_id")
            else:
                print(f"Failed to save feedback: {response.status_code}")
                return None
        except Exception as e:
            print(f"Error saving feedback: {str(e)}")
            return None

class AudioTranscriber:
    def __init__(self):
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다.")
        openai.api_key = self.openai_api_key

    def transcribe_audio(self, audio_file_path):
        """오디오 파일을 텍스트로 변환합니다."""
        try:
            with open(audio_file_path, "rb") as audio_file:
                # 최신 OpenAI API 형식으로 수정
                transcript = openai.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="ko"
                )
                return transcript.text
        except Exception as e:
            print(f"음성 인식 중 오류 발생: {str(e)}")
            return None

def process_audio_file(audio_file):
    """오디오 파일을 처리하고 텍스트로 변환합니다."""
    try:
        # 임시 디렉토리 생성
        temp_dir = "temp_audio"
        os.makedirs(temp_dir, exist_ok=True)
        
        # 원본 파일 저장
        input_path = os.path.join(temp_dir, "temp_audio_input" + os.path.splitext(audio_file.name)[1])
        output_path = os.path.join(temp_dir, "temp_audio_output.wav")
        
        # 원본 파일 저장
        with open(input_path, "wb") as f:
            f.write(audio_file.getvalue())
        
        try:
            # ffmpeg 명령어로 오디오 변환
            command = [
                'ffmpeg',
                '-i', input_path,
                '-acodec', 'pcm_s16le',  # WAV 포맷
                '-ac', '1',              # 모노
                '-ar', '16000',          # 16kHz
                '-y',                    # 기존 파일 덮어쓰기
                output_path
            ]
            
            # ffmpeg 실행
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # 프로세스 완료 대기
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                print(f"FFmpeg 오류: {stderr.decode()}")
                raise Exception("오디오 변환 실패")
            
            # 변환된 파일로 Whisper API 호출
            with open(output_path, "rb") as audio_file:
                transcriber = AudioTranscriber()
                transcribed_text = transcriber.transcribe_audio(output_path)
                
            return transcribed_text
            
        finally:
            # 임시 파일 정리
            try:
                if os.path.exists(input_path):
                    os.remove(input_path)
                if os.path.exists(output_path):
                    os.remove(output_path)
            except Exception as e:
                print(f"임시 파일 정리 중 오류: {str(e)}")
            
    except Exception as e:
        print(f"오디오 처리 중 오류 발생: {str(e)}")
        return None

def create_audio_recorder():
    return """
    <div style="width: 100%; max-width: 600px; margin: 0 auto; padding: 20px;">
        <style>
            .recorder-container {
                border: 1px solid #ddd;
                border-radius: 8px;
                padding: 20px;
                background: #f8f9fa;
            }
            .button-container {
                display: flex;
                gap: 10px;
                margin-bottom: 15px;
            }
            .recorder-button {
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                cursor: pointer;
                font-weight: 500;
                transition: all 0.3s ease;
            }
            .record-button {
                background-color: #dc3545;
                color: white;
            }
            .record-button:disabled {
                background-color: #6c757d;
                cursor: not-allowed;
            }
            .stop-button {
                background-color: #6c757d;
                color: white;
            }
            .download-button {
                background-color: #28a745;
                color: white;
                text-decoration: none;
                display: inline-block;
                text-align: center;
            }
            .download-button:hover {
                background-color: #218838;
            }
            .visualizer-container {
                width: 100%;
                height: 100px;
                background: #fff;
                border-radius: 5px;
                margin-bottom: 15px;
                position: relative;
            }
            #waveform {
                width: 100%;
                height: 100%;
            }
            .timer {
                text-align: center;
                font-size: 1.2em;
                margin-bottom: 15px;
                font-family: monospace;
            }
            .audio-controls {
                width: 100%;
                margin-top: 15px;
                display: none;
            }
            .audio-player {
                width: 100%;
                margin-bottom: 10px;
            }
            .audio-player audio {
                width: 100%;
            }
            .recording-controls {
                display: flex;
                gap: 10px;
                justify-content: center;
                margin-top: 10px;
            }
            .status-message {
                text-align: center;
                margin-top: 10px;
                color: #6c757d;
            }
        </style>
        
        <div class="recorder-container">
            <div class="button-container">
                <button id="recordButton" class="recorder-button record-button">
                    <i class="fas fa-microphone"></i> 녹음 시작
                </button>
                <button id="stopButton" class="recorder-button stop-button" disabled>
                    <i class="fas fa-stop"></i> 녹음 중지
                </button>
            </div>
            
            <div class="timer" id="timer">00:00</div>
            
            <div class="visualizer-container">
                <canvas id="waveform"></canvas>
            </div>
            
            <div class="audio-controls" id="audioControls">
                <div class="audio-player">
                    <audio id="audioPlayback" controls></audio>
                </div>
                <div class="recording-controls">
                    <a id="downloadButton" class="recorder-button download-button" download="recorded_audio.wav">
                        <i class="fas fa-download"></i> 다운로드
                    </a>
                    <button id="useRecordingButton" class="recorder-button record-button">
                        <i class="fas fa-check"></i> 이 녹음 사용하기
                    </button>
                </div>
                <div class="status-message" id="statusMessage"></div>
            </div>
        </div>

        <script src="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/js/all.min.js"></script>
        
        <script>
            let mediaRecorder;
            let audioContext;
            let analyser;
            let chunks = [];
            let startTime;
            let timerInterval;
            let audioBlob;
            
            const recordButton = document.getElementById('recordButton');
            const stopButton = document.getElementById('stopButton');
            const timerDisplay = document.getElementById('timer');
            const canvas = document.getElementById('waveform');
            const audioControls = document.getElementById('audioControls');
            const downloadButton = document.getElementById('downloadButton');
            const useRecordingButton = document.getElementById('useRecordingButton');
            const statusMessage = document.getElementById('statusMessage');
            const ctx = canvas.getContext('2d');
            
            function updateTimer() {
                const now = Date.now();
                const diff = now - startTime;
                const minutes = Math.floor(diff / 60000);
                const seconds = Math.floor((diff % 60000) / 1000);
                timerDisplay.textContent = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
            }
            
            function drawWaveform(analyser) {
                const bufferLength = analyser.frequencyBinCount;
                const dataArray = new Uint8Array(bufferLength);
                
                function draw() {
                    if (!mediaRecorder || mediaRecorder.state !== 'recording') return;
                    
                    requestAnimationFrame(draw);
                    analyser.getByteTimeDomainData(dataArray);
                    
                    ctx.fillStyle = '#ffffff';
                    ctx.fillRect(0, 0, canvas.width, canvas.height);
                    
                    ctx.lineWidth = 2;
                    ctx.strokeStyle = '#ff4b4b';
                    ctx.beginPath();
                    
                    const sliceWidth = canvas.width * 1.0 / bufferLength;
                    let x = 0;
                    
                    for (let i = 0; i < bufferLength; i++) {
                        const v = dataArray[i] / 128.0;
                        const y = v * canvas.height / 2;
                        
                        if (i === 0) {
                            ctx.moveTo(x, y);
                        } else {
                            ctx.lineTo(x, y);
                        }
                        
                        x += sliceWidth;
                    }
                    
                    ctx.lineTo(canvas.width, canvas.height / 2);
                    ctx.stroke();
                }
                
                draw();
            }
            
            function resizeCanvas() {
                canvas.width = canvas.offsetWidth;
                canvas.height = canvas.offsetHeight;
            }
            
            window.addEventListener('resize', resizeCanvas);
            resizeCanvas();
            
            recordButton.onclick = async () => {
                try {
                    const stream = await navigator.mediaDevices.getUserMedia({ 
                        audio: {
                            sampleRate: 16000,
                            channelCount: 1,
                            echoCancellation: true,
                            noiseSuppression: true
                        } 
                    });
                    
                    audioContext = new AudioContext({ sampleRate: 16000 });
                    const source = audioContext.createMediaStreamSource(stream);
                    analyser = audioContext.createAnalyser();
                    analyser.fftSize = 2048;
                    source.connect(analyser);
                    
                    mediaRecorder = new MediaRecorder(stream, {
                        mimeType: 'audio/webm;codecs=opus',
                        audioBitsPerSecond: 16000
                    });
                    
                    mediaRecorder.ondataavailable = (e) => {
                        chunks.push(e.data);
                    };
                    
                    mediaRecorder.onstop = async () => {
                        audioBlob = new Blob(chunks, { type: 'audio/webm' });
                        chunks = [];
                        
                        // 오디오 플레이어 설정
                        const audioURL = URL.createObjectURL(audioBlob);
                        const audio = document.getElementById('audioPlayback');
                        audio.src = audioURL;
                        
                        // 다운로드 버튼 설정
                        downloadButton.href = audioURL;
                        
                        // 컨트롤 표시
                        audioControls.style.display = 'block';
                        statusMessage.textContent = '녹음이 완료되었습니다. 녹음을 확인하고 사용하거나 다시 녹음할 수 있습니다.';
                    };
                    
                    mediaRecorder.start(100);
                    startTime = Date.now();
                    timerInterval = setInterval(updateTimer, 100);
                    
                    recordButton.disabled = true;
                    stopButton.disabled = false;
                    recordButton.innerHTML = '<i class="fas fa-microphone"></i> 녹음 중...';
                    audioControls.style.display = 'none';
                    statusMessage.textContent = '';
                    drawWaveform(analyser);
                    
                } catch (err) {
                    console.error('마이크 접근 오류:', err);
                    alert('마이크 접근이 거부되었습니다. 마이크 권한을 확인해주세요.');
                }
            };
            
            stopButton.onclick = () => {
                if (mediaRecorder && mediaRecorder.state === 'recording') {
                    mediaRecorder.stop();
                    clearInterval(timerInterval);
                    
                    recordButton.disabled = false;
                    stopButton.disabled = true;
                    recordButton.innerHTML = '<i class="fas fa-microphone"></i> 녹음 시작';
                    
                    // 스트림 정리
                    mediaRecorder.stream.getTracks().forEach(track => track.stop());
                }
            };
            
            useRecordingButton.onclick = async () => {
                if (audioBlob) {
                    statusMessage.textContent = '음성을 텍스트로 변환하는 중...';
                    useRecordingButton.disabled = true;
                    
                    // FormData 생성
                    const formData = new FormData();
                    formData.append('audio', audioBlob, 'recording.webm');
                    
                    try {
                        // 파일을 서버로 전송
                        const response = await fetch('/process_audio', {
                            method: 'POST',
                            body: formData
                        });
                        
                        if (response.ok) {
                            const result = await response.json();
                            if (result.text) {
                                // 텍스트 영역에 결과 표시
                                const textArea = document.querySelector('textarea');
                                if (textArea) {
                                    textArea.value = result.text;
                                    textArea.dispatchEvent(new Event('input', { bubbles: true }));
                                }
                                statusMessage.textContent = '음성 인식이 완료되었습니다.';
                            } else {
                                statusMessage.textContent = '음성 인식에 실패했습니다.';
                            }
                        } else {
                            throw new Error('서버 응답 오류');
                        }
                    } catch (error) {
                        console.error('오디오 처리 중 오류:', error);
                        statusMessage.textContent = '오류가 발생했습니다. 다시 시도해주세요.';
                    } finally {
                        useRecordingButton.disabled = false;
                    }
                }
            };
        </script>
    </div>
    """

def initialize_session_state():
    """세션 상태 초기화"""
    if 'conversation_history' not in st.session_state:
        st.session_state.conversation_history = []
    if 'generated_complaint' not in st.session_state:
        st.session_state.generated_complaint = None
    if 'consultation_text' not in st.session_state:
        st.session_state.consultation_text = ""
    if 'edit_mode' not in st.session_state:
        st.session_state.edit_mode = False
    if 'evaluation_mode' not in st.session_state:
        st.session_state.evaluation_mode = False
    if 'rating' not in st.session_state:
        st.session_state.rating = 1  # 최소값 1로 설정
    if 'session_id' not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    if 'user_manager' not in st.session_state:
        st.session_state.user_manager = UserManager()
    if 'session_manager' not in st.session_state:
        st.session_state.session_manager = SessionManager()
    if 'audio_transcriber' not in st.session_state:
        st.session_state.audio_transcriber = AudioTranscriber()

def submit_feedback(session_id: str, complaint: str, rating: float, feedback: str = None):
    """피드백을 서버에 제출합니다."""
    try:
        response = requests.post(
            f"{API_BASE_URL}/feedback",
            headers=st.session_state.user_manager._get_auth_headers(),
            json={
                "session_id": session_id,
                "complaint": complaint,
                "rating": rating,
                "feedback": feedback
            }
        )
        
        if response.status_code == 200:
            print(f"피드백 저장 성공: {response.json()}")
            return True
        else:
            print(f"피드백 저장 실패: {response.status_code}")
            print(f"응답 내용: {response.text}")
            return False
            
    except Exception as e:
        print(f"피드백 제출 중 오류 발생: {str(e)}")
        return False

def display_sessions():
    """사용자의 세션 목록을 표시합니다."""
    sessions = st.session_state.session_manager.get_sessions()
    
    for session in sessions:
        with st.expander(f"세션 {session.session_id[:8]} ({session.timestamp})"):
            # 대화 기록 표시
            st.write("대화 기록:")
            for message in session.conversation_history:
                if message["role"] == "user":
                    st.write("사용자: " + message["content"])
                else:
                    st.write("시스템: " + message["content"])
            
            # 생성된 소장이 있는 경우 표시
            if session.generated_complaint:
                st.write("생성된 소장:")
                st.write(session.generated_complaint)
            
            # 평가 정보 표시
            if session.rating:
                st.write(f"평가: {session.rating}점")
            if session.feedback:
                st.write(f"피드백: {session.feedback}")
            
            # 평가하기 섹션
            if not session.rating and session.generated_complaint:
                rating = st.slider(
                    "소장 평가",
                    min_value=1,
                    max_value=5,
                    value=3,
                    key=f"rating_{session.session_id}"
                )
                
                feedback = st.text_area(
                    "피드백 (선택사항)",
                    key=f"feedback_{session.session_id}"
                )
                
                if st.button("평가 제출", key=f"submit_{session.session_id}"):
                    with st.spinner("평가를 저장하는 중..."):
                        success = submit_feedback(
                            session_id=session.session_id,
                            complaint=session.generated_complaint,
                            rating=rating,
                            feedback=feedback
                        )
                        
                        if success:
                            st.success("평가가 성공적으로 저장되었습니다.")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("평가 저장에 실패했습니다. 다시 시도해주세요.")

def main():
    st.set_page_config(
        page_title="이혼 소장 생성기",
        page_icon="⚖️",
        layout="wide"
    )
    
    initialize_session_state()
    
    # 2분할 레이아웃
    left_col, right_col = st.columns([2, 8])
    
    # 왼쪽 사이드바 - 세션 목록
    with left_col:
        if st.session_state.user_manager.is_logged_in():
            st.subheader("세션 관리")
            display_sessions()
    
    # 오른쪽 컬럼 - 메인 컨텐츠
    with right_col:
        st.title("이혼 소장 생성기")
        
        # 로그인/회원가입 섹션
        if not st.session_state.user_manager.is_logged_in():
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("로그인")
                username = st.text_input("사용자명", key="login_username")
                password = st.text_input("비밀번호", type="password", key="login_password")
                if st.button("로그인"):
                    try:
                        if st.session_state.user_manager.login(username, password):
                            st.success("로그인 성공!")
                            st.rerun()
                        else:
                            st.error("로그인 실패. 사용자명과 비밀번호를 확인해주세요.")
                    except Exception as e:
                        st.error(f"로그인 중 오류 발생: {str(e)}")
            
            with col2:
                st.subheader("회원가입")
                new_username = st.text_input("새 사용자명", key="register_username")
                new_password = st.text_input("새 비밀번호", type="password", key="register_password")
                if st.button("회원가입"):
                    try:
                        if st.session_state.user_manager.register(new_username, new_password):
                            st.success("회원가입 성공! 이제 로그인할 수 있습니다.")
                        else:
                            st.error("회원가입 실패. 다른 사용자명을 시도해주세요.")
                    except Exception as e:
                        st.error(f"회원가입 중 오류 발생: {str(e)}")
        
        else:
            st.write(f"환영합니다, {st.session_state.user_manager.get_current_user().get('username', '')}님!")
            
            if st.button("로그아웃", type="secondary"):
                st.session_state.user_manager.logout()
                st.rerun()
            
            # 대화 인터페이스
            st.subheader("대화 인터페이스")
            
            # 음성 상담 섹션
            st.subheader("음성으로 상담하기")
            audio_tab1, audio_tab2 = st.tabs(["음성 녹음", "파일 업로드"])
            
            with audio_tab1:
                # 음성 녹음 컴포넌트
                audio_recorder_html = create_audio_recorder()
                st.components.v1.html(audio_recorder_html, height=500)
            
            with audio_tab2:
                uploaded_file = st.file_uploader("오디오 파일 업로드", type=['webm', 'wav', 'mp3'])
                if uploaded_file is not None:
                    st.audio(uploaded_file)
                    if st.button("이 음성 사용하기"):
                        with st.spinner("음성을 텍스트로 변환하는 중..."):
                            transcribed_text = process_audio_file(uploaded_file)
                            if transcribed_text:
                                st.session_state.consultation_text = transcribed_text
                                st.success("음성 인식이 완료되었습니다.")
                                st.write("변환된 텍스트:")
                                st.write(transcribed_text)
                                if st.button("이 텍스트로 상담 시작"):
                                    st.session_state.user_input = transcribed_text
                                    st.rerun()
                            else:
                                st.error("음성 인식에 실패했습니다.")
            
            # 텍스트 입력 섹션
            st.subheader("텍스트로 상담하기")
            # 음성 인식 결과가 있으면 자동으로 채워넣기
            default_text = st.session_state.get("consultation_text", "")
            user_input = st.text_area("상담 내용을 입력하세요:", value=default_text, height=300)
            
            # 음성 인식 결과가 있으면 표시
            if st.session_state.get("transcribed_text"):
                st.info(f"음성 인식 결과: {st.session_state.transcribed_text}")
                if st.button("음성 인식 결과 사용"):
                    user_input = st.session_state.transcribed_text
                    del st.session_state.transcribed_text
            
            if st.button("상담 시작", type="primary"):
                if user_input:
                    # 대화 기록에 사용자 입력 추가
                    st.session_state.conversation_history.append({"role": "user", "content": user_input})
                    
                    try:
                        # API 호출하여 응답 받기
                        response = requests.post(
                            f"{API_BASE_URL}/generate-complaint",
                            headers=st.session_state.user_manager._get_auth_headers(),
                            json={
                                "user_input": user_input,
                                "conversation_history": st.session_state.conversation_history
                            }
                        )
                        
                        if response.status_code == 200:
                            # API 응답 처리
                            result = response.json()
                            assistant_response = result.get("response", "")
                            generated_complaint = result.get("complaint", "")
                            
                            # 대화 기록에 응답 추가
                            st.session_state.conversation_history.append(
                                {"role": "assistant", "content": assistant_response}
                            )
                            
                            # 생성된 소장 저장
                            if generated_complaint:
                                st.session_state.generated_complaint = generated_complaint
                            
                            # 세션 업데이트
                            st.session_state.session_manager.save_session(
                                st.session_state.consultation_text,
                                st.session_state.generated_complaint
                            )
                            
                            st.rerun()
                        elif response.status_code == 401:
                            st.error("인증이 만료되었습니다. 다시 로그인해주세요.")
                            st.session_state.user_manager.logout()
                            st.rerun()
                        else:
                            st.error(f"서버 응답 오류가 발생했습니다. (상태 코드: {response.status_code})")
                            if response.content:
                                try:
                                    error_detail = response.json()
                                    st.error(f"오류 상세: {error_detail.get('error', '알 수 없는 오류')}")
                                except:
                                    st.error(f"오류 내용: {response.content.decode()}")
                    except Exception as e:
                        st.error(f"API 호출 중 오류 발생: {str(e)}")
            
            # 대화 기록 표시
            st.subheader("대화 기록")
            for message in st.session_state.conversation_history:
                if message["role"] == "user":
                    st.write("사용자: " + message["content"])
                else:
                    st.write("시스템: " + message["content"])
            
            # 생성된 소장이 있는 경우 표시
            if st.session_state.generated_complaint:
                st.subheader("생성된 소장")
                st.write(st.session_state.generated_complaint)
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("소장 수정"):
                        st.session_state.edit_mode = True
                
                with col2:
                    if st.button("소장 다운로드"):
                        # 소장을 Word 문서 변환
                        doc_content = st.session_state.generated_complaint
                        b64 = base64.b64encode(doc_content.encode()).decode()
                        href = f'<a href="data:file/txt;base64,{b64}" download="generated_complaint.txt">다운로드</a>'
                        st.markdown(href, unsafe_allow_html=True)
                
                if st.session_state.edit_mode:
                    edited_complaint = st.text_area("소장 수정", value=st.session_state.generated_complaint, height=300)
                    if st.button("수정 완료"):
                        st.session_state.generated_complaint = edited_complaint
                        st.session_state.edit_mode = False
                        st.rerun()
                
                # 평가 모드
                if not st.session_state.evaluation_mode:
                    if st.button("소장 평가하기"):
                        st.session_state.evaluation_mode = True
                        st.rerun()
                else:
                    st.subheader("소장 평가")
                    st.session_state.rating = st.slider("평점", 1, 5, st.session_state.rating)
                    feedback = st.text_area("피드백")
                    
                    if st.button("평가 제출"):
                        try:
                            # 평가 저장 로직
                            st.success("평가가 성공적으로 저장되었니다!")
                            st.session_state.evaluation_mode = False
                            st.rerun()
                        except Exception as e:
                            st.error(f"평가 저장 중 오류 발생: {str(e)}")

if __name__ == "__main__":
    main()
