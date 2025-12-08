from .util.crypto import Signature

def sign_payload(payload: bytes) -> bytes:
    return Signature.sign_data(payload)

def verify_signature(payload: bytes, signature: bytes) -> bool:
    return Signature.verify_data(payload, signature)