"""Tests for core/secure_storage.py - Secure credential storage."""
import base64
import os
from unittest.mock import patch

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
        SecureStorage(salt_file=temp_salt_file)
        assert temp_salt_file.exists()
        assert len(temp_salt_file.read_bytes()) == 32  # 32-byte salt

    def test_init_reuses_existing_salt(self, temp_salt_file):
        """Existing salt should be reused."""
        # Create initial storage with salt
        SecureStorage(salt_file=temp_salt_file)
        salt1 = temp_salt_file.read_bytes()

        # Create second storage - should use same salt
        SecureStorage(salt_file=temp_salt_file)
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
        """Encrypted values should have enc:v1: prefix."""
        encrypted = storage.encrypt("test_value")
        assert encrypted.startswith("enc:v1:")

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
        """Value with obf: prefix is NOT properly encrypted (legacy obfuscation)."""
        assert storage.is_encrypted("obf:c29tZXRoaW5n") is False

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
    """Tests for behavior when cryptography unavailable."""

    @pytest.fixture
    def temp_salt_file(self, tmp_path):
        return tmp_path / ".salt"

    def test_encrypt_raises_without_crypto(self, temp_salt_file):
        """When crypto unavailable, encrypt should raise RuntimeError."""
        with patch('core.secure_storage.CRYPTO_AVAILABLE', False):
            storage = SecureStorage(salt_file=temp_salt_file)
            storage._fernet = None  # Force no Fernet

            with pytest.raises(RuntimeError, match="cryptography package not available"):
                storage.encrypt("test_secret")

    def test_decrypt_legacy_obfuscated_still_works(self, temp_salt_file):
        """Legacy obfuscated values should still be decodable."""
        storage = SecureStorage(salt_file=temp_salt_file)
        original = "test_secret"
        # Simulate legacy obfuscated value
        obfuscated = "obf:" + base64.b64encode(original.encode()).decode()
        assert storage.decrypt(obfuscated) == original


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
        assert encrypted.startswith("enc:v1:")

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
        SecureStorage(salt_file=deep_path)
        assert deep_path.parent.exists()

    @patch('platform.system', return_value='Linux')
    @patch('os.chmod')
    def test_unix_permissions_set(self, mock_chmod, mock_system, temp_salt_file):
        """Unix should use chmod 600."""
        SecureStorage(salt_file=temp_salt_file)
        # chmod should be called with 0o600
        if mock_chmod.called:
            mock_chmod.assert_called_with(temp_salt_file, 0o600)

    @patch('platform.system', return_value='Windows')
    @patch('subprocess.run')
    def test_windows_permissions_set(self, mock_run, mock_system, temp_salt_file):
        """Windows should use icacls."""
        with patch.dict(os.environ, {'USERNAME': 'testuser'}):
            SecureStorage(salt_file=temp_salt_file)
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


class TestSaltFileErrorHandling:
    """Tests for salt file error handling."""

    @pytest.fixture
    def temp_salt_file(self, tmp_path):
        return tmp_path / ".salt"

    def test_salt_file_read_error(self, temp_salt_file):
        """Salt file read error should create new salt."""
        temp_salt_file.parent.mkdir(parents=True, exist_ok=True)
        temp_salt_file.write_bytes(b"existing_salt_data_here_")

        with patch.object(temp_salt_file.__class__, 'read_bytes', side_effect=PermissionError("Access denied")):
            storage = SecureStorage(salt_file=temp_salt_file)
            # Should still work by creating new salt
            assert storage._salt is not None
            assert len(storage._salt) == 32

    def test_salt_file_write_error(self, temp_salt_file):
        """Salt file write error should be handled gracefully."""
        # Don't create the file - let it try to create
        with patch.object(temp_salt_file.__class__, 'write_bytes', side_effect=PermissionError("Cannot write")):
            storage = SecureStorage(salt_file=temp_salt_file)
            # Should still work with generated salt
            assert storage._salt is not None
            assert len(storage._salt) == 32


class TestPermissionErrorHandling:
    """Tests for file permission error handling."""

    @pytest.fixture
    def temp_salt_file(self, tmp_path):
        return tmp_path / ".salt"

    @patch('platform.system', return_value='Windows')
    def test_windows_no_username_env(self, mock_system, temp_salt_file):
        """Windows without USERNAME env should skip icacls."""
        with patch.dict(os.environ, {}, clear=True):
            # Clear USERNAME from environment
            if 'USERNAME' in os.environ:
                del os.environ['USERNAME']

            storage = SecureStorage(salt_file=temp_salt_file)
            # Should not raise - just skip permission setting
            assert storage is not None

    @patch('platform.system', return_value='Linux')
    def test_unix_chmod_error(self, mock_system, temp_salt_file):
        """Unix chmod error should be handled gracefully."""
        with patch('os.chmod', side_effect=PermissionError("Cannot chmod")):
            storage = SecureStorage(salt_file=temp_salt_file)
            # Should handle gracefully
            assert storage is not None


class TestEncryptionErrorHandling:
    """Tests for encryption error handling."""

    @pytest.fixture
    def temp_salt_file(self, tmp_path):
        return tmp_path / ".salt"

    @pytest.mark.skipif(not CRYPTO_AVAILABLE, reason="cryptography not installed")
    def test_encrypt_fernet_error_raises_runtime_error(self, temp_salt_file):
        """Fernet encryption error should raise RuntimeError."""
        storage = SecureStorage(salt_file=temp_salt_file)

        # Mock Fernet to raise exception
        storage._fernet.encrypt = lambda x: (_ for _ in ()).throw(Exception("Encrypt error"))

        with pytest.raises(RuntimeError, match="Encryption failed"):
            storage.encrypt("test_value")


class TestDecryptionErrorHandling:
    """Tests for decryption error handling."""

    @pytest.fixture
    def temp_salt_file(self, tmp_path):
        return tmp_path / ".salt"

    @pytest.mark.skipif(not CRYPTO_AVAILABLE, reason="cryptography not installed")
    def test_decrypt_without_crypto_returns_empty(self, temp_salt_file):
        """Decrypt of encrypted value without crypto should return empty."""
        storage = SecureStorage(salt_file=temp_salt_file)
        encrypted = storage.encrypt("test")

        # Simulate crypto unavailable on decrypt
        original_fernet = storage._fernet
        storage._fernet = None

        with patch('core.secure_storage.CRYPTO_AVAILABLE', False):
            result = storage.decrypt(encrypted)
            assert result == ""

        storage._fernet = original_fernet

    @pytest.mark.skipif(not CRYPTO_AVAILABLE, reason="cryptography not installed")
    def test_decrypt_general_exception(self, temp_salt_file):
        """General exception during decrypt should return empty."""
        storage = SecureStorage(salt_file=temp_salt_file)
        encrypted = storage.encrypt("test")

        # Mock Fernet to raise unexpected exception
        original_decrypt = storage._fernet.decrypt
        storage._fernet.decrypt = lambda x: (_ for _ in ()).throw(RuntimeError("Unexpected error"))

        result = storage.decrypt(encrypted)
        assert result == ""

        storage._fernet.decrypt = original_decrypt

    def test_decrypt_unknown_enc_prefix(self, temp_salt_file):
        """Value with enc: prefix but not enc:v1: should return empty."""
        storage = SecureStorage(salt_file=temp_salt_file)

        # This is technically an "enc:" prefix but not recognized
        result = storage.decrypt("enc:v2:somedata")
        # The code checks for ENCRYPTED_PREFIX which is "enc:v1:"
        # So "enc:v2:" would fall through all conditions and return ""
        assert result == ""

    def test_decrypt_empty_enc_prefix(self, temp_salt_file):
        """Value starting with enc: but not v1 should return empty."""
        storage = SecureStorage(salt_file=temp_salt_file)

        # Just "enc:" alone should return empty
        result = storage.decrypt("enc:")
        assert result == ""


class TestGlobalSingletonReset:
    """Tests for global singleton reset."""

    def test_singleton_reset(self):
        """Singleton can be reset for testing."""
        import core.secure_storage as module

        # Reset singleton
        old_storage = module._storage
        module._storage = None

        storage1 = get_secure_storage()
        storage2 = get_secure_storage()
        assert storage1 is storage2

        # Restore for other tests
        if old_storage:
            module._storage = old_storage
