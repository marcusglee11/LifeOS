import pytest
from runtime.sign import sign_payload, verify_signature

def test_sign_verify_round_trip():
    payload = b"important data"
    signature = sign_payload(payload)
    
    assert verify_signature(payload, signature)
    assert not verify_signature(b"tampered data", signature)

def test_sign_determinism():
    payload = b"same data"
    sig1 = sign_payload(payload)
    sig2 = sign_payload(payload)
    assert sig1 == sig2
