from core.security import encrypt_secret, decrypt_secret, mask_secrets

def test_encryption_decryption():
    secret = "my-super-secret-key"
    encrypted = encrypt_secret(secret)
    assert encrypted != secret
    assert decrypt_secret(encrypted) == secret

def test_mask_secrets():
    secrets = ["secret123", "token_abc"]
    text = "Connecting with secret123 and token_abc to http://token_abc@github.com"
    
    masked = mask_secrets(text, secrets)
    
    assert "secret123" not in masked
    assert "token_abc" not in masked
    assert "********" in masked
    assert "http://********@github.com" in masked

def test_mask_secrets_empty():
    text = "Nothing to hide"
    assert mask_secrets(text, []) == text
    assert mask_secrets(text, [None, ""]) == text
