# 이혼 소장 작성 도우미

이 프로젝트는 이혼 소장 작성을 도와주는 AI 기반 웹 애플리케이션입니다. 클라이언트-서버 아키텍처를 사용하여 구현되었습니다.

## 구조

프로젝트는 다음과 같이 구성되어 있습니다:

```
rag/
├── client/
│   ├── app_streamlit.py    # Streamlit 기반 프론트엔드
│   └── requirements.txt    # 클라이언트 의존성
├── server/
│   ├── app.py             # Flask 기반 백엔드
│   └── requirements.txt    # 서버 의존성
└── README.md
```

## 설치 방법

1. 서버 설치:
```bash
cd server
pip install -r requirements.txt
```

2. 클라이언트 설치:
```bash
cd client
pip install -r requirements.txt
```

## 환경 변수 설정

서버에서 사용할 환경 변수를 `server/.env` 파일에 설정해야 합니다:

```
OPENAI_API_KEY=your_openai_api_key
MONGO_URI=your_mongodb_uri
LANGCHAIN_API_KEY=your_langchain_api_key
LANGCHAIN_PROJECT=your_project_name
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
```

## 실행 방법

1. 서버 실행:
```bash
cd server
python app.py
```

2. 클라이언트 실행 (새 터미널에서):
```bash
cd client
streamlit run app_streamlit.py
```

## 기능

- 사용자 인증 (로그인/로그아웃)
- 상담 내용 입력 및 소장 생성
- 생성된 소장 평가 및 피드백
- 상담 기록 조회
- 음성 상담 (개발 중)

## API 엔드포인트

서버는 다음과 같은 API 엔드포인트를 제공합니다:

- POST `/api/generate-complaint`: 소장 생성
- POST `/api/save-feedback`: 피드백 저장
- GET `/api/feedback-statistics`: 피드백 통계 조회
- POST `/api/upload-audio`: 음성 파일 업로드 및 변환
