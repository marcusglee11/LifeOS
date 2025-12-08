class InvariantViolation(Exception):
    pass

def check_invariant(condition: bool, message: str):
    if not condition:
        raise InvariantViolation(f"Invariant violated: {message}")