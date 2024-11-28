// API 엔드포인트
const API_BASE_URL = 'http://localhost:5000/api';

// 현재 세션 ID를 추적하는 전역 변수
let currentSessionId = null;

// 음성 녹음 관련 전역 변수
let audioContext, analyser, mediaRecorder, audioChunks = [], audioBlob = null;
let isRecording = false;
let audioStream = null;

// 시간 포맷 함수 (전역 함수로 정의)
function formatTime(seconds) {
    if (isNaN(seconds) || seconds < 0) return '0:00';
    
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

// 소장 수정 모드 토글 함수
function toggleComplaintEdit() {
    const complaintContainer = document.getElementById('complaintContent');
    const complaintTextarea = document.getElementById('complaintEditTextarea');
    const editComplaintBtn = document.getElementById('editComplaintBtn');
    const saveComplaintBtn = document.getElementById('saveComplaintBtn');

    // 소장 수정 모드 토글
    if (!complaintTextarea.hasAttribute('data-edit-mode')) {
        // 수정 모드 활성화
        complaintTextarea.value = complaintContainer.innerText.trim();
        complaintTextarea.style.display = 'block';
        complaintContainer.style.display = 'none';
        
        editComplaintBtn.textContent = '취소';
        saveComplaintBtn.style.display = 'inline-block';
        
        complaintTextarea.setAttribute('data-edit-mode', 'true');
        complaintTextarea.focus();
    } else {
        // 수정 모드 비활성화 (취소)
        complaintTextarea.style.display = 'none';
        complaintContainer.style.display = 'block';
        
        editComplaintBtn.textContent = '수정';
        saveComplaintBtn.style.display = 'none';
        
        complaintTextarea.removeAttribute('data-edit-mode');
    }
}

// 소장 저장 함수
async function saveComplaint() {
    const complaintContainer = document.getElementById('complaintContent');
    const complaintTextarea = document.getElementById('complaintEditTextarea');
    const editComplaintBtn = document.getElementById('editComplaintBtn');
    const saveComplaintBtn = document.getElementById('saveComplaintBtn');

    // 수정된 내용 가져오기
    const updatedComplaint = complaintTextarea.value.trim();

    try {
        // 서버에 소장 업데이트 요청
        const response = await fetch('/api/update_complaint', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            },
            body: JSON.stringify({
                complaint: updatedComplaint,
                session_id: localStorage.getItem('lastSummarySessionId')
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || '소장 수정 실패');
        }

        // UI 업데이트
        complaintContainer.innerText = updatedComplaint;
        complaintTextarea.style.display = 'none';
        complaintContainer.style.display = 'block';
        
        editComplaintBtn.textContent = '수정';
        saveComplaintBtn.style.display = 'none';
        
        complaintTextarea.removeAttribute('data-edit-mode');

        alert('소장이 성공적으로 수정되었습니다.');
    } catch (error) {
        console.error('소장 수정 오류:', error);
        alert(error.message || '소장 수정 중 오류가 발생했습니다.');
    }
}

// 문서 생성 함수 (진행 표시줄 추가)
async function generateDocument() {
    const transcription = document.getElementById('convertedTextDisplay').value;
    const summary = document.getElementById('conversationSummary').value;
    const generateDocumentBtn = document.getElementById('generateDocumentBtn');
    const progressContainer = document.createElement('div');
    
    try {
        // 진행 표시줄 생성
        progressContainer.innerHTML = `
            <div class="progress-bar-container">
                <div class="progress-bar" id="documentGenerationProgress">
                    <div class="progress-bar-fill"></div>
                </div>
                <div class="progress-text">소장 생성 중...</div>
            </div>
        `;
        generateDocumentBtn.parentNode.insertBefore(progressContainer, generateDocumentBtn.nextSibling);
        
        // 버튼 비활성화
        generateDocumentBtn.disabled = true;
        
        // 진행 표시줄 애니메이션
        const progressBarFill = document.querySelector('.progress-bar-fill');
        const progressText = document.querySelector('.progress-text');
        
        // 가상의 진행 애니메이션
        let progress = 0;
        const animateProgress = setInterval(() => {
            progress += Math.random() * 20;
            if (progress > 90) progress = 90;
            progressBarFill.style.width = `${progress}%`;
        }, 500);

        // 서버에 문서 생성 요청
        const response = await fetch('/api/generate_document', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            },
            body: JSON.stringify({
                transcription: transcription,
                summary: summary
            })
        });

        // 애니메이션 중지
        clearInterval(animateProgress);

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || '문서 생성 실패');
        }

        // 문서 다운로드
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = '이혼소장.docx';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        
        // 진행 표시줄 완료
        progressBarFill.style.width = '100%';
        progressText.textContent = '소장 생성 완료!';
        
        // 잠시 후 진행 표시줄 제거
        setTimeout(() => {
            progressContainer.remove();
        }, 2000);

    } catch (error) {
        console.error('문서 생성 오류:', error);
        
        // 진행 표시줄 오류 상태로 변경
        const progressBarFill = document.querySelector('.progress-bar-fill');
        const progressText = document.querySelector('.progress-text');
        
        if (progressBarFill) {
            progressBarFill.style.backgroundColor = '#ff4444';
            progressText.textContent = '문서 생성 중 오류 발생';
        }
        
        alert(error.message || '문서 생성 중 오류가 발생했습니다.');
    } finally {
        // 버튼 다시 활성화
        generateDocumentBtn.disabled = false;
    }
}

// 페이지 로드 시 초기화
document.addEventListener('DOMContentLoaded', () => {
    checkAuth();
    loadSessions();
    
    // 음성 녹음 및 업로드 초기화
    initializeVoiceUpload();
    
    // 음성 녹음 기능 초기화
    if (document.getElementById('recordButton')) {
        initializeVoiceRecording();
    }
    
    // 문서 생성 버튼 이벤트 리스너 추가
    const generateDocumentBtn = document.getElementById('generateDocumentBtn');
    if (generateDocumentBtn) {
        generateDocumentBtn.addEventListener('click', generateDocument);
    }
    
    // 텍스트 변환 버튼 이벤트 리스너
    const generateTextBtn = document.getElementById('generateTextBtn');
    if (generateTextBtn) {
        generateTextBtn.addEventListener('click', async () => {
            if (!audioBlob) {
                alert('먼저 음성을 녹음해주세요.');
                return;
            }

            try {
                // FormData 생성
                const formData = new FormData();
                formData.append('audio', audioBlob, 'recording.webm');

                // 음성을 텍스트로 변환
                const response = await fetch('/api/upload-audio', {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'Authorization': `Bearer ${localStorage.getItem('token')}`  // JWT 토큰 추가
                    }
                });

                // 응답 처리
                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.error || '음성 변환 중 오류가 발생했습니다.');
                }

                const result = await response.json();
                
                // 텍스트 표시
                const convertedTextDisplay = document.getElementById('convertedTextDisplay');
                convertedTextDisplay.value = result.text || '';
                
                // 자동으로 상담 내역 요약 실행
                // await summarizeConsultation();
                
                alert('음성이 텍스트로 성공적으로 변환되었습니다.');
                
            } catch (error) {
                console.error('텍스트 변환 중 오류:', error);
                alert(error.message || '텍스트 변환 중 오류가 발생했습니다.');
            }
        });
    }
    
    // 소장 수정 모드 토글 함수
    const editComplaintBtn = document.getElementById('editComplaintBtn');
    if (editComplaintBtn) {
        editComplaintBtn.addEventListener('click', toggleComplaintEdit);
    }
    
    // 소장 저장 버튼 이벤트 리스너
    const saveComplaintBtn = document.getElementById('saveComplaintBtn');
    if (saveComplaintBtn) {
        saveComplaintBtn.addEventListener('click', saveComplaint);
        // 초기에는 저장 버튼 숨김
        saveComplaintBtn.style.display = 'none';
    }
});

// 인증 확인
function checkAuth() {
    const token = localStorage.getItem('token');
    if (!token) {
        window.location.href = '/';
        return;
    }
    
    // 사용자 정보 표시
    const username = localStorage.getItem('username');
    document.getElementById('username').textContent = username;
}

// 로그아웃
function logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('username');
    window.location.href = '/';
}

// 세션 목록 로드
async function loadSessions() {
    try {
        const response = await fetch(`${API_BASE_URL}/sessions`, {
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            }
        });
        
        if (response.ok) {
            const sessions = await response.json();
            displaySessions(sessions);
        } else if (response.status === 401) {
            logout();
        }
    } catch (error) {
        console.error('세션 로드 중 오류:', error);
    }
}

// 날짜 포맷 함수
function formatKoreanDateTime(dateString) {
    if (!dateString) return '날짜 정보 없음';
    
    try {
        // 한국 시간대로 날짜 변환
        const date = new Date(dateString);
        
        // 유효한 날짜인지 확인
        if (isNaN(date.getTime())) {
            return '유효하지 않은 날짜';
        }
        
        // 한국 로케일 옵션 설정 (연, 월, 일, 시, 분까지 표기)
        const options = {
            timeZone: 'Asia/Seoul',
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            hour12: true
        };
        
        // 한국어로 포맷팅
        return new Intl.DateTimeFormat('ko-KR', options).format(date);
    } catch (error) {
        console.error('날짜 포맷 오류:', error);
        return '날짜 형식 오류';
    }
}

// 세션 목록 표시
function displaySessions(sessions) {
    console.log('로드한 세션 목록:', sessions);
    const sessionList = document.getElementById('sessionList');
    sessionList.innerHTML = ''; // Clear existing sessions

    if (!sessions || sessions.length === 0) {
        sessionList.innerHTML = '<p>저장된 세션이 없습니다.</p>';
        return;
    }

    sessions.forEach(session => {
        const sessionElement = document.createElement('div');
        sessionElement.classList.add('session-item');
        
        // 세션 날짜를 한국어 형식으로 포맷팅
        const formattedDate = formatKoreanDateTime(session.created_at);
        
        // 평가 상태 표시
        const ratingStatus = session.rating 
            ? `평가됨 (${session.rating}점)` 
            : '평가 대기';
        
        sessionElement.innerHTML = `
            <div class="session-header">
                <span class="session-date">${formattedDate}</span>
                <span class="session-rating-status">${ratingStatus}</span>
            </div>
            <div class="session-actions">
                <button onclick="loadSession('${session.session_id || session.session_id}')">세션 보기</button>
                ${!session.rating ? `<button onclick="openRatingModal('${session.session_id}')">세션 평가</button>` : ''}
            </div>
        `;
        
        sessionList.appendChild(sessionElement);
    });
}

// 세션 로드
async function loadSession(sessionId) {
    try {
        // 세션 데이터 로드
        const response = await fetch(`${API_BASE_URL}/sessions/${sessionId}`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            }
        });

        if (!response.ok) {
            throw new Error('세션을 불러오는 데 실패했습니다.');
        }

        const sessionData = await response.json();
        console.log('로드한 세션 데이터:', sessionData);

        // 탭 전환
        switchTab('text');

        // 세션 날짜 표시
        const sessionDateElement = document.getElementById('sessionDetailDate');
        if (sessionDateElement) {
            sessionDateElement.textContent = formatKoreanDateTime(sessionData.created_at);
        }

        // 상담 내용 표시 (sessionData.conversation)
        const consultationTextElement = document.getElementById('consultationText');
        if (consultationTextElement) {
            consultationTextElement.value = sessionData.consultatation_text || '상담 내용이 없습니다.';
        }

        // 대화 기록 표시 (complaint.response)
        const conversationContainer = document.getElementById('conversationHistory');
        if (conversationContainer) {
            conversationContainer.innerHTML = '';
            if (sessionData.complaint && sessionData.complaint.response) {
                const conversations = sessionData.complaint.response;
                
                if (typeof conversations === 'string') {
                    conversationContainer.innerHTML = conversations;
                } else if (Array.isArray(conversations)) {
                    conversations.forEach(conversation => {
                        const messageElement = document.createElement('div');
                        messageElement.classList.add('conversation-message');
                        messageElement.innerHTML = `
                            <strong>${conversation.role === 'user' ? '사용자' : '시스템'}</strong>
                            <p>${conversation.content || conversation}</p>
                        `;
                        conversationContainer.appendChild(messageElement);
                    });
                } else {
                    conversationContainer.innerHTML = '대화 내용이 없습니다.';
                }
            } else {
                conversationContainer.innerHTML = '대화 내용이 없습니다.';
            }
        }

        // 소장 섹션 표시 및 내용 채우기 (sessionData.complaint.response)
        const complaintSection = document.getElementById('complaintSection');
        const complaintContentElement = document.getElementById('complaintContent');
        const complaintEditTextarea = document.getElementById('complaintEditTextarea');
        
        if (complaintSection && complaintContentElement && complaintEditTextarea) {
            // 소장 섹션 보이기
            complaintSection.style.display = 'block';

            // 소장 내용 표시
            if (sessionData.complaint.response) {
                complaintContentElement.innerHTML = sessionData.complaint.complaint;
                complaintEditTextarea.value = sessionData.complaint.complaint;
                
                // 평가 상태 표시
                const ratingDisplay = document.createElement('div');
                ratingDisplay.className = 'rating-display';
                ratingDisplay.innerHTML = sessionData.rating 
                    ? `평가: ${'⭐'.repeat(sessionData.rating)}` 
                    : '평가 없음';
                complaintContentElement.appendChild(ratingDisplay);
            } else {
                complaintContentElement.innerHTML = '생성된 소장이 없습니다.';
                complaintEditTextarea.value = '';
            }

            // 소장 작성 버튼들 상태 조정
            const editComplaintBtn = document.getElementById('editComplaintBtn');
            const saveComplaintBtn = document.getElementById('saveComplaintBtn');
            
            if (editComplaintBtn) editComplaintBtn.style.display = 'inline-block';
            if (saveComplaintBtn) saveComplaintBtn.style.display = 'none';
        }

        // 음성 관련 정보 표시
        const convertedTextDisplay = document.getElementById('convertedTextDisplay');
        if (convertedTextDisplay && sessionData.transcribed_text) {
            convertedTextDisplay.value = sessionData.transcribed_text;
        }

        const conversationSummary = document.getElementById('conversationSummary');
        if (conversationSummary && sessionData.conversation_summary) {
            conversationSummary.value = sessionData.conversation_summary;
        }

        // 현재 세션 ID 업데이트
        currentSessionId = sessionId;

    } catch (error) {
        console.error('세션 로드 중 오류:', error);
        alert(error.message);
    }
}

// 탭 전환
function switchTab(tabName) {
    const tabs = document.querySelectorAll('.tab-btn');
    const contents = document.querySelectorAll('.tab-content');
    
    tabs.forEach(tab => tab.classList.remove('active'));
    contents.forEach(content => content.classList.remove('active'));
    
    document.querySelector(`[onclick="switchTab('${tabName}')"]`).classList.add('active');
    document.getElementById(`${tabName}Input`).classList.add('active');
    
    // 음성 녹음 탭에서 초기화
    if (tabName === 'voice') {
        initializeVoiceRecording();
    }
}

// 새 세션 시작 함수
function startNewSession() {
    // Clear any existing session data
    currentSessionId = null;
    selectedRating = 0;
    
    // Reset UI elements
    const consultationText = document.getElementById('consultationText');
    if (consultationText) consultationText.value = '';
    
    const conversationHistory = document.getElementById('conversationHistory');
    if (conversationHistory) conversationHistory.innerHTML = '';
    
    const complaintContent = document.getElementById('complaintContent');
    if (complaintContent) complaintContent.innerHTML = '';
    
    const complaintEditTextarea = document.getElementById('complaintEditTextarea');
    if (complaintEditTextarea) complaintEditTextarea.value = '';
    
    const complaintSection = document.getElementById('complaintSection');
    if (complaintSection) complaintSection.style.display = 'none';
    
    const convertedTextDisplay = document.getElementById('convertedTextDisplay');
    if (convertedTextDisplay) convertedTextDisplay.value = '';
    
    const conversationSummary = document.getElementById('conversationSummary');
    if (conversationSummary) conversationSummary.value = '';
    // Switch to text tab and start consultation
    switchTab('text');
    startConsultation();
}

// 상담 시작
async function startConsultation() {
    const text = document.getElementById('consultationText').value;
    if (!text) return;
    
    // 생성 중 프로그레스 바 표시
    const complaintResult = document.getElementById('complaintResult');
    
    // 요소가 없으면 동적으로 생성
    if (!complaintResult) {
        const mainContent = document.querySelector('.main-content');
        const newSection = document.createElement('section');
        newSection.className = 'complaint-result-section';
        newSection.innerHTML = `<div id="complaintResult"></div>`;
        mainContent.appendChild(newSection);
    }
    
    const resultElement = document.getElementById('complaintResult');
    if (!resultElement) {
        console.error('Could not find or create complaintResult element');
        return;
    }
    
    resultElement.innerHTML = `
        <div class="progress-container">
            <div class="progress-bar">
                <div class="progress-bar-fill"></div>
            </div>
            <p>소장 생성 중입니다...</p>
        </div>
    `;
    
    try {
        const response = await fetch(`${API_BASE_URL}/generate-complaint`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                user_input: text
            })
        });

        // Check if response is JSON
        const contentType = response.headers.get("content-type");
        if (!contentType || !contentType.includes("application/json")) {
            const errorText = await response.text();
            throw new Error(`Server returned non-JSON response: ${errorText}`);
        }

        const result = await response.json();
        
        if (response.ok) {
            displayConversation(result.response);
            if (result.complaint) {
                displayComplaint(result.complaint);
            }
            // Store the session ID if provided
            if (result.session_id) {
                currentSessionId = result.session_id;
                console.log('Current session ID:', currentSessionId);
            }
        } else {
            throw new Error(result.error || 'Server returned an error');
        }
    } catch (error) {
        console.error('상담 중 오류:', error);
        resultElement.innerHTML = `<p class="error-message">소장 생성 중 오류가 발생했습니다: ${error.message}</p>`;
    }
}

// 대화 표시
function displayConversation(message) {
    const history = document.getElementById('conversationHistory');
    history.innerHTML += `
        <div class="message">
            <div class="message-content">${message}</div>
        </div>
    `;
    history.scrollTop = history.scrollHeight;
}

// 소장 표시
function displayComplaint(complaint) {
    const complaintResult = document.getElementById('complaintResult');
    if (!complaintResult) {
        console.error('complaintResult element not found');
        return;
    }
    
    // 소장 내용을 줄바꿈과 함께 포맷팅
    const formattedComplaint = complaint
        .replace(/\n\n/g, '</p><p>')  // 문단 구분
        .replace(/\n/g, '<br>');  // 줄바꿈 처리
    
    complaintResult.innerHTML = `
        <div class="complaint-container">
            <h2>생성된 소장</h2>
            <div class="complaint-content">
                <p>${formattedComplaint}</p>
            </div>
            <div class="complaint-actions">
                <button class="btn edit-btn" onclick="toggleComplaintEdit()">소장 수정하기</button>
                <button class="btn download-btn" onclick="downloadComplaint()">워드로 다운받기</button>
                <button class="btn rate-btn" onclick="rateComplaint()">소장 평가하기</button>
            </div>
        </div>
    `;
}

// 소장 수정
function editComplaint() {
    const complaintContent = document.querySelector('.complaint-content p');
    const currentText = complaintContent.innerHTML.replace(/<br>/g, '\n').replace(/<\/p><p>/g, '\n\n');
    
    const editTextarea = document.createElement('textarea');
    editTextarea.value = currentText;
    editTextarea.className = 'complaint-edit-textarea';
    
    complaintContent.innerHTML = '';
    complaintContent.appendChild(editTextarea);
    
    const actionButtons = document.querySelector('.complaint-actions');
    actionButtons.innerHTML = `
        <button class="btn save-btn" onclick="saveComplaint()">저장</button>
        <button class="btn cancel-btn" onclick="cancelEdit()">취소</button>
    `;
}

// 소장 저장
function saveComplaint() {
    const editTextarea = document.querySelector('.complaint-edit-textarea');
    const complaintContent = document.querySelector('.complaint-content');
    
    const formattedText = editTextarea.value
        .replace(/\n\n/g, '</p><p>')  // 문단 구분
        .replace(/\n/g, '<br>');  // 줄바꿈 처리
    
    complaintContent.innerHTML = `<p>${formattedText}</p>`;
    
    // 원래 액션 버튼 복원
    const actionButtons = document.querySelector('.complaint-actions');
    actionButtons.innerHTML = `
        <button class="btn edit-btn" onclick="editComplaint()">소장 수정하기</button>
        <button class="btn download-btn" onclick="downloadComplaint()">워드로 다운받기</button>
        <button class="btn rate-btn" onclick="rateComplaint()">소장 평가하기</button>
    `;
}

// 수정 취소
function cancelEdit() {
    const complaintContent = document.querySelector('.complaint-content');
    const originalText = complaintContent.querySelector('textarea').value;
    
    const formattedText = originalText
        .replace(/\n\n/g, '</p><p>')  // 문단 구분
        .replace(/\n/g, '<br>');  // 줄바꿈 처리
    
    complaintContent.innerHTML = `<p>${formattedText}</p>`;
    
    // 원래 액션 버튼 복원
    const actionButtons = document.querySelector('.complaint-actions');
    actionButtons.innerHTML = `
        <button class="btn edit-btn" onclick="editComplaint()">소장 수정하기</button>
        <button class="btn download-btn" onclick="downloadComplaint()">워드로 다운받기</button>
        <button class="btn rate-btn" onclick="rateComplaint()">소장 평가하기</button>
    `;
}

// 소장 다운로드
function downloadComplaint() {
    const complaintContent = document.querySelector('.complaint-content p');
    const text = complaintContent.innerHTML
        .replace(/<br>/g, '\n')
        .replace(/<\/p><p>/g, '\n\n')
        .replace(/<[^>]*>/g, '');  // 모든 HTML 태그 제거
    
    const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `이혼소장_${new Date().toISOString().slice(0,10)}.docx`;
    link.click();
}

// 소장 평가
function openRatingModal(currentSessionId) {
    // 이미 평가했는지 확인
    if (localStorage.getItem(`session_rated_${currentSessionId}`)) {
        alert('이미 이 세션에 대해 평가하셨습니다.');
        return;
    }

    const ratingModal = document.getElementById('ratingModal');
    ratingModal.innerHTML = `
        <div class="rating-content">
            <h3>소장 평가</h3>
            <div class="rating-stars">
                <span class="star" data-rating="1" onclick="selectRating(1)">★</span>
                <span class="star" data-rating="2" onclick="selectRating(2)">★</span>
                <span class="star" data-rating="3" onclick="selectRating(3)">★</span>
                <span class="star" data-rating="4" onclick="selectRating(4)">★</span>
                <span class="star" data-rating="5" onclick="selectRating(5)">★</span>
            </div>
            <div class="rating-feedback">
                <textarea id="ratingFeedback" placeholder="이 소장에 대한 피드백을 남겨주세요 (선택사항)"></textarea>
            </div>
            <div class="rating-actions">
                <button class="btn submit-btn" onclick="submitRating()">평가 제출</button>
                <button class="btn close-btn" onclick="closeRatingModal()">취소</button>
            </div>
        </div>
    `;
    
    ratingModal.classList.remove('hidden');
    selectedRating = 0; // Reset rating when opening modal
}

// 별점 선택
let selectedRating = 0;

function selectRating(rating) {
    selectedRating = rating;
    const stars = document.querySelectorAll('.star');
    stars.forEach(star => {
        const starRating = parseInt(star.dataset.rating);
        if (starRating <= rating) {
            star.classList.add('selected');
        } else {
            star.classList.remove('selected');
        }
    });
}

// 평가 제출
async function submitRating() {
    console.log(currentSessionId)
    if (selectedRating === 0) {
        alert('평점을 선택해주세요.');
        return;
    }

    if (!currentSessionId) {
        console.error('현재 세션 ID가 없습니다.');
        alert('세션 정보를 찾을 수 없습니다. 다시 시도해주세요.');
        return;
    }

    const token = localStorage.getItem('token');
    if (!token) {
        alert('인증 토큰이 만료되었습니다. 다시 로그인해주세요.');
        return;
    }

    const feedback = document.getElementById('ratingFeedback')?.value.trim() || '';

    try {
        const response = await fetch(`${API_BASE_URL}/rate-session`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                session_id: currentSessionId,
                rating: selectedRating,
                feedback: feedback
            })
        });

        const result = await response.json();

        if (response.ok) {
            localStorage.setItem(`session_rated_${currentSessionId}`, 'true');
            closeRatingModal();
            loadSessions();
            alert('평가가 성공적으로 제출되었습니다.');
        } else {
            throw new Error(result.error || '평가 제출 중 오류가 발생했습니다.');
        }
    } catch (error) {
        console.error('Rating submission error:', error);
        alert(error.message || '평가 제출 중 오류가 발생했습니다.');
    }
}

// 평가 모달 닫기
function closeRatingModal() {
    const modal = document.getElementById('ratingModal');
    if (modal) {
        modal.classList.add('hidden');
        selectedRating = 0; // Reset rating when closing modal
    }
}

// 음성 녹음 초기화
function initializeVoiceRecording() {
    const canvas = document.getElementById('waveformCanvas');
    const startRecordingBtn = document.getElementById('startRecordingBtn');
    const recordingResult = document.getElementById('recordingResult');
    const playPauseBtn = document.getElementById('playPauseBtn');
    const progressBar = document.getElementById('progressBar');
    const currentTimeSpan = document.getElementById('currentTime');
    const totalTimeSpan = document.getElementById('totalTime');
    const downloadRecordingBtn = document.getElementById('downloadRecordingBtn');
    const generateTextBtn = document.getElementById('generateTextBtn');

    let audioPlayer = null;

    // 캔버스 초기화
    const canvasCtx = canvas.getContext('2d');
    canvasCtx.clearRect(0, 0, canvas.width, canvas.height);

    // 버튼 상태 초기화
    function resetButtonStates() {
        startRecordingBtn.textContent = '녹음 시작';
        startRecordingBtn.classList.remove('recording');
        recordingResult.classList.add('hidden');
    }

    // 녹음 시작 버튼 이벤트
    startRecordingBtn.onclick = async () => {
        try {
            if (!isRecording) {
                // 녹음 시작
                audioStream = await navigator.mediaDevices.getUserMedia({ audio: true });
                audioContext = new (window.AudioContext || window.webkitAudioContext)();
                analyser = audioContext.createAnalyser();
                const source = audioContext.createMediaStreamSource(audioStream);
                source.connect(analyser);
                
                mediaRecorder = new MediaRecorder(audioStream);
                audioChunks = [];
                
                mediaRecorder.ondataavailable = (event) => {
                    audioChunks.push(event.data);
                };
                
                mediaRecorder.onstop = () => {
                    audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
                    
                    // 오디오 플레이어 설정
                    audioPlayer = initializeAudioPlayer(audioBlob);
                    
                    // 총 재생 시간 설정
                    audioPlayer.onloadedmetadata = () => {
                        totalTimeSpan.textContent = formatTime(audioPlayer.duration);
                    };

                    // 재생/일시정지 버튼 설정
                    playPauseBtn.innerHTML = '<i class="fas fa-play"></i>';
                    playPauseBtn.onclick = () => {
                        if (audioPlayer.paused) {
                            audioPlayer.play();
                            playPauseBtn.innerHTML = '<i class="fas fa-pause"></i>';
                        } else {
                            audioPlayer.pause();
                            playPauseBtn.innerHTML = '<i class="fas fa-play"></i>';
                        }
                    };

                    // 진행 표시줄 업데이트
                    audioPlayer.ontimeupdate = () => {
                        const progress = (audioPlayer.currentTime / audioPlayer.duration) * 100;
                        progressBar.style.width = `${progress}%`;
                        currentTimeSpan.textContent = formatTime(audioPlayer.currentTime);
                    };

                    // 재생 완료 시 버튼 초기화
                    audioPlayer.onended = () => {
                        playPauseBtn.innerHTML = '<i class="fas fa-play"></i>';
                    };
                    
                    // UI 업데이트
                    recordingResult.classList.remove('hidden');
                    isRecording = false;
                };
                
                mediaRecorder.start();
                startRecordingBtn.textContent = '녹음 종료';
                startRecordingBtn.classList.add('recording');
                isRecording = true;
                
                // 파형 시각화
                visualizeAudio(canvas, analyser);
            } else {
                // 녹음 종료
                mediaRecorder.stop();
                audioStream.getTracks().forEach(track => track.stop());
                startRecordingBtn.textContent = '녹음 시작';
                startRecordingBtn.classList.remove('recording');
            }
        } catch (error) {
            console.error('녹음 시작/종료 오류:', error);
            alert('마이크 접근 권한을 허용해주세요.');
            resetButtonStates();
        }
    };

    // 다운로드 버튼 이벤트
    downloadRecordingBtn.onclick = () => {
        if (audioBlob) {
            const audioURL = URL.createObjectURL(audioBlob);
            const a = document.createElement('a');
            a.href = audioURL;
            a.download = 'recording.wav';
            a.click();
        }
    };

    // 텍스트 생성 버튼 이벤트
    generateTextBtn.onclick = async () => {
        if (audioBlob) {
            const formData = new FormData();
            formData.append('audio', audioBlob, 'recording.wav');

            try {
                const response = await fetch(`${API_BASE_URL}/upload-audio`, {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${localStorage.getItem('token')}`
                    },
                    body: formData
                });

                if (response.ok) {
                    const result = await response.json();
                    document.getElementById('convertedTextDisplay').value = result.text;
                    alert('음성이 텍스트로 성공적으로 변환되었습니다.');
                } else {
                    const error = await response.json();
                    alert(`텍스트 변환 오류: ${error.error}`);
                }
            } catch (error) {
                console.error('텍스트 생성 오류:', error);
                alert('텍스트 생성 중 오류가 발생했습니다.');
            }
        }
    };

    // 녹음 중지 버튼 이벤트
    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape' && isRecording) {
            mediaRecorder.stop();
            audioStream.getTracks().forEach(track => track.stop());
            resetButtonStates();
        }
    });
}

// 오디오 파형 시각화
function visualizeAudio(canvas, analyser) {
    const canvasCtx = canvas.getContext('2d');
    const WIDTH = canvas.offsetWidth; // Use full width of container
    const HEIGHT = 50; // Reduced height to 50px
    canvas.height = HEIGHT; // Explicitly set canvas height
    
    analyser.fftSize = 2048;
    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);
    
    function draw() {
        requestAnimationFrame(draw);
        
        analyser.getByteTimeDomainData(dataArray);
        
        canvasCtx.fillStyle = 'rgb(240, 240, 240)';
        canvasCtx.fillRect(0, 0, WIDTH, HEIGHT);
        
        canvasCtx.lineWidth = 2;
        canvasCtx.strokeStyle = 'rgb(0, 0, 0)';
        
        canvasCtx.beginPath();
        
        const sliceWidth = WIDTH * 1.0 / bufferLength;
        let x = 0;
        
        // Find the midpoint of the amplitude range
        const midHeight = HEIGHT / 2;
        const amplitudeScale = HEIGHT / 4; // Reduce amplitude to make waveform more compact
        
        for (let i = 0; i < bufferLength; i++) {
            const v = dataArray[i] / 128.0 - 1; // Normalize to range [-1, 1]
            const y = v * amplitudeScale + midHeight;
            
            if (i === 0) {
                canvasCtx.moveTo(x, y);
            } else {
                canvasCtx.lineTo(x, y);
            }
            
            x += sliceWidth;
        }
        
        canvasCtx.lineTo(canvas.width, midHeight);
        canvasCtx.stroke();
    }
    
    if (isRecording) {
        draw();
    }
}

// 음성 파일 업로드 초기화
function initializeVoiceUpload() {
    const audioFileUpload = document.getElementById('audioFileUpload');
    const uploadedFileInfo = document.getElementById('uploadedFileInfo');
    const processAudioBtn = document.getElementById('processAudioBtn');
    const transcribedText = document.getElementById('transcribedText');

    audioFileUpload.addEventListener('change', (event) => {
        const file = event.target.files[0];
        if (file) {
            uploadedFileInfo.textContent = `선택된 파일: ${file.name} (${(file.size / 1024).toFixed(2)} KB)`;
            processAudioBtn.classList.remove('hidden');
        }
    });

    processAudioBtn.addEventListener('click', async () => {
        const file = audioFileUpload.files[0];
        if (file) {
            const formData = new FormData();
            formData.append('audio', file);

            try {
                const response = await fetch(`${API_BASE_URL}/upload-audio`, {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${localStorage.getItem('token')}`
                    },
                    body: formData
                });

                if (response.ok) {
                    const result = await response.json();
                    transcribedText.textContent = result.text;
                    transcribedText.classList.remove('hidden');
                } else {
                    const error = await response.json();
                    transcribedText.textContent = `오류: ${error.error}`;
                    transcribedText.classList.remove('hidden');
                }
            } catch (error) {
                console.error('음성 파일 처리 오류:', error);
                transcribedText.textContent = '음성 파일 처리 중 오류가 발생했습니다.';
                transcribedText.classList.remove('hidden');
            }
        }
    });
}

// 오디오 플레이어 초기화
function initializeAudioPlayer(audioBlob) {
    const audioPlayer = document.getElementById('audioPlayer');
    const playPauseBtn = document.getElementById('playPauseBtn');
    const progressBar = document.getElementById('progressBar');
    const currentTimeEl = document.getElementById('currentTime');
    const totalTimeEl = document.getElementById('totalTime');

    // Remove any existing audio elements
    if (audioPlayer) {
        audioPlayer.remove();
    }

    // Create new audio element
    const audioElement = new Audio(URL.createObjectURL(audioBlob));
    audioElement.id = 'audioPlayer';
    
    // Track play/pause state
    let isPlaying = false;

    // Update play/pause button
    playPauseBtn.innerHTML = '<i class="fas fa-play"></i>';
    
    // Event listeners for audio
    audioElement.addEventListener('loadedmetadata', () => {
        // Set total time
        totalTimeEl.textContent = formatTime(audioElement.duration);
    });

    audioElement.addEventListener('timeupdate', () => {
        // Update current time and progress bar
        const progress = (audioElement.currentTime / audioElement.duration) * 100;
        progressBar.style.width = `${progress}%`;
        currentTimeEl.textContent = formatTime(audioElement.currentTime);
    });

    audioElement.addEventListener('ended', () => {
        // Reset play button and progress
        playPauseBtn.innerHTML = '<i class="fas fa-play"></i>';
        progressBar.style.width = '0%';
        isPlaying = false;
    });

    // Play/Pause functionality
    playPauseBtn.addEventListener('click', () => {
        if (isPlaying) {
            audioElement.pause();
            playPauseBtn.innerHTML = '<i class="fas fa-play"></i>';
            isPlaying = false;
        } else {
            audioElement.play();
            playPauseBtn.innerHTML = '<i class="fas fa-pause"></i>';
            isPlaying = true;
        }
    });

    // Append audio element to body (hidden)
    document.body.appendChild(audioElement);

    return audioElement;
}

// 녹음 중지 이벤트 핸들러
function handleRecordingStop(audioBlob) {
    // Existing recording stop logic
    const recordingResult = document.getElementById('recordingResult');
    recordingResult.classList.remove('hidden');
    
    // Draw waveform
    const audioContext = new (window.AudioContext || window.webkitAudioContext)();
    const fileReader = new FileReader();
    
    fileReader.onloadend = async () => {
        const arrayBuffer = fileReader.result;
        const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
        drawWaveform(audioBuffer);
    };
    
    fileReader.readAsArrayBuffer(audioBlob);
    
    // Initialize audio player
    const audioPlayer = initializeAudioPlayer(audioBlob);
    
    // Update download button
    const downloadBtn = document.getElementById('downloadRecordingBtn');
    downloadBtn.onclick = () => {
        const url = URL.createObjectURL(audioBlob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'recording.webm';
        a.click();
        URL.revokeObjectURL(url);
    };
}

// 요약 생성
async function summarizeTranscription(transcription) {
    try {
        const response = await fetch('/summarize_text', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                text: transcription,
                model: 'gpt-4-turbo'
            })
        });

        if (!response.ok) {
            throw new Error('Summarization failed');
        }

        const data = await response.json();
        return data.summary;
    } catch (error) {
        console.error('Error summarizing text:', error);
        return '요약 중 오류가 발생했습니다.';
    }
}

// 파형 그리기
function drawWaveform(audioBuffer) {
    const canvas = document.getElementById('waveformCanvas');
    const canvasWidth = canvas.offsetWidth;
    const canvasHeight = canvas.height;
    
    const ctx = canvas.getContext('2d');
    
    // Clear previous drawing
    ctx.clearRect(0, 0, canvasWidth, canvasHeight);
    
    const channelData = audioBuffer.getChannelData(0);
    const step = Math.ceil(channelData.length / canvasWidth);
    
    // Calculate max amplitude to normalize waveform
    let maxAmplitude = 0;
    for (let i = 0; i < channelData.length; i++) {
        maxAmplitude = Math.max(maxAmplitude, Math.abs(channelData[i]));
    }
    
    // Vertical centering variables
    const midY = canvasHeight / 2;
    const drawHeight = canvasHeight / 2; // Use half the canvas height for drawing
    
    ctx.beginPath();
    ctx.moveTo(0, midY);
    
    for (let x = 0; x < canvasWidth; x++) {
        let min = 0;
        let max = 0;
        
        for (let j = 0; j < step; j++) {
            const index = Math.floor((x * step + j) * channelData.length / canvasWidth);
            if (index < channelData.length) {
                const datum = channelData[index];
                if (datum < min) min = datum;
                if (datum > max) max = datum;
            }
        }
        
        // Normalize and scale
        const normalizedMin = (min / maxAmplitude) * drawHeight;
        const normalizedMax = (max / maxAmplitude) * drawHeight;
        
        // Draw waveform centered
        ctx.lineTo(x, midY - normalizedMin);
        ctx.lineTo(x, midY - normalizedMax);
    }
    
    ctx.strokeStyle = '#4CAF50';
    ctx.lineWidth = 1;
    ctx.stroke();
}

// 음성 텍스트 생성
async function generateTextFromAudio() {
    try {
        // Existing text generation logic
        const transcription = await performSpeechRecognition();
        
        // Display transcription
        const convertedTextDisplay = document.getElementById('convertedTextDisplay');
        convertedTextDisplay.textContent = transcription;
        
        // Summarize transcription
        const summary = await summarizeTranscription(transcription);
        
        // Add summary to conversation history
        await addMessageToChatHistory('system', '음성 요약', summary);
        
    } catch (error) {
        console.error('Text generation error:', error);
        alert('텍스트 변환 중 오류가 발생했습니다.');
    }
}

// 상담 내역 요약 및 정리 함수
async function summarizeConsultation() {
    const convertedTextDisplay = document.getElementById('convertedTextDisplay');
    const conversationSummary = document.getElementById('conversationSummary');
    
    if (!convertedTextDisplay || !conversationSummary) {
        alert('먼저 음성을 텍스트로 변환해주세요.');
        return;
    }
    
    const transcription = convertedTextDisplay.value.trim();
    
    if (!transcription) {
        alert('변환된 텍스트가 없습니다.');
        return;
    }
    
    try {
        const response = await fetch('/api/summarize_consultation', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            },
            body: JSON.stringify({
                text: transcription,
                model: 'gpt-4o'
            })
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || '상담 내역 요약 실패');
        }
        
        const data = await response.json();
        
        // 요약된 내용을 textarea에 표시
        conversationSummary.value = data.summary || '요약을 생성할 수 없습니다.';
        
        // 대화 기록에 추가 (선택적)
        if (typeof addMessageToChatHistory === 'function') {
            await addMessageToChatHistory('system', '상담 내역 요약', data.summary);
        }
        
        // 세션 ID 저장 (필요한 경우)
        if (data.session_id) {
            localStorage.setItem('lastSummarySessionId', data.session_id);
        }
        
    } catch (error) {
        console.error('상담 내역 요약 오류:', error);
        alert(error.message || '상담 내역을 요약하는 중 오류가 발생했습니다.');
    }
}
