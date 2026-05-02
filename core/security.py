import re
import hashlib
import os
from uuid import UUID
from cryptography.fernet import Fernet
from core.config import settings

fernet = Fernet(settings.ENCRYPTION_KEY.encode())

def hash_password(password: str, salt_uuid: UUID) -> str:
    salt = str(salt_uuid).encode()
    # Using PBKDF2 with SHA256
    pwd_hash = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt,
        100000 # iterations
    )
    return pwd_hash.hex()

def verify_password(password: str, salt_uuid: UUID, hashed_password: str) -> bool:
    return hash_password(password, salt_uuid) == hashed_password

def encrypt_secret(secret: str) -> str:
    return fernet.encrypt(secret.encode()).decode()

def decrypt_secret(encrypted_secret: str) -> str:
    try:
        return fernet.decrypt(encrypted_secret.encode()).decode()
    except Exception as e:
        raise ValueError(
            "Failed to decrypt secret. This usually means your ENCRYPTION_KEY has changed "
            "since this secret was saved. Please re-save the repository credentials in the dashboard."
        ) from e

def mask_secrets(text: str, secrets: list[str]) -> str:
    if not secrets:
        return text
    
    masked_text = text
    for secret in secrets:
        if secret:
            masked_text = masked_text.replace(secret, "********")
    
    # Also mask potential tokens in URLs like https://token@github.com
    masked_text = re.sub(r"://[^@:]+@", "://********@", masked_text)
    
    return masked_text
