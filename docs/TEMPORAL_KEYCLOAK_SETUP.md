# Temporal UI + Keycloak (toji realm) 인증 설정

Temporal UI(`https://temporal.toji.homes`)에 접속할 때 Keycloak의 **toji** realm 사용자만 로그인 가능하도록 설정합니다.

## 1. Keycloak Client 생성

`middle/keycloak-sdk`를 사용해 Temporal UI용 OIDC 클라이언트를 생성합니다.

```bash
cd lymphhub

# keycloak-sdk 설치
pip install -e middle/keycloak-sdk

# 환경변수 설정 후 실행
export KEYCLOAK_SERVER_URL=https://auth.lyckabc.xyz
export KEYCLOAK_ADMIN_USERNAME=admin
export KEYCLOAK_ADMIN_PASSWORD=<your-admin-password>
export KEYCLOAK_ADMIN_REALM=master

python middle/keycloak-sdk/scripts/setup_temporal_keycloak.py
```

출력된 **Client Secret**을 복사합니다.

## 2. cicd/temporal .env 설정

`cicd/temporal/.env`에 다음 변수를 추가합니다:

```bash
# Temporal UI Keycloak OIDC (toji realm)
TEMPORAL_AUTH_ENABLED=true
TEMPORAL_AUTH_PROVIDER_URL=https://auth.lyckabc.xyz/realms/toji
TEMPORAL_AUTH_ISSUER_URL=https://auth.lyckabc.xyz/realms/toji
TEMPORAL_AUTH_CLIENT_ID=temporal-ui
TEMPORAL_AUTH_CLIENT_SECRET=<setup_temporal_keycloak.py 출력값>
TEMPORAL_AUTH_CALLBACK_URL=https://temporal.toji.homes/auth/sso/callback
TEMPORAL_AUTH_SCOPES=openid,profile,email
```

## 3. Temporal UI 재시작

```bash
cd cicd/temporal
docker compose up -d temporal-ui
```

## 4. 동작 확인

1. `https://temporal.toji.homes` 접속
2. Keycloak 로그인 페이지로 리다이렉트
3. **toji** realm 사용자로 로그인
4. Temporal UI 접근 가능

다른 realm 사용자는 toji realm에 사용자가 없으므로 로그인할 수 없습니다.
