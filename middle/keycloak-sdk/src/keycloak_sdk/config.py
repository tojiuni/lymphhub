"""Keycloak connection configuration."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class KeycloakConfig:
    """Keycloak server and admin connection settings."""

    server_url: str
    admin_username: str
    admin_password: str
    realm_name: str = "master"
    client_id: str = "admin-cli"
    client_secret_key: Optional[str] = None
    verify_ssl: bool = True
    timeout: int = 60

    @classmethod
    def from_env(cls) -> "KeycloakConfig":
        """Load config from environment variables."""
        import os

        return cls(
            server_url=os.getenv("KEYCLOAK_SERVER_URL", "https://auth.lyckabc.xyz"),
            admin_username=os.getenv("KEYCLOAK_ADMIN_USERNAME", ""),
            admin_password=os.getenv("KEYCLOAK_ADMIN_PASSWORD", ""),
            realm_name=os.getenv("KEYCLOAK_ADMIN_REALM", "master"),
            client_id=os.getenv("KEYCLOAK_ADMIN_CLIENT_ID", "admin-cli"),
            client_secret_key=os.getenv("KEYCLOAK_ADMIN_CLIENT_SECRET") or None,
            verify_ssl=os.getenv("KEYCLOAK_VERIFY_SSL", "true").lower() == "true",
            timeout=int(os.getenv("KEYCLOAK_TIMEOUT", "60")),
        )
