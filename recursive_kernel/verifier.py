import subprocess
import shlex
import os
import sys
from typing import Optional

class Verifier:
    """
    Verifier for recursive kernel tasks.
    
    FP-005: Supports optional cwd parameter for explicit working directory control.
    """
    
    def __init__(self, test_command: str, cwd: Optional[str] = None):
        """
        Initialize the Verifier.
        
        Args:
            test_command: The command to run for verification.
                         Preferred default is "python -m pytest" for cross-platform determinism.
            cwd: Optional working directory. If None, uses current process cwd.
        """
        self.test_command = test_command
        self.cwd = cwd

    def verify(self) -> bool:
        try:
            print(f"Running verification command: {self.test_command}")
            # Use shell=True on Windows for robustness with commands (pytest, python, etc.)
            # This avoids shlex parsing issues and handled path quotes naturally by the shell.
            if sys.platform == "win32":
                args = self.test_command
                u_shell = True
            else:
                args = shlex.split(self.test_command)
                u_shell = False
                
            # FP-005: Pass cwd to subprocess.run (may be None for default behavior)
            result = subprocess.run(args, shell=u_shell, capture_output=True, text=True, cwd=self.cwd)
            if result.returncode != 0:
                print(f"Verification failed:\n{result.stdout}\n{result.stderr}")
            return result.returncode == 0
        except Exception as e:
            print(f"Verification failed with exception: {e}")
            return False

