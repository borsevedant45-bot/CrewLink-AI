#!/usr/bin/env bash
# TDD-of-test-infrastructure #2: Deliberately break a golden-set fixture and
# confirm CI would fail.
#
# Usage: bash scripts/test-broken-fixture.sh
#
# Breaks the T7 translation golden-set fixture by changing the expected
# confidence to 0 (below the 0.4 floor), runs the golden-set tests,
# asserts they FAIL, then restores the fixture.

set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

echo "=== TDD #2: Broken-fixture test ==="

GOLDEN_FILE="backend/tests/test_phase10/test_translation_golden_set.py"

# 1. Back up original and inject a broken fixture
cp "$GOLDEN_FILE" "${GOLDEN_FILE}.bak"
echo "1/4 Backed up ${GOLDEN_FILE}"

sed -i 's/id="T7-ko-accessibility-quiet"/id="T7-ko-accessibility-quiet-BROKEN"/' "$GOLDEN_FILE"
sed -i '/id="T7-ko-accessibility-quiet-BROKEN"/,/^    )/s/0\.75/0.001/' "$GOLDEN_FILE"
echo "2/4 Injected broken T7 fixture (confidence set to 0.001)"

# 2. Run the golden-set tests and expect failure
echo "3/4 Running golden-set tests (expecting failure)..."
cd backend
if python -m pytest tests/test_phase10/test_translation_golden_set.py::TestTranslationGoldenSet::test_confidence_floor --maxfail=1 --tb=line -q 2>&1; then
    echo "  FAIL: Tests passed even with broken fixture"
    TESTS_FAILED=false
else
    echo "  PASS: Tests correctly FAILED with broken fixture"
    TESTS_FAILED=true
fi
cd ..

# 3. Restore original
mv "${GOLDEN_FILE}.bak" "$GOLDEN_FILE"
echo "4/4 Restored original ${GOLDEN_FILE}"

if [ "$TESTS_FAILED" = true ]; then
    echo ""
    echo "=== VERDICT: PASS — Broken golden-set fixture correctly fails CI ==="
    exit 0
else
    echo ""
    echo "=== VERDICT: FAIL — Broken fixture did NOT cause test failure ==="
    exit 1
fi
