import hashlib

class Signature:
    @staticmethod
    def sign_data(data: bytes) -> bytes:
        # deterministic mock signature for v0.1
        return hashlib.sha256(data).digest()

    @staticmethod
    def verify_data(data: bytes, signature: bytes) -> bool:
        return hashlib.sha256(data).digest() == signature
