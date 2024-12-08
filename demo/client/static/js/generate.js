// API 엔드포인트
// 현재 세션 ID를 추적하는 전역 변수
let currentSessionId = null;

// 음성 녹음 관련 전역 변수
let recordingTimer = null, recordingDuration = 0, audioContext, analyser, animationId = null, mediaRecorder = null, audioChunks = [], audioBlob = null;
let isRecording = false;
let audioStream = null;

// 평가 관련 변수
let currentRating = null;
let isRatingSubmitted = false;

// WebSocket 변수
let ws = null;

// 시간 포맷 함수 (전역 함수로 정의)
function formatTime(seconds) {
    if (isNaN(seconds) || seconds < 0) return '0:00';
    
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

function resetText() {
    const consultationSection = document.getElementById('consultationSection');
    if(!consultationSection) return;
    if(consultationSection.classList.contains('hidden')) return;
    const mainContent = document.querySelector('.main-content')
    mainContent.classList.toggle('generate');
    consultationSection.classList.toggle('hidden');
    const consultationText = document.getElementById('consultationText');
    consultationText.value = '';
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

function handleText() {
    const mainContent = document.querySelector('.main-content')
    const consultationSection = document.getElementById('consultationSection')
    consultationSection.classList.toggle('hidden');
    mainContent.classList.toggle('generate');
}

// 상담 시작 함수 수정
async function startConsultation() {
    const consultationText = document.getElementById('consultationText');

    if(consultationText.value.trim() === '') return;
    const text = consultationText.value.trim();

    // 로딩 컨테이너 생성
    const loadingContainer = document.createElement('div');
    loadingContainer.className = 'loading-container';
    loadingContainer.innerHTML = `
        <div class="loading-overlay"></div>
        <div class="loading-content">
            <div class="progress-container">
                <div class="progress-bar">
                    <div class="progress-bar-fill"></div>
                </div>
                <div class="progress-text">소장 생성 중...</div>
                <div class="progress-percentage">0%</div>
            </div>
        </div>
    `;

    // 로딩 컨테이너를 body에 추가
    document.body.appendChild(loadingContainer);

    const progressBarFill = loadingContainer.querySelector('.progress-bar-fill');
    const progressText = loadingContainer.querySelector('.progress-text');
    const progressPercentage = loadingContainer.querySelector('.progress-percentage');

    // 프로그레스 바 애니메이션
    let progress = 0;
    const progressInterval = setInterval(() => {
        if (progress < 90) {
            progress += Math.random() * 15;
            if (progress > 90) progress = 90;
            progressBarFill.style.width = `${progress}%`;
            progressPercentage.textContent = `${Math.round(progress)}%`;
        }
    }, 1000);

    try {
        const response = await fetch(`${API_BASE_URL}/generate-complaint`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            },
            body: JSON.stringify({
                user_input: consultationText.value.trim()
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.message || errorData.error || '소장 생성 실패');
        }

        const data = await response.json();
        
        // 프로그레스 바 100%로 설정
        clearInterval(progressInterval);
        progressBarFill.style.width = '100%';
        progressPercentage.textContent = '100%';
        progressText.textContent = '소장 생성 완료!';

        const resultContent = document.getElementById('resultContent');
        const resultContentEdit = document.getElementById('resultContentEdit');
        const resultSummary = document.getElementById('resultSummary');
        const resultModalElement = document.getElementById('resultModal');
        
        // 모달 요소가 존재하는지 확인
        if (!resultModalElement) {
            console.error('Result modal element not found');
            return;
        }
        
        // Bootstrap 모달 인스턴스 생성
        const resultModal = new bootstrap.Modal(resultModalElement);
        
        if (resultContent) {
            // 내용 설정
            resultContent.innerHTML = data.complaint
                .replace(/\n\n/g, '</p><p>')
                .replace(/\n/g, '<br>');
            resultContentEdit.value = data.complaint;
            // resultSummary.innerHTML = data.summary
            //     .replace(/\n\n/g, '</p><p>')
            //     .replace(/\n/g, '<br>');
            
            // 모달 표시 전에 콘솔에 로그
            
            console.log('Showing modal...');
            
            // 모달 표시
            try {
                resultModal.show();
                if (data.session_id) {
                    currentSessionId = data.session_id;
                }
            } catch (error) {
                console.error('Error showing modal:', error);
            }
        }

        // 잠시 후 로딩 컨테이너 제거
        setTimeout(() => {
            loadingContainer.remove();
        }, 1000);

    } catch (error) {
        console.error('소장 생성 오류:', error);
        
        // 에러 상태로 프로그레스 바 변경
        clearInterval(progressInterval);
        progressBarFill.style.backgroundColor = '#ff4444';
        progressText.textContent = '소장 생성 실패';
        progressPercentage.style.display = 'none';

        // 에러 메시지 표시
        const errorMessage = document.createElement('div');
        errorMessage.className = 'error-message';
        errorMessage.textContent = error.message.includes('module') 
            ? '서버 설정 오류가 발생했습니다. 관리자에게 문의해주세요.'
            : '소장 생성 중 오류가 발생했습니다.';
        
        loadingContainer.querySelector('.loading-content').appendChild(errorMessage);

        // 재시도 버튼 추가
        const retryButton = document.createElement('button');
        retryButton.className = 'retry-button';
        retryButton.textContent = '다시 시도';
        retryButton.onclick = () => {
            loadingContainer.remove();
            startConsultation();
        };
        loadingContainer.querySelector('.loading-content').appendChild(retryButton);
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

// 수정 취소
function cancelEdit() {
    const resultContentEdit = document.getElementById('resultContentEdit');
    const resultContent = document.getElementById('resultContent');
    const resultEditActions = document.querySelector('.result-edit-actions');
    const resultActions = document.querySelector('.result-actions');

    
    resultContentEdit.classList.add('hidden');
    resultContent.classList.remove('hidden');
    resultEditActions.classList.add('hidden');
    resultActions.classList.remove('hidden');
}

// 소장 다운로드
function downloadComplaint() {
    const complaintContent = document.querySelector('#resultContent').value;
    const text = complaintContent
        .replace(/<br>/g, '\n')
        .replace(/<\/p><p>/g, '\n\n')
        .replace(/<[^>]*>/g, '');  // 모든 HTML 태그 제거
    
    const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'complaint.docx';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
}

function toggleComplaintEdit() {
    const resultContentEdit = document.getElementById('resultContentEdit');
    const resultContent = document.getElementById('resultContent');
    const resultEditActions = document.querySelector('.result-edit-actions');
    const resultActions = document.querySelector('.result-actions');
    resultContentEdit.classList.toggle('hidden');
    resultContent.classList.toggle('hidden');
    resultEditActions.classList.toggle('hidden');
    resultActions.classList.toggle('hidden');
}

function visualizeStream(stream) {
    const audioContext = new (window.AudioContext || window.webkitAudioContext)();
    const source = audioContext.createMediaStreamSource(stream);
    analyser = audioContext.createAnalyser();
    analyser.fftSize = 2048;
    source.connect(analyser);
    
    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);
    const waveform = document.getElementById('waveform');
    waveform.classList.remove('d-none');
    const canvas = document.getElementById('waveformCanvas');
    const ctx = canvas.getContext('2d');
    
    function draw() {
        animationId = requestAnimationFrame(draw);
        
        analyser.getByteTimeDomainData(dataArray);
        
        ctx.fillStyle = 'rgb(200, 200, 200)';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.lineWidth = 2;
        ctx.strokeStyle = 'rgb(0, 0, 0)';
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

function stopVisualization() {
    if (animationId) {
        cancelAnimationFrame(animationId);
        animationId = null;
    }
    if (analyser) {
        analyser = null;
    }
    // 캔버스 초기화
    const waveform = document.getElementById('waveform');
    const canvas = document.getElementById('waveformCanvas');
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    waveform.classList.add('d-none');
}

// 음성 녹음 초기화
async function initializeVoiceRecording() {
    console.info('Initializing voice recording...');
    const recordButton = document.getElementById('recordButton');
    const recordingResult = document.getElementById('recordingResult');
    const playPauseBtn = document.getElementById('playPauseBtn');
    const progressBar = document.getElementById('progressBar');
    const currentTimeSpan = document.getElementById('currentTime');
    const totalTimeSpan = document.getElementById('totalTime');
    const downloadRecordingBtn = document.getElementById('downloadRecordingBtn');
    const generateDocumentBtn = document.getElementById('generateDocumentBtn');
    const consultationText = document.getElementById('consultationText');

    let audioPlayer = null;


    // 버튼 상태 초기화
    function resetButtonStates() {
        recordButton.textContent = '녹음 시작';
        recordButton.classList.remove('recording');
        recordingResult.classList.add('hidden');
    }
}

async function generateDocument() {
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
            document.getElementById('consultationText').value = result.text;
            alert('음성이 텍스트로 성공적으로 변환되었습니다.');
        } else {
            const error = await response.json();
            alert(`텍스트 변환 오류: ${error.error}`);
        }
    } catch (error) {
        console.error('텍스트 생성 오류:', error);
        alert('텍스트 생성 중 오류가 발생했습니다.');
    }
};

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

function startNewSession() {
    // Clear any existing session data
    currentSessionId = null;
    selectedRating = 0;
}

// WebSocket을 사용하여 실시간 STT 스트리밍을 구현합니다.
async function startStreamingStt() {
    try {
        // WebSocket 연결
        console.log('Connecting to WebSocket:', wsUrl + '/stream-stt');
        ws = new WebSocket(wsUrl + '/stream-stt');

        ws.onmessage = (event) => {
            const response = JSON.parse(event.data);
            const consultationSection = document.getElementById('consultationSection');
            const consultationText = document.getElementById('consultationText');
            consultationSection.classList.toggle('hidden');
            
            if (response.type === 'interim' || response.type === 'final') {
                // 기존 텍스트가 있으면 줄바꿈 후 새 텍스트 추가
                if ( consultationText .value &&  consultationText .value.trim() !== '') {
                     consultationText .value += '\n';
                }
                 consultationText .value += response.text;
            } else if (response.type === 'error') {
                console.error('STT 오류:', response.error);
                alert(response.error);
            }
        };
        
        ws.onerror = (error) => {
            console.error('WebSocket 오류:', error);
            alert('음성 스트리밍 연결에 문제가 발생했습니다.');
        };
        
    } catch (error) {
        console.error('WebSocket 연결 오류:', error);
        alert('음성 스트리밍 연결을 시작할 수 없습니다.');
    }
}

async function stopStreamingStt() {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send('END_STREAM');
        ws.close();
        ws = null;
    }
}

// 음성 녹음 모달 관련 함수들
function handleVoiceRecording() {
    resetText();
    const voiceModal = new bootstrap.Modal(document.getElementById('voiceModal'));
    
    // 모달 표시 전 초기화
    resetVoiceModal();
    
    // 녹음 버튼 이벤트 리스너 재설정
    const recordButton = document.getElementById('recordButton');
    recordButton.onclick = toggleRecording;
    
    // 저장 버튼 이벤트 리스너 설정
    const saveButton = document.getElementById('saveVoiceButton');
    saveButton.onclick = async () => {

        try {
            if (audioBlob) {
                const formData = new FormData();
                formData.append('audio', audioBlob);
                
                // 로딩 표시
                const loadingModal = document.getElementById('loadingModal');
                loadingModal.classList.remove('hidden');
                
                // API 호출
                const response = await fetch(`${API_BASE_URL}/upload-audio`, {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${localStorage.getItem('token')}`
                    },
                    body: formData
                });
                
                if (!response.ok) {
                    throw new Error('음성 변환 실패');
                }
                
                const result = await response.json();
                
                // 3초 후 모달 닫기
                setTimeout(() => {
                    voiceModal.hide();
                    const backdrop = document.querySelector('.modal-backdrop');
                    if (backdrop) {
                        backdrop.remove();
                    }
                    // 변환된 텍스트를 상담 입력창에 추가
                    mainContent.classList.toggle('generate');
                    consultationSection.classList.toggle('hidden');
                    consultationText.value += (consultationText.value ? '\n\n' : '') + result.text;
                }, 3000);
            }
        } catch (error) {
            console.error('음성 변환 오류:', error);
            alert('음성 변환 중 오류가 발생했습니다.');
        } finally {
            // 로딩 모달 숨기기
            const loadingModal = document.getElementById('loadingModal');
            loadingModal.classList.add('hidden');
        }
    };
    
    // 모달 표시
    voiceModal.show();
}

// 녹음 시작/중지 함수
async function toggleRecording() {
    const recordButton = document.getElementById('recordButton');
    const recordingStatus = document.getElementById('recordingStatus');

    if (!mediaRecorder || mediaRecorder.state === 'inactive') {
        console.log("Starting recording...");
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            audioChunks = [];
            
            // 실시간 STT 스트리밍 시작
            await startStreamingStt();
            
            mediaRecorder = new MediaRecorder(stream);
            visualizeStream(stream);
            
            mediaRecorder.ondataavailable = async (event) => {
                if (event.data.size > 0) {
                    // WebSocket을 통해 오디오 데이터 전송
                    if (ws && ws.readyState === WebSocket.OPEN) {
                        ws.send(await event.data.arrayBuffer());
                    }
                    audioChunks.push(event.data);
                }
            };
            
            // 더 작은 시간 간격으로 데이터 전송
            mediaRecorder.start(1000);  // 1초마다 데이터 전송
            
            recordButton.classList.add('recording');
            recordingStatus.textContent = '녹음 중...';
            startRecordingTimer();
            
        } catch (error) {
            console.error('마이크 접근 오류:', error);
            alert('마이크 접근 권한이 필요합니다.');
        }
    } else {
        // 녹음 중지
        mediaRecorder.stop();
        mediaRecorder.stream.getTracks().forEach(track => track.stop());
        await stopStreamingStt();
        stopVisualization();
        
        recordButton.classList.remove('recording');
        recordingStatus.textContent = '녹음 완료';
        stopRecordingTimer();
    }
}

// 녹음 타이머 관련 함수들
function startRecordingTimer() {
    recordingDuration = 0;
    updateRecordingTime();
    recordingTimer = setInterval(updateRecordingTime, 1000);
}

function stopRecordingTimer() {
    if (recordingTimer) {
        clearInterval(recordingTimer);
        recordingTimer = null;
    }
}

function updateRecordingTime() {
    recordingDuration++;
    const minutes = Math.floor(recordingDuration / 60);
    const seconds = recordingDuration % 60;
    document.getElementById('recordingTime').textContent = 
        `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
}

// 음성 데이터 저장
function saveVoiceData() {
    // 녹음된 오디오나 업로드된 파일을 서버로 전송하는 로직
    console.log("saveVoiceData");
    let audioData;
    audioData = new Blob(audioChunks, { type: 'audio/wav' });
    if (audioData) {
        // TODO: 서버로 오디오 데이터 전송
        const modal = bootstrap.Modal.getInstance(document.getElementById('voiceModal'));
        modal.hide();
        
        // 모달 초기화
        resetVoiceModal();
    }
}

// 파일 업로드 처리
function handleAudioFileUpload() {
    resetText();
    // 모달 요소 가져오기
    const uploadModal = new bootstrap.Modal(document.getElementById('uploadModal'));
    const fileInput = document.getElementById('audioFileInput');
    const uploadButton = document.getElementById('uploadAudioButton');
    const uploadStatus = document.getElementById('uploadStatus');
    const mainContent = document.querySelector('.main-content')
    const consultationSection = document.getElementById('consultationSection');
    const consultationText = document.getElementById('consultationText');
    // 파일 선택 시 이벤트
    fileInput.onchange = (event) => {
        const file = event.target.files[0];
        if (file) {
            uploadStatus.textContent = `선택된 파일: ${file.name}`;
            uploadButton.disabled = false;
        } else {
            uploadStatus.textContent = '파일을 선택해주세요';
            uploadButton.disabled = true;
        }
    };
    
    // 업로드 버튼 클릭 이벤트
    uploadButton.onclick = async () => {
        const file = fileInput.files[0];
        if (!file) {
            alert('파일을 선택해주세요.');
            return;
        }

        try {
            // 로딩 상태 표시
            uploadStatus.textContent = '파일 업로드 중...';
            uploadButton.disabled = true;
            
            const formData = new FormData();
            formData.append('audio', file);
            
            // API 호출
            const response = await fetch(`${API_BASE_URL}/upload-audio`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                },
                body: formData
            });
            
            if (!response.ok) {
                throw new Error('음성 변환 실패');
            }
            
            const result = await response.json();
                
            // 성공 메시지 표시
            uploadStatus.textContent = '음성이 성공적으로 텍스트로 변환되었습니다.';
            
            // 3초 후 모달 닫기
            setTimeout(() => {
                uploadModal.hide();
                const backdrop = document.querySelector('.modal-backdrop');
                if (backdrop) {
                    backdrop.remove();
                }
                // 입력 초기화
                fileInput.value = '';
                uploadStatus.textContent = '';
                uploadButton.disabled = true;
                // 변환된 텍스트를 상담 입력창에 추가
                mainContent.classList.toggle('generate');
                consultationSection.classList.toggle('hidden');
                consultationText.value += (consultationText.value ? '\n\n' : '') + result.text;
            }, 3000);
            
        } catch (error) {
            console.error('파일 업로드 오류:', error);
            uploadStatus.textContent = '파일 업로드 중 오류가 발생했습니다.';
            uploadButton.disabled = false;
        }
    };
    uploadModal.show();
}


// 모달 초기화
function resetVoiceModal() {
    stopRecordingTimer();
    document.getElementById('recordingTime').textContent = '00:00';
    document.getElementById('recordingStatus').textContent = '녹음 대기중...';
    document.getElementById('recordButton').classList.remove('recording');
    document.getElementById('audioPreview').src = '';
    document.getElementById('audioPreview').classList.add('d-none');
    document.getElementById('audioFileInput').value = '';
    document.getElementById('uploadStatus').textContent = '';
    document.getElementById('uploadAudioButton').disabled = true;
    document.getElementById('waveform').classList.add('d-none');
    
    if (mediaRecorder) {
        mediaRecorder.stream.getTracks().forEach(track => track.stop());
        mediaRecorder = null;
    }

    audioChunks = [];
}

function copyToClipboard() {
    const textToCopy = document.getElementById('resultContent').innerText;
    navigator.clipboard.writeText(textToCopy);
    alert('클립보드에 복사되었습니다.');
}

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
    if (isRatingSubmitted) return;
    
    const feedback = document.getElementById('ratingFeedback').value;
    
    try {
        const response = await fetch('/api/submit_rating', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            },
            body: JSON.stringify({
                session_id: currentSessionId,
                rating: rating,
                feedback: feedback
            })
        });
        
        if (response.ok) {
            isRatingSubmitted = true;
            currentRating = rating;
            updateRatingUI(rating);
            document.querySelector('.rating-status').textContent = '평가가 제출되었습니다.';
        } else {
            throw new Error('평가 제출 실패');
        }
    } catch (error) {
        console.error('평가 제출 오류:', error);
        alert('평가 제출 중 오류가 발생했습니다.');
    }
}

// 평가 UI 업데이트
function updateRatingUI(rating) {
    const goodBtn = document.getElementById('goodRatingBtn');
    const badBtn = document.getElementById('badRatingBtn');
    
    goodBtn.disabled = isRatingSubmitted;
    badBtn.disabled = isRatingSubmitted;
    
    if (rating === 'good') {
        goodBtn.classList.add('selected');
        badBtn.classList.remove('selected');
    } else if (rating === 'bad') {
        badBtn.classList.add('selected');
        goodBtn.classList.remove('selected');
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

// 페이지 로드 시 초기화
document.addEventListener('DOMContentLoaded', () => {
    checkAuth();
    startNewSession();
    document.getElementById('username').textContent = localStorage.getItem('username');

    // 음성 녹음 기능 초기화
    if (document.getElementById('recordButton')) {
        initializeVoiceRecording();
    }
    // 녹음 버튼 이벤트
    // document.getElementById('recordButton').addEventListener('click', toggleRecording);
    // 파일 업로드 이벤트
    document.getElementById('audioFileInput').addEventListener('change', handleAudioFileUpload);
    // 저장 버튼 이벤트
    document.getElementById('saveVoiceButton').addEventListener('click', saveVoiceData);    
    // 모달 닫힐 때 초기화
    document.getElementById('voiceModal').addEventListener('hidden.bs.modal', resetVoiceModal);
    initializeAutoResize();
    
    // 평가 모달 이벤트
});