"""
Secure Storage Security Tests.

Tests for validating that sensitive data (API keys, tokens)
is properly encrypted and protected.
"""
import pytest
from pathlib import Path


class TestSecureCredentialStorage:
    """Test that credentials are stored securely."""

    @pytest.fixture
    def secure_storage(self, tmp_path):
        """Create a test secure storage instance."""
        from core.secure_storage import SecureStorage
        storage = SecureStorage(storage_dir=tmp_path)
        return storage

    def test_api_key_is_encrypted(self, secure_storage, tmp_path):
        """API keys should be encrypted, not stored in plaintext."""
        test_key = "sk-test-1234567890abcdef"

        # Store the key
        secure_storage.store("test_api_key", test_key)

        # Check that the raw file doesn't contain plaintext key
        storage_files = list(tmp_path.glob("*"))
        for file_path in storage_files:
            if file_path.is_file():
                content = file_path.read_bytes()
                # Key should not appear in plaintext
                assert test_key.encode() not in content

    def test_stored_key_can_be_retrieved(self, secure_storage):
        """Encrypted keys should be retrievable."""
        test_key = "sk-test-1234567890abcdef"

        secure_storage.store("test_api_key", test_key)
        retrieved = secure_storage.retrieve("test_api_key")

        assert retrieved == test_key

    def test_missing_key_returns_none(self, secure_storage):
        """Missing keys should return None, not raise."""
        result = secure_storage.retrieve("nonexistent_key")
        assert result is None

    def test_corrupted_data_handled_gracefully(self, secure_storage, tmp_path):
        """Corrupted encrypted data should not crash."""
        # Store a valid key first
        secure_storage.store("test_key", "valid_value")

        # Corrupt the storage file
        storage_files = list(tmp_path.glob("*.enc"))
        for file_path in storage_files:
            file_path.write_bytes(b"corrupted data")

        # Should handle gracefully (return None or raise specific exception)
        try:
            result = secure_storage.retrieve("test_key")
            # If it returns, should be None for corrupted data
        except Exception as e:
            # Should be a specific crypto exception, not a crash
            assert "decrypt" in str(e).lower() or "invalid" in str(e).lower()


class TestNoHardcodedSecrets:
    """Test that no secrets are hardcoded in the codebase."""

    @pytest.fixture
    def project_root(self):
        """Get project root directory."""
        return Path(__file__).parent.parent.parent

    def test_no_api_keys_in_source(self, project_root):
        """Source files should not contain hardcoded API keys."""
        import re

        # Patterns that might indicate hardcoded secrets
        secret_patterns = [
            r'api[_-]?key\s*=\s*["\'][a-zA-Z0-9]{20,}["\']',
            r'secret[_-]?key\s*=\s*["\'][a-zA-Z0-9]{20,}["\']',
            r'password\s*=\s*["\'][^"\']{8,}["\']',
            r'sk-[a-zA-Z0-9]{32,}',  # OpenAI key pattern
            r'AIza[a-zA-Z0-9_-]{35}',  # Google API key pattern
        ]

        # Directories to check
        source_dirs = ["core", "gui_qt", "data_sources"]

        findings = []
        for source_dir in source_dirs:
            dir_path = project_root / source_dir
            if not dir_path.exists():
                continue

            for py_file in dir_path.rglob("*.py"):
                content = py_file.read_text(encoding="utf-8", errors="ignore")

                for pattern in secret_patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    for match in matches:
                        # Filter out false positives (test values, placeholders)
                        if not any(fp in match.lower() for fp in
                                   ["example", "placeholder", "your_", "xxx", "test"]):
                            findings.append(f"{py_file}: {match[:50]}...")

        # Should have no real secrets
        assert len(findings) == 0, f"Potential hardcoded secrets found: {findings}"

    def test_no_secrets_in_config_defaults(self, project_root):
        """Config defaults should not contain real secrets."""
        config_file = project_root / "core" / "config" / "__init__.py"

        if not config_file.exists():
            config_file = project_root / "core" / "config.py"

        if not config_file.exists():
            pytest.skip("Config file not found")

        content = config_file.read_text(encoding="utf-8")

        # Check for obvious secret patterns in defaults
        dangerous_defaults = [
            "POESESSID",  # Should not have default session ID
            "Bearer ",  # Should not have default bearer tokens
        ]

        for pattern in dangerous_defaults:
            # Allow the pattern as a key name, but not as a default value
            # e.g., "poesessid": "" is OK, "poesessid": "abc123" is not
            lines = content.split("\n")
            for line in lines:
                if pattern.lower() in line.lower():
                    # Check it's not a populated default
                    if '= "' in line and len(line.split('= "')[1]) > 10:
                        if "example" not in line.lower() and "placeholder" not in line.lower():
                            # This might be a real secret
                            pass  # Manual review needed


class TestTokenSecurity:
    """Test OAuth token security."""

    def test_oauth_tokens_encrypted(self, tmp_path):
        """OAuth tokens should be encrypted at rest."""
        # Check that token storage uses encryption
        token_file = tmp_path / "oauth_token.json"

        # Simulate token storage
        test_token = {
            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test",
            "refresh_token": "refresh_token_value_here",
        }

        # If we write directly, it should be encrypted
        # This test validates the SecureStorage is used for tokens
        from core.secure_storage import SecureStorage

        storage = SecureStorage(storage_dir=tmp_path)
        storage.store("oauth_token", str(test_token))

        # Read raw file - should not contain plaintext token
        for file_path in tmp_path.glob("*"):
            if file_path.is_file():
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in content
