import sys
import difflib
from pathlib import Path

def main():
    repo_root = Path.cwd()
    file_path = repo_root / "runtime/tests/test_opencode_governance/test_phase1_contract.py"
    
    if not file_path.exists():
        print("Test file not found")
        sys.exit(1)
        
    new_content = file_path.read_text(encoding="utf-8").splitlines(keepends=True)
    
    # Reconstruct old content by inserting the lines we removed
    # We removed:
    # jit_validators:
    #   # This section isn't standard, steward_runner uses 'validators'
    # BEFORE "validators:" inside full_config_content
    
    old_content = []
    found = False
    for line in new_content:
        if "validators:" in line and "jit_validators" not in line and not found:
            # Check context to be sure it's the right place (inside full_config_content)
            # It's hard to be precise without parsing, but the file is small.
            # actually we search for the block `logging:` then `log_dir:` then `streams_dir:` 
            # then we inserted `jit_validators:`
            pass
            
    # Simpler approach: Locate the specific block text
    # The block in new content:
    # logging:
    #   log_dir: "{log_dir_str}"
    #   streams_dir: "{streams_dir_str}"
    # validators:
    
    search_block = [
        'logging:\n',
        '  log_dir: "{log_dir_str}"\n',
        '  streams_dir: "{streams_dir_str}"\n',
        'validators:\n'
    ]
    
    # We iterate and try to match
    old_content = []
    i = 0
    inserted = False
    while i < len(new_content):
        line = new_content[i]
        # Check if we match the sequence
        match = True
        if i + len(search_block) <= len(new_content):
            for j in range(len(search_block)):
                if new_content[i+j] != search_block[j]:
                    match = False
                    break
        else:
            match = False
            
        if match and not inserted:
            # We found the block, reconstruct old version
            # append the first 3 lines
            old_content.append(new_content[i])   # logging:
            old_content.append(new_content[i+1]) #   log_dir:
            old_content.append(new_content[i+2]) #   streams_dir:
            # Insert removed lines
            old_content.append('jit_validators:\n')
            old_content.append('  # This section isn\'t standard, steward_runner uses \'validators\'\n')
            # The next line in new_content is validators:, which we will append next loop/skip?
            # No, we just appended the pre-lines. 
            # Now we continue to append the rest from new_content[i+3]...
            # But wait, logic is simpler:
            i += 3 # skip the 3 lines we handled
            inserted = True
            # The next line in iteration will be 'validators:\n' which is correct for both old and new (it was after the inserted block in old, and is current line in new)
            # Actually, we processed new_content[i], [i+1], [i+2]. We inserted extra lines.
            # Next iteration should process new_content[i+3] which is 'validators:\n'.
            continue
            
        old_content.append(line)
        i += 1

    # Generate Diff
    diff = difflib.unified_diff(
        old_content, 
        new_content, 
        fromfile="runtime/tests/test_opencode_governance/test_phase1_contract.py (Original)", 
        tofile="runtime/tests/test_opencode_governance/test_phase1_contract.py (Patched)"
    )
    
    patch_path = repo_root / "artifacts/evidence/Diff_TestChanges.patch"
    with open(patch_path, "w", encoding="utf-8") as f:
        f.writelines(diff)
        
    print(f"Generated patch at {patch_path}")

if __name__ == "__main__":
    main()
