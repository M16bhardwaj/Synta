import base64
import hashlib

from cryptography.fernet import Fernet

from syntra.core.config import get_settings


class SecretBox:
    def __init__(self):
        settings = get_settings()
        if settings.encryption_key:
            key = settings.encryption_key.encode()
        else:
            seed = f"{settings.github_token}:{settings.llm_api_key}".encode()
            key = base64.urlsafe_b64encode(hashlib.sha256(seed).digest())
        self.fernet = Fernet(key)

    def encrypt(self, value: str | None) -> str | None:
        if not value:
            return None
        return self.fernet.encrypt(value.encode()).decode()

    def decrypt(self, value: str | None) -> str | None:
        if not value:
            return None
        return self.fernet.decrypt(value.encode()).decode()
