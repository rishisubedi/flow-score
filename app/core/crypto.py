from cryptography.fernet import Fernet
import os

# In production, this would be injected via env variables (e.g., from AWS KMS)
# For MVP, we generate one dynamically or use a fallback if missing.
ENCRYPTION_KEY = os.environ.get("FERNET_ENCRYPTION_KEY", Fernet.generate_key().decode())
fernet = Fernet(ENCRYPTION_KEY.encode())

def encrypt_api_key(api_key: str) -> str:
    """Encrypts a plaintext API key before saving to the database."""
    return fernet.encrypt(api_key.encode()).decode()

def decrypt_api_key(encrypted_key: str) -> str:
    """Decrypts an API key retrieved from the database."""
    return fernet.decrypt(encrypted_key.encode()).decode()
