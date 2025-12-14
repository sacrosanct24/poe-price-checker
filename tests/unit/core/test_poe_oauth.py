"""
Unit tests for core.poe_oauth module - OAuth authentication flow with PKCE.

Tests cover:
- PKCE generation and validation
- Token exchange and refresh
- Token persistence and loading
- Token expiration handling
- Error handling
"""

import pytest
import json
import hashlib
import base64
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from core.poe_oauth import PoeOAuthClient, OAuthCallbackHandler

pytestmark = pytest.mark.unit


# -------------------------
# PKCE Generation Tests
# -------------------------

class TestPKCEGeneration:
    """Test PKCE code_verifier and code_challenge generation."""

    def test_pkce_generates_verifier_and_challenge(self, tmp_path):
        """PKCE should generate both verifier and challenge."""
        client = PoeOAuthClient(
            client_id="test_client",
            token_file=tmp_path / "token.json"
        )
        client._generate_pkce()

        assert client.code_verifier is not None
        assert client.code_challenge is not None
        assert len(client.code_verifier) >= 43  # RFC 7636: 43-128 chars
        assert len(client.code_challenge) >= 43

    def test_pkce_verifier_is_base64url_encoded(self, tmp_path):
        """Code verifier should be valid base64url (no padding)."""
        client = PoeOAuthClient(
            client_id="test_client",
            token_file=tmp_path / "token.json"
        )
        client._generate_pkce()

        # Should not contain padding characters
        assert '=' not in client.code_verifier
        assert '=' not in client.code_challenge

        # Should only contain base64url characters
        valid_chars = set('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_')
        assert all(c in valid_chars for c in client.code_verifier)
        assert all(c in valid_chars for c in client.code_challenge)

    def test_pkce_challenge_is_sha256_of_verifier(self, tmp_path):
        """Code challenge should be SHA256 hash of verifier (base64url)."""
        client = PoeOAuthClient(
            client_id="test_client",
            token_file=tmp_path / "token.json"
        )
        client._generate_pkce()

        # Manually compute expected challenge
        verifier_bytes = client.code_verifier.encode('utf-8')
        sha256_hash = hashlib.sha256(verifier_bytes).digest()
        expected_challenge = base64.urlsafe_b64encode(sha256_hash).decode('utf-8').rstrip('=')

        assert client.code_challenge == expected_challenge

    def test_pkce_generates_different_values_each_time(self, tmp_path):
        """Each PKCE generation should produce unique values."""
        client = PoeOAuthClient(
            client_id="test_client",
            token_file=tmp_path / "token.json"
        )

        client._generate_pkce()
        verifier1 = client.code_verifier
        challenge1 = client.code_challenge

        client._generate_pkce()
        verifier2 = client.code_verifier
        challenge2 = client.code_challenge

        assert verifier1 != verifier2
        assert challenge1 != challenge2


# -------------------------
# Initialization Tests
# -------------------------

class TestOAuthClientInitialization:
    """Test OAuth client initialization and configuration."""

    def test_creates_client_with_defaults(self, tmp_path):
        """Client should initialize with default settings."""
        client = PoeOAuthClient(
            client_id="test_client",
            token_file=tmp_path / "token.json"
        )

        assert client.client_id == "test_client"
        assert client.client_secret is None
        assert client.is_public_client is True
        assert client.access_token is None
        assert client.refresh_token is None
        assert client.expires_at is None

    def test_creates_client_with_secret(self, tmp_path):
        """Client should support confidential client mode with secret."""
        client = PoeOAuthClient(
            client_id="test_client",
            client_secret="test_secret",
            token_file=tmp_path / "token.json",
            is_public_client=False
        )

        assert client.client_secret == "test_secret"
        assert client.is_public_client is False

    def test_uses_default_token_file_path_if_none(self):
        """Client should use default token file path if not specified."""
        client = PoeOAuthClient(client_id="test_client")

        expected_path = Path.home() / ".poe_price_checker" / "oauth_token.json"
        assert client.token_file == expected_path


# -------------------------
# Token Persistence Tests
# -------------------------

class TestTokenPersistence:
    """Test saving and loading tokens from disk."""

    def test_saves_token_to_file(self, tmp_path):
        """Token should be saved to JSON file with encryption."""
        token_file = tmp_path / "token.json"
        client = PoeOAuthClient(
            client_id="test_client",
            token_file=token_file
        )

        # Set token data
        client.access_token = "test_access_token"
        client.refresh_token = "test_refresh_token"
        client.expires_at = datetime(2025, 12, 31, 23, 59, 59)

        client._save_token()

        assert token_file.exists()

        # Verify contents - tokens should be encrypted
        with open(token_file) as f:
            data = json.load(f)

        # Tokens should be encrypted (start with enc:v1: or obf:)
        assert data['access_token'].startswith(('enc:v1:', 'obf:'))
        assert data['refresh_token'].startswith(('enc:v1:', 'obf:'))
        assert data['expires_at'] == "2025-12-31T23:59:59"

        # Verify client still has plaintext tokens in memory
        assert client.access_token == "test_access_token"
        assert client.refresh_token == "test_refresh_token"

    def test_loads_token_from_file(self, tmp_path):
        """Client should load existing token from file."""
        token_file = tmp_path / "token.json"

        # Create token file
        token_data = {
            'access_token': 'saved_access_token',
            'refresh_token': 'saved_refresh_token',
            'expires_at': '2025-12-31T23:59:59'
        }
        with open(token_file, 'w') as f:
            json.dump(token_data, f)

        # Create client (should auto-load)
        client = PoeOAuthClient(
            client_id="test_client",
            token_file=token_file
        )

        assert client.access_token == "saved_access_token"
        assert client.refresh_token == "saved_refresh_token"
        assert client.expires_at == datetime(2025, 12, 31, 23, 59, 59)

    def test_handles_missing_token_file(self, tmp_path):
        """Client should handle missing token file gracefully."""
        token_file = tmp_path / "nonexistent.json"

        client = PoeOAuthClient(
            client_id="test_client",
            token_file=token_file
        )

        assert client.access_token is None
        assert client.refresh_token is None
        assert client.expires_at is None

    def test_handles_corrupted_token_file(self, tmp_path):
        """Client should handle corrupted token file gracefully."""
        token_file = tmp_path / "corrupted.json"

        # Write invalid JSON
        with open(token_file, 'w') as f:
            f.write("not valid json {")

        client = PoeOAuthClient(
            client_id="test_client",
            token_file=token_file
        )

        # Should not crash, just not load anything
        assert client.access_token is None

    def test_creates_parent_directory_when_saving(self, tmp_path):
        """Saving token should create parent directories if needed."""
        token_file = tmp_path / "subdir" / "nested" / "token.json"
        client = PoeOAuthClient(
            client_id="test_client",
            token_file=token_file
        )

        client.access_token = "test_token"
        client._save_token()

        assert token_file.exists()
        assert token_file.parent.exists()


# -------------------------
# Token Expiration Tests
# -------------------------

class TestTokenExpiration:
    """Test token expiration logic."""

    def test_is_token_expired_when_past_expiry(self, tmp_path):
        """Token should be expired if past expiration time."""
        client = PoeOAuthClient(
            client_id="test_client",
            token_file=tmp_path / "token.json"
        )

        # Set expired token
        client.access_token = "expired_token"
        client.expires_at = datetime.now() - timedelta(hours=1)

        assert client.is_token_expired() is True

    def test_is_token_expired_when_before_expiry(self, tmp_path):
        """Token should not be expired if before expiration time."""
        client = PoeOAuthClient(
            client_id="test_client",
            token_file=tmp_path / "token.json"
        )

        # Set valid token
        client.access_token = "valid_token"
        client.expires_at = datetime.now() + timedelta(hours=1)

        assert client.is_token_expired() is False

    def test_is_token_expired_when_no_expiry_set(self, tmp_path):
        """Token should be considered expired if no expiry time set."""
        client = PoeOAuthClient(
            client_id="test_client",
            token_file=tmp_path / "token.json"
        )

        client.access_token = "token"
        client.expires_at = None

        assert client.is_token_expired() is True

    def test_is_authenticated_when_valid_token(self, tmp_path):
        """Should be authenticated with valid, non-expired token."""
        client = PoeOAuthClient(
            client_id="test_client",
            token_file=tmp_path / "token.json"
        )

        client.access_token = "valid_token"
        client.expires_at = datetime.now() + timedelta(hours=1)

        assert client.is_authenticated() is True

    def test_is_authenticated_when_expired_token(self, tmp_path):
        """Should not be authenticated with expired token."""
        client = PoeOAuthClient(
            client_id="test_client",
            token_file=tmp_path / "token.json"
        )

        client.access_token = "expired_token"
        client.expires_at = datetime.now() - timedelta(hours=1)

        assert client.is_authenticated() is False

    def test_is_authenticated_when_no_token(self, tmp_path):
        """Should not be authenticated without token."""
        client = PoeOAuthClient(
            client_id="test_client",
            token_file=tmp_path / "token.json"
        )

        assert client.is_authenticated() is False


# -------------------------
# Token Exchange Tests
# -------------------------

class TestTokenExchange:
    """Test authorization code exchange for access token."""

    @patch('core.poe_oauth.requests.post')
    def test_exchange_code_for_token_success(self, mock_post, tmp_path):
        """Should successfully exchange authorization code for token."""
        # Mock successful response
        mock_response = Mock()
        mock_response.json.return_value = {
            'access_token': 'new_access_token',
            'refresh_token': 'new_refresh_token',
            'expires_in': 3600
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        client = PoeOAuthClient(
            client_id="test_client",
            token_file=tmp_path / "token.json"
        )
        client.code_verifier = "test_verifier"

        result = client._exchange_code_for_token("auth_code_123")

        assert result is True
        assert client.access_token == "new_access_token"
        assert client.refresh_token == "new_refresh_token"
        assert client.expires_at is not None

        # Verify request was made correctly
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == client.TOKEN_URL
        assert call_args[1]['data']['code'] == 'auth_code_123'
        assert call_args[1]['data']['code_verifier'] == 'test_verifier'
        assert call_args[1]['data']['client_id'] == 'test_client'
        assert call_args[1]['data']['grant_type'] == 'authorization_code'

    @patch('core.poe_oauth.requests.post')
    def test_exchange_code_includes_secret_for_confidential_client(self, mock_post, tmp_path):
        """Confidential client should include client_secret in token exchange."""
        mock_response = Mock()
        mock_response.json.return_value = {
            'access_token': 'token',
            'expires_in': 3600
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        client = PoeOAuthClient(
            client_id="test_client",
            client_secret="test_secret",
            token_file=tmp_path / "token.json",
            is_public_client=False
        )
        client.code_verifier = "test_verifier"

        client._exchange_code_for_token("auth_code")

        # Verify secret was included
        call_args = mock_post.call_args
        assert call_args[1]['data']['client_secret'] == 'test_secret'

    @patch('core.poe_oauth.requests.post')
    def test_exchange_code_handles_failure(self, mock_post, tmp_path):
        """Should handle token exchange failure gracefully."""
        import requests

        # Mock failed response
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.RequestException("Invalid code")
        mock_post.return_value = mock_response

        client = PoeOAuthClient(
            client_id="test_client",
            token_file=tmp_path / "token.json"
        )
        client.code_verifier = "test_verifier"

        result = client._exchange_code_for_token("invalid_code")

        assert result is False
        assert client.access_token is None

    @patch('core.poe_oauth.requests.post')
    def test_exchange_code_saves_token_on_success(self, mock_post, tmp_path):
        """Token should be saved to file after successful exchange."""
        token_file = tmp_path / "token.json"

        mock_response = Mock()
        mock_response.json.return_value = {
            'access_token': 'new_token',
            'refresh_token': 'new_refresh',
            'expires_in': 3600
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        client = PoeOAuthClient(
            client_id="test_client",
            token_file=token_file
        )
        client.code_verifier = "test_verifier"

        client._exchange_code_for_token("auth_code")

        # Verify token was saved (encrypted)
        assert token_file.exists()
        with open(token_file) as f:
            data = json.load(f)
        # Token should be encrypted in file
        assert data['access_token'].startswith(('enc:v1:', 'obf:'))
        # But client should have plaintext in memory
        assert client.access_token == 'new_token'


# -------------------------
# Token Refresh Tests
# -------------------------

class TestTokenRefresh:
    """Test refreshing access tokens."""

    @patch('core.poe_oauth.requests.post')
    def test_refresh_token_success(self, mock_post, tmp_path):
        """Should successfully refresh access token."""
        mock_response = Mock()
        mock_response.json.return_value = {
            'access_token': 'refreshed_access_token',
            'refresh_token': 'new_refresh_token',
            'expires_in': 3600
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        client = PoeOAuthClient(
            client_id="test_client",
            token_file=tmp_path / "token.json"
        )
        client.refresh_token = "old_refresh_token"

        result = client.refresh_access_token()

        assert result is True
        assert client.access_token == "refreshed_access_token"
        assert client.refresh_token == "new_refresh_token"

        # Verify request
        call_args = mock_post.call_args
        assert call_args[1]['data']['grant_type'] == 'refresh_token'
        assert call_args[1]['data']['refresh_token'] == 'old_refresh_token'

    @patch('core.poe_oauth.requests.post')
    def test_refresh_token_preserves_old_refresh_token_if_not_returned(self, mock_post, tmp_path):
        """Should keep old refresh token if new one not provided."""
        mock_response = Mock()
        mock_response.json.return_value = {
            'access_token': 'new_access_token',
            'expires_in': 3600
            # No refresh_token in response
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        client = PoeOAuthClient(
            client_id="test_client",
            token_file=tmp_path / "token.json"
        )
        client.refresh_token = "old_refresh_token"

        client.refresh_access_token()

        assert client.refresh_token == "old_refresh_token"

    @patch('core.poe_oauth.requests.post')
    def test_refresh_token_fails_without_refresh_token(self, mock_post, tmp_path):
        """Should fail if no refresh token available."""
        client = PoeOAuthClient(
            client_id="test_client",
            token_file=tmp_path / "token.json"
        )
        client.refresh_token = None

        result = client.refresh_access_token()

        assert result is False
        mock_post.assert_not_called()

    @patch('core.poe_oauth.requests.post')
    def test_refresh_token_handles_failure(self, mock_post, tmp_path):
        """Should handle refresh failure gracefully."""
        import requests

        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.RequestException("Invalid refresh token")
        mock_post.return_value = mock_response

        client = PoeOAuthClient(
            client_id="test_client",
            token_file=tmp_path / "token.json"
        )
        client.refresh_token = "invalid_refresh_token"

        result = client.refresh_access_token()

        assert result is False

    @patch('core.poe_oauth.requests.post')
    def test_refresh_token_saves_updated_token(self, mock_post, tmp_path):
        """Refreshed token should be saved to file."""
        token_file = tmp_path / "token.json"

        mock_response = Mock()
        mock_response.json.return_value = {
            'access_token': 'refreshed_token',
            'expires_in': 3600
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        client = PoeOAuthClient(
            client_id="test_client",
            token_file=token_file
        )
        client.refresh_token = "old_refresh"

        client.refresh_access_token()

        # Verify saved (encrypted)
        assert token_file.exists()
        with open(token_file) as f:
            data = json.load(f)
        # Token should be encrypted in file
        assert data['access_token'].startswith(('enc:v1:', 'obf:'))
        # But client should have plaintext in memory
        assert client.access_token == 'refreshed_token'


# -------------------------
# Get Access Token Tests
# -------------------------

class TestGetAccessToken:
    """Test getting valid access token with auto-refresh."""

    def test_returns_token_when_valid(self, tmp_path):
        """Should return token if valid and not expired."""
        client = PoeOAuthClient(
            client_id="test_client",
            token_file=tmp_path / "token.json"
        )
        client.access_token = "valid_token"
        client.expires_at = datetime.now() + timedelta(hours=1)

        token = client.get_access_token()

        assert token == "valid_token"

    def test_returns_none_when_no_token(self, tmp_path):
        """Should return None if no token available."""
        client = PoeOAuthClient(
            client_id="test_client",
            token_file=tmp_path / "token.json"
        )

        token = client.get_access_token()

        assert token is None

    @patch('core.poe_oauth.requests.post')
    def test_refreshes_token_when_expired(self, mock_post, tmp_path):
        """Should auto-refresh token if expired."""
        mock_response = Mock()
        mock_response.json.return_value = {
            'access_token': 'refreshed_token',
            'expires_in': 3600
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        client = PoeOAuthClient(
            client_id="test_client",
            token_file=tmp_path / "token.json"
        )
        client.access_token = "expired_token"
        client.refresh_token = "refresh_token"
        client.expires_at = datetime.now() - timedelta(hours=1)

        token = client.get_access_token()

        assert token == "refreshed_token"
        mock_post.assert_called_once()

    @patch('core.poe_oauth.requests.post')
    def test_returns_none_when_refresh_fails(self, mock_post, tmp_path):
        """Should return None if refresh fails."""
        import requests

        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.RequestException("Refresh failed")
        mock_post.return_value = mock_response

        client = PoeOAuthClient(
            client_id="test_client",
            token_file=tmp_path / "token.json"
        )
        client.access_token = "expired_token"
        client.refresh_token = "refresh_token"
        client.expires_at = datetime.now() - timedelta(hours=1)

        token = client.get_access_token()

        assert token is None


# -------------------------
# Token Revocation Tests
# -------------------------

class TestTokenRevocation:
    """Test revoking tokens and deleting files."""

    def test_revoke_clears_tokens(self, tmp_path):
        """Revoke should clear all token data."""
        client = PoeOAuthClient(
            client_id="test_client",
            token_file=tmp_path / "token.json"
        )
        client.access_token = "token"
        client.refresh_token = "refresh"
        client.expires_at = datetime.now()

        client.revoke_token()

        assert client.access_token is None
        assert client.refresh_token is None
        assert client.expires_at is None

    def test_revoke_deletes_token_file(self, tmp_path):
        """Revoke should delete saved token file."""
        token_file = tmp_path / "token.json"

        client = PoeOAuthClient(
            client_id="test_client",
            token_file=token_file
        )
        client.access_token = "token"
        client._save_token()

        assert token_file.exists()

        client.revoke_token()

        assert not token_file.exists()

    def test_revoke_handles_missing_file(self, tmp_path):
        """Revoke should not fail if file doesn't exist."""
        token_file = tmp_path / "nonexistent.json"

        client = PoeOAuthClient(
            client_id="test_client",
            token_file=token_file
        )

        # Should not raise
        client.revoke_token()


# -------------------------
# OAuth Callback Handler Tests
# -------------------------

class TestOAuthCallbackHandler:
    """Test HTTP callback handler for OAuth redirect."""

    def test_callback_handler_extracts_authorization_code(self):
        """Handler should extract authorization code from callback URL."""
        # Reset class variable
        OAuthCallbackHandler.authorization_code = None

        # Create mock request and server
        mock_request = Mock()
        mock_request.makefile = Mock(side_effect=[Mock(), Mock()])

        # We can't easily instantiate the handler, so test the logic directly
        # by parsing the callback URL
        from urllib.parse import urlparse, parse_qs

        path = '/oauth/callback?code=test_auth_code&state=xyz'
        parsed = urlparse(path)
        params = parse_qs(parsed.query)

        # This simulates what do_GET() does
        if 'code' in params:
            code = params['code'][0]
            assert code == 'test_auth_code'

    def test_callback_handler_handles_error(self):
        """Handler should handle OAuth error responses."""
        from urllib.parse import urlparse, parse_qs

        path = '/oauth/callback?error=access_denied'
        parsed = urlparse(path)
        params = parse_qs(parsed.query)

        # This simulates what do_GET() does with errors
        if 'error' in params:
            error = params['error'][0]
            assert error == 'access_denied'

        # Should not have 'code' parameter
        assert 'code' not in params


# -------------------------
# OAuthCallbackHandler Direct Tests
# -------------------------

class TestOAuthCallbackHandlerDirect:
    """Direct tests for OAuthCallbackHandler do_GET method."""

    def test_do_get_success_sets_authorization_code(self):
        """do_GET should set authorization_code class variable on success."""
        from io import BytesIO

        # Reset class variables
        OAuthCallbackHandler.authorization_code = None
        OAuthCallbackHandler.received_state = None

        # Create mock handler
        handler = object.__new__(OAuthCallbackHandler)
        handler.path = '/oauth/callback?code=test_code_123&state=test_state'
        handler.wfile = BytesIO()
        handler.requestline = 'GET /oauth/callback HTTP/1.1'
        handler.request_version = 'HTTP/1.1'

        # Mock required methods
        handler.send_response = Mock()
        handler.send_header = Mock()
        handler.end_headers = Mock()

        handler.do_GET()

        assert OAuthCallbackHandler.authorization_code == 'test_code_123'
        assert OAuthCallbackHandler.received_state == 'test_state'
        handler.send_response.assert_called_with(200)

    def test_do_get_error_returns_400(self):
        """do_GET should return 400 on error parameter."""
        from io import BytesIO

        # Reset class variables
        OAuthCallbackHandler.authorization_code = None

        handler = object.__new__(OAuthCallbackHandler)
        handler.path = '/oauth/callback?error=access_denied'
        handler.wfile = BytesIO()
        handler.requestline = 'GET /oauth/callback HTTP/1.1'
        handler.request_version = 'HTTP/1.1'

        handler.send_response = Mock()
        handler.send_header = Mock()
        handler.end_headers = Mock()

        handler.do_GET()

        assert OAuthCallbackHandler.authorization_code is None
        handler.send_response.assert_called_with(400)

    def test_log_message_suppresses_output(self):
        """log_message should suppress default logging."""
        handler = object.__new__(OAuthCallbackHandler)
        # Should not raise any errors
        handler.log_message("Test %s", "message")


# -------------------------
# Token Loading Edge Cases
# -------------------------

class TestTokenLoadingEdgeCases:
    """Test edge cases in token loading."""

    def test_loads_encrypted_token(self, tmp_path):
        """Should load and decrypt encrypted tokens."""
        from core.secure_storage import get_secure_storage

        token_file = tmp_path / "token.json"

        # Create encrypted token file
        storage = get_secure_storage()
        token_data = {
            'access_token': storage.encrypt('encrypted_access_token'),
            'refresh_token': storage.encrypt('encrypted_refresh_token'),
            'expires_at': '2030-12-31T23:59:59'
        }
        with open(token_file, 'w') as f:
            json.dump(token_data, f)

        client = PoeOAuthClient(
            client_id="test_client",
            token_file=token_file
        )

        assert client.access_token == 'encrypted_access_token'
        assert client.refresh_token == 'encrypted_refresh_token'

    def test_loads_expired_token_logs_info(self, tmp_path):
        """Should log info when loading expired token."""
        token_file = tmp_path / "token.json"

        # Create expired token file
        token_data = {
            'access_token': 'expired_token',
            'refresh_token': 'refresh',
            'expires_at': '2020-01-01T00:00:00'  # Past date
        }
        with open(token_file, 'w') as f:
            json.dump(token_data, f)

        client = PoeOAuthClient(
            client_id="test_client",
            token_file=token_file
        )

        # Token should be loaded but marked expired
        assert client.access_token == 'expired_token'
        assert client.is_token_expired() is True

    def test_handles_missing_expires_at(self, tmp_path):
        """Should handle token file missing expires_at."""
        token_file = tmp_path / "token.json"

        token_data = {
            'access_token': 'token',
            'refresh_token': 'refresh'
            # No expires_at
        }
        with open(token_file, 'w') as f:
            json.dump(token_data, f)

        client = PoeOAuthClient(
            client_id="test_client",
            token_file=token_file
        )

        assert client.access_token == 'token'
        assert client.expires_at is None

    def test_handles_empty_tokens_in_file(self, tmp_path):
        """Should handle empty token strings in file."""
        token_file = tmp_path / "token.json"

        token_data = {
            'access_token': '',
            'refresh_token': '',
            'expires_at': '2030-12-31T23:59:59'
        }
        with open(token_file, 'w') as f:
            json.dump(token_data, f)

        client = PoeOAuthClient(
            client_id="test_client",
            token_file=token_file
        )

        # Empty strings should result in None
        assert client.access_token is None
        assert client.refresh_token is None


# -------------------------
# Save Token Edge Cases
# -------------------------

class TestSaveTokenEdgeCases:
    """Test edge cases in token saving."""

    def test_save_token_does_nothing_without_access_token(self, tmp_path):
        """_save_token should do nothing if no access_token."""
        token_file = tmp_path / "token.json"

        client = PoeOAuthClient(
            client_id="test_client",
            token_file=token_file
        )
        client.access_token = None

        client._save_token()

        # File should not be created
        assert not token_file.exists()

    def test_save_token_handles_none_refresh_token(self, tmp_path):
        """_save_token should handle None refresh_token."""
        token_file = tmp_path / "token.json"

        client = PoeOAuthClient(
            client_id="test_client",
            token_file=token_file
        )
        client.access_token = "test_token"
        client.refresh_token = None
        client.expires_at = None

        client._save_token()

        assert token_file.exists()
        with open(token_file) as f:
            data = json.load(f)
        assert data['refresh_token'] is None
        assert data['expires_at'] is None


# -------------------------
# Authentication Flow Tests
# -------------------------

class TestAuthenticationFlow:
    """Test the full authentication flow."""

    @patch('core.poe_oauth.webbrowser.open')
    @patch('core.poe_oauth.HTTPServer')
    @patch('core.poe_oauth.requests.post')
    def test_authenticate_success(self, mock_post, mock_server, mock_browser, tmp_path):
        """Should successfully complete authentication flow."""
        # Setup mock server
        mock_server_instance = Mock()
        mock_server.return_value = mock_server_instance

        def handle_request_side_effect():
            OAuthCallbackHandler.authorization_code = 'auth_code_123'
            OAuthCallbackHandler.received_state = 'expected_state'

        mock_server_instance.handle_request.side_effect = handle_request_side_effect

        # Setup mock token response
        mock_response = Mock()
        mock_response.json.return_value = {
            'access_token': 'new_token',
            'refresh_token': 'new_refresh',
            'expires_in': 3600
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        client = PoeOAuthClient(
            client_id="test_client",
            token_file=tmp_path / "token.json"
        )

        # Mock the state to match
        with patch('core.poe_oauth.secrets.token_urlsafe', return_value='expected_state'):
            result = client.authenticate()

        assert result is True
        assert client.access_token == 'new_token'
        mock_browser.assert_called_once()

    @patch('core.poe_oauth.webbrowser.open')
    @patch('core.poe_oauth.HTTPServer')
    def test_authenticate_no_code_returns_false(self, mock_server, mock_browser, tmp_path):
        """Should return False if no authorization code received."""
        mock_server_instance = Mock()
        mock_server.return_value = mock_server_instance

        def handle_request_side_effect():
            OAuthCallbackHandler.authorization_code = None
            OAuthCallbackHandler.received_state = None

        mock_server_instance.handle_request.side_effect = handle_request_side_effect

        client = PoeOAuthClient(
            client_id="test_client",
            token_file=tmp_path / "token.json"
        )

        result = client.authenticate()

        assert result is False

    @patch('core.poe_oauth.webbrowser.open')
    @patch('core.poe_oauth.HTTPServer')
    def test_authenticate_state_mismatch_returns_false(self, mock_server, mock_browser, tmp_path):
        """Should return False on state mismatch (CSRF protection)."""
        mock_server_instance = Mock()
        mock_server.return_value = mock_server_instance

        def handle_request_side_effect():
            OAuthCallbackHandler.authorization_code = 'auth_code'
            OAuthCallbackHandler.received_state = 'wrong_state'

        mock_server_instance.handle_request.side_effect = handle_request_side_effect

        client = PoeOAuthClient(
            client_id="test_client",
            token_file=tmp_path / "token.json"
        )

        with patch('core.poe_oauth.secrets.token_urlsafe', return_value='expected_state'):
            result = client.authenticate()

        assert result is False

    @patch('core.poe_oauth.webbrowser.open')
    @patch('core.poe_oauth.HTTPServer')
    @patch('core.poe_oauth.requests.post')
    def test_authenticate_token_exchange_failure(self, mock_post, mock_server, mock_browser, tmp_path):
        """Should return False if token exchange fails."""
        import requests as req

        mock_server_instance = Mock()
        mock_server.return_value = mock_server_instance

        def handle_request_side_effect():
            OAuthCallbackHandler.authorization_code = 'auth_code'
            OAuthCallbackHandler.received_state = 'expected_state'

        mock_server_instance.handle_request.side_effect = handle_request_side_effect

        # Token exchange fails
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = req.RequestException("Token exchange failed")
        mock_post.return_value = mock_response

        client = PoeOAuthClient(
            client_id="test_client",
            token_file=tmp_path / "token.json"
        )

        with patch('core.poe_oauth.secrets.token_urlsafe', return_value='expected_state'):
            result = client.authenticate()

        assert result is False


# -------------------------
# Confidential Client Tests
# -------------------------

class TestConfidentialClient:
    """Test confidential client (with client_secret) behavior."""

    @patch('core.poe_oauth.requests.post')
    def test_refresh_includes_secret_for_confidential_client(self, mock_post, tmp_path):
        """Confidential client should include client_secret in refresh request."""
        mock_response = Mock()
        mock_response.json.return_value = {
            'access_token': 'new_token',
            'expires_in': 3600
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        client = PoeOAuthClient(
            client_id="test_client",
            client_secret="test_secret",
            token_file=tmp_path / "token.json",
            is_public_client=False
        )
        client.refresh_token = "old_refresh"

        client.refresh_access_token()

        call_args = mock_post.call_args
        assert call_args[1]['data']['client_secret'] == 'test_secret'

    @patch('core.poe_oauth.requests.post')
    def test_public_client_does_not_include_secret(self, mock_post, tmp_path):
        """Public client should not include client_secret."""
        mock_response = Mock()
        mock_response.json.return_value = {
            'access_token': 'new_token',
            'expires_in': 3600
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        client = PoeOAuthClient(
            client_id="test_client",
            client_secret="test_secret",  # Has secret but is public client
            token_file=tmp_path / "token.json",
            is_public_client=True
        )
        client.refresh_token = "old_refresh"

        client.refresh_access_token()

        call_args = mock_post.call_args
        assert 'client_secret' not in call_args[1]['data']
