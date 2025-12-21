# LymphHub Configuration Guide

This guide details the integration of LymphHub with `lyckabc.xyz` domain, Keycloak (Realm: `toji`), and Traefik.

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

## 3. Keycloak Manual Configuration
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

## 4. Traefik Configuration (Reference)
The LymphHub authentication middleware is defined in `infrastructure/docker-compose.yaml` as `lymphhub-auth`.
To protect any other service (e.g., Plane), add these labels to that service's container:

```yaml
labels:
  - "traefik.enable=true"
  - "traefik.docker.network=traefik-net"
  - "traefik.http.routers.YOUR_SERVICE.rule=Host(`YOUR_APP.lyckabc.xyz`)"
  - "traefik.http.routers.YOUR_SERVICE.entrypoints=websecure"
  - "traefik.http.routers.YOUR_SERVICE.tls.certresolver=letsencrypt"
  # Apply the Middleware
  - "traefik.http.routers.YOUR_SERVICE.middlewares=lymphhub-auth@docker"
```

## 5. Deployment
1.  Navigate to `infrastructure` folder.
2.  Update `.env` with your real secrets.
3.  Run:
    ```bash
    docker-compose up -d --build
    ```
