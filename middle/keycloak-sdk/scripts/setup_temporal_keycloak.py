#!/usr/bin/env python3
"""
Setup Temporal UI OIDC client in Keycloak (toji realm).

Creates a confidential OIDC client so only toji realm users can log into Temporal UI.
Run from project root with env vars set:

  KEYCLOAK_SERVER_URL=https://auth.lyckabc.xyz
  KEYCLOAK_ADMIN_USERNAME=admin
  KEYCLOAK_ADMIN_PASSWORD=...
  KEYCLOAK_ADMIN_REALM=master

Usage:
  cd middle/keycloak-sdk && pip install -e . && python scripts/setup_temporal_keycloak.py
  # or from lymphhub root:
  python -m keycloak_sdk.scripts.setup_temporal_keycloak  # if installed
"""

import os
import sys

# Add src to path when run as script
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_SDK_ROOT = os.path.dirname(_SCRIPT_DIR)
_SRC = os.path.join(_SDK_ROOT, "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from keycloak_sdk import KeycloakSDK, KeycloakConfig


def main() -> None:
    config = KeycloakConfig.from_env()
    if not config.admin_username or not config.admin_password:
        print("ERROR: Set KEYCLOAK_ADMIN_USERNAME and KEYCLOAK_ADMIN_PASSWORD")
        sys.exit(1)

    sdk = KeycloakSDK(config)
    callback_url = os.getenv(
        "TEMPORAL_CALLBACK_URL", "https://temporal.toji.homes/auth/sso/callback"
    )
    web_origin = os.getenv("TEMPORAL_WEB_ORIGIN", "https://temporal.toji.homes")

    print("Creating Temporal UI OIDC client in Keycloak (realm: toji)...")
    client_id, secret = sdk.create_temporal_oidc_client(
        realm_name="toji",
        client_id="temporal-ui",
        callback_url=callback_url,
        web_origin=web_origin,
        skip_exists=True,
    )

    print(f"\nClient ID: {client_id}")
    if secret:
        print(f"Client Secret: {secret}")
        print("\nAdd to temporal-ui environment (e.g. cicd/temporal docker-compose):")
        print("  TEMPORAL_AUTH_ENABLED=true")
        print("  TEMPORAL_AUTH_TYPE=oidc")
        print(f"  TEMPORAL_AUTH_PROVIDER_URL={config.server_url}/realms/toji")
        print(f"  TEMPORAL_AUTH_ISSUER_URL={config.server_url}/realms/toji")
        print(f"  TEMPORAL_AUTH_CLIENT_ID={client_id}")
        print(f"  TEMPORAL_AUTH_CLIENT_SECRET={secret}")
        print(f"  TEMPORAL_AUTH_CALLBACK_URL={callback_url}")
        print("  TEMPORAL_AUTH_SCOPES=openid,profile,email")
    else:
        print("\nClient already exists. Get secret from Keycloak Admin Console:")
        print(f"  {config.server_url} → Realm 'toji' → Clients → temporal-ui → Credentials")


if __name__ == "__main__":
    main()
