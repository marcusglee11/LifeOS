Param(
    [string]$LifeRoot = "C:\Users\cabra\Projects\LifeOS"
)

$DocRoot = Join-Path $LifeRoot "docs"

Write-Host "Creating LifeOS docs tree under: $DocRoot"

# Create docs root
if (-not (Test-Path -LiteralPath $DocRoot)) {
    New-Item -ItemType Directory -Path $DocRoot -Force | Out-Null
}

# Ordered category folders
$dirs = @(
    "00_foundations",
    "01_governance",
    "02_alignment",
    "03_runtime",
    "04_project_builder",
    "05_agents",
    "06_user_surface",
    "12_productisation",
    "08_manuals",
    "09_prompts",
    "10_meta",
    "99_archive"
)

foreach ($d in $dirs) {
    $path = Join-Path $DocRoot $d
    if (-not (Test-Path -LiteralPath $path)) {
        Write-Host "  - $d"
        New-Item -ItemType Directory -Path $path -Force | Out-Null
    } else {
        Write-Host "  - $d (already exists)"
    }
}

# Root README
$readmePath = Join-Path $LifeRoot "README.md"
if (-not (Test-Path -LiteralPath $readmePath)) {
    @"
This repository contains the authoritative documentation for the LifeOS system.

All specifications, governance rules, alignment layers, runtime contracts,
and engineering packets live in /docs/.

Anything outside /docs/ is non-authoritative and may be deprecated.
"@ | Set-Content -LiteralPath $readmePath -Encoding UTF8
    Write-Host "Created root README at: $readmePath"
} else {
    Write-Host "Root README already exists at: $readmePath (leaving unchanged)"
}

Write-Host "Docs tree creation complete."
