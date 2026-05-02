import re
from cryptography.fernet import Fernet
from core.config import settings

fernet = Fernet(settings.ENCRYPTION_KEY.encode())

def encrypt_secret(secret: str) -> str:
    return fernet.encrypt(secret.encode()).decode()

def decrypt_secret(encrypted_secret: str) -> str:
    return fernet.decrypt(encrypted_secret.encode()).decode()

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
