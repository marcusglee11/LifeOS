# Phase1_Reversion_Moves.ps1
# LifeOS Phase 1 — Reversioning & Deprecation Audit
# Purpose: Move/Archive stragglers and legacy structures in accordance with REVERSION_PLAN_v1.0.

param(
    [string]$RootPath = "C:\Users\cabra\Projects\LifeOS"
)

$docs    = Join-Path $RootPath "docs"
$archive = Join-Path $docs "99_archive"

Write-Host "Phase 1 Moves - starting."

# Ensure target directories exist
$targets = @(
    $archive,
    (Join-Path $archive "concept"),
    (Join-Path $archive "cso"),
    (Join-Path $archive "legacy_structures"),
    (Join-Path $docs "07_productisation")
)

foreach ($t in $targets) {
    if (-not (Test-Path $t)) {
        Write-Host "Creating directory: $t"
        New-Item -ItemType Directory -Path $t | Out-Null
    }
}

function Move-IfExists {
    param(
        [string]$OldPath,
        [string]$NewPath
    )

    $newDir = Split-Path $NewPath -Parent
    if (-not (Test-Path $newDir)) {
        Write-Host "Creating directory for move: $newDir"
        New-Item -ItemType Directory -Path $newDir | Out-Null
    }

    if (Test-Path $OldPath) {
        Write-Host "Moving:"
        Write-Host "  $OldPath"
        Write-Host "  -> $NewPath"
        Move-Item -Path $OldPath -Destination $NewPath
    } else {
        Write-Warning ("SKIP (missing): {0}" -f $OldPath)
    }
}

# 1. Root-level docs in /docs

# DocumentAudit_MINI_DIGEST1.md -> archive with version suffix
Move-IfExists `
    -OldPath (Join-Path $docs "DocumentAudit_MINI_DIGEST1.md") `
    -NewPath (Join-Path $archive "DocumentAudit_MINI_DIGEST1_v1.0.md")

# 2. Concept folder (repo root) -> archive/concept

$conceptRoot = Join-Path $RootPath "Concept"

Move-IfExists `
    -OldPath (Join-Path $conceptRoot "Distilled Opus Abstract.md") `
    -NewPath (Join-Path $archive "concept\Distilled_Opus_Abstract_v1.0.md")

Move-IfExists `
    -OldPath (Join-Path $conceptRoot "Opus LifeOS Audit Prompt and Response.md") `
    -NewPath (Join-Path $archive "concept\Opus_LifeOS_Audit_Prompt_and_Response_v1.0.md")

Move-IfExists `
    -OldPath (Join-Path $conceptRoot "Opus LifeOS Audit Prompt 2 and Response.md") `
    -NewPath (Join-Path $archive "concept\Opus_LifeOS_Audit_Prompt_2_and_Response_v1.0.md")

# 3. CSO Strategic Layer -> archive/cso

$csoRoot = Join-Path $RootPath "CSO Strategic Layer"

Move-IfExists `
    -OldPath (Join-Path $csoRoot "ChatGPTProjectPrimer.md") `
    -NewPath (Join-Path $archive "cso\ChatGPT_Project_Primer_v1.0.md")

Move-IfExists `
    -OldPath (Join-Path $csoRoot "CSO_Operating_Model_v1.md") `
    -NewPath (Join-Path $archive "cso\CSO_Operating_Model_v1.0.md")

Move-IfExists `
    -OldPath (Join-Path $csoRoot "FULL STRATEGY AUDIT PACKET v1.md") `
    -NewPath (Join-Path $archive "cso\Full_Strategy_Audit_Packet_v1.0.md")

Move-IfExists `
    -OldPath (Join-Path $csoRoot "Intent Routing Rule v1.0.md") `
    -NewPath (Join-Path $archive "cso\Intent_Routing_Rule_v1.0.md")

# 4. Productisation brief -> 07_productisation

$productRoot = Join-Path $RootPath "Productisation"

Move-IfExists `
    -OldPath (Join-Path $productRoot "PRODUCTISATION BRIEF v1.md") `
    -NewPath (Join-Path $docs "07_productisation\Productisation_Brief_v1.0.md")

# 5. Legacy auxiliary folders under /docs -> archive/legacy_structures

$legacyRoot = Join-Path $archive "legacy_structures"

$legacyFolders = @(
    "CommunicationsProtocols",
    "Governance",
    "pipelines",
    "Runtime",
    "Specs"
)

foreach ($folder in $legacyFolders) {
    $src = Join-Path $docs $folder
    $dst = Join-Path $legacyRoot $folder
    if (Test-Path $src) {
        Write-Host "Moving legacy folder:"
        Write-Host "  $src"
        Write-Host "  -> $dst"
        Move-Item -Path $src -Destination $dst
    } else {
        Write-Warning ("SKIP (missing legacy folder): {0}" -f $src)
    }
}

Write-Host "Phase 1 Moves - complete."
