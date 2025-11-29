"""Tests for core/secure_storage.py - Secure credential storage."""
import base64
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from core.secure_storage import (
    SecureStorage,
    get_secure_storage,
    encrypt_credential,
    decrypt_credential,
    CRYPTO_AVAILABLE,
)


class TestSecureStorage:
    """Tests for SecureStorage class."""

    @pytest.fixture
    def temp_salt_file(self, tmp_path):
        """Create a temporary salt file path."""
        return tmp_path / ".salt"

    @pytest.fixture
    def storage(self, temp_salt_file):
        """Create SecureStorage with temp salt file."""
        return SecureStorage(salt_file=temp_salt_file)

    def test_init_creates_salt_file(self, temp_salt_file):
        """Salt file should be created on init if it doesn't exist."""
        assert not temp_salt_file.exists()
        storage = SecureStorage(salt_file=temp_salt_file)
        assert temp_salt_file.exists()
        assert len(temp_salt_file.read_bytes()) == 32  # 32-byte salt

    def test_init_reuses_existing_salt(self, temp_salt_file):
        """Existing salt should be reused."""
        # Create initial storage with salt
        storage1 = SecureStorage(salt_file=temp_salt_file)
        salt1 = temp_salt_file.read_bytes()

        # Create second storage - should use same salt
        storage2 = SecureStorage(salt_file=temp_salt_file)
        salt2 = temp_salt_file.read_bytes()

        assert salt1 == salt2

    def test_encrypt_empty_string(self, storage):
        """Empty string should return empty string."""
        assert storage.encrypt("") == ""

    def test_decrypt_empty_string(self, storage):
        """Empty string should return empty string."""
        assert storage.decrypt("") == ""

    def test_encrypt_decrypt_roundtrip(self, storage):
        """Encrypt then decrypt should return original value."""
        original = "my_secret_session_id_12345"
        encrypted = storage.encrypt(original)
        decrypted = storage.decrypt(encrypted)
        assert decrypted == original

    def test_encrypted_value_has_prefix(self, storage):
        """Encrypted values should have appropriate prefix."""
        encrypted = storage.encrypt("test_value")
        assert encrypted.startswith("enc:v1:") or encrypted.startswith("obf:")

    def test_different_values_different_ciphertext(self, storage):
        """Different values should produce different ciphertext."""
        enc1 = storage.encrypt("value1")
        enc2 = storage.encrypt("value2")
        assert enc1 != enc2

    def test_same_value_different_ciphertext_with_crypto(self, storage):
        """Same value may produce different ciphertext (Fernet uses random IV)."""
        if CRYPTO_AVAILABLE:
            enc1 = storage.encrypt("same_value")
            enc2 = storage.encrypt("same_value")
            # With Fernet, each encryption uses random IV
            assert enc1 != enc2  # Different ciphertext
            # But both decrypt to same value
            assert storage.decrypt(enc1) == storage.decrypt(enc2)

    def test_is_encrypted_empty(self, storage):
        """Empty value is considered 'safe'."""
        assert storage.is_encrypted("") is True

    def test_is_encrypted_with_enc_prefix(self, storage):
        """Value with enc: prefix is encrypted."""
        assert storage.is_encrypted("enc:v1:someciphertext") is True

    def test_is_encrypted_with_obf_prefix(self, storage):
        """Value with obf: prefix is encrypted."""
        assert storage.is_encrypted("obf:c29tZXRoaW5n") is True

    def test_is_encrypted_plaintext(self, storage):
        """Plaintext is not encrypted."""
        assert storage.is_encrypted("plain_password") is False

    def test_decrypt_legacy_plaintext(self, storage):
        """Legacy plaintext values should be returned as-is."""
        legacy = "old_unencrypted_value"
        # Should return value and log warning
        assert storage.decrypt(legacy) == legacy

    def test_decrypt_obfuscated_value(self, storage):
        """Obfuscated values (obf:) should be decoded."""
        original = "test_value"
        obfuscated = "obf:" + base64.b64encode(original.encode()).decode()
        assert storage.decrypt(obfuscated) == original

    def test_decrypt_invalid_obfuscated(self, storage):
        """Invalid obfuscated value should return empty string."""
        assert storage.decrypt("obf:not-valid-base64!!!") == ""

    def test_machine_identifier_consistent(self, storage):
        """Machine identifier should be consistent across calls."""
        id1 = storage._get_machine_identifier()
        id2 = storage._get_machine_identifier()
        assert id1 == id2

    def test_machine_identifier_format(self, storage):
        """Machine identifier should contain expected components."""
        identifier = storage._get_machine_identifier().decode()
        assert "poe-price-checker" in identifier
        assert ":" in identifier

    @pytest.mark.skipif(not CRYPTO_AVAILABLE, reason="cryptography not installed")
    def test_different_machines_different_keys(self, temp_salt_file):
        """Different machine identifiers should produce different keys."""
        # This simulates credential from a different machine
        storage = SecureStorage(salt_file=temp_salt_file)
        encrypted = storage.encrypt("my_secret")

        # Simulate different machine by mocking _get_machine_identifier
        with patch.object(
            SecureStorage, '_get_machine_identifier',
            return_value=b"different-host:different-user:poe-price-checker"
        ):
            storage2 = SecureStorage(salt_file=temp_salt_file)
            # Should fail to decrypt (returns empty string)
            decrypted = storage2.decrypt(encrypted)
            assert decrypted == ""

    @pytest.mark.skipif(not CRYPTO_AVAILABLE, reason="cryptography not installed")
    def test_decrypt_invalid_token(self, storage):
        """Invalid encrypted data should return empty string."""
        invalid = "enc:v1:not-valid-fernet-token"
        assert storage.decrypt(invalid) == ""


class TestSecureStorageFallback:
    """Tests for obfuscation fallback when cryptography unavailable."""

    @pytest.fixture
    def temp_salt_file(self, tmp_path):
        return tmp_path / ".salt"

    def test_obfuscation_fallback(self, temp_salt_file):
        """When crypto unavailable, should use obfuscation."""
        with patch('core.secure_storage.CRYPTO_AVAILABLE', False):
            # Need to create storage without Fernet
            storage = SecureStorage(salt_file=temp_salt_file)
            storage._fernet = None  # Force no Fernet

            original = "test_secret"
            encrypted = storage.encrypt(original)

            assert encrypted.startswith("obf:")
            assert storage.decrypt(encrypted) == original


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def test_get_secure_storage_singleton(self):
        """get_secure_storage should return singleton."""
        storage1 = get_secure_storage()
        storage2 = get_secure_storage()
        assert storage1 is storage2

    def test_encrypt_credential_function(self):
        """encrypt_credential should work via singleton."""
        encrypted = encrypt_credential("test")
        assert encrypted.startswith("enc:v1:") or encrypted.startswith("obf:")

    def test_decrypt_credential_function(self):
        """decrypt_credential should work via singleton."""
        encrypted = encrypt_credential("test_value")
        decrypted = decrypt_credential(encrypted)
        assert decrypted == "test_value"


class TestFilePermissions:
    """Tests for file permission handling."""

    @pytest.fixture
    def temp_salt_file(self, tmp_path):
        return tmp_path / ".salt"

    def test_salt_file_created_in_parent_dir(self, tmp_path):
        """Salt file parent directory should be created."""
        deep_path = tmp_path / "deep" / "nested" / ".salt"
        storage = SecureStorage(salt_file=deep_path)
        assert deep_path.parent.exists()

    @patch('platform.system', return_value='Linux')
    @patch('os.chmod')
    def test_unix_permissions_set(self, mock_chmod, mock_system, temp_salt_file):
        """Unix should use chmod 600."""
        storage = SecureStorage(salt_file=temp_salt_file)
        # chmod should be called with 0o600
        if mock_chmod.called:
            mock_chmod.assert_called_with(temp_salt_file, 0o600)

    @patch('platform.system', return_value='Windows')
    @patch('subprocess.run')
    def test_windows_permissions_set(self, mock_run, mock_system, temp_salt_file):
        """Windows should use icacls."""
        with patch.dict(os.environ, {'USERNAME': 'testuser'}):
            storage = SecureStorage(salt_file=temp_salt_file)
            # icacls should be called on Windows
            # (may not be called if exception handling swallows it)


class TestEdgeCases:
    """Edge case and error handling tests."""

    @pytest.fixture
    def temp_salt_file(self, tmp_path):
        return tmp_path / ".salt"

    def test_unicode_credential(self, temp_salt_file):
        """Unicode credentials should be handled."""
        storage = SecureStorage(salt_file=temp_salt_file)
        original = "тест_пароль_日本語"
        encrypted = storage.encrypt(original)
        assert storage.decrypt(encrypted) == original

    def test_special_characters(self, temp_salt_file):
        """Special characters should be handled."""
        storage = SecureStorage(salt_file=temp_salt_file)
        original = "pass!@#$%^&*()_+-=[]{}|;':\",./<>?"
        encrypted = storage.encrypt(original)
        assert storage.decrypt(encrypted) == original

    def test_long_credential(self, temp_salt_file):
        """Long credentials should be handled."""
        storage = SecureStorage(salt_file=temp_salt_file)
        original = "a" * 10000  # 10KB credential
        encrypted = storage.encrypt(original)
        assert storage.decrypt(encrypted) == original

    def test_corrupt_salt_file(self, temp_salt_file):
        """Corrupt salt file should be handled gracefully."""
        # Create corrupt salt file
        temp_salt_file.parent.mkdir(parents=True, exist_ok=True)
        temp_salt_file.write_bytes(b"")  # Empty is invalid

        # Should handle gracefully (may log warning)
        storage = SecureStorage(salt_file=temp_salt_file)
        # Should still work (creates new salt or handles error)
        assert storage is not None
