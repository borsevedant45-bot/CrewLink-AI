# TDD-of-test-infrastructure #1: Plant a fake API key and confirm secret-scan fails.
# Usage: pwsh scripts\test-secret-scan.ps1

$ErrorActionPreference = "Stop"
$rootDir = Split-Path -Parent (Split-Path -Parent $PSCommandPath)

Write-Host "=== TDD #1: Planted-secret test ===" -ForegroundColor Cyan

# 1. Plant a fake Anthropic API key in a temporary file
$plantedFile = Join-Path $rootDir "scripts\__test_planted_secret.txt"
@"
# This is a deliberately planted fake API key for CI testing.
# It MUST trigger the secret-scan regex sk-ant-...
sk-ant-CpEF4aBcDeFgHiJkLmNoPqRsTuVwXyZa1b2c3d4e5f6g7h8i9j0k
"@ | Set-Content -Path $plantedFile

Write-Host "1/3 Planted fake key in $plantedFile"

# 2. Run the same regex as ci.yml's secret-scan step
Write-Host "2/3 Running secret-scan regex..."
$result = Select-String -Path $plantedFile -Pattern "sk-ant-|DATABASE_URL=|JWT_SECRET|LLM_API_KEY|sim-service-token"
if ($result) {
    Write-Host "  PASS: Secret-scan DETECTED the planted key (expected)" -ForegroundColor Green
    $detected = $true
} else {
    Write-Host "  FAIL: Secret-scan did NOT detect the planted key" -ForegroundColor Red
    $detected = $false
}

# 3. Clean up
Remove-Item -Path $plantedFile -Force
Write-Host "3/3 Cleaned up planted file"

if ($detected) {
    Write-Host ""
    Write-Host "=== VERDICT: PASS - Secret scan catches planted credentials ===" -ForegroundColor Green
    exit 0
} else {
    Write-Host ""
    Write-Host "=== VERDICT: FAIL - Secret scan did not catch planted credential ===" -ForegroundColor Red
    exit 1
}
