<#
.SYNOPSIS
    Copies staged root files to their final locations at repo root.

.DESCRIPTION
    This script copies files from docs/.pending_root_files/ to their
    intended locations at the repository root:
    
    - validate_governance_index.py  -> tools/validate_governance_index.py
    - validate-governance-index.yml -> .github/workflows/validate-governance-index.yml
    - PULL_REQUEST_TEMPLATE.md      -> .github/PULL_REQUEST_TEMPLATE.md

.NOTES
    Run from the repository root directory:
    powershell -ExecutionPolicy Bypass -File docs/.pending_root_files/APPLY_PENDING_ROOT_FILES.ps1
#>

$ErrorActionPreference = "Stop"

# Define source and destination mappings
$fileMappings = @(
    @{
        Source = "docs/.pending_root_files/validate_governance_index.py"
        Dest   = "tools/validate_governance_index.py"
    },
    @{
        Source = "docs/.pending_root_files/validate-governance-index.yml"
        Dest   = ".github/workflows/validate-governance-index.yml"
    },
    @{
        Source = "docs/.pending_root_files/PULL_REQUEST_TEMPLATE.md"
        Dest   = ".github/PULL_REQUEST_TEMPLATE.md"
    }
)

Write-Host "`n=== Applying pending root files ===" -ForegroundColor Cyan
Write-Host ""

$successCount = 0

foreach ($mapping in $fileMappings) {
    $sourcePath = $mapping.Source
    $destPath = $mapping.Dest

    # Check source exists
    if (-not (Test-Path $sourcePath)) {
        Write-Host "[ERROR] Source file not found: $sourcePath" -ForegroundColor Red
        exit 1
    }

    # Create destination directory if needed
    $destDir = Split-Path -Parent $destPath
    if ($destDir -and -not (Test-Path $destDir)) {
        Write-Host "[CREATE] Directory: $destDir" -ForegroundColor Yellow
        New-Item -ItemType Directory -Path $destDir -Force | Out-Null
    }

    # Copy file
    Copy-Item -Path $sourcePath -Destination $destPath -Force
    Write-Host "[COPIED] $sourcePath -> $destPath" -ForegroundColor Green
    $successCount++
}

Write-Host ""
Write-Host "=== Done: $successCount file(s) copied ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor White
Write-Host "  1. Run validator:  python tools/validate_governance_index.py" -ForegroundColor Gray
Write-Host "  2. Commit changes: git add -A && git commit -m 'GOV: initial governance stewardship setup'" -ForegroundColor Gray
Write-Host "  3. Push and open PR to main" -ForegroundColor Gray
Write-Host ""
