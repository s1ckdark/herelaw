// 현재 세션 ID를 추적하는 전역 변수
let currentSessionId = null;

// 음성 녹음 관련 전역 변수
let recordingTimer = null, recordingDuration = 0, audioContext, analyser, mediaRecorder = null, audioChunks = [], audioBlob = null;
let isRecording = false;
let audioStream = null;

// 평가 관련 변수
let currentRating = null;
let isRatingSubmitted = false;

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
                <div class="session-info">
                    <span class="session-date">${formattedDate}</span>
                    <span class="session-title">${session.title ? session.title : '제목 없음'}</span>
                </div>
            </div>
        `;
        
        sessionList.appendChild(sessionElement);
    });
}

// 세션 로드
async function loadSession(sessionId) {
    try {
        currentSessionId = sessionId;
        
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
        
        // 소장 섹션 표시 및 내용 채우기
        const complaintContent = document.getElementById('complaintContent');
        const complaintResult = document.getElementById('complaintResult');
        const complaintEditTextarea = document.getElementById('complaintEditTextarea');
        
        if (complaintContent && complaintResult && complaintEditTextarea) {
            // 소장 섹션 보이기
            complaintContent.classList.remove('hidden');

            // 소장 내용 표시
            if (sessionData.complaint && sessionData.complaint.complaint) {
                complaintResult.innerText = sessionData.complaint.complaint;
                complaintEditTextarea.value = sessionData.complaint.complaint;
            } else {
                complaintResult.innerText = '소장 내용이 없습니다.';
                complaintEditTextarea.value = '';
            }

            // 소장 작성 버튼들 상태 조정
            const editComplaintBtn = document.getElementById('editComplaintBtn');
            const saveComplaintBtn = document.getElementById('saveComplaintBtn');
            
            if (editComplaintBtn) editComplaintBtn.style.display = 'inline-block';
            if (saveComplaintBtn) saveComplaintBtn.style.display = 'none';
        }
        
        // 평가 상태 업데이트
        if (sessionData.rating) {
            updateRatingUI(sessionData.rating);
        } else {
            updateRatingUI(null);
        }
        
    } catch (error) {
        console.error('세션 로드 중 오류:', error);
        alert('세션을 로드하는 중 오류가 발생했습니다.');
    }
}

// 평가 UI 업데이트
function updateRatingUI(rating) {
    const goodBtn = document.getElementById('goodRatingBtn');
    const badBtn = document.getElementById('badRatingBtn');
    
    // 버튼이 없는 경우 처리하지 않음
    if (!goodBtn || !badBtn) {
        console.log('Rating buttons not found');
        return;
    }
    
    // 모든 버튼의 active 클래스 제거
    goodBtn.classList.remove('active');
    badBtn.classList.remove('active');
    badBtn.classList.remove('bad');
    
    // rating 값에 따라 해당 버튼에 active 클래스 추가
    if (rating !== null) {
        if (rating === 1) {
            goodBtn.classList.add('active');
            goodBtn.disabled = true;
            badBtn.disabled = true;
        } else if (rating === 0) {
            badBtn.classList.add('active');
            badBtn.classList.add('bad');
            goodBtn.disabled = true;
            badBtn.disabled = true;
        }
    } else {
        // rating이 null인 경우 버튼 활성화
        goodBtn.disabled = false;
        badBtn.disabled = false;
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
    location.href = '/generate';
}

// 소장 수정 모드 토글 함수
function toggleComplaintEdit() {
    const complaintResult = document.getElementById('complaintResult');
    const complaintTextarea = document.getElementById('complaintEditTextarea');
    const editComplaintBtn = document.getElementById('editComplaintBtn');
    const saveComplaintBtn = document.getElementById('saveComplaintBtn');

    if (complaintTextarea.classList.contains('hidden')) {
        // 수정 모드 활성화
        console.log('수정 모드 활성화');
        complaintTextarea.classList.remove('hidden');
        complaintResult.classList.add('hidden');
        
        // textarea에 현재 내용 복사 (안전하게 처리)
        const complaintText = complaintResult.innerHTML || complaintResult.innerText || '';
        complaintTextarea.value = typeof complaintText === 'string' ? htmlToText(complaintText) : '';
        
        // 버튼 상태 변경
        editComplaintBtn.textContent = '취소';
        saveComplaintBtn.style.display = 'inline-block';
        
        complaintTextarea.focus();
    } else {
        // 수정 모드 비활성화 (취소)
        console.log('수정 모드 비활성화');
        complaintTextarea.classList.add('hidden');
        complaintResult.classList.remove('hidden');
        
        // 버튼 상태 변경
        editComplaintBtn.textContent = '수정';
        saveComplaintBtn.style.display = 'none';
    }
}

// 소장 저장 함수
async function saveComplaint() {
    const complaintTextarea = document.getElementById('complaintEditTextarea');
    const complaintResult = document.getElementById('complaintResult');
    const editComplaintBtn = document.getElementById('editComplaintBtn');
    const saveComplaintBtn = document.getElementById('saveComplaintBtn');
    const downloadBtn = document.getElementById('downloadComplaintBtn');
    
    try {
        // 서버에 소장 업데이트 요청
        const response = await fetch(`${API_BASE_URL}/update_complaint`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            },
            body: JSON.stringify({
                complaint: complaintTextarea.value,
                session_id: currentSessionId
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || '소장 업데이트에 실패했습니다.');
        }

        const data = await response.json();
        
        // UI 업데이트
        complaintResult.innerText = data.updated_complaint;
        complaintTextarea.classList.add('hidden');
        complaintResult.classList.remove('hidden');
        
        // 버튼 상태 변경
        editComplaintBtn.textContent = '수정';
        saveComplaintBtn.style.display = 'none';
        
        // 수정과 다운로드 버튼 표시
        editComplaintBtn.style.display = 'inline-block';
        if (downloadBtn) downloadBtn.style.display = 'inline-block';
        
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
                <button class="btn rate-btn" onclick="openRatingModal()">소장 평가하기</button>
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
// function saveComplaint() {
//     const editTextarea = document.querySelector('.complaint-edit-textarea');
//     const complaintContent = document.querySelector('.complaint-content');
    
//     const formattedText = editTextarea.value
//         .replace(/\n\n/g, '</p><p>')  // 문단 구분
//         .replace(/\n/g, '<br>');  // 줄바꿈 처리
    
//     complaintContent.innerHTML = `<p>${formattedText}</p>`;
    
//     // 원래 액션 버튼 복원
//     const actionButtons = document.querySelector('.complaint-actions');
//     actionButtons.innerHTML = `
//         <button class="btn edit-btn" onclick="editComplaint()">소장 수정하기</button>
//         <button class="btn download-btn" onclick="downloadComplaint()">워드로 다운받기</button>
//         <button class="btn rate-btn" onclick="openRatingModal()">소장 평가하기</button>
//     `;
// }

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
    //     <button class="btn rate-btn" onclick="openRatingModal()">소장 평가하기</button>
    // `;
}

// 소장 다운로드
async function downloadComplaint() {
    const complaintResult = document.getElementById('complaintResult');
    if (!complaintResult) {
        console.error('소장 내용을 찾을 수 없습니다.');
        return;
    }

    try {
        // HTML 내용을 일반 텍스트로 변환
        const text = htmlToText(complaintResult.innerHTML || complaintResult.innerText || '');
        
        // 서버에 DOCX 변환 요청
        const response = await fetch(`${API_BASE_URL}/download-complaint`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            },
            body: JSON.stringify({
                complaint: text
            })
        });

        if (!response.ok) {
            throw new Error('문서 다운로드에 실패했습니다.');
        }

        // 파일 다운로드
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `이혼소장_${new Date().toISOString().slice(0,10)}.docx`;
        
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        // Blob URL 해제
        window.URL.revokeObjectURL(url);
        
    } catch (error) {
        console.error('소장 다운로드 중 오류:', error);
        alert(error.message);
    }
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

// 평가 모달 열기
function openRatingModal(sessionId) {
    currentSessionId = sessionId;
    isRatingSubmitted = false;
    resetRatingModal();
    
    // 이전 평가 데이터 불러오기
    checkPreviousRating(sessionId);
    
    const ratingModal = new bootstrap.Modal(document.getElementById('ratingModal'));
    ratingModal.show();
}

// 이전 평가 확인
async function checkPreviousRating(sessionId) {
    try {
        const response = await fetch(`/api/get_rating/${sessionId}`, {
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            if (data.rating) {
                currentRating = data.rating;
                isRatingSubmitted = true;
                updateRatingUI(data.rating);
            }
        }
    } catch (error) {
        console.error('평가 데이터 로딩 실패:', error);
    }
}

// 평가 제출
async function submitRating(rating) {
    if (!currentSessionId) return;
    
    try {
        // 현재 소장 내용 가져오기
        const complaintContent = document.getElementById('complaintResult').innerText;
        
        const response = await fetch(`${API_BASE_URL}/rating`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            },
            body: JSON.stringify({
                session_id: currentSessionId,
                complaint: complaintContent,
                rating: rating === 'good' ? 1 : 0  // good이면 1, bad면 0
            })
        });
        
        if (!response.ok) {
            throw new Error('평가 제출 실패');
        }

        // UI 업데이트
        updateRatingUI(rating);
        
    } catch (error) {
        console.error('평가 제출 오류:', error);
        alert('평가 제출 중 오류가 발생했습니다.');
    }
}

// 평가 모달 초기화
function resetRatingModal() {
    document.getElementById('ratingFeedback').value = '';
    document.querySelector('.rating-status').textContent = '';
    document.getElementById('goodRatingBtn').classList.remove('selected');
    document.getElementById('badRatingBtn').classList.remove('selected');
    updateRatingUI(null);
}
