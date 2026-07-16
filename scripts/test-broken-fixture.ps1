# TDD-of-test-infrastructure #2: Deliberately break a golden-set fixture and
# confirm tests fail.
# Usage: pwsh scripts\test-broken-fixture.ps1

$ErrorActionPreference = "Stop"
$rootDir = Split-Path -Parent (Split-Path -Parent $PSCommandPath)

Write-Host "=== TDD #2: Broken-fixture test ===" -ForegroundColor Cyan

$goldenFile = Join-Path $rootDir "backend\tests\test_phase10\test_translation_golden_set.py"

# 1. Back up original
Copy-Item -Path $goldenFile -Destination "${goldenFile}.bak"
Write-Host "1/4 Backed up"

# 2. Inject broken fixture: lower test_confidence_floor threshold so T7 (0.75) still passes
# but change the assertion to always fail
$content = Get-Content -Path $goldenFile -Raw
# Replace the confidence floor assertion value to require >= 2.0 (impossible)
$content = $content -replace 'assert confidence >= 0.4', 'assert confidence >= 2.0'
$content | Set-Content -Path $goldenFile
Write-Host "2/4 Injected broken confidence floor assertion (0.4 -> 2.0)"

# 3. Run the golden-set confidence tests (expect failure)
Write-Host "3/4 Running golden-set tests (expecting failure)..."
Set-Location -Path (Join-Path $rootDir "backend")
$testsFailed = $false
try {
    $output = python -m pytest tests/test_phase10/test_translation_golden_set.py::TestTranslationGoldenSet::test_confidence_floor --maxfail=1 --tb=line -q 2>&1
    Write-Host $output
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  FAIL: Tests passed even with broken fixture" -ForegroundColor Red
        $testsFailed = $false
    } else {
        Write-Host "  PASS: Tests correctly FAILED with broken fixture" -ForegroundColor Green
        $testsFailed = $true
    }
} catch {
    Write-Host "  (pytest error expected: $_)" -ForegroundColor Yellow
    $testsFailed = $true
}
Set-Location -Path $rootDir

# 4. Restore original
Move-Item -Path "${goldenFile}.bak" -Destination $goldenFile -Force
Write-Host "4/4 Restored original"

if ($testsFailed) {
    Write-Host ""
    Write-Host "=== VERDICT: PASS - Broken golden-set fixture correctly fails CI ===" -ForegroundColor Green
    exit 0
} else {
    Write-Host ""
    Write-Host "=== VERDICT: FAIL - Broken fixture did NOT cause test failure ===" -ForegroundColor Red
    exit 1
}
