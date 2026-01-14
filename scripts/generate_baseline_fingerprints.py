import subprocess
import json
import hashlib
import sys
import os

def get_fingerprint(nodeid):
    """Run pytest on a single nodeid and extract exception info + signature."""
    cmd = ["pytest", nodeid, "--tb=short"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    # Simple parsing of short traceback
    output = result.stdout
    lines = output.splitlines()
    
    exception_type = "Unknown"
    exception_message = "No message"
    stack_frames = []
    
    found_error = False
    for i, line in enumerate(lines):
        if line.startswith("E   "):
            found_error = True
            # Extraction logic: E   ExceptionType: Message
            error_part = line[4:]
            if ":" in error_part:
                exception_type, exception_message = error_part.split(":", 1)
                exception_type = exception_type.strip()
                exception_message = exception_message.strip()
            else:
                exception_type = error_part.strip()
            
            # Look for stack frames before the error
            # In tb=short, frames are shown as:
            # path/to/file.py:line: in function
            #     code
            for j in range(i-1, 0, -1):
                prev_line = lines[j]
                if ":" in prev_line and (" in " in prev_line or prev_line.strip().replace("\\","/").startswith("runtime/")):
                    stack_frames.append(prev_line.strip())
                if len(stack_frames) >= 3:
                    break
            break
            
    # Combine for signature
    sig_base = f"{exception_type}|{exception_message}|{'|'.join(stack_frames)}"
    signature = hashlib.sha256(sig_base.encode()).hexdigest()[:16]
    
    return {
        "nodeid": nodeid,
        "type": exception_type,
        "message": exception_message,
        "signature": signature
    }

def main():
    print("Running full suite to identify failing nodeids...")
    cmd = ["pytest", "--tb=no", "-q"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    failing_nodeids = []
    for line in result.stdout.splitlines():
        if line.startswith("FAILED "):
            nodeid = line.split(" ")[1]
            failing_nodeids.append(nodeid)
            
    failing_nodeids.sort()
    print(f"Found {len(failing_nodeids)} failures.")
    
    results = []
    for nodeid in failing_nodeids:
        print(f"Fingerprinting {nodeid}...")
        results.append(get_fingerprint(nodeid))
        
    output_file = sys.argv[1] if len(sys.argv) > 1 else "fingerprints.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Results written to {output_file}")

if __name__ == "__main__":
    main()
