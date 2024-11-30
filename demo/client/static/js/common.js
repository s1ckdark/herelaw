// API 엔드포인트 설정
const API_BASE_URL = 'http://localhost:5000/api';
const ADMIN_API_URL = `${API_BASE_URL}/admin`;

// 인증 관련 유틸리티
const auth = {
    getToken() {
        return localStorage.getItem('token') || localStorage.getItem('authToken');
    },

    setToken(token) {
        localStorage.setItem('token', token);
    },

    removeToken() {
        localStorage.removeItem('token');
        localStorage.removeItem('authToken');
    },

    getUsername() {
        return localStorage.getItem('username');
    },

    setUsername(username) {
        localStorage.setItem('username', username);
    },

    removeUsername() {
        localStorage.removeItem('username');
    },

    isAuthenticated() {
        return !!this.getToken();
    },

    checkAuth() {
        if (!this.isAuthenticated()) {
            window.location.href = '/login';
            return false;
        }
        return true;
    },

    logout() {
        this.removeToken();
        this.removeUsername();
        window.location.href = '/';
    }
};

// 날짜 포맷 유틸리티
const dateUtils = {
    formatDate(dateString) {
        if (!dateString) return '날짜 정보 없음';
        
        try {
            const date = new Date(dateString);
            return date.toLocaleDateString('ko-KR', {
                year: 'numeric',
                month: 'long',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
        } catch (error) {
            console.error('날짜 포맷 오류:', error);
            return '날짜 형식 오류';
        }
    },

    formatTime(seconds) {
        if (isNaN(seconds) || seconds < 0) return '0:00';
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    }
};

// HTML 안전성 유틸리티
const htmlUtils = {
    escapeHtml(unsafe) {
        return unsafe
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    },

    getStatusBadge(status) {
        const statusClasses = {
            success: 'success',
            pending: 'warning',
            error: 'danger'
        };
        
        const statusClass = statusClasses[status.toLowerCase()] || 'secondary';
        return `<span class="badge badge-${statusClass}">${status}</span>`;
    }
};

// UI 메시지 유틸리티
const uiUtils = {
    showMessage(message, type = 'info') {
        const container = document.createElement('div');
        container.className = `message ${type}-message`;
        container.textContent = message;
        
        document.querySelector('.admin-content, .main-content')?.prepend(container);
        
        setTimeout(() => {
            container.remove();
        }, type === 'success' ? 3000 : 5000);
    },

    showSuccessMessage(message) {
        this.showMessage(message, 'success');
    },

    showErrorMessage(message) {
        this.showMessage(message, 'error');
    }
};

// API 요청 유틸리티
const apiUtils = {
    async fetchWithAuth(endpoint, options = {}) {
        const token = auth.getToken();
        const defaultHeaders = {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        };

        try {
            const response = await fetch(endpoint, {
                ...options,
                headers: {
                    ...defaultHeaders,
                    ...options.headers
                }
            });

            if (response.status === 401) {
                auth.logout();
                return null;
            }

            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                return await response.json();
            }

            return response;
        } catch (error) {
            console.error('API 요청 오류:', error);
            throw error;
        }
    }
};

// 패스워드 유틸리티
const passwordUtils = {
    generateTemporary() {
        return Math.random().toString(36).slice(-8);
    }
};

// 모듈 내보내기
export {
    API_BASE_URL,
    ADMIN_API_URL,
    auth,
    dateUtils,
    htmlUtils,
    uiUtils,
    apiUtils,
    passwordUtils
};
