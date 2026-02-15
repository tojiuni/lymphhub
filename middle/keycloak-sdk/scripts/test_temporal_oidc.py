#!/usr/bin/env python3
"""
Test Temporal OIDC client in Keycloak (toji realm).
Verifies: client exists, secret retrievable, OIDC endpoints reachable.
"""

import os
import sys

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_SDK_ROOT = os.path.dirname(_SCRIPT_DIR)
_SRC = os.path.join(_SDK_ROOT, "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from keycloak_sdk import KeycloakSDK, KeycloakConfig


def main() -> int:
    config = KeycloakConfig.from_env()
    if not config.admin_username or not config.admin_password:
        print("ERROR: Set KEYCLOAK_ADMIN_USERNAME and KEYCLOAK_ADMIN_PASSWORD")
        return 1

    sdk = KeycloakSDK(config)
    realm = "toji"
    client_id = "temporal-ui"

    print("1. Checking temporal-ui client exists in toji realm...")
    if not sdk.client_exists(realm, client_id):
        print("   FAIL: Client not found. Run setup_temporal_keycloak.py first.")
        return 1
    print("   OK")

    print("2. Retrieving client secret...")
    secret = sdk.get_client_secret(realm, client_id)
    if not secret:
        print("   FAIL: Could not get client secret")
        return 1
    print("   OK (secret length:", len(secret), ")")

    print("3. Verifying OIDC well-known endpoint...")
    import urllib.request
    url = f"{config.server_url.rstrip('/')}/realms/{realm}/.well-known/openid-configuration"
    try:
        with urllib.request.urlopen(url, timeout=5) as r:
            data = r.read().decode()
            if "authorization_endpoint" in data and "token_endpoint" in data:
                print("   OK")
            else:
                print("   WARN: Unexpected response")
    except Exception as e:
        print("   FAIL:", e)
        return 1

    print("\nAll checks passed. Temporal OIDC client is ready.")
    print("Note: temporal-ui requires temporal server to be running.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
