import os
from cryptography.fernet import Fernet

def get_fernet():
    key = os.getenv("ENCRYPTION_KEY")
    if not key:
        raise ValueError("ENCRYPTION_KEY not set in .env")
    return Fernet(key.encode())

def encrypt_key(api_key: str) -> str:
    """Encrypt an API key before storing"""
    f = get_fernet()
    return f.encrypt(api_key.encode()).decode()

def decrypt_key(encrypted_key: str) -> str:
    """Decrypt an API key for use"""
    f = get_fernet()
    return f.decrypt(encrypted_key.encode()).decode()