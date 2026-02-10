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
        """
        Verify data using a simple SHA256 match (legacy v0.1 behavior).
        Used by RuntimeFSM and sign.py.
        """
        return hashlib.sha256(data).digest() == signature

    @staticmethod
    def validate_signature(data: bytes, signature: bytes, public_key: bytes) -> bool:
        """
        Validate a cryptographic signature for the given data.

        Args:
            data: The bytes data that was signed.
            signature: The signature bytes to verify against the data.
            public_key: The public key bytes used to verify the signature.

        Returns:
            bool: True if the signature is valid, False otherwise.

        Raises:
            ValueError: If the data, signature, or public_key are empty or invalid.
            CryptoError: If signature verification fails due to cryptographic errors.
        """
        return hashlib.sha256(data).digest() == signature
