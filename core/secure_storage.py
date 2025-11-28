"""
Secure credential storage for sensitive data like POESESSID.

Uses machine-specific encryption to protect credentials at rest.
The encryption key is derived from machine identifiers, providing
defense-in-depth against credential theft if config files are copied.
"""

import base64
import hashlib
import logging
import os
import platform
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Try to import cryptography, fall back to basic obfuscation if unavailable
try:
    from cryptography.fernet import Fernet, InvalidToken
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    logger.warning(
        "cryptography package not available. "
        "Credentials will use basic obfuscation only."
    )


class SecureStorage:
    """
    Encrypts and decrypts sensitive credentials using machine-specific keys.

    The encryption key is derived from:
    - Machine hostname
    - Username
    - A static salt stored alongside the app

    This ensures credentials encrypted on one machine cannot be decrypted
    on another, even if the config file is copied.
    """

    # Prefix to identify encrypted values
    ENCRYPTED_PREFIX = "enc:v1:"

    def __init__(self, salt_file: Optional[Path] = None):
        """
        Initialize secure storage.

        Args:
            salt_file: Path to salt file. If None, uses default location.
        """
        if salt_file is None:
            salt_file = Path.home() / ".poe_price_checker" / ".salt"

        self._salt_file = salt_file
        self._salt = self._get_or_create_salt()
        self._fernet: Optional["Fernet"] = None

        if CRYPTO_AVAILABLE:
            self._fernet = self._create_fernet()

    def _get_or_create_salt(self) -> bytes:
        """Get existing salt or create a new random one."""
        if self._salt_file.exists():
            try:
                return self._salt_file.read_bytes()
            except Exception as e:
                logger.warning(f"Failed to read salt file: {e}")

        # Create new random salt
        salt = os.urandom(32)
        try:
            self._salt_file.parent.mkdir(parents=True, exist_ok=True)
            self._salt_file.write_bytes(salt)
            # Make salt file readable only by owner
            self._restrict_file_permissions(self._salt_file)
        except Exception as e:
            logger.warning(f"Failed to save salt file: {e}")

        return salt

    def _restrict_file_permissions(self, file_path: Path) -> None:
        """
        Restrict file permissions to owner-only access.

        On Unix: chmod 600
        On Windows: Use icacls to remove inheritance and set owner-only access
        """
        try:
            if platform.system() == "Windows":
                import subprocess
                # Remove inherited permissions and grant only current user full control
                # /inheritance:r = remove inherited ACLs
                # /grant:r = replace existing permissions
                username = os.getenv("USERNAME", "")
                if username:
                    subprocess.run(
                        [
                            "icacls", str(file_path),
                            "/inheritance:r",
                            "/grant:r", f"{username}:(F)"
                        ],
                        capture_output=True,
                        check=True
                    )
                    logger.debug(f"Set Windows file permissions for {file_path}")
            else:
                os.chmod(file_path, 0o600)
                logger.debug(f"Set Unix file permissions for {file_path}")
        except Exception as e:
            logger.warning(f"Failed to set file permissions for {file_path}: {e}")

    def _get_machine_identifier(self) -> bytes:
        """
        Get a machine-specific identifier for key derivation.

        Combines hostname and username to create a unique identifier
        for this machine/user combination.
        """
        hostname = platform.node() or "unknown-host"
        username = os.getenv("USER") or os.getenv("USERNAME") or "unknown-user"

        identifier = f"{hostname}:{username}:poe-price-checker"
        return identifier.encode("utf-8")

    def _create_fernet(self) -> "Fernet":
        """Create a Fernet instance with a derived key."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self._salt,
            iterations=480000,  # OWASP recommended minimum
        )

        key = base64.urlsafe_b64encode(
            kdf.derive(self._get_machine_identifier())
        )
        return Fernet(key)

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a string credential.

        Args:
            plaintext: The credential to encrypt

        Returns:
            Encrypted string with prefix, or obfuscated string if
            cryptography is unavailable.
        """
        if not plaintext:
            return ""

        if CRYPTO_AVAILABLE and self._fernet:
            try:
                encrypted = self._fernet.encrypt(plaintext.encode("utf-8"))
                return f"{self.ENCRYPTED_PREFIX}{encrypted.decode('utf-8')}"
            except Exception as e:
                logger.error(f"Encryption failed: {e}")
                # Fall through to obfuscation

        # Basic obfuscation fallback (NOT secure, just obscures casual viewing)
        obfuscated = base64.b64encode(plaintext.encode("utf-8")).decode("utf-8")
        return f"obf:{obfuscated}"

    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt an encrypted credential.

        Args:
            ciphertext: The encrypted string (with prefix)

        Returns:
            Decrypted plaintext, or empty string on failure.
        """
        if not ciphertext:
            return ""

        # Handle encrypted format
        if ciphertext.startswith(self.ENCRYPTED_PREFIX):
            if not CRYPTO_AVAILABLE or not self._fernet:
                logger.error(
                    "Cannot decrypt: cryptography package not available"
                )
                return ""

            try:
                encrypted_data = ciphertext[len(self.ENCRYPTED_PREFIX):]
                decrypted = self._fernet.decrypt(encrypted_data.encode("utf-8"))
                return decrypted.decode("utf-8")
            except InvalidToken:
                logger.error(
                    "Decryption failed: invalid token. "
                    "Credential may have been encrypted on a different machine."
                )
                return ""
            except Exception as e:
                logger.error(f"Decryption failed: {e}")
                return ""

        # Handle obfuscated format
        if ciphertext.startswith("obf:"):
            try:
                obfuscated = ciphertext[4:]
                return base64.b64decode(obfuscated).decode("utf-8")
            except Exception as e:
                logger.error(f"Deobfuscation failed: {e}")
                return ""

        # Plain text (legacy/unencrypted) - return as-is but log warning
        if ciphertext and not ciphertext.startswith(("enc:", "obf:")):
            logger.warning(
                "Found unencrypted credential. "
                "It will be encrypted on next save."
            )
            return ciphertext

        return ""

    def is_encrypted(self, value: str) -> bool:
        """Check if a value is already encrypted."""
        if not value:
            return True  # Empty is "safe"
        return value.startswith((self.ENCRYPTED_PREFIX, "obf:"))


# Module-level singleton for convenience
_storage: Optional[SecureStorage] = None


def get_secure_storage() -> SecureStorage:
    """Get or create the global SecureStorage instance."""
    global _storage
    if _storage is None:
        _storage = SecureStorage()
    return _storage


def encrypt_credential(plaintext: str) -> str:
    """Convenience function to encrypt a credential."""
    return get_secure_storage().encrypt(plaintext)


def decrypt_credential(ciphertext: str) -> str:
    """Convenience function to decrypt a credential."""
    return get_secure_storage().decrypt(ciphertext)
