Param(
    [string]$LifeRoot = "C:\Users\cabra\Projects\LifeOS"
)

$DocRoot    = Join-Path $LifeRoot "docs"

$CooRoot    = "C:\Users\cabra\Projects\COOProject\coo-agent"
$CooIdeas   = "C:\Users\cabra\Projects\COOProject\Ideas&Planning"
$CooStart   = "C:\Users\cabra\Projects\COOProject\ChatGPTStartingFiles"
$CooTest    = "C:\Users\cabra\Projects\COOProject\UserTesting"

$GovRoot    = "C:\Users\cabra\Projects\governance-hub"
$GovManuals = Join-Path $GovRoot "manuals"

if (-not (Test-Path -LiteralPath $DocRoot)) {
    Write-Host "Docs root $DocRoot does not exist. Run Create-LifeOSDocsTree.ps1 first." -ForegroundColor Red
    exit 1
}

function Move-IfExists {
    param(
        [Parameter(Mandatory)][string]$Source,
        [Parameter(Mandatory)][string]$Destination
    )

    if (Test-Path -LiteralPath $Source) {
        $destDir = Split-Path -Path $Destination -Parent
        if (-not (Test-Path -LiteralPath $destDir)) {
            New-Item -ItemType Directory -Path $destDir -Force | Out-Null
        }
        Write-Host "MOVE: `"$Source`" -> `"$Destination`""
        Move-Item -LiteralPath $Source -Destination $Destination -Force
    } else {
        Write-Host "SKIP (not found): `"$Source`""
    }
}

Write-Host "Migrating documents into $DocRoot"
Write-Host ""

# --------------------------------------------------
# 1. COOProject: Ideas & Planning (Alignment + old PB packet)
# --------------------------------------------------

Move-IfExists `
  (Join-Path $CooIdeas "Alignment Layer v1.4.md") `
  (Join-Path $DocRoot "02_alignment\Alignment_Layer_v1.4.md")

Move-IfExists `
  (Join-Path $CooIdeas "LifeOS_Alignment_Layer_v1.0.md") `
  (Join-Path $DocRoot "02_alignment\LifeOS_Alignment_Layer_v1.0.md")

Move-IfExists `
  (Join-Path $CooIdeas "Antigravity_Implementation_Packet_v0_9_6.md") `
  (Join-Path $DocRoot "99_archive\Antigravity_Implementation_Packet_v0.9.6.md")

# --------------------------------------------------
# 2. COOProject: ChatGPTStartingFiles (COO governance + starter docs)
# --------------------------------------------------

Move-IfExists `
  (Join-Path $CooStart "COO_Operating_Contract.md") `
  (Join-Path $DocRoot "01_governance\COO_Operating_Contract_v1.0.md")

Move-IfExists `
  (Join-Path $CooStart "COO_Expectations_Log.md") `
  (Join-Path $DocRoot "01_governance\COO_Expectations_Log.md")

Move-IfExists `
  (Join-Path $CooStart "Architecture_Skeleton.md") `
  (Join-Path $DocRoot "00_foundations\Architecture_Skeleton.md")

Move-IfExists `
  (Join-Path $CooStart "COO Runtime — V1.1 CLEAN BUILD.md") `
  (Join-Path $DocRoot "03_runtime\COO_Runtime_V1.1_Clean_Build_Spec.md")

Move-IfExists `
  (Join-Path $CooStart "README.md") `
  (Join-Path $DocRoot "10_meta\COO_Clean_Build_Readme.md")

# --------------------------------------------------
# 3. COOProject: UserTesting (User Surface / Stage B)
# --------------------------------------------------

Move-IfExists `
  (Join-Path $CooTest "COO Runtime V1.1 — User Surface Implementation (Stage B + Test Harness).md") `
  (Join-Path $DocRoot "06_user_surface\COO_Runtime_V1.1_User_Surface_StageB_TestHarness.md")

# --------------------------------------------------
# 4. coo-agent docs root (PB spec, meta, walkthrough, etc.)
# --------------------------------------------------

# Project Builder spec (clean)
Move-IfExists `
  (Join-Path $CooRoot "docs\GPTCOO_v1_1_ProjectBuilder_v0_9_FinalCleanSpec.md") `
  (Join-Path $DocRoot "04_project_builder\ProjectBuilder_Spec_v0.9_FinalClean.md")

# PB implementation packet v0.9.7 (could be in docs or docs/specs)
Move-IfExists `
  (Join-Path $CooRoot "docs\Antigravity_Implementation_Packet_v0_9_7.md") `
  (Join-Path $DocRoot "04_project_builder\Antigravity_Implementation_Packet_v0.9.7.md")

Move-IfExists `
  (Join-Path $CooRoot "docs\specs\Antigravity_Implementation_Packet_v0_9_7.md") `
  (Join-Path $DocRoot "04_project_builder\Antigravity_Implementation_Packet_v0.9.7.md")

# PB patched spec (history -> archive)
Move-IfExists `
  (Join-Path $CooRoot "docs\GPTCOO_v1_1_ProjectBuilder_v0_9_PatchedSpec.md") `
  (Join-Path $DocRoot "99_archive\ProjectBuilder_Spec_v0.9_PatchHistory.md")

# Antigravity council review packet
Move-IfExists `
  (Join-Path $CooRoot "docs\Antigravity_Council_Review_Packet_Spec_v1.0.md") `
  (Join-Path $DocRoot "01_governance\Antigravity_Council_Review_Packet_Spec_v1.0.md")

# Meta docs
Move-IfExists `
  (Join-Path $CooRoot "docs\CODE_REVIEW_STATUS.md") `
  (Join-Path $DocRoot "10_meta\CODE_REVIEW_STATUS.md")

Move-IfExists `
  (Join-Path $CooRoot "docs\governance_digest.md") `
  (Join-Path $DocRoot "10_meta\governance_digest.md")

Move-IfExists `
  (Join-Path $CooRoot "docs\IMPLEMENTATION_PLAN.md") `
  (Join-Path $DocRoot "10_meta\IMPLEMENTATION_PLAN.md")

Move-IfExists `
  (Join-Path $CooRoot "docs\TASKS.md") `
  (Join-Path $DocRoot "10_meta\TASKS.md")

Move-IfExists `
  (Join-Path $CooRoot "docs\Review_Packet_Reminder.md") `
  (Join-Path $DocRoot "10_meta\Review_Packet_Reminder.md")

Move-IfExists `
  (Join-Path $CooRoot "docs\WALKTHROUGH.md") `
  (Join-Path $DocRoot "03_runtime\WALKTHROUGH.md")

Move-IfExists `
  (Join-Path $CooRoot "docs\ARCHITECTUREold.md") `
  (Join-Path $DocRoot "99_archive\ARCHITECTUREold.md")

# --------------------------------------------------
# 5. coo-agent docs/specs (runtime spec + impl + index + COOSpec)
# --------------------------------------------------

Move-IfExists `
  (Join-Path $CooRoot "docs\specs\COO_RUNTIME_SPECIFICATION_v1.0.md") `
  (Join-Path $DocRoot "03_runtime\COO_Runtime_Spec_v1.0.md")

Move-IfExists `
  (Join-Path $CooRoot "docs\specs\IMPLEMENTATION PACKET v1.0.md") `
  (Join-Path $DocRoot "03_runtime\COO_Runtime_Implementation_Packet_v1.0.md")

Move-IfExists `
  (Join-Path $CooRoot "docs\specs\Spec_Canon_Index.md") `
  (Join-Path $DocRoot "03_runtime\COO_Runtime_Spec_Index_v1.0.md")

# COOSpec master (wherever it is under coo-agent/docs)
Move-IfExists `
  (Join-Path $CooRoot "docs\COOSpecv1.0Final.md") `
  (Join-Path $DocRoot "03_runtime\COO_Runtime_Core_Spec_v1.0.md")

Move-IfExists `
  (Join-Path $CooRoot "docs\specs\COOSpecv1.0Final.md") `
  (Join-Path $DocRoot "03_runtime\COO_Runtime_Core_Spec_v1.0.md")

# Mission Orchestrator architecture
Move-IfExists `
  (Join-Path $CooRoot "docs\ARCHITECTURE.md") `
  (Join-Path $DocRoot "05_agents\COO_Agent_Mission_Orchestrator_Arch_v0.7_Aligned.md")

# --------------------------------------------------
# 6. governance-hub (council + manuals + prompts v1.0)
# --------------------------------------------------

Move-IfExists `
  (Join-Path $GovRoot "Council_Invoke.md") `
  (Join-Path $DocRoot "01_governance\Council_Invocation_Runtime_Binding_Spec_v1.0.md")

Move-IfExists `
  (Join-Path $GovManuals "governance_runtime_manual_v1.0.md") `
  (Join-Path $DocRoot "08_manuals\Governance_Runtime_Manual_v1.0.md")

# Prompt library v1.0 (copy, don't move)
$govPrompts = Join-Path $GovRoot "prompts\v1.0"
$dstPrompts = Join-Path $DocRoot "09_prompts\v1.0"

if (Test-Path -LiteralPath $govPrompts) {
    if (-not (Test-Path -LiteralPath (Split-Path -Path $dstPrompts -Parent))) {
        New-Item -ItemType Directory -Path (Split-Path -Path $dstPrompts -Parent) -Force | Out-Null
    }
    Write-Host "COPY: `"$govPrompts`" -> `"$dstPrompts`""
    Copy-Item -LiteralPath $govPrompts -Destination $dstPrompts -Recurse -Force
} else {
    Write-Host "SKIP (prompt dir not found): `"$govPrompts`""
}

Write-Host ""
Write-Host "Migration script completed. Review the output above to confirm moves."
Write-Host "You can now treat $DocRoot as your single authoritative docs tree."
