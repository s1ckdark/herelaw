// 현재 세션 ID를 추적하는 전역 변수
let currentSessionId = null;

// 음성 녹음 관련 전역 변수
let recordingTimer = null, recordingDuration = 0, audioContext, analyser, mediaRecorder = null, audioChunks = [], audioBlob = null;
let isRecording = false;
let audioStream = null;

// 시간 포맷 함수 (전역 함수로 정의)
function formatTime(seconds) {
    if (isNaN(seconds) || seconds < 0) return '0:00';
    
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    
    return `${mins}:${secs.toString().padStart(2, '0')}`;
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
        
        sessionElement.innerHTML = `
            <div class="session-header" onclick="loadSession('${session.session_id || session.session_id}')">
                <span class="session-date">${formattedDate}</span>
                <span class="session-title">${session.title ? session.title : '제목 없음'}</span>
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

        // 세션 날짜 표시
        const sessionDateElement = document.getElementById('sessionDetailDate');
        if (sessionDateElement) {
            sessionDateElement.textContent = formatKoreanDateTime(sessionData.created_at);
        }
        // 소장 섹션 표시 및 내용 채우기 (sessionData.complaint.response)
        const complaintContent = document.getElementById('complaintContent');
        const complaintResult = document.getElementById('complaintResult');
        const complaintEditTextarea = document.getElementById('complaintEditTextarea');
        
        console.log(complaintContent, complaintResult, complaintEditTextarea);
        if (complaintContent && complaintResult && complaintEditTextarea) {
            // 소장 섹션 보이기
            complaintContent.classList.remove('hidden');

            // 소장 내용 표시
            if (sessionData.complaint.response) {
                console.log(sessionData.complaint.complaint);
                var text = sessionData.complaint.complaint;


                complaintEditTextarea.value = text;
                
            } 

            // 소장 작성 버튼들 상태 조정
            const editComplaintBtn = document.getElementById('editComplaintBtn');
            const saveComplaintBtn = document.getElementById('saveComplaintBtn');
            
            if (editComplaintBtn) editComplaintBtn.style.display = 'inline-block';
            if (saveComplaintBtn) saveComplaintBtn.style.display = 'none';
        }

        // 현재 세션 ID 업데이트
        currentSessionId = sessionId;

    } catch (error) {
        console.error('세션 로드 중 오류:', error);
    }
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

// 소장 수정 모드 토글 함수
function toggleComplaintEdit() {
    const complaintContent = document.getElementById('complaintContent');
    const editComplaintBtn = document.getElementById('editComplaintBtn');
    const saveComplaintBtn = document.getElementById('saveComplaintBtn');

 // 소장 수정 모드 토글
    if (complaintContent.hasAttribute('readonly')) {
        // 수정 모드 활성화   
        console.log('수정 모드 활성화');
        editComplaintBtn.textContent = '취소';
        saveComplaintBtn.style.display = 'inline-block';
        
        complaintContent.removeAttribute('readonly');
        complaintContent.focus();
    } else {
        // 수정 모드 비활성화 (취소)
        console.log('수정 모드 비활성화');
        editComplaintBtn.textContent = '수정';
        saveComplaintBtn.style.display = 'none';
        
        complaintContent.setAttribute('readonly', 'true');
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


// 페이지 로드 시 초기화
document.addEventListener('DOMContentLoaded', () => {
    checkAuth();
    loadSessions();
});


// 소장 표시
function displayComplaint(complaint) {
    // const complaintResult = document.getElementById('complaintResult');
    // if (!complaintResult) {
    //     console.error('complaintResult element not found');
    //     return;
    // }
    
    // 소장 내용을 줄바꿈과 함께 포맷팅
    function htmlToText(html) {
        return html
            .replace(/<\/p><p>/g, '\n\n')  // 문단 구분을 두 줄바꿈으로
            .replace(/<br\s*\/?>/g, '\n')   // <br> 태그를 줄바꿈으로
            .replace(/<[^>]*>/g, '')        // 나머지 HTML 태그 제거
            .trim();
    }
    
    // textarea에 소장 내용 설정
    const complaintContent = document.getElementById('complaintContent');
    if (complaintContent) {
        complaintContent.value = htmlToText(complaint);
    }
    const complaintTextarea = document.getElementById('complaintEditTextarea');
    if (complaintTextarea) {
        complaintTextarea.value = htmlToText(complaint);
    }
    
    complaintResult.innerHTML = `
        <div class="complaint-container">
            <h2>생성된 소장</h2>
            <textarea id="complaintContent">
                ${htmlToText(complaint)}
            </textarea>
            <div class="complaint-actions">
                <button class="btn edit-btn" onclick="toggleComplaintEdit()">소장 수정하기</button>
                <button class="btn download-btn" onclick="downloadComplaint()">워드로 다운받기</button>
                <button class="btn rate-btn" onclick="open()">소장 평가하기</button>
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
        <button class="btn rate-btn" onclick="openRatingModal(currentSessionId)">소장 평가하기</button>
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
    // const actionButtons = document.querySelector('.complaint-actions');
    // actionButtons.innerHTML = `
    //     <button class="btn edit-btn" onclick="editComplaint()">소장 수정하기</button>
    //     <button class="btn download-btn" onclick="downloadComplaint()">워드로 다운받기</button>
    //     <button class="btn rate-btn" onclick="open()">소장 평가하기</button>
    // `;
}

// 소장 다운로드
function downloadComplaint() {
    const complaintContent = document.querySelector('#complaintContent').value;
    const text = complaintContent
        .replace(/<br>/g, '\n')
        .replace(/<\/p><p>/g, '\n\n')
        .replace(/<[^>]*>/g, '');  // 모든 HTML 태그 제거
    
    const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `이혼소장_${new Date().toISOString().slice(0,10)}.docx`;
    link.click();
}

// 입력창 자동 크기 조절
function initializeAutoResize() {
    const textarea = document.getElementById('consultationText');
    
    textarea.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = (this.scrollHeight) + 'px';
    });
    
    // Enter 키로 전송
    textarea.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            startConsultation();
        }
    });
}


