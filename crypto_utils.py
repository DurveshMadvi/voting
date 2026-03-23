import os
import hashlib
import base64
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.backends import default_backend

class CryptoEngine:
    """Handles RSA Encryption, Digital Signatures, and SHA-256 Hashing"""
    
    def __init__(self, key_dir="keys"):
        self.key_dir = key_dir
        self.private_key_path = os.path.join(key_dir, "private_key.pem")
        self.public_key_path = os.path.join(key_dir, "public_key.pem")
        self.private_key = None
        self.public_key = None
        
        # Ensure the key directory exists
        if not os.path.exists(self.key_dir):
            os.makedirs(self.key_dir)
            
        self._load_or_generate_keys()

    def _load_or_generate_keys(self):
        """Loads RSA keys from disk, or generates a new 2048-bit pair if missing."""
        if os.path.exists(self.private_key_path) and os.path.exists(self.public_key_path):
            with open(self.private_key_path, "rb") as f:
                self.private_key = serialization.load_pem_private_key(
                    f.read(), password=None, backend=default_backend()
                )
            with open(self.public_key_path, "rb") as f:
                self.public_key = serialization.load_pem_public_key(
                    f.read(), backend=default_backend()
                )
        else:
            # Generate new 2048-bit RSA key pair
            self.private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
                backend=default_backend()
            )
            self.public_key = self.private_key.public_key()
            
            # Save Private Key
            with open(self.private_key_path, "wb") as f:
                f.write(self.private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                ))
            
            # Save Public Key
            with open(self.public_key_path, "wb") as f:
                f.write(self.public_key.public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo
                ))

    def encrypt_vote(self, vote_data: str) -> str:
        """Encrypt plain text data using RSA Public Key."""
        encrypted = self.public_key.encrypt(
            vote_data.encode('utf-8'),
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        return base64.b64encode(encrypted).decode('utf-8')

    def sign_vote(self, encrypted_vote_data: str) -> str:
        """Digitally sign the encrypted vote using the RSA Private Key."""
        signature = self.private_key.sign(
            encrypted_vote_data.encode('utf-8'),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        return base64.b64encode(signature).decode('utf-8')

    @staticmethod
    def generate_sha256_hash(data: str) -> str:
        """Generate a SHA-256 hash for data integrity."""
        return hashlib.sha256(data.encode('utf-8')).hexdigest()

    def decrypt_vote(self, encrypted_vote_data: str) -> str:
        """Decrypt vote data using the RSA Private Key."""
        encrypted_bytes = base64.b64decode(encrypted_vote_data)
        decrypted = self.private_key.decrypt(
            encrypted_bytes,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        return decrypted.decode('utf-8')

# Instantiate a global engine to be used by the app
crypto_engine = CryptoEngine()
