"""
FP-3.2: AMU₀ Discipline & State Lineage
Implements deterministic, reproducible state snapshot operations.
"""
import os
import json
import shutil
import hashlib
from typing import Optional, Dict, Any


class AMU0Error(Exception):
    """Raised when AMU0 operations fail."""
    pass


class AMU0Manager:
    """
    Manages AMU₀ baseline snapshots for deterministic state lineage.
    
    Provides:
    - create_amu0_baseline: Create a baseline snapshot
    - restore_from_amu0: Restore to a baseline
    - promote_run_to_amu0: Promote a successful run to become the new baseline
    """
    
    def __init__(self, state_root: str):
        """
        Initialize AMU0 Manager.
        
        Args:
            state_root: Root directory for all runtime state.
        """
        self.state_root = state_root
        os.makedirs(state_root, exist_ok=True)
    
    def create_amu0_baseline(
        self,
        baseline_name: str,
        source_paths: list[str],
        timestamp: str
    ) -> str:
        """
        Create a new AMU₀ baseline snapshot.
        
        Args:
            baseline_name: Name for this baseline (e.g., "PRE_HARDENING")
            source_paths: List of paths to include in the snapshot
            timestamp: Required pinned timestamp (ISO format)
        
        Returns:
            Path to the created baseline directory.
        
        Raises:
            AMU0Error: If baseline creation fails or timestamp is missing.
        """
        if not timestamp:
            raise AMU0Error("Timestamp must be explicitly provided for deterministic baseline creation")

        baseline_dir = os.path.join(self.state_root, f"{baseline_name}_AMU0")
        
        if os.path.exists(baseline_dir):
            raise AMU0Error(f"Baseline {baseline_name} already exists at {baseline_dir}")
        
        os.makedirs(baseline_dir)
        
        # Create manifest
        manifest = {
            "baseline_name": baseline_name,
            "created_at": timestamp,
            "source_paths": source_paths,
            "files": []
        }
        
        # Copy files and compute checksums
        # Sort source paths for deterministic processing order
        for source_path in sorted(source_paths):
            if os.path.isfile(source_path):
                self._copy_file_to_baseline(source_path, baseline_dir, manifest)
            elif os.path.isdir(source_path):
                for root, dirs, files in os.walk(source_path):
                    # Sort dirs and files for deterministic traversal
                    dirs.sort()
                    for fname in sorted(files):
                        fpath = os.path.join(root, fname)
                        self._copy_file_to_baseline(fpath, baseline_dir, manifest)
        
        # Write manifest
        manifest_path = os.path.join(baseline_dir, "amu0_manifest.json")
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2, sort_keys=True)
        
        # Compute and store manifest checksum
        with open(manifest_path, "rb") as f:
            manifest_hash = hashlib.sha256(f.read()).hexdigest()
        
        with open(os.path.join(baseline_dir, "amu0_manifest.sha256"), "w") as f:
            f.write(manifest_hash)
        
        return baseline_dir
    
    def _copy_file_to_baseline(
        self,
        source_path: str,
        baseline_dir: str,
        manifest: Dict[str, Any]
    ) -> None:
        """Copy a file to baseline and update manifest."""
        # Compute relative path
        rel_path = os.path.basename(source_path)
        dest_path = os.path.join(baseline_dir, "files", rel_path)
        
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        shutil.copy2(source_path, dest_path)
        
        # Compute checksum
        with open(dest_path, "rb") as f:
            checksum = hashlib.sha256(f.read()).hexdigest()
        
        manifest["files"].append({
            "path": rel_path,
            "sha256": checksum,
            "size": os.path.getsize(dest_path)
        })
    
    def restore_from_amu0(self, baseline_name: str, target_dir: str) -> None:
        """
        Restore state from an AMU₀ baseline.
        
        Args:
            baseline_name: Name of the baseline to restore from
            target_dir: Directory to restore files into
        
        Raises:
            AMU0Error: If restoration fails or integrity check fails.
        """
        baseline_dir = os.path.join(self.state_root, f"{baseline_name}_AMU0")
        
        if not os.path.exists(baseline_dir):
            raise AMU0Error(f"Baseline {baseline_name} not found at {baseline_dir}")
        
        # Verify manifest integrity
        manifest_path = os.path.join(baseline_dir, "amu0_manifest.json")
        checksum_path = os.path.join(baseline_dir, "amu0_manifest.sha256")
        
        with open(manifest_path, "rb") as f:
            actual_hash = hashlib.sha256(f.read()).hexdigest()
        
        with open(checksum_path, "r") as f:
            expected_hash = f.read().strip()
        
        if actual_hash != expected_hash:
            raise AMU0Error("Manifest integrity check failed. Baseline may be corrupted.")
        
        # Load manifest
        with open(manifest_path, "r") as f:
            manifest = json.load(f)
        
        # Restore files
        os.makedirs(target_dir, exist_ok=True)
        files_dir = os.path.join(baseline_dir, "files")
        
        for file_entry in manifest["files"]:
            src = os.path.join(files_dir, file_entry["path"])
            dst = os.path.join(target_dir, file_entry["path"])
            
            # Verify file integrity
            with open(src, "rb") as f:
                actual_checksum = hashlib.sha256(f.read()).hexdigest()
            
            if actual_checksum != file_entry["sha256"]:
                raise AMU0Error(f"File integrity check failed for {file_entry['path']}")
            
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
    
    def promote_run_to_amu0(
        self,
        run_dir: str,
        new_baseline_name: str,
        timestamp: str
    ) -> str:
        """
        Promote a successful run to become a new AMU₀ baseline.
        
        Args:
            run_dir: Directory containing the successful run state
            new_baseline_name: Name for the new baseline
            timestamp: Required pinned timestamp
        
        Returns:
            Path to the new baseline directory.
        
        Raises:
            AMU0Error: If promotion fails.
        """
        if not os.path.exists(run_dir):
            raise AMU0Error(f"Run directory {run_dir} does not exist")
        
        # Collect all files in run_dir
        source_paths = []
        for root, dirs, files in os.walk(run_dir):
            # Sort for deterministic processing
            dirs.sort()
            for fname in sorted(files):
                source_paths.append(os.path.join(root, fname))
        
        return self.create_amu0_baseline(new_baseline_name, source_paths, timestamp)
    
    def verify_baseline(self, baseline_name: str) -> bool:
        """
        Verify integrity of an existing baseline.
        
        Args:
            baseline_name: Name of the baseline to verify
        
        Returns:
            True if baseline is valid, False otherwise.
        """
        baseline_dir = os.path.join(self.state_root, f"{baseline_name}_AMU0")
        
        if not os.path.exists(baseline_dir):
            return False
        
        try:
            manifest_path = os.path.join(baseline_dir, "amu0_manifest.json")
            checksum_path = os.path.join(baseline_dir, "amu0_manifest.sha256")
            
            with open(manifest_path, "rb") as f:
                actual_hash = hashlib.sha256(f.read()).hexdigest()
            
            with open(checksum_path, "r") as f:
                expected_hash = f.read().strip()
            
            if actual_hash != expected_hash:
                return False
            
            # Verify all files
            with open(manifest_path, "r") as f:
                manifest = json.load(f)
            
            files_dir = os.path.join(baseline_dir, "files")
            for file_entry in manifest["files"]:
                fpath = os.path.join(files_dir, file_entry["path"])
                if not os.path.exists(fpath):
                    return False
                
                with open(fpath, "rb") as f:
                    if hashlib.sha256(f.read()).hexdigest() != file_entry["sha256"]:
                        return False
            
            return True
        except Exception:
            return False
    
    def list_baselines(self) -> list[str]:
        """List all available baselines."""
        baselines = []
        if os.path.exists(self.state_root):
            for name in os.listdir(self.state_root):
                if name.endswith("_AMU0") and os.path.isdir(os.path.join(self.state_root, name)):
                    baselines.append(name.replace("_AMU0", ""))
        return sorted(baselines)
