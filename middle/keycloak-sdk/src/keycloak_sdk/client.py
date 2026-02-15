"""
Keycloak SDK client - wrapper around python-keycloak KeycloakAdmin.

Provides reusable methods for creating clients, realms, users, etc.
"""

from typing import Any, Optional

from keycloak import KeycloakAdmin
from keycloak.exceptions import KeycloakError

from .config import KeycloakConfig


class KeycloakSDK:
    """
    Keycloak SDK for programmatic management.

    Use methods to create/update clients, realms, users.
    """

    def __init__(self, config: Optional[KeycloakConfig] = None):
        """
        Initialize SDK.

        :param config: KeycloakConfig. If None, loads from env via KeycloakConfig.from_env()
        """
        self._config = config or KeycloakConfig.from_env()
        self._admin: Optional[KeycloakAdmin] = None

    def _get_admin(self, realm_name: Optional[str] = None) -> KeycloakAdmin:
        """Get or create KeycloakAdmin connection (master realm for admin ops)."""
        if self._admin is None:
            self._admin = KeycloakAdmin(
                server_url=self._config.server_url.rstrip("/") + "/",
                username=self._config.admin_username,
                password=self._config.admin_password,
                realm_name=self._config.realm_name,
                client_id=self._config.client_id,
                client_secret_key=self._config.client_secret_key,
                verify=self._config.verify_ssl,
                timeout=self._config.timeout,
            )
        return self._admin

    def _admin_for_realm(self, realm_name: str) -> KeycloakAdmin:
        """Get KeycloakAdmin scoped to a specific realm (for realm-specific ops)."""
        # Admin user lives in master realm; use user_realm_name for token, realm_name for API
        return KeycloakAdmin(
            server_url=self._config.server_url.rstrip("/") + "/",
            username=self._config.admin_username,
            password=self._config.admin_password,
            realm_name=realm_name,
            user_realm_name="master" if realm_name != "master" else None,
            client_id=self._config.client_id,
            client_secret_key=self._config.client_secret_key,
            verify=self._config.verify_ssl,
            timeout=self._config.timeout,
        )

    # -------------------------------------------------------------------------
    # Realm methods
    # -------------------------------------------------------------------------

    def create_realm(
        self,
        realm_name: str,
        enabled: bool = True,
        skip_exists: bool = True,
        **kwargs: Any,
    ) -> str:
        """
        Create a realm.

        :param realm_name: Realm name
        :param enabled: Whether realm is enabled
        :param skip_exists: If True, do not raise when realm already exists
        :param kwargs: Additional RealmRepresentation fields
        :return: Realm name
        """
        admin = self._get_admin()
        payload = {
            "realm": realm_name,
            "enabled": enabled,
            **kwargs,
        }
        admin.create_realm(payload, skip_exists=skip_exists)
        return realm_name

    def realm_exists(self, realm_name: str) -> bool:
        """Check if a realm exists."""
        admin = self._get_admin()
        try:
            realms = admin.get_realms()
            return any(r.get("realm") == realm_name for r in realms)
        except KeycloakError:
            return False

    # -------------------------------------------------------------------------
    # Client methods
    # -------------------------------------------------------------------------

    def create_oidc_client(
        self,
        realm_name: str,
        client_id: str,
        *,
        redirect_uris: Optional[list[str]] = None,
        web_origins: Optional[list[str]] = None,
        confidential: bool = True,
        standard_flow_enabled: bool = True,
        direct_access_grants_enabled: bool = False,
        skip_exists: bool = True,
        **kwargs: Any,
    ) -> str:
        """
        Create an OIDC client in the given realm.

        :param realm_name: Target realm (e.g. 'toji')
        :param client_id: Client ID
        :param redirect_uris: Valid redirect URIs
        :param web_origins: Web origins (CORS)
        :param confidential: Use client secret (confidential client)
        :param standard_flow_enabled: Enable authorization code flow
        :param direct_access_grants_enabled: Enable direct access grants
        :param skip_exists: If True, return existing client id when already exists
        :param kwargs: Additional ClientRepresentation fields
        :return: Keycloak internal client UUID
        """
        admin = self._admin_for_realm(realm_name)
        payload = {
            "clientId": client_id,
            "protocol": "openid-connect",
            "enabled": True,
            "publicClient": not confidential,
            "standardFlowEnabled": standard_flow_enabled,
            "directAccessGrantsEnabled": direct_access_grants_enabled,
            "redirectUris": redirect_uris or [],
            "webOrigins": web_origins or ["+"],
            **kwargs,
        }
        return admin.create_client(payload, skip_exists=skip_exists)

    def get_client_secret(self, realm_name: str, client_id: str) -> Optional[str]:
        """
        Get client secret for a confidential client.

        :param realm_name: Realm name
        :param client_id: Client ID (clientId, not internal uuid)
        :return: Client secret value or None
        """
        admin = self._admin_for_realm(realm_name)
        internal_id = admin.get_client_id(client_id)
        if internal_id is None:
            return None
        secrets = admin.get_client_secrets(internal_id)
        return secrets.get("value")

    def get_client_id(self, realm_name: str, client_id: str) -> Optional[str]:
        """Get Keycloak internal client UUID from clientId."""
        admin = self._admin_for_realm(realm_name)
        return admin.get_client_id(client_id)

    def client_exists(self, realm_name: str, client_id: str) -> bool:
        """Check if a client exists in the realm."""
        return self.get_client_id(realm_name, client_id) is not None

    def create_temporal_oidc_client(
        self,
        realm_name: str = "toji",
        client_id: str = "temporal-ui",
        callback_url: str = "https://temporal.toji.homes/auth/sso/callback",
        web_origin: str = "https://temporal.toji.homes",
        skip_exists: bool = True,
    ) -> tuple[str, Optional[str]]:
        """
        Create OIDC client for Temporal UI (toji realm users only).

        :param realm_name: Realm (default: toji - only toji users can log in)
        :param client_id: Client ID
        :param callback_url: Temporal UI OIDC callback URL
        :param web_origin: Web origin for CORS
        :param skip_exists: If True, return existing client
        :return: (client_id, client_secret) - secret is None if client existed
        """
        internal_id = self.create_oidc_client(
            realm_name=realm_name,
            client_id=client_id,
            redirect_uris=[callback_url],
            web_origins=[web_origin, "+"],
            confidential=True,
            standard_flow_enabled=True,
            direct_access_grants_enabled=False,
            skip_exists=skip_exists,
        )
        secret = self.get_client_secret(realm_name, client_id)
        return client_id, secret

    # -------------------------------------------------------------------------
    # User methods
    # -------------------------------------------------------------------------

    def create_user(
        self,
        realm_name: str,
        username: str,
        *,
        email: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        enabled: bool = True,
        password: Optional[str] = None,
        exist_ok: bool = True,
        **kwargs: Any,
    ) -> str:
        """
        Create a user in the realm.

        :param realm_name: Target realm
        :param username: Username
        :param email: Email
        :param first_name: First name
        :param last_name: Last name
        :param enabled: Whether user is enabled
        :param password: Initial password (optional)
        :param exist_ok: If True, do not raise when user exists
        :param kwargs: Additional UserRepresentation fields
        :return: User ID (uuid)
        """
        admin = self._admin_for_realm(realm_name)
        payload = {
            "username": username,
            "enabled": enabled,
            "email": email or username,
            "firstName": first_name or "",
            "lastName": last_name or "",
            **kwargs,
        }
        if password:
            payload["credentials"] = [{"type": "password", "value": password}]
        return admin.create_user(payload, exist_ok=exist_ok)

    def get_users(self, realm_name: str, query: Optional[dict] = None) -> list:
        """Get users in realm."""
        admin = self._admin_for_realm(realm_name)
        return admin.get_users(query or {})
