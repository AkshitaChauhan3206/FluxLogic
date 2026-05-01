import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# We use the App's Secret Key as a salt for the Master Key
def get_encryption_key(secret_key_string):
    password = secret_key_string.encode()
    salt = b'FluxLogic_Salt_2026' # Hardcoded salt for consistency
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password))
    return Fernet(key)

def encrypt_file(file_path, secret_key):
    fernet = get_encryption_key(secret_key)
    with open(file_path, "rb") as f:
        data = f.read()
    encrypted = fernet.encrypt(data)
    with open(file_path, "wb") as f:
        f.write(encrypted)

def decrypt_file_to_df(file_path, secret_key):
    import pandas as pd
    import io
    fernet = get_encryption_key(secret_key)
    with open(file_path, "rb") as f:
        encrypted_data = f.read()
    decrypted_data = fernet.decrypt(encrypted_data)
    return pd.read_csv(io.BytesIO(decrypted_data))
