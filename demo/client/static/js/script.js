// API 엔드포인트
const API_BASE_URL = 'http://localhost:5000/api';

// 폼 전환 함수
function toggleForm(formType) {
    const loginForm = document.getElementById('loginForm');
    const signupForm = document.getElementById('signupForm');
    
    if (formType === 'signup') {
        loginForm.classList.add('hidden');
        signupForm.classList.remove('hidden');
    } else {
        signupForm.classList.add('hidden');
        loginForm.classList.remove('hidden');
    }
}

// 로그인 처리
document.getElementById('login').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const username = document.getElementById('loginUsername').value;
    const password = document.getElementById('loginPassword').value;
    
    try {
        const response = await fetch(`${API_BASE_URL}/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ username, password }),
        });
        
        const data = await response.json();
        
        if (response.ok) {
            localStorage.setItem('token', data.token);
            window.location.href = '/dashboard.html';  // 로그인 성공 시 대시보드로 이동
        } else {
            alert('로그인 실패: ' + data.message);
        }
    } catch (error) {
        alert('로그인 중 오류가 발생했습니다.');
        console.error('Error:', error);
    }
});

// 회원가입 처리
document.getElementById('signup').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const username = document.getElementById('signupUsername').value;
    const password = document.getElementById('signupPassword').value;
    const confirmPassword = document.getElementById('confirmPassword').value;
    
    if (password !== confirmPassword) {
        alert('비밀번호가 일치하지 않습니다.');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/register`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ username, password }),
        });
        
        const data = await response.json();
        
        if (response.ok) {
            alert('회원가입이 완료되었습니다. 로그인해주세요.');
            toggleForm('login');
        } else {
            alert('회원가입 실패: ' + data.message);
        }
    } catch (error) {
        alert('회원가입 중 오류가 발생했습니다.');
        console.error('Error:', error);
    }
});
