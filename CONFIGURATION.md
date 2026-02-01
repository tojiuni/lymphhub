# LymphHub Configuration Guide

This guide details the integration of LymphHub with `lyckabc.xyz` domain, Keycloak (Realm: `toji`), and **Caddy** for reverse proxy and auth management (Traefik is not used).

## 1. Domain & Network Architecture
- **Domain**: `lyckabc.xyz`
- **Services**:
  - Auth: `https://auth.lyckabc.xyz` (Keycloak)
  - LymphHub API: `https://lymphhub.lyckabc.xyz` (Auth Manager)
  - Protected App: `https://todo.lyckabc.xyz` (Example)
- **Docker Networks**:
  - `traefik-net`: External network for Traefik to route traffic.
  - `neunexus_network`: Internal network for service-to-service communication.

## 2. Pre-requisites
Before deploying, ensure the following Docker networks exist:
```bash
docker network create traefik-net
docker network create neunexus_network
```

## 3. Authelia 설치 가이드 (Standalone)

Authelia는 `data/authelia/config` 와 `data/authelia/secrets` 를 사용하며, PostgreSQL 을 저장소로 사용한다. 외부 네트워크 `neunexus_network` (bridge) 가 필요하다.

### 3.1 디렉터리 구조

- **설정**: `data/authelia/config/configuration.yml` (실제 설정 파일)
- **시크릿**: `data/authelia/secrets/` 아래 다음 파일이 있어야 한다.
  - `JWT_SECRET` — identity validation reset password JWT 시크릿
  - `SESSION_SECRET` — 세션 시크릿
  - `STORAGE_PASSWORD` — PostgreSQL 비밀번호 (DB 사용자 비밀번호)
  - `STORAGE_ENCRYPTION_KEY` — 저장소 암호화 키 (20자 이상, 64자 이상 권장)

### 3.2 초기 설정

1. **설정 파일 생성**
   ```bash
   cd lymphhub
   cp data/authelia/config/configuration.yml.example data/authelia/config/configuration.yml
   cp data/authelia/config/users_database.yml.example data/authelia/config/users_database.yml
   ```

2. **configuration.yml 수정**
   - `storage.postgres`: `address`, `database`, `username` 를 사용 중인 PostgreSQL 에 맞게 수정 (비밀번호는 시크릿 파일로만 설정).
   - `access_control.rules`, `session.cookies` 의 도메인을 실제 도메인으로 변경 (예: `example.com` → `toji.homes`).

3. **시크릿 파일 생성** (`data/authelia/secrets/` 에 생성)
   - **자동 생성**: `deploy_and_verify.sh` 실행 시 시크릿 디렉터리가 없거나 파일이 비어 있으면 자동으로 생성한다.  
     `JWT_SECRET`, `SESSION_SECRET`, `STORAGE_ENCRYPTION_KEY` 는 랜덤 값으로 채우고, `STORAGE_PASSWORD` 는 `.env` 의 `DB_PASSWORD` 가 있으면 그 값으로, 없으면 랜덤으로 채운 뒤 경고를 남긴다.
   - **수동 생성** (필요 시):
   ```bash
   mkdir -p data/authelia/secrets
   # 64자 이상 랜덤 문자열 권장 (예: openssl rand -base64 48)
   echo -n 'YOUR_JWT_SECRET_64CHARS_OR_MORE'       > data/authelia/secrets/JWT_SECRET
   echo -n 'YOUR_SESSION_SECRET_64CHARS_OR_MORE' > data/authelia/secrets/SESSION_SECRET
   echo -n 'YOUR_POSTGRES_PASSWORD'               > data/authelia/secrets/STORAGE_PASSWORD
   echo -n 'YOUR_STORAGE_ENCRYPTION_KEY_64CHARS'  > data/authelia/secrets/STORAGE_ENCRYPTION_KEY
   chmod 600 data/authelia/secrets/*
   ```
   - `STORAGE_PASSWORD`: PostgreSQL 사용자 비밀번호 (`.env` 의 `DB_PASSWORD` 와 동일하게 설정 가능).
   - `STORAGE_ENCRYPTION_KEY`: 20자 이상 필수, 64자 이상 랜덤 문자열 권장.

4. **users_database.yml**  
   Authelia 사용자 비밀번호는 해시로 저장한다. 비밀번호 해시 생성:
   ```bash
   docker run --rm authelia/authelia:latest authelia crypto hash generate argon2 --password 'your_password'
   ```
   생성된 해시를 `users_database.yml` 의 해당 사용자 `password` 에 넣는다.

### 3.3 Docker Compose (볼륨·시크릿)

- **볼륨**
  - `./data/authelia/config` → `/config`
  - `./data/authelia/secrets` → `/secrets`
- **환경 변수** (시크릿 파일 경로)
  - `AUTHELIA_IDENTITY_VALIDATION_RESET_PASSWORD_JWT_SECRET_FILE=/secrets/JWT_SECRET`
  - `AUTHELIA_SESSION_SECRET_FILE=/secrets/SESSION_SECRET`
  - `AUTHELIA_STORAGE_POSTGRES_PASSWORD_FILE=/secrets/STORAGE_PASSWORD`
  - `AUTHELIA_STORAGE_ENCRYPTION_KEY_FILE=/secrets/STORAGE_ENCRYPTION_KEY`
- **포트**: 호스트에서 프록시(Caddy/Traefik) 등이 접속할 수 있도록 `127.0.0.1:9091:9091` 노출.

### 3.4 동작 확인

- 컨테이너 기동 후: `curl -s http://127.0.0.1:9091` 로 응답 확인.
- 설정 검증: `docker exec authelia authelia validate-config --config /config/configuration.yml`

**PostgreSQL 연결 간단 확인** (storage unreachable 경고가 날 때):
1. 같은 네트워크에 있는지: `docker network inspect neunexus_network --format '{{range .Containers}}{{.Name}} {{end}}'` → `authelia`, `neunexus_postgres_db` 등이 나와야 함.
2. 호스트에서 Postgres 포트: `nc -zv 127.0.0.1 54311` (또는 `.env` 의 `DB_PORT`) → 포트가 열려 있으면 OK.
3. 컨테이너→Postgres TCP: `docker run --rm --network neunexus_network busybox nc -zv neunexus_postgres_db 5432` → `open` 이면 Authelia도 같은 네트워크에서 접속 가능.

---

## 4. Keycloak Manual Configuration
You must configure Keycloak manually via the Admin Console (`https://auth.lyckabc.xyz`).

1.  **Create Realm**:
    *   Name: `toji`
2.  **Create Client**:
    *   Client ID: `lymphhub-portal`
    *   Client Protocol: `openid-connect`
    *   Access Type: `confidential` (Client Secret required)
    *   **Valid Redirect URIs**:
        *   `https://lymphhub.lyckabc.xyz/api/callback`
    *   **Web Origins**:
        *   `https://todo.lyckabc.xyz`
        *   `+` (or `https://lymphhub.lyckabc.xyz`)
3.  **Get Client Secret**:
    *   Go to *Credentials* tab and copy the secret.
    *   Update `KEYCLOAK_CLIENT_SECRET` in `infrastructure/.env`.

## 5. Caddy Configuration (Reverse Proxy & Auth)
LymphHub uses **Caddy** (not Traefik) for reverse proxy and auth management. Caddy 설정은 `data/caddy/` 및 관련 Dockerfile/볼륨을 참고한다.  
Authelia는 `192.168.0.88:9091` (또는 compose에 정의된 포트)에서 동작하며, Caddy가 해당 백엔드로 프록시·인증을 처리한다.

**SSL 인증서 (`*.$DOMAIN`)**: Caddy가 **자동으로** 처리한다. `config/caddy/Caddyfile`의 `*.{$DOMAIN}` 블록과 `tls { dns cloudflare {$CF_API_TOKEN} }` 설정으로 Let's Encrypt(ACME) + Cloudflare DNS challenge를 사용해 와일드카드 인증서를 발급·갱신한다. 별도의 "Generating SSL certificate" 단계는 필요 없으며, `.env`에 `DOMAIN`, `EMAIL`, `CF_API_TOKEN`만 맞추면 된다. 인증서는 Caddy가 `./data/.caddy` 볼륨에 저장한다.

*(Traefik 사용 시 참고: LymphHub 인증 미들웨어는 `infrastructure/docker-compose.yaml` 의 `lymphhub-auth` 등으로 정의할 수 있으나, 본 구성은 Caddy 기준이다.)*

## 6. Headscale (Tailscale 호환)

Headscale 설정은 `lymphhub/config/headscale/config.yaml` 에서 직접 수정한다.

- **볼륨**: `./config/headscale` → `/etc/headscale`, `./data/headscale` → `/var/lib/headscale`, `./data/headscale/run` → `/var/run/headscale`
- **설정**: `server_url`, `base_domain` 을 실제 도메인으로 수정 (Caddy 리버스프록시 사용 시 `https://headscale.<도메인>`)
- **동작 확인**: `curl http://192.168.0.88:9090/metrics` (호스트에서 metrics 포트 9090)

**사용자 생성**:
```bash
docker exec -it headscale headscale users create myfirstuser
```

**기기 등록 (노드 키로)**:
```bash
tailscale up --login-server https://headscale.<YOUR_DOMAIN>
# 그 다음 컨테이너에서:
docker exec -it headscale headscale nodes register --user myfirstuser --key <YOUR_MACHINE_KEY>
```

**Pre-auth 키로 등록**:
```bash
docker exec -it headscale headscale preauthkeys create --user myfirstuser --reusable --expiration 24h
# 클라이언트에서:
tailscale up --login-server https://headscale.<YOUR_DOMAIN> --authkey <YOUR_AUTH_KEY>
```

## 7. Deployment

### 7.1 자동 배포 및 검증 스크립트 (권장)

`deploy_and_verify.sh` 로 한 번에 올리고 상태·설정까지 검증할 수 있다.

```bash
cd lymphhub
./deploy_and_verify.sh
```

동작 요약:

- **사전 검사**: `.env` 존재, `NETWORK` 설정, Docker 네트워크 생성 여부, Authelia 설정 경고
- **Authelia 시크릿**: `data/authelia/secrets/` 에 `JWT_SECRET`, `SESSION_SECRET`, `STORAGE_PASSWORD`, `STORAGE_ENCRYPTION_KEY` 가 없거나 비어 있으면 자동 생성 (STORAGE_PASSWORD 는 가능하면 `.env` 의 `DB_PASSWORD` 사용)
- **배포**: `docker compose up -d --build`
- **대기**: 모든 컨테이너가 `running` 될 때까지 대기 (기본 120초)
- **헬스 체크**:
  - **Caddy**: HTTP 8080, Admin API 2019 응답 확인
  - **Authelia**: 호스트 포트 9091 응답 확인
  - **Headscale**: Docker healthcheck 또는 metrics 9090 응답 확인
- **설정 검증**: Authelia `authelia validate-config` 실행
- **Headscale 사용자**: 환경변수 `HEADSCALE_FIRST_USER` 가 있으면 해당 사용자 생성

Headscale 첫 사용자까지 스크립트로 생성하려면:

```bash
HEADSCALE_FIRST_USER=myfirstuser ./deploy_and_verify.sh
```

실패 시 각 서비스 최근 로그(20줄)를 출력한다.

### 7.2 수동 배포

1.  Navigate to `lymphhub` (or `infrastructure`) folder.
2.  Update `.env` with your real secrets. Authelia 설정은 `config/authelia/configuration.yml` 및 `data/authelia/secrets/` 참고.
3.  Run:
    ```bash
    docker compose up -d --build
    ```
