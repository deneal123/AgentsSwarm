"""Minimal secret loader — reads encryption key from environment or settings."""
import os


class SecretLoader:
    def get_encryption_key(self) -> str | None:
        return os.environ.get("SESSION_ENCRYPTION_KEY") or None


secret_loader = SecretLoader()
