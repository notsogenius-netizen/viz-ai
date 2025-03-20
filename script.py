from cryptography.fernet import Fernet

# Generate a new encryption key
key = Fernet.generate_key()

# Print the key (Save it in your .env file)
print(f"Your encryption key: {key.decode()}")