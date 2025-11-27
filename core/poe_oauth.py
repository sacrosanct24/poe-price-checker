"""
OAuth authentication for Path of Exile API.

Handles the OAuth flow to get access tokens for accessing
private stash tabs and character data.
"""

import webbrowser
import logging
import secrets
import hashlib
import base64
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlencode, parse_qs, urlparse
from typing import Optional, Any
import requests
import json
from pathlib import Path
from datetime import datetime, timedelta


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """HTTP handler for OAuth callback."""

    authorization_code: Optional[str] = None

    def do_GET(self) -> None:
        """Handle GET request from OAuth redirect."""
        # Parse the callback URL
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        if 'code' in params:
            # Success - got authorization code
            OAuthCallbackHandler.authorization_code = params['code'][0]

            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()

            html = """
            <html>
            <head><title>Authentication Successful</title></head>
            <body>
                <h1>✓ Authentication Successful!</h1>
                <p>You can close this window and return to PoE Price Checker.</p>
            </body>
            </html>
            """
            self.wfile.write(html.encode())
        else:
            # Error
            error = params.get('error', ['Unknown error'])[0]

            self.send_response(400)
            self.send_header('Content-type', 'text/html')
            self.end_headers()

            html = f"""
            <html>
            <head><title>Authentication Failed</title></head>
            <body>
                <h1>✗ Authentication Failed</h1>
                <p>Error: {error}</p>
                <p>Please close this window and try again.</p>
            </body>
            </html>
            """
            self.wfile.write(html.encode())

    def log_message(self, format: str, *args: Any) -> None:
        """Suppress default logging."""
        pass


class PoeOAuthClient:
    """
    OAuth client for Path of Exile API.

    Handles authentication flow and token management.
    """

    # PoE OAuth endpoints
    AUTH_URL = "https://www.pathofexile.com/oauth/authorize"
    TOKEN_URL = "https://www.pathofexile.com/oauth/token"

    # Default redirect URI (local server)
    # Note: Using 127.0.0.1 for PUBLIC CLIENT (localhost not allowed for
    # confidential)
    REDIRECT_URI = "http://127.0.0.1:8080/oauth/callback"

    def __init__(
        self,
        client_id: str,
        client_secret: Optional[str] = None,
        token_file: Optional[Path] = None,
        is_public_client: bool = True,
    ) -> None:
        """
        Initialize OAuth client.

        Args:
            client_id: OAuth client ID from PoE
            client_secret: OAuth client secret (only for confidential clients)
            token_file: Path to save/load tokens (optional)
            is_public_client: True for desktop apps (default), False for web servers
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.is_public_client = is_public_client
        self.token_file = token_file or Path.home() / ".poe_price_checker" / \
            "oauth_token.json"

        # PKCE values (saved during auth flow)
        self.code_verifier: Optional[str] = None
        self.code_challenge: Optional[str] = None

        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.expires_at: Optional[datetime] = None

        self.logger = logging.getLogger("poe_oauth")

        # Try to load existing token
        self._load_token()

    def _load_token(self) -> None:
        """Load saved token from file if it exists."""
        if not self.token_file.exists():
            return

        try:
            with open(self.token_file, 'r') as f:
                data = json.load(f)

            self.access_token = data.get('access_token')
            self.refresh_token = data.get('refresh_token')

            expires_at_str = data.get('expires_at')
            if expires_at_str:
                self.expires_at = datetime.fromisoformat(expires_at_str)

            self.logger.info("Loaded OAuth token from %s", self.token_file)

            # Check if token is expired
            if self.is_token_expired():
                self.logger.info("Token is expired, will need to refresh")
        except Exception as e:
            self.logger.warning("Failed to load token: %s", e)

    def _save_token(self) -> None:
        """Save current token to file."""
        if not self.access_token:
            return

        data = {
            'access_token': self.access_token,
            'refresh_token': self.refresh_token,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
        }

        # Ensure directory exists
        self.token_file.parent.mkdir(parents=True, exist_ok=True)

        with open(self.token_file, 'w') as f:
            json.dump(data, f, indent=2)

        self.logger.info("Saved OAuth token to %s", self.token_file)

    def is_token_expired(self) -> bool:
        """Check if the access token is expired."""
        if not self.expires_at:
            return True
        return datetime.now() >= self.expires_at

    def is_authenticated(self) -> bool:
        """Check if we have a valid access token."""
        return bool(self.access_token and not self.is_token_expired())

    def authenticate(self) -> bool:
        """
        Run the OAuth authentication flow with PKCE.

        Opens browser for user to authenticate, then starts local
        server to receive callback.

        Returns:
            True if authentication successful
        """
        self.logger.info(
            "Starting OAuth authentication flow (PUBLIC CLIENT with PKCE)")

        # Generate PKCE parameters (required for public clients)
        self._generate_pkce()

        # Generate random state for CSRF protection
        state = secrets.token_urlsafe(32)

        # Build authorization URL
        params = {
            'client_id': self.client_id,
            'response_type': 'code',
            'scope': 'account:characters account:stashes',
            'redirect_uri': self.REDIRECT_URI,
            'state': state,
            'code_challenge': self.code_challenge,
            'code_challenge_method': 'S256',
        }

        auth_url = f"{self.AUTH_URL}?{urlencode(params)}"

        self.logger.info("Opening browser for authentication")
        # Redact sensitive parameters (state, code_challenge) from logs
        self.logger.info("URL: %s?... (params redacted)", self.AUTH_URL)

        # Open browser
        webbrowser.open(auth_url)

        # Start local server to receive callback
        self.logger.info("Starting local server on port 8080")

        server = HTTPServer(('localhost', 8080), OAuthCallbackHandler)

        # Wait for one request (the callback)
        OAuthCallbackHandler.authorization_code = None
        server.handle_request()

        code = OAuthCallbackHandler.authorization_code

        if not code:
            self.logger.error("Failed to get authorization code")
            return False

        self.logger.info("Got authorization code: %s...", code[:10])

        # Exchange code for token
        return self._exchange_code_for_token(code)

    def _generate_pkce(self) -> None:
        """
        Generate PKCE code_verifier and code_challenge.

        Per RFC 7636:
        - code_verifier: 43-128 character string (base64url-encoded 32+ random bytes)
        - code_challenge: base64url(SHA256(code_verifier))
        """
        # Generate code_verifier (32 random bytes = 43 chars base64url)
        verifier_bytes = secrets.token_bytes(32)
        self.code_verifier = base64.urlsafe_b64encode(
            verifier_bytes).decode('utf-8').rstrip('=')

        # Generate code_challenge (SHA256 hash of verifier)
        challenge_bytes = hashlib.sha256(
            self.code_verifier.encode('utf-8')).digest()
        self.code_challenge = base64.urlsafe_b64encode(
            challenge_bytes).decode('utf-8').rstrip('=')

        self.logger.debug(
            "Generated PKCE: verifier=%s..., challenge=%s...",
            self.code_verifier[:10],
            self.code_challenge[:10],
        )

    def _exchange_code_for_token(self, code: str) -> bool:
        """
        Exchange authorization code for access token.

        Args:
            code: Authorization code from callback

        Returns:
            True if successful
        """
        self.logger.info("Exchanging authorization code for access token")

        data = {
            'client_id': self.client_id,
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': self.REDIRECT_URI,
            'scope': 'account:characters account:stashes',
            'code_verifier': self.code_verifier,  # PKCE required!
        }

        # Only include client_secret for confidential clients
        if not self.is_public_client and self.client_secret:
            data['client_secret'] = self.client_secret

        try:
            response = requests.post(self.TOKEN_URL, data=data)
            response.raise_for_status()

            token_data = response.json()

            self.access_token = token_data['access_token']
            self.refresh_token = token_data.get('refresh_token')

            # Calculate expiration time
            expires_in = token_data.get('expires_in', 3600)
            self.expires_at = datetime.now() + timedelta(seconds=expires_in)

            self.logger.info(
                "Got access token, expires in %d seconds",
                expires_in)

            # Save token
            self._save_token()

            return True

        except requests.RequestException as e:
            self.logger.error("Failed to exchange code for token: %s", e)
            return False

    def refresh_access_token(self) -> bool:
        """
        Refresh the access token using refresh token.

        Returns:
            True if successful
        """
        if not self.refresh_token:
            self.logger.warning("No refresh token available")
            return False

        self.logger.info("Refreshing access token")

        data = {
            'client_id': self.client_id,
            'grant_type': 'refresh_token',
            'refresh_token': self.refresh_token,
        }

        # Only include client_secret for confidential clients
        if not self.is_public_client and self.client_secret:
            data['client_secret'] = self.client_secret

        try:
            response = requests.post(self.TOKEN_URL, data=data)
            response.raise_for_status()

            token_data = response.json()

            self.access_token = token_data['access_token']
            if 'refresh_token' in token_data:
                self.refresh_token = token_data['refresh_token']

            expires_in = token_data.get('expires_in', 3600)
            self.expires_at = datetime.now() + timedelta(seconds=expires_in)

            self.logger.info(
                "Refreshed access token, expires in %d seconds",
                expires_in)

            # Save updated token
            self._save_token()

            return True

        except requests.RequestException as e:
            self.logger.error("Failed to refresh token: %s", e)
            return False

    def get_access_token(self) -> Optional[str]:
        """
        Get a valid access token, refreshing if necessary.

        Returns:
            Access token or None if unavailable
        """
        if not self.access_token:
            return None

        if self.is_token_expired():
            if not self.refresh_access_token():
                return None

        return self.access_token

    def revoke_token(self) -> None:
        """Revoke the current token and delete saved file."""
        self.access_token = None
        self.refresh_token = None
        self.expires_at = None

        if self.token_file.exists():
            self.token_file.unlink()
            self.logger.info("Deleted token file")


if __name__ == "__main__":
    # Test OAuth flow
    logging.basicConfig(level=logging.INFO)

    # You need to get these from PoE developer portal
    # For PUBLIC CLIENT (desktop app), you don't need a client_secret!
    CLIENT_ID = "your_client_id_here"

    client = PoeOAuthClient(CLIENT_ID, is_public_client=True)

    if client.is_authenticated():
        print("✓ Already authenticated!")
        print(f"Access token: {client.access_token[:20]}...")
    else:
        print("Starting authentication...")
        if client.authenticate():
            print("✓ Authentication successful!")
            print(f"Access token: {client.access_token[:20]}...")
        else:
            print("✗ Authentication failed")
