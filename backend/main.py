from fastapi import FastAPI, Header, HTTPException, Request, Response, Depends, Cookie
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, List
import os
from keycloak import KeycloakOpenID
from jose import jwt, JWTError

app = FastAPI(title="LymphHub Backend")

# Configuration
KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "https://auth.lyckabc.xyz")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "toji")
KEYCLOAK_CLIENT_ID = os.getenv("KEYCLOAK_CLIENT_ID", "lymphhub-portal")
KEYCLOAK_CLIENT_SECRET = os.getenv("KEYCLOAK_CLIENT_SECRET", "change-me")
LYMPHHUB_PUBLIC_URL = os.getenv("LYMPHHUB_PUBLIC_URL", "https://lymphhub.lyckabc.xyz")
COOKIE_DOMAIN = os.getenv("COOKIE_DOMAIN", ".lyckabc.xyz")

# Initialize Keycloak Client
keycloak_openid = KeycloakOpenID(
    server_url=KEYCLOAK_URL,
    client_id=KEYCLOAK_CLIENT_ID,
    realm_name=KEYCLOAK_REALM,
    client_secret_key=KEYCLOAK_CLIENT_SECRET
)

class Service(BaseModel):
    id: str
    name: str
    url: str
    description: str
    icon: str

SERVICES = [
    Service(id="plane", name="Plane", url="https://todo.lyckabc.xyz", description="Project Management", icon="✈️"),
    Service(id="keycloak", name="Keycloak", url="https://auth.lyckabc.xyz", description="Identity Provider", icon="🔐"),
    Service(id="pgadmin", name="pgAdmin", url="https://pgadmin.lyckabc.xyz", description="Database Management", icon="🐘"),
]

@app.get("/api/health")
def health_check():
    return {"status": "ok"}

@app.get("/api/auth")
async def forward_auth(
    request: Request,
    lymphhub_session: Optional[str] = Cookie(None)
):
    """
    Forward Auth Endpoint called by Traefik.
    """
    if not lymphhub_session:
        # Check if it's an API call or Browser navigation
        accept = request.headers.get("Accept", "")
        if "text/html" in accept:
            # Redirect to login with original URL as state
            # X-Forwarded-Uri is set by Traefik
            original_uri = request.headers.get("X-Forwarded-Uri", "/")
            original_host = request.headers.get("X-Forwarded-Host", "")
            # Construct return URL
            proto = request.headers.get("X-Forwarded-Proto", "http")
            target_url = f"{proto}://{original_host}{original_uri}" if original_host else original_uri
            
            login_url = keycloak_openid.auth_url(
                redirect_uri=f"{LYMPHHUB_PUBLIC_URL}/api/callback",
                scope="openid email profile",
                state=target_url
            )
            return RedirectResponse(login_url)
        else:
            return Response(status_code=401)

    try:
        # Verify Token
        # Ideally, use keycloak_openid.decode_token which validates signature against JWKS
        # For performance, caching JWKS is recommended.
        # Here we do a simple introspection or decode.
        # Introspection is safer but slower (network call).
        # Decode is faster. Let's start with decode/verify using library.
        
        # Verify token options
        options = {"verify_signature": True, "verify_aud": True, "exp": True}
        token_info = keycloak_openid.decode_token(lymphhub_session, key=KEYCLOAK_PUBLIC_KEY, options=options) if 'KEYCLOAK_PUBLIC_KEY' in globals() else keycloak_openid.userinfo(lymphhub_session)
        
        # If we reach here, token is valid
        # Pass headers to upstream
        headers = {
            "X-Auth-User": token_info.get("preferred_username", ""),
            "X-Auth-Email": token_info.get("email", ""),
            "X-Auth-Name": token_info.get("name", "")
        }
        return Response(status_code=200, headers=headers)

    except Exception as e:
        print(f"Auth failed: {e}")
        # Invalid token
        if "text/html" in request.headers.get("Accept", ""):
             login_url = keycloak_openid.auth_url(
                redirect_uri=f"{LYMPHHUB_PUBLIC_URL}/api/callback",
                scope="openid email profile"
            )
             return RedirectResponse(login_url)
        return Response(status_code=401)

@app.get("/api/login")
def login(redirect_url: str = "/"):
    auth_url = keycloak_openid.auth_url(
        redirect_uri=f"{LYMPHHUB_PUBLIC_URL}/api/callback",
        scope="openid email profile",
        state=redirect_url
    )
    return RedirectResponse(auth_url)

@app.get("/api/callback")
async def callback(code: str, state: str = "/"):
    try:
        token = keycloak_openid.token(
            grant_type="authorization_code",
            code=code,
            redirect_uri=f"{LYMPHHUB_PUBLIC_URL}/api/callback"
        )
        access_token = token["access_token"]
        
        response = RedirectResponse(url=state)
        # Set cookie for the parent domain so all subdomains can see it
        # Note: In production, assume https and secure=True
        response.set_cookie(
            key="lymphhub_session",
            value=access_token,
            httponly=True,
            domain=COOKIE_DOMAIN,
            max_age=token.get("expires_in", 300),
            secure=True, # Always True for HTTPS
            samesite="lax"
        )
        return response
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/user/me")
def get_current_user(lymphhub_session: Optional[str] = Cookie(None)):
    if not lymphhub_session:
         return {"authenticated": False}
    try:
        userinfo = keycloak_openid.userinfo(lymphhub_session)
        return {"authenticated": True, "user": userinfo}
    except:
        return {"authenticated": False}

@app.get("/api/services", response_model=List[Service])
def get_services():
    return SERVICES
