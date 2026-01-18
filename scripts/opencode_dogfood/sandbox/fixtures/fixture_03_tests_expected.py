import pytest
from generated_code import discount

def test_discount_basic():
    assert discount(100, 10) == 90.0

def test_discount_zero():
    assert discount(100, 0) == 100.0

def test_discount_full():
    assert discount(100, 100) == 0.0
