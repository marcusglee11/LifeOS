#!/usr/bin/env python3
import os
import sys
import shutil
import argparse
import subprocess
from pathlib import Path

# Constants
FOR_CEO_DIR = Path("artifacts/for_ceo")
VALIDATOR_SCRIPT = Path("scripts/validate_review_packet.py")

def fail(msg):
    print(f"FAIL: {msg}")
    sys.exit(1)

def ensure_dir(path):
    if not path.exists():
        try:
            path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            fail(f"Could not create directory {path}: {e}")

def run_validation(packet_path):
    print(f"Validating {packet_path}...")
    try:
        # Popen to capture output if needed, but for now just check return code
        result = subprocess.run(
            [sys.executable, str(VALIDATOR_SCRIPT), str(packet_path)],
            check=False,
            capture_output=False # Let validator print to stdout
        )
        if result.returncode != 0:
            fail("Packet validation failed.")
    except Exception as e:
        fail(f"Error running validator: {e}")

def deliver_file(src, dest_dir):
    try:
        shutil.copy2(src, dest_dir)
        dest_path = dest_dir / src.name
        print(f"📦 Delivered: {dest_path}")
        return dest_path
    except Exception as e:
        fail(f"Failed to deliver {src}: {e}")

def main():
    parser = argparse.ArgumentParser(description="Review Packet Protocol Validator & Delivery Agent (RPPV)")
    parser.add_argument("packet", type=Path, help="Path to the Review Packet (.md)")
    parser.add_argument("--bundle", type=Path, help="Optional: Path to the associated closure bundle (.zip)")
    
    args = parser.parse_args()

    # 1. Validation
    if not args.packet.exists():
        fail(f"Packet not found: {args.packet}")
    
    run_validation(args.packet)

    # 2. Delivery
    ensure_dir(FOR_CEO_DIR)

    # Deliver Packet
    deliver_file(args.packet, FOR_CEO_DIR)

    # Deliver Bundle (if present)
    if args.bundle:
        if not args.bundle.exists():
            fail(f"Bundle not found: {args.bundle}")
        
        deliver_file(args.bundle, FOR_CEO_DIR)
        
        # Check and deliver sidecar
        sidecar = args.bundle.with_name(args.bundle.name + ".sha256")
        if sidecar.exists():
            deliver_file(sidecar, FOR_CEO_DIR)
        else:
            print(f"⚠️ Warning: associated .sha256 sidecar not found for {args.bundle}")

    print("\n✅ Verification & Delivery Complete.")

if __name__ == "__main__":
    main()
