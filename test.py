from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
# Copy this output into ENCRYPTION_KEY