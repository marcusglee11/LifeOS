def reverse_string(s):
    """Reverses a string."""
    return s[::-1]

def count_vowels(s):
    """Counts vowels in a string."""
    return sum(1 for char in s if char.lower() in 'aeiou')

def add(a, b):
    """Adds two numbers."""
    return a + b

def subtract(a, b):
    """Subtracts b from a."""
    return a - b

def to_uppercase(s):
    """Converts string to uppercase."""
    return s.upper()

def multiply(a, b):
    """Multiplies two numbers."""
    return a * b
