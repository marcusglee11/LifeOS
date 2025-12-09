from recursive_kernel.verifier import Verifier
import sys
import tempfile
import os

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


# ============ FP-005 Tests ============

def test_fp005_verifier_with_cwd():
    """FP-005: Verify Verifier respects explicitly provided cwd."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a simple test file in tmpdir
        test_file = os.path.join(tmpdir, "test.txt")
        with open(test_file, "w") as f:
            f.write("test")
        
        # Use a command that checks for test.txt existence
        if sys.platform == "win32":
            cmd = "cmd /c if exist test.txt exit 0"
        else:
            cmd = "test -f test.txt"
        
        # Without cwd, should fail (test.txt not in current dir)
        v_no_cwd = Verifier(cmd)
        # This might fail or succeed depending on cwd, so just test with cwd
        
        # With cwd set to tmpdir, should succeed
        v_with_cwd = Verifier(cmd, cwd=tmpdir)
        assert v_with_cwd.cwd == tmpdir
        result = v_with_cwd.verify()
        assert result is True

def test_fp005_verifier_default_cwd():
    """FP-005: Verify Verifier with no cwd preserves default behavior."""
    v = Verifier("cmd /c exit 0" if sys.platform == "win32" else "true")
    assert v.cwd is None  # Default should be None
    assert v.verify() is True

