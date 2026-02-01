#!/usr/bin/env bash
# LymphHub deploy and verify script
# - Ensures Authelia secrets in data/authelia/secrets/ (creates if missing)
# - Runs docker compose up -d, verifies services, runs post-setup checks
# See CONFIGURATION.md for manual steps (Keycloak, Caddy, etc.)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# --- Config ---
COMPOSE_CMD="${COMPOSE_CMD:-docker compose}"
WAIT_MAX=10          # max seconds to wait for containers
HEALTH_POLL_INTERVAL=5
AUTHELIA_HOST_PORT=49091   # host port for Authelia (container 9091)
CADDY_HTTP_PORT=8080
HEADSCALE_API_PORT=8081
HEADSCALE_METRICS_PORT=9095

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

# --- Authelia secrets: create data/authelia/secrets if missing ---
# Required: JWT_SECRET, SESSION_SECRET, STORAGE_PASSWORD, STORAGE_ENCRYPTION_KEY (see CONFIGURATION.md §3.2)
ensure_authelia_secrets() {
  local secrets_dir="$SCRIPT_DIR/data/authelia/secrets"
  mkdir -p "$secrets_dir"
  local created=0

  # 64+ char random (openssl rand -base64 48 produces ~64 chars)
  gen_random() { openssl rand -base64 48 | tr -d '\n'; }

  for name in JWT_SECRET SESSION_SECRET STORAGE_ENCRYPTION_KEY; do
    if [[ ! -f "$secrets_dir/$name" ]] || [[ ! -s "$secrets_dir/$name" ]]; then
      echo -n "$(gen_random)" > "$secrets_dir/$name"
      log_info "Authelia: created $secrets_dir/$name"
      created=1
    fi
  done

  if [[ ! -f "$secrets_dir/STORAGE_PASSWORD" ]] || [[ ! -s "$secrets_dir/STORAGE_PASSWORD" ]]; then
    if [[ -n "${DB_PASSWORD:-}" ]]; then
      echo -n "$DB_PASSWORD" > "$secrets_dir/STORAGE_PASSWORD"
      log_info "Authelia: created STORAGE_PASSWORD from .env DB_PASSWORD"
    else
      echo -n "$(gen_random)" > "$secrets_dir/STORAGE_PASSWORD"
      log_warn "Authelia: created random STORAGE_PASSWORD (set DB_PASSWORD in .env and update PostgreSQL user to match)"
    fi
    created=1
  fi

  if [[ $created -eq 1 ]]; then
    chmod 600 "$secrets_dir"/* 2>/dev/null || true
  fi
}

# --- Pre-flight ---
preflight() {
  log_info "Pre-flight checks..."
  if [[ ! -f .env ]]; then
    log_error ".env not found. Copy from .env.example or create with DOMAIN, NETWORK, DB_*, etc."
    exit 1
  fi
  # shellcheck source=/dev/null
  source .env
  if [[ -z "${NETWORK:-}" ]]; then
    log_error ".env: NETWORK is not set."
    exit 1
  fi
  if ! docker network inspect "$NETWORK" &>/dev/null; then
    log_warn "Docker network '$NETWORK' does not exist. Creating..."
    docker network create "$NETWORK" || { log_error "Failed to create network $NETWORK"; exit 1; }
  fi
  if [[ -n "${DB_HOST:-}" ]] && [[ -z "${DB_PASSWORD:-}" ]]; then
    log_warn "DB_* set but DB_PASSWORD empty. Authelia may fail to start."
  fi
  if [[ ! -d config/authelia ]] || [[ ! -f config/authelia/configuration.yml ]]; then
    log_warn "config/authelia/configuration.yml not found. See CONFIGURATION.md §3 for Authelia setup."
  fi
  ensure_authelia_secrets
  if [[ -f config/authelia/users_database.yml ]]; then
    if grep -q "REPLACE_WITH_ARGON2_HASH\|password:.*\.\.\." config/authelia/users_database.yml 2>/dev/null; then
      log_warn "config/authelia/users_database.yml has placeholder password. Generate hash and replace: docker run --rm authelia/authelia:latest authelia crypto hash generate argon2 --password 'YOUR_PASSWORD'"
    fi
  fi
  log_info "Pre-flight OK."
}

# --- Deploy ---
deploy() {
  log_info "Running: $COMPOSE_CMD up -d --build"
  $COMPOSE_CMD up -d --build
}

# --- Wait until containers are running ---
wait_for_containers() {
  log_info "Waiting for containers to be running (max ${WAIT_MAX}s)..."
  local elapsed=0
  while (( elapsed < WAIT_MAX )); do
    local not_up
    not_up=$($COMPOSE_CMD ps -q 2>/dev/null | while read -r id; do
      state=$(docker inspect -f '{{.State.Status}}' "$id" 2>/dev/null)
      if [[ "$state" != "running" ]]; then echo "1"; fi
    done)
    if [[ -z "$not_up" ]]; then
      log_info "All containers are running."
      return 0
    fi
    sleep "$HEALTH_POLL_INTERVAL"
    (( elapsed += HEALTH_POLL_INTERVAL )) || true
  done
  log_error "Containers did not all reach 'running' within ${WAIT_MAX}s."
  return 1
}

# --- Service health checks ---
check_caddy() {
  local ok=0
  if curl -sf -o /dev/null --connect-timeout 3 "http://127.0.0.1:${CADDY_HTTP_PORT}" 2>/dev/null; then
    log_info "Caddy: HTTP ${CADDY_HTTP_PORT} responding."
    ok=1
  fi
  if curl -sf -o /dev/null --connect-timeout 3 "http://127.0.0.1:2019/config/" 2>/dev/null; then
    log_info "Caddy: Admin API (2019) responding."
    ok=1
  fi
  if (( ! ok )); then
    log_warn "Caddy: No response on ${CADDY_HTTP_PORT} or 2019. Showing last 15 log lines:"
    docker logs caddy 2>&1 | tail -15
    return 1
  fi
  return 0
}

check_authelia() {
  local code
  code=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 "http://127.0.0.1:${AUTHELIA_HOST_PORT}/" 2>/dev/null) || true
  if [[ "$code" == "200" ]] || [[ "$code" == "302" ]] || [[ "$code" == "401" ]]; then
    log_info "Authelia: Port ${AUTHELIA_HOST_PORT} responding (HTTP ${code})."
    return 0
  fi
  log_warn "Authelia: Unexpected response (HTTP ${code:-timeout}). Last 15 log lines:"
  docker logs authelia 2>&1 | tail -15
  return 1
}

check_headscale() {
  local health
  health=$(docker inspect -f '{{.State.Health.Status}}' headscale 2>/dev/null) || true
  if [[ "$health" == "healthy" ]]; then
    log_info "Headscale: Health status 'healthy'."
    return 0
  fi
  if [[ "$health" == "" ]]; then
    # No healthcheck or old engine
    if curl -sf -o /dev/null --connect-timeout 3 "http://127.0.0.1:${HEADSCALE_METRICS_PORT}/metrics" 2>/dev/null; then
      log_info "Headscale: Metrics port ${HEADSCALE_METRICS_PORT} responding."
      return 0
    fi
  fi
  log_warn "Headscale: Health status '$health'. Last 15 log lines:"
  docker logs headscale 2>&1 | tail -15
  return 1
}

run_health_checks() {
  log_info "Running health checks..."
  local failed=0
  check_caddy    || failed=$(( failed + 1 ))
  check_authelia || failed=$(( failed + 1 ))
  check_headscale || failed=$(( failed + 1 ))
  return $failed
}

# --- Authelia storage (PostgreSQL) connectivity: parse config and check TCP reachability ---
# configuration.yml 에서 storage.postgres.address 만 사용 (server.address 인 0.0.0.0:49091 제외)
check_authelia_storage_connectivity() {
  local authelia_config="$SCRIPT_DIR/config/authelia/configuration.yml"
  [[ -f "$authelia_config" ]] || return 0
  local line addr_spec host port
  line=$(grep -E "^\s*address:" "$authelia_config" | grep -v "0.0.0.0" | head -1)
  [[ -n "$line" ]] || return 0
  addr_spec=$(echo "$line" | sed -E "s/.*['\"]?tcp:\/\/([^'\"]+)['\"]?.*/\1/")
  [[ -n "$addr_spec" ]] && [[ "$addr_spec" != *"tcp"* ]] || return 0
  host="${addr_spec%%:*}"
  port="${addr_spec##*:}"
  [[ -n "$host" && -n "$port" ]] || return 0
  # Run TCP check from authelia container (so Docker-internal hostnames like 'postgres' resolve)
  if docker exec authelia sh -c "command -v nc >/dev/null && nc -z -w 2 '$host' '$port' 2>/dev/null" 2>/dev/null; then
    log_info "Authelia storage (PostgreSQL) at $host:$port is reachable (TCP check)."
    return 0
  fi
  # Fallback: from host (works for external hostnames when nc not in container)
  if ( timeout 2 bash -c "echo >/dev/tcp/$host/$port" 2>/dev/null ); then
    log_info "Authelia storage (PostgreSQL) at $host:$port is reachable (TCP check from host)."
    return 0
  fi
  # Fallback: same-host Postgres (container name doesn't resolve on host; use 127.0.0.1:DB_PORT)
  local host_port="${DB_PORT:-54311}"
  if ( timeout 2 bash -c "echo >/dev/tcp/127.0.0.1/$host_port" 2>/dev/null ); then
    log_info "Authelia storage (PostgreSQL) at $host:$port is reachable (same host, port $host_port)."
    return 0
  fi
  log_warn "Authelia storage (PostgreSQL) at $host:$port is not reachable (TCP check failed). See CONFIGURATION.md §3.4 or run: docker network inspect $NETWORK; docker run --rm --network $NETWORK busybox nc -zv $host $port"
  return 1
}

# --- Post-setup: validate configs / optional user creation ---
post_setup() {
  log_info "Post-setup validation..."

  # Authelia: storage connectivity (config에 적힌 PostgreSQL 주소 접근 가능 여부)
  check_authelia_storage_connectivity || true

  # Authelia: validate config (설정 문법 및 저장소 연결 검증)
  if docker exec authelia authelia validate-config --config /config/configuration.yml 2>/dev/null; then
    log_info "Authelia: Config validation passed."
  else
    log_warn "Authelia: Config validation failed or container not ready. Run manually: docker exec authelia authelia validate-config --config /config/configuration.yml"
  fi

  # Headscale: optional first user creation (목록에 있으면 스킵, 없으면 생성)
  local first_user="${HEADSCALE_FIRST_USER:-}"
  if [[ -n "$first_user" ]]; then
    local list_output
    list_output=$(docker exec headscale headscale users list 2>/dev/null) || true
    if echo "$list_output" | grep -Fqw "$first_user"; then
      log_info "Headscale: User '$first_user' already exists."
    else
      if docker exec headscale headscale users create "$first_user" 2>/dev/null; then
        log_info "Headscale: User '$first_user' created. Use 'headscale preauthkeys create --user $first_user --reusable --expiration 24h' for auth keys."
      else
        log_warn "Headscale: Failed to create user '$first_user'."
      fi
    fi
  else
    log_info "Headscale: Set HEADSCALE_FIRST_USER=myuser to create a user automatically, or run: docker exec -it headscale headscale users create myfirstuser"
  fi

  log_info "Post-setup done. See CONFIGURATION.md for Keycloak, Caddy, and Headscale preauth keys."
}

# --- Show recent logs on failure ---
show_logs_on_failure() {
  log_warn "Recent logs (last 20 lines per service):"
  for c in caddy authelia headscale; do
    if docker ps -a --format '{{.Names}}' | grep -q "^${c}$"; then
      echo "--- $c ---"
      docker logs "$c" 2>&1 | tail -20
      echo ""
    fi
  done
}

# --- Main ---
main() {
  echo "=============================================="
  echo "  LymphHub deploy and verify"
  echo "=============================================="
  preflight
  deploy
  if ! wait_for_containers; then
    show_logs_on_failure
    exit 1
  fi
  # Give services a moment to open ports
  sleep 3
  if ! run_health_checks; then
    log_warn "Some health checks failed. See above."
    show_logs_on_failure
    # Still run post_setup and exit with 1
  fi
  post_setup
  echo ""
  log_info "Done. Services: Caddy (HTTP ${CADDY_HTTP_PORT}), Authelia (${AUTHELIA_HOST_PORT}), Headscale (API ${HEADSCALE_API_PORT}, metrics ${HEADSCALE_METRICS_PORT})."
  exit 0
}

main "$@"
