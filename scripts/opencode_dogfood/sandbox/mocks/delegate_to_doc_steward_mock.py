import argparse
import sys
import os

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mission", required=True)
    parser.add_argument("--mode", default="dry-run")
    parser.add_argument("--trial-type", default="trial")
    args, unknown = parser.parse_known_args()
    
    print(f"Mock Doc Steward executing mission: {args.mission}")
    
    # Generate Mock Evidence
    dummy_dir = "artifacts/ledger/dl_doc"
    os.makedirs(dummy_dir, exist_ok=True)
    with open(f"{dummy_dir}/mock_artifact_{hash(args.mission)}.txt", "w") as f:
        f.write(f"Evidence for {args.mission}")
    
    # Handle T2B write headers
    if "Add test marker line: T2B01 PASS" in args.mission:
        target = "docs/zz_scratch/opencode_dogfood_probe.md"
        with open(target, "w") as f:
            f.write("T2B01 PASS\n")
        print(f"Modified {target}")
        
    if "Append line: T2B02 PASS" in args.mission:
        target = "docs/zz_scratch/opencode_dogfood_probe.md"
        with open(target, "a") as f:
            f.write("T2B02 PASS\n")
        print(f"Appended to {target}")
        
    sys.exit(0)

if __name__ == "__main__":
    main()
