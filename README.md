# LymphHub

LymphHub는 Keycloak과 Traefik을 활용한 중앙 집중식 인증 관리 서비스입니다.
다양한 마이크로서비스에 대한 Single Sign-On (SSO)을 제공하며, `forwardauth` 미들웨어를 통해 Traefik 레벨에서 요청을 검증하고, Keycloak OIDC 토큰을 관리합니다.

## Project Structure

- **backend/**: FastAPI 기반의 인증 처리 백엔드 서비스.
- **frontend/**: Next.js 기반의 프론트엔드 애플리케이션 (상태 대시보드 및 로그인 UI 등).
- **infrastructure/**: Docker Compose 및 환경 설정을 포함한 인프라 구성 파일.

## Prerequisites

- **Docker** & **Docker Compose**
- **Node.js** (v18+ recommended)
- **Python** (v3.10+ recommended)

---


---

## Quick Start (Docker Compose)

가장 빠르게 LymphHub의 모든 서비스(Frontend, Backend)를 실행하려면 Docker Compose를 사용하세요.

1. `infrastructure` 디렉토리로 이동하여 환경 설정 파일을 준비합니다.
   ```bash
   cd infrastructure
   cp .env.example .env
   ```
   `.env` 파일을 열어 `LYMPHHUB_PUBLIC_URL`(백엔드)과 `LYMPHHUB_FRONTEND_URL`(프론트엔드) 등을 본인의 환경에 맞게 수정합니다.

2. 서비스를 실행합니다.
   ```bash
   docker-compose up -d --build
   ```
   
   실행 후 브라우저에서 `LYMPHHUB_FRONTEND_URL`로 설정한 주소로 접속하면 프론트엔드 대시보드를 확인할 수 있습니다.

---

## Setup Guide

### 1. Backend Setup (Local Development)

백엔드는 Python FastAPI로 작성되었습니다. 로컬에서 실행하기 위해 다음 단계를 따르세요.

1. `backend` 디렉토리로 이동합니다.
   ```bash
   cd backend
   ```

2. 가상 환경을 생성하고 활성화합니다 (권장).
   ```bash
   python -m venv venv
   source venv/bin/activate  # macOS/Linux
   # .\venv\Scripts\activate  # Windows
   ```

3. 의존성 패키지를 설치합니다.
   ```bash
   pip install -r requirements.txt
   ```

4. 개발 서버를 실행합니다.
   ```bash
   uvicorn main:app --reload --port 8000
   ```
   서버가 `http://localhost:8000`에서 실행됩니다.

&nbsp;

### 2. Frontend Setup (Local Development)

프론트엔드는 Next.js 16과 TailwindCSS 4로 구성되어 있습니다.

1. `frontend` 디렉토리로 이동합니다.
   ```bash
   cd frontend
   ```

2. 의존성 패키지를 설치합니다.
   ```bash
   npm install
   ```

3. 개발 서버를 실행합니다.
   ```bash
   npm run dev
   ```
   애플리케이션이 `http://localhost:3000`에서 실행됩니다.

---

## Intrastructure & Docker Compose

LymphHub 백엔드 서비스를 Docker 컨테이너로 실행하고 Traefik과 연동하려면 `infrastructure` 디렉토리의 설정을 사용합니다.

### 1. Environment Configuration

`infrastructure` 디렉토리 내의 `.env.example` 파일을 복사하여 `.env` 파일을 생성하고, 필요한 Keycloak 및 도메인 설정을 입력하세요.

```bash
cd infrastructure
cp .env.example .env
vi .env
```

**필수 환경 변수:**
- `KEYCLOAK_URL`: Keycloak 서버 주소
- `KEYCLOAK_REALM`: 사용할 Realm 이름
- `KEYCLOAK_CLIENT_ID`: Keycloak Client ID
- `KEYCLOAK_CLIENT_SECRET`: Keycloak Client Secret
- `LYMPHHUB_PUBLIC_URL`: 백엔드 API 서비스 도메인 (예: `api.auth.yourdomain.com`)
- `LYMPHHUB_FRONTEND_URL`: 프론트엔드 서비스 도메인 (예: `auth.yourdomain.com`)

### 2. Run with Docker Compose

설정이 완료되면 다음 명령어로 서비스를 실행합니다.

```bash
docker-compose up -d --build
```

이 명령어는 `backend`와 `frontend` 디렉토리의 내용을 기반으로 Docker 이미지를 빌드하고 컨테이너를 실행합니다.
서비스는 `traefik-net` 네트워크에 연결되며, 설정된 도메인을 통해 접근할 수 있게 됩니다.
