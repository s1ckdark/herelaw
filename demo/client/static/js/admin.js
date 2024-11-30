// API 엔드포인트
const API_BASE_URL = 'http://localhost:5000/api/admin';

// 전역 변수
let currentUserId = null;
let currentPage = 1;
let itemsPerPage = 10;

// 유틸리티 함수들
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('ko-KR', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function escapeHtml(unsafe) {
    return unsafe
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function getStatusBadge(status) {
    const statusClasses = {
        success: 'success',
        pending: 'warning',
        error: 'danger'
    };
    
    const statusClass = statusClasses[status.toLowerCase()] || 'secondary';
    return `<span class="badge badge-${statusClass}">${status}</span>`;
}

function getAuthToken() {
    return localStorage.getItem('authToken');
}

function generateTemporaryPassword() {
    return Math.random().toString(36).slice(-8);
}

// 페이지 로드 시 초기화
document.addEventListener('DOMContentLoaded', () => {
    checkAuth();
    loadDashboardData();
    highlightCurrentMenu();
    setupEventListeners();
    
    // 사용자 관리 페이지인 경우 사용자 목록 로드
    if (window.location.pathname.includes('/admin/users')) {
        loadUsers();
    }
});

// 인증 확인
function checkAuth() {
    const token = getAuthToken();
    if (!token) {
        window.location.href = '/login';
        return;
    }
}

// 메시지 표시 함수들
function showSuccessMessage(message) {
    showMessage(message, 'success-message');
}

function showErrorMessage(message) {
    showMessage(message, 'error-message');
}

function showMessage(message, className) {
    const container = document.createElement('div');
    container.className = className;
    container.textContent = message;
    
    document.querySelector('.admin-content').prepend(container);
    
    setTimeout(() => {
        container.remove();
    }, className.includes('success') ? 3000 : 5000);
}

// 대시보드 데이터 로드
async function loadDashboardData() {
    try {
        // 통계 데이터 로드
        const statsResponse = await fetch('/api/admin/statistics');
        const statsData = await statsResponse.json();
        
        updateStatistics(statsData);
        
        // 최근 활동 데이터 로드
        const activitiesResponse = await fetch('/api/admin/recent-activities');
        const activitiesData = await activitiesResponse.json();
        
        updateRecentActivities(activitiesData);
    } catch (error) {
        console.error('데이터 로드 중 오류 발생:', error);
        showErrorMessage('데이터를 불러오는 중 오류가 발생했습니다.');
    }
}

// 통계 업데이트
function updateStatistics(data) {
    document.getElementById('totalUsers').textContent = data.totalUsers.toLocaleString();
    document.getElementById('totalPosts').textContent = data.totalPosts.toLocaleString();
    document.getElementById('totalComments').textContent = data.totalComments.toLocaleString();
}

// 최근 활동 테이블 업데이트
function updateRecentActivities(activities) {
    const tbody = document.getElementById('recentActivities');
    tbody.innerHTML = '';
    
    activities.forEach(activity => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${formatDate(activity.date)}</td>
            <td>${escapeHtml(activity.user)}</td>
            <td>${escapeHtml(activity.action)}</td>
            <td>${getStatusBadge(activity.status)}</td>
        `;
        tbody.appendChild(tr);
    });
}

// 현재 메뉴 하이라이트
function highlightCurrentMenu() {
    const currentPath = window.location.pathname;
    const menuLinks = document.querySelectorAll('.admin-menu a');
    
    menuLinks.forEach(link => {
        if (link.getAttribute('href') === currentPath) {
            link.classList.add('active');
        }
    });
}

// 이벤트 리스너 설정
function setupEventListeners() {
    // 새로고침 버튼 이벤트 (있는 경우)
    const refreshButton = document.getElementById('refreshData');
    if (refreshButton) {
        refreshButton.addEventListener('click', loadDashboardData);
    }
    
    // 사용자 관리 이벤트
    document.addEventListener('click', async (e) => {
        if (e.target.classList.contains('edit-user')) {
            const userId = e.target.dataset.id;
            // 사용자 편집 모달 표시 로직
            showEditUserModal(userId);
        }
        
        if (e.target.classList.contains('reset-password')) {
            const userId = e.target.dataset.id;
            if (confirm('해당 사용자의 비밀번호를 초기화하시겠습니까?')) {
                await resetUserPassword(userId);
            }
        }
    });
}

// 사용자 목록 로드 및 표시
async function loadUsers() {
    try {
        const response = await fetch('/api/admin/users', {
            headers: {
                'Authorization': `Bearer ${getAuthToken()}`
            }
        });
        const users = await response.json();
        
        updateUsersTable(users);
    } catch (error) {
        console.error('사용자 목록 로드 중 오류:', error);
        showErrorMessage('사용자 목록을 불러오는 중 오류가 발생했습니다.');
    }
}

// 사용자 테이블 업데이트
function updateUsersTable(users) {
    const tbody = document.getElementById('usersList');
    if (!tbody) return;
    
    tbody.innerHTML = '';
    
    users.forEach(user => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${escapeHtml(user.username)}</td>
            <td>${escapeHtml(user.email)}</td>
            <td>${escapeHtml(user.role)}</td>
            <td>${escapeHtml(user.status)}</td>
            <td>
                <button class="btn btn-sm btn-primary edit-user" data-id="${user._id}">수정</button>
                <button class="btn btn-sm btn-warning reset-password" data-id="${user._id}">비밀번호 초기화</button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

// 사용자 정보 업데이트
async function updateUser(userId, userData) {
    try {
        const response = await fetch(`/api/admin/users/${userId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getAuthToken()}`
            },
            body: JSON.stringify(userData)
        });
        
        if (!response.ok) throw new Error('사용자 정보 업데이트 실패');
        
        showSuccessMessage('사용자 정보가 업데이트되었습니다.');
        loadUsers(); // 목록 새로고침
    } catch (error) {
        console.error('사용자 정보 업데이트 중 오류:', error);
        showErrorMessage('사용자 정보 업데이트 중 오류가 발생했습니다.');
    }
}

// 사용자 비밀번호 초기화
async function resetUserPassword(userId) {
    try {
        const response = await fetch(`/api/admin/users/${userId}/reset-password`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getAuthToken()}`
            },
            body: JSON.stringify({
                new_password: generateTemporaryPassword() // 임시 비밀번호 생성
            })
        });
        
        if (!response.ok) throw new Error('비밀번호 초기화 실패');
        
        showSuccessMessage('비밀번호가 초기화되었습니다.');
    } catch (error) {
        console.error('비밀번호 초기화 중 오류:', error);
        showErrorMessage('비밀번호 초기화 중 오류가 발생했습니다.');
    }
}

// 사용자 활동 로그 조회
async function getUserLogs(userId) {
    try {
        const response = await fetch(`/api/admin/users/${userId}/logs`, {
            headers: {
                'Authorization': `Bearer ${getAuthToken()}`
            }
        });
        const logs = await response.json();
        
        updateLogsTable(logs);
    } catch (error) {
        console.error('사용자 로그 조회 중 오류:', error);
        showErrorMessage('사용자 로그를 불러오는 중 오류가 발생했습니다.');
    }
}

// 로그 테이블 업데이트
function updateLogsTable(logs) {
    const tbody = document.getElementById('userLogs');
    if (!tbody) return;
    
    tbody.innerHTML = '';
    
    logs.forEach(log => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${formatDate(log.created_at)}</td>
            <td>${escapeHtml(log.action)}</td>
            <td>${escapeHtml(log.details || '-')}</td>
        `;
        tbody.appendChild(tr);
    });
} 