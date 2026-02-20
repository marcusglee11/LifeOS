from .util.crypto import Signature

def sign_payload(payload: bytes) -> bytes:
    """
    Sign arbitrary payload using cryptographic signature.
    
    Creates a cryptographic signature for the given payload bytes using
    the system's signing key. The signature can later be verified to
    ensure payload integrity and authenticity.
    
    Args:
        payload: The bytes to sign.
        
    Returns:
        The signature bytes.
        
    Example:
        >>> payload = b"Important message"
        >>> signature = sign_payload(payload)
        >>> verify_signature(payload, signature)
        True
    """
    return Signature.sign_data(payload)

def verify_signature(payload: bytes, signature: bytes) -> bool:
    """
    Verify signature against payload.
    
    Validates that the given signature was created by signing the payload
    with the system's signing key. Used to verify payload integrity and
    authenticity.
    
    Args:
        payload: The original bytes that were signed.
        signature: The signature bytes to verify.
        
    Returns:
        True if the signature is valid for the payload, False otherwise.
        
    Example:
        >>> payload = b"Important message"
        >>> signature = sign_payload(payload)
        >>> verify_signature(payload, signature)
        True
        >>> verify_signature(b"Tampered message", signature)
        False
    """
    return Signature.verify_data(payload, signature)
