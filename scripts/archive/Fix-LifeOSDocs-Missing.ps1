Param(
    [string]$LifeRoot = "C:\Users\cabra\Projects\LifeOS"
)

$DocRoot  = Join-Path $LifeRoot "docs"

$CooRoot  = "C:\Users\cabra\Projects\COOProject\coo-agent"
$CooStart = "C:\Users\cabra\Projects\COOProject\ChatGPTStartingFiles"
$CooTest  = "C:\Users\cabra\Projects\COOProject\UserTesting"

if (-not (Test-Path -LiteralPath $DocRoot)) {
    Write-Host "Docs root $DocRoot does not exist. Run Create-LifeOSDocsTree.ps1 first." -ForegroundColor Red
    exit 1
}

function Move-ByPattern {
    param(
        [Parameter(Mandatory)][string]$SearchRoot,
        [Parameter(Mandatory)][string]$Pattern,
        [Parameter(Mandatory)][string]$Destination
    )

    if (-not (Test-Path -LiteralPath $SearchRoot)) {
        Write-Host "SKIP (search root missing): `"$SearchRoot`""
        return
    }

    $file = Get-ChildItem -Path $SearchRoot -File -Recurse |
            Where-Object { $_.Name -like $Pattern } |
            Select-Object -First 1

    if ($null -ne $file) {
        $destDir = Split-Path -Path $Destination -Parent
        if (-not (Test-Path -LiteralPath $destDir)) {
            New-Item -ItemType Directory -Path $destDir -Force | Out-Null
        }
        Write-Host "MOVE (pattern '$Pattern'): `"$($file.FullName)`" -> `"$Destination`""
        Move-Item -LiteralPath $file.FullName -Destination $Destination -Force
    } else {
        Write-Host "NOT FOUND (pattern '$Pattern' under '$SearchRoot')"
    }
}

Write-Host "Running fix-up moves into $DocRoot"
Write-Host ""

# 1) COO Runtime V1.1 CLEAN BUILD (from ChatGPTStartingFiles)
Move-ByPattern `
  -SearchRoot $CooStart `
  -Pattern "COO Runtime*V1.1*CLEAN*BUILD*.md" `
  -Destination (Join-Path $DocRoot "03_runtime\COO_Runtime_V1.1_Clean_Build_Spec.md")

# 2) Stage B user-surface spec (from UserTesting)
Move-ByPattern `
  -SearchRoot $CooTest `
  -Pattern "COO Runtime*User Surface*Test Harness*.md" `
  -Destination (Join-Path $DocRoot "06_user_surface\COO_Runtime_V1.1_User_Surface_StageB_TestHarness.md")

# 3) COOSpecv1.0Final.md (runtime core spec)
Move-ByPattern `
  -SearchRoot $CooRoot `
  -Pattern "COOSpecv1.0Final*.md" `
  -Destination (Join-Path $DocRoot "03_runtime\COO_Runtime_Core_Spec_v1.0.md")

# 4) ARCHITECTURE.md (coo-agent mission orchestrator)
Move-ByPattern `
  -SearchRoot $CooRoot `
  -Pattern "ARCHITECTURE.md" `
  -Destination (Join-Path $DocRoot "05_agents\COO_Agent_Mission_Orchestrator_Arch_v0.7_Aligned.md")

Write-Host ""
Write-Host "Fix-up script completed."
