import os
import base64
import io
import hashlib
import pandas as pd
from cryptography.fernet import Fernet

# We use a stable SHA256 hash of the App Secret to ensure the key never drifts
def get_encryption_key(secret_key_string):
    if not secret_key_string:
        secret_key_string = "fluxlogic-internal-stable-key-2026"
    
    # Hash the secret key to get a consistent 32-byte key for Fernet
    key_hash = hashlib.sha256(secret_key_string.encode()).digest()
    fernet_key = base64.urlsafe_b64encode(key_hash)
    return Fernet(fernet_key)

def encrypt_file(file_path, secret_key):
    try:
        fernet = get_encryption_key(secret_key)
        with open(file_path, "rb") as f:
            data = f.read()
        
        # Avoid double encryption
        if data.startswith(b'gAAAA'):
            return True
            
        encrypted = fernet.encrypt(data)
        with open(file_path, "wb") as f:
            f.write(encrypted)
        return True
    except Exception as e:
        print(f"Encryption failed: {e}")
        return False

def decrypt_file_to_df(file_path, secret_key):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found at {file_path}")
        
    with open(file_path, "rb") as f:
        data = f.read()
    
    # If it doesn't look like a Fernet token, try reading as raw CSV
    if not data.startswith(b'gAAAA'):
        return pd.read_csv(io.BytesIO(data))
        
    try:
        fernet = get_encryption_key(secret_key)
        decrypted_data = fernet.decrypt(data)
        return pd.read_csv(io.BytesIO(decrypted_data))
    except Exception as e:
        print(f"Decryption failed: {e}")
        # Last ditch effort: try reading raw in case it's a false positive
        try:
            return pd.read_csv(io.BytesIO(data))
        except:
            raise ValueError("Decryption failed: The security key does not match this file.")
