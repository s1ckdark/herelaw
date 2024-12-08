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
        
        // 서버 응답이 JSON이 아닐 수 있으므로 체크
        const contentType = response.headers.get('content-type');
        let data;
        if (contentType && contentType.includes('application/json')) {
            data = await response.json();
        } else {
            throw new Error('서버에서 JSON 응답이 오지 않았습니다.');
        }
        
        if (response.ok) {
            localStorage.setItem('token', data.token);
            localStorage.setItem('username', username);
            window.location.href = '/generate.html';
        } else {
            alert(`로그인 실패: ${data.message || '알 수 없는 오류가 발생했습니다.'}`);
        }
    } catch (error) {
        alert('로그인 중 오류가 발생했습니다: ' + error.message);
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

// 인증 확인
function checkAuth() {
    const token = localStorage.getItem('token');
    if (token) {
        window.location.href = '/generate.html';
        return;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    checkAuth();
});
