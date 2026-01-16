#!/usr/bin/env python3
import os
import sys
import zipfile
import argparse
from pathlib import Path

# Determinism Constants
CANONICAL_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
EXTERNAL_ATTR_FILE = 0o644 << 16
ZIP_COMPRESSION = zipfile.ZIP_DEFLATED

def create_verify_txt(bundle_name, sidecar_name):
    content = f"""VERIFICATION INSTRUCTIONS
=========================

This package contains the canonical closure bundle and its detached digest sidecar.

1. Components:
   - {bundle_name}  (The Canonical Closure Bundle)
   - {sidecar_name}  (The Detached Digest Sidecar)

2. Verification (Windows PowerShell):
   Get-FileHash -Algorithm SHA256 .\\{bundle_name}
   # Compare output with content of {sidecar_name}

   certutil -hashfile .\\{bundle_name} SHA256
   # Compare output with content of {sidecar_name}

3. Verification (POSIX):
   sha256sum -c {sidecar_name}
   # Should output: {bundle_name}: OK

   shasum -a 256 -c {sidecar_name}
   # Should output: {bundle_name}: OK

NOTE: The canonical closure record is the inner zip ({bundle_name}).
This outer zip is a delivery wrapper to ensure the sidecar travels with the bundle.
"""
    return content

def main():
    parser = argparse.ArgumentParser(description="Create Delivery Wrapper Zip")
    parser.add_argument("--bundle", required=True, help="Path to canonical bundle zip")
    parser.add_argument("--sidecar", required=True, help="Path to sidecar .sha256")
    parser.add_argument("--context", required=False, help="Path to context/review packet md")
    parser.add_argument("--output", required=True, help="Output wrapper zip path")
    args = parser.parse_args()

    bundle_path = Path(args.bundle)
    sidecar_path = Path(args.sidecar)
    output_path = Path(args.output)
    
    if not bundle_path.exists():
        print(f"Error: Bundle not found: {bundle_path}")
        sys.exit(1)
    if not sidecar_path.exists():
        print(f"Error: Sidecar not found: {sidecar_path}")
        sys.exit(1)

    print(f"Creating Wrapper: {output_path}")
    
    with zipfile.ZipFile(output_path, 'w', ZIP_COMPRESSION) as zf:
        # 1. Add Bundle (Payload)
        print(f"Adding: payload/{bundle_path.name}")
        zinfo = zipfile.ZipInfo(f"payload/{bundle_path.name}", date_time=CANONICAL_TIMESTAMP)
        zinfo.compress_type = ZIP_COMPRESSION
        zinfo.external_attr = EXTERNAL_ATTR_FILE
        with open(bundle_path, "rb") as f:
            zf.writestr(zinfo, f.read())

        # 2. Add Sidecar (Payload)
        print(f"Adding: payload/{sidecar_path.name}")
        zinfo = zipfile.ZipInfo(f"payload/{sidecar_path.name}", date_time=CANONICAL_TIMESTAMP)
        zinfo.compress_type = ZIP_COMPRESSION
        zinfo.external_attr = EXTERNAL_ATTR_FILE
        with open(sidecar_path, "rb") as f:
            zf.writestr(zinfo, f.read())

        # 3. Add VERIFY.txt (Generated)
        print("Adding: payload/VERIFY.txt")
        verify_content = create_verify_txt(bundle_path.name, sidecar_path.name)
        zinfo = zipfile.ZipInfo("payload/VERIFY.txt", date_time=CANONICAL_TIMESTAMP)
        zinfo.compress_type = ZIP_COMPRESSION
        zinfo.external_attr = EXTERNAL_ATTR_FILE
        zf.writestr(zinfo, verify_content)
        
        # 4. Add Context (Optional)
        if args.context:
            context_path = Path(args.context)
            if context_path.exists():
                print(f"Adding: payload/{context_path.name}")
                zinfo = zipfile.ZipInfo(f"payload/{context_path.name}", date_time=CANONICAL_TIMESTAMP)
                zinfo.compress_type = ZIP_COMPRESSION
                zinfo.external_attr = EXTERNAL_ATTR_FILE
                with open(context_path, "rb") as f:
                    zf.writestr(zinfo, f.read())
            else:
                print(f"Warning: Context file not found: {context_path}")

    print("Wrapper Created Successfully.")

if __name__ == "__main__":
    main()
