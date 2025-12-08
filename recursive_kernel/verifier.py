import subprocess
import shlex
import os
import sys

class Verifier:
    def __init__(self, test_command: str):
        self.test_command = test_command

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
                
            # Ensure we capture output to avoid spamming console, but maybe log it?
            # For this pass, we just need return code.
            result = subprocess.run(args, shell=u_shell, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"Verification failed:\n{result.stdout}\n{result.stderr}")
            return result.returncode == 0
        except Exception as e:
            print(f"Verification failed with exception: {e}")
            return False
