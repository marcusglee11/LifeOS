import hashlib

class Signature:
    @staticmethod
    def sign_data(data: bytes) -> bytes:
        """
        Generate a cryptographic signature for the given data.

        Args:
            data: The bytes data to sign.

        Returns:
            The signature bytes generated from the data.
        """
        return hashlib.sha256(data).digest()

    @staticmethod
    def verify_data(data: bytes, signature: bytes) -> bool:
        return hashlib.sha256(data).digest() == signature
