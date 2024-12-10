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
    initializeAutoResize();
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
        
        // Clear the canvas instead of filling with grey
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
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
    // audioBlob이 없다면 에러 처리
    if (!audioBlob) {
        alert('변환할 음성 데이터가 없습니다.');
        return;
    }

    // FormData 객체 생성 및 오디오 데이터 추가
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
}

// 오디오 플레이어 초기화
function initializeAudioPlayer(audioBlob) {
    const audioPreview = document.getElementById('audioPreview');
    const recordedAudio = document.getElementById('recordedAudio');
    
    // 오디오 URL 생성 및 설정
    const audioUrl = URL.createObjectURL(audioBlob);
    recordedAudio.src = audioUrl;
    
    // 오디오 미리듣기 섹션 표시
    audioPreview.classList.remove('d-none');
    
    // 이전 URL 해제
    return () => {
        URL.revokeObjectURL(audioUrl);
    };
}

function startNewSession() {
    // Clear any existing session data
    currentSessionId = null;
    selectedRating = 0;
}

async function startStreamingStt() {
    try {
        console.log('[WebSocket] Attempting to connect to:', wsUrl + '/stream-stt');

        ws = new WebSocket(wsUrl + '/stream-stt');

        // WebSocket 상태를 정기적으로 체크하는 헬퍼
        const logWsState = () => {
            let stateStr = '';
            switch (ws.readyState) {
                case WebSocket.CONNECTING: stateStr = 'CONNECTING'; break;
                case WebSocket.OPEN: stateStr = 'OPEN'; break;
                case WebSocket.CLOSING: stateStr = 'CLOSING'; break;
                case WebSocket.CLOSED: stateStr = 'CLOSED'; break;
                default: stateStr = 'UNKNOWN'; break;
            }
            console.log(`[WebSocket] Current readyState: ${ws.readyState} (${stateStr})`);
        };

        // 주기적으로 상태 체크 (디버깅용, 필요 없으면 제거 가능)
        const intervalId = setInterval(() => {
            if (ws) logWsState();
        }, 5000);

        ws.onopen = () => {
            console.log('[WebSocket] Connection established (onopen)');
            logWsState();
        };

        ws.onmessage = (event) => {
            console.log('[WebSocket] Message received:', event.data);
            try {
                const response = JSON.parse(event.data);
                const consultationSection = document.getElementById('consultationSection');
                const consultationText = document.getElementById('consultationText');

                if (response.type === 'interim' || response.type === 'final') {
                    const currentText = consultationText.value.trim();
                    consultationText.value = currentText ? currentText + '\n' + response.text : response.text;
                    console.log(`[WebSocket] ${response.type} text appended to consultationText.`);
                } else if (response.type === 'error') {
                    console.error('[WebSocket] STT error received:', response.error);
                    alert(response.error);
                }
            } catch (parseError) {
                console.error('[WebSocket] JSON parse error:', parseError, 'Event data:', event.data);
            }
        };

        ws.onerror = (error) => {
            console.error('[WebSocket] onerror event triggered:', error);
            logWsState();
            alert('음성 스트리밍 연결에 문제가 발생했습니다. 콘솔 로그를 확인하세요.');
        };

        ws.onclose = (event) => {
            console.log(`[WebSocket] Connection closed: code=${event.code}, reason=${event.reason}`);
            logWsState();
            clearInterval(intervalId);

            // 1006은 비정상 종료 코드로, 서버측 오류나 네트워크 문제일 가능성이 높습니다.
            if (event.code === 1006) {
                console.warn('[WebSocket] Connection closed with 1006 - abnormal closure. Check server logs or network issues.');
            }
        };
        
    } catch (error) {
        console.error('[WebSocket] Connection error (startStreamingStt):', error);
        alert('음성 스트리밍 연결을 시작할 수 없습니다. 콘솔 로그를 확인하세요.');
    }
}

async function sendAudioData(audioData) {
    if (!ws || ws.readyState !== WebSocket.OPEN) {
        console.warn('[WebSocket] Attempted to send audio data when connection is not open. State:', ws ? ws.readyState : 'ws is null');
        return;
    }

    console.log('[WebSocket] Preparing to send audio data.');
    try {
        const buffer = await audioData.arrayBuffer();
        const chunkSize = 16 * 1024;
        const totalLength = buffer.byteLength;
        let offset = 0;

        console.log(`[WebSocket] Total audio data length: ${totalLength} bytes.`);

        while (offset < totalLength) {
            const chunk = buffer.slice(offset, Math.min(offset + chunkSize, totalLength));
            
            // 전송 전 상태 확인
            if (ws.readyState !== WebSocket.OPEN) {
                console.warn('[WebSocket] Connection closed during audio sending. Stopping transmission.');
                break;
            }

            ws.send(chunk);
            console.log(`[WebSocket] Sent chunk: ${chunk.byteLength} bytes, offset: ${offset}.`);

            offset += chunkSize;

            // 서버 부하 방지를 위한 잠시 대기
            await new Promise(resolve => setTimeout(resolve, 10));
        }

        console.log('[WebSocket] Audio data transmission completed.');
    } catch (error) {
        console.error('[WebSocket] Error sending audio data:', error);
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
            await saveVoiceData();
        } catch (error) {
            console.error('음성 저장 오류:', error);
            alert(error.message || '음성 저장 중 오류가 발생했습니다.');
        }
    };
    
    // 모달 표시
    voiceModal.show();
}

// 음성 데이터 저장
async function saveVoiceData() {
    try {
        // 녹음 중이라면 중지하고 Blob이 생성될 때까지 대기
        if (mediaRecorder && mediaRecorder.state === 'recording') {
            // Blob이 생성될 때까지 기다리는 Promise
            const waitForBlob = new Promise((resolve) => {
                mediaRecorder.onstop = () => {
                    audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
                    initializeAudioPlayer(audioBlob);
                    resolve();
                };
            });

            // 녹음 중지
            mediaRecorder.stop();
            mediaRecorder.stream.getTracks().forEach(track => track.stop());
            stopVisualization();
            
            const recordButton = document.getElementById('recordButton');
            recordButton.classList.remove('recording');
            document.getElementById('recordingStatus').textContent = '녹음 완료';
            stopRecordingTimer();
            
            // Blob이 생성될 때까지 대기
            await waitForBlob;
        }

        // audioBlob이 없으면 에러
        if (!audioBlob) {
            throw new Error('녹음된 음성이 없습니다.');
        }

        // WAV 형식으로 명시적 변환
        const wavFile = new File([audioBlob], 'recording.wav', {
            type: 'audio/wav'
        });
        
        // 로딩 표시
        const loadingModal = document.getElementById('loadingModal');
        loadingModal.classList.remove('hidden');
        
        console.log('Uploading audio file:', wavFile); // 디버깅용

        await handleAudioUpload(wavFile, 'voice');
        
    } catch (error) {
        console.error('음성 변환 오류:', error);
        throw error; // 상위 호출자에게 에러를 전파
    }
}

// 녹음 시작/중지 함수
async function toggleRecording() {
    const recordButton = document.getElementById('recordButton');
    const recordingStatus = document.getElementById('recordingStatus');
    const audioPreview = document.getElementById('audioPreview');

    if (!mediaRecorder || mediaRecorder.state === 'inactive') {
        // 녹음 시작 시 오디오 미듣기 숨기기
        audioPreview.classList.add('d-none');
        
        console.log("Starting recording...");
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            audioChunks = [];
            
            mediaRecorder = new MediaRecorder(stream);
            visualizeStream(stream);
            
            mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    audioChunks.push(event.data);
                }
            };
            
            mediaRecorder.onstop = () => {
                audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
                initializeAudioPlayer(audioBlob);
            };
            
            mediaRecorder.start(1000);
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

// 파일 업로드 처리
function handleAudioFileUpload() {
    resetText();
    // 모달 요소 가져오기
    const uploadModal = new bootstrap.Modal(document.getElementById('uploadModal'));
    const fileInput = document.getElementById('audioFileInput');
    const uploadButton = document.getElementById('uploadAudioButton');
    const uploadStatus = document.getElementById('uploadStatus');
    

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
        await handleAudioUpload(file, 'upload');
    };
    
    // 모달 표시
    uploadModal.show();
}

// 음성 파일 업로드 및 처리 함수
const handleAudioUpload = async (file, type = 'upload') => {
    if (!file) {
        alert('파일을 선택해주세요.');
        return;
    }

    try {
        const fileInput = document.getElementById('audioFileInput');
        const uploadStatus = document.getElementById('uploadStatus');
        const progressBar = type === 'upload' ? 
            document.getElementById('uploadProgress').querySelector('.progress-bar') :
            document.getElementById('voiceProgress').querySelector('.progress-bar');
        const progressDiv = type === 'upload' ? 
            document.getElementById('uploadProgress') :
            document.getElementById('voiceProgress');
        const progressStatus = type === 'upload' ? 
            document.getElementById('uploadProgressStatus') :
            document.getElementById('voiceProgressStatus');
        
        // 초기화
        progressDiv.classList.remove('d-none');
        progressStatus.classList.remove('d-none');
        progressBar.style.width = '0%';
        progressBar.setAttribute('aria-valuenow', 0);
        progressStatus.textContent = '파일 업로드 준비 중...';
        
        if (type === 'upload') {
            uploadStatus.textContent = '파일 업로드 중...';
            const uploadButton = document.getElementById('uploadAudioButton');
            uploadButton.disabled = true;
        }
        
        const formData = new FormData();
        formData.append('audio', file);
        
        // XMLHttpRequest 사용하여 진행률 표시
        const xhr = new XMLHttpRequest();
        
        // 업로드 진행률 업데이트를 더 부드럽게 처리
        let lastProgress = 0;
        const updateProgress = (current) => {
            const step = (current - lastProgress) / 10;
            let currentProgress = lastProgress;
            
            const animate = () => {
                currentProgress += step;
                if (current >= lastProgress && currentProgress <= current) {
                    progressBar.style.width = currentProgress + '%';
                    progressBar.setAttribute('aria-valuenow', currentProgress);
                    progressStatus.textContent = `업로드 중... ${Math.round(currentProgress)}%`;
                    requestAnimationFrame(animate);
                }
            };
            requestAnimationFrame(animate);
            lastProgress = current;
        };
        
        xhr.upload.onprogress = (event) => {
            if (event.lengthComputable) {
                const percentComplete = (event.loaded / event.total) * 100;
                updateProgress(percentComplete);
            }
        };
        
        const response = await new Promise((resolve, reject) => {
            xhr.onload = () => {
                if (xhr.status >= 200 && xhr.status < 300) {
                    updateProgress(100);
                    progressStatus.textContent = '음성 변환 중...';
                    resolve(JSON.parse(xhr.responseText));
                } else {
                    reject(new Error('업로드 실패'));
                }
            };
            
            xhr.onerror = () => reject(new Error('네트워크 오류'));
            
            xhr.open('POST', `${API_BASE_URL}/upload-audio`);
            xhr.setRequestHeader('Authorization', `Bearer ${localStorage.getItem('token')}`);
            xhr.send(formData);
        });
        
        // 성공 메시지 표시
        progressStatus.textContent = '음성이 성공적으로 텍스트로 변환되었습니다.';
        
        // 3초 후 모달 닫기
        setTimeout(() => {
            const uploadModal = bootstrap.Modal.getInstance(document.getElementById('uploadModal'));
            const voiceModal = bootstrap.Modal.getInstance(document.getElementById('voiceModal'));
            
            // 모달 타입에 따라 적절한 모달 닫기
            if (type === 'upload' && uploadModal) {
                uploadModal.hide();
                fileInput.value = '';
                uploadStatus.textContent = '';
                const uploadButton = document.getElementById('uploadAudioButton');
                uploadButton.disabled = true;
            } else if (type === 'voice' && voiceModal) {
                voiceModal.hide();
            }
    
            const backdrop = document.querySelector('.modal-backdrop');
            if (backdrop) {
                backdrop.remove();
            }
            
            // 변환된 텍스트를 상담 입력창에 추가
            const mainContent = document.querySelector('.main-content');
            const consultationSection = document.getElementById('consultationSection');
            const consultationText = document.getElementById('consultationText');
            if (mainContent && consultationSection && consultationText) {
                mainContent.classList.toggle('generate');
                consultationSection.classList.toggle('hidden');
                consultationText.value += (consultationText.value ? '\n\n' : '') + response.text;
            }
            
            // 프로그레스 바 초기화 및 숨기기
            progressDiv.classList.add('d-none');
            progressStatus.classList.add('d-none');
            progressBar.style.width = '0%';
            
        }, 3000);
        
    } catch (error) {
        console.error('파일 업로드 오류:', error);
        const uploadStatus = document.getElementById('uploadStatus');
        uploadStatus.textContent = '파일 업로드 중 오류가 발생했습니다.';
        console.error('상세 오류:', error);
        
        const progressStatus = type === 'upload' ? 
            document.getElementById('uploadProgressStatus') :
            document.getElementById('voiceProgressStatus');
        progressStatus.textContent = '업로드 실패';
        
        if (type === 'upload') {
            const uploadButton = document.getElementById('uploadAudioButton');
            uploadButton.disabled = false;
        }
    }
};

// 모달 초기화
function resetVoiceModal() {
    stopRecordingTimer();
    
    const recordingTimeEl = document.getElementById('recordingTime');
    const recordingStatusEl = document.getElementById('recordingStatus');
    const recordButton = document.getElementById('recordButton');
    const audioPreview = document.getElementById('audioPreview');
    const recordedAudio = document.getElementById('recordedAudio');
    const waveform = document.getElementById('waveform');
    
    // 각 요소 초기화
    if (recordingTimeEl) recordingTimeEl.textContent = '00:00';
    if (recordingStatusEl) recordingStatusEl.textContent = '녹음 대기중...';
    if (recordButton) recordButton.classList.remove('recording');
    if (audioPreview) audioPreview.classList.add('d-none');
    if (recordedAudio) recordedAudio.src = '';
    if (waveform) waveform.classList.add('d-none');
    
    // 미디어 리소스 정리
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        mediaRecorder.stream.getTracks().forEach(track => track.stop());
        mediaRecorder = null;
    }

    audioChunks = [];
    audioBlob = null;
}

function copyToClipboard() {
    const textToCopy = document.getElementById('resultContent').innerText;
    navigator.clipboard.writeText(textToCopy);
    alert('클립보드에 사되었습니다.');
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
        console.error('평가 이터 로딩 실패:', error);
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
    
});