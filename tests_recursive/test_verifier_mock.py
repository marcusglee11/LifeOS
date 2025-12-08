from recursive_kernel.verifier import Verifier
import sys

def test_verifier_success():
    # Use cmd /c exit 0 which is robust on Windows with shell=True
    cmd = "cmd /c exit 0" if sys.platform == "win32" else "true"
    v = Verifier(cmd)
    assert v.verify() is True

def test_verifier_failure():
    # Use cmd /c exit 1
    cmd = "cmd /c exit 1" if sys.platform == "win32" else "false"
    v = Verifier(cmd)
    assert v.verify() is False
