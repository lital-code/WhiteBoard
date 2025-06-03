# Generate a random 256-bit AES key and save it to 'aes.key'
import os

key = os.urandom(32)  # 256-bit key
with open("aes.key", "wb") as f:
    f.write(key)

print("AES key saved to 'aes.key'")