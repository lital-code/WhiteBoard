# aes_cypher.py

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import os

with open("aes.key", "rb") as f:
    key = f.read()  # חשוב: 16/24/32 בתים

def encrypt(data: bytes) -> bytes:
    nonce = os.urandom(16)  # חדש לכל הודעה
    cipher = Cipher(algorithms.AES(key), modes.CTR(nonce), backend=default_backend())
    encryptor = cipher.encryptor()
    return nonce + encryptor.update(data) + encryptor.finalize()

def decrypt(data: bytes) -> bytes:
    nonce = data[:16]
    ciphertext = data[16:]
    cipher = Cipher(algorithms.AES(key), modes.CTR(nonce), backend=default_backend())
    decryptor = cipher.decryptor()
    return decryptor.update(ciphertext) + decryptor.finalize()
