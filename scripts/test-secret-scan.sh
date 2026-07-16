#!/usr/bin/env bash
# TDD-of-test-infrastructure #1: Plant a fake API key and confirm secret-scan fails.
#
# Usage: bash scripts/test-secret-scan.sh
#
# Creates a scratch commit with a planted sk-ant-... key in a non-source file,
# runs the secret-scan regex from ci.yml, asserts it DETECTS the leak.
# The scratch commit is NOT pushed — we `git reset` afterwards.

set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

echo "=== TDD #1: Planted-secret test ==="

# 1. Plant a fake Anthropic API key in a temporary file
PLANTED_FILE="scripts/__test_planted_secret.txt"
cat > "$PLANTED_FILE" <<'EOF'
# This is a deliberately planted fake API key for CI testing.
# It MUST trigger the secret-scan regex sk-ant-...
sk-ant-CpEF4aBcDeFgHiJkLmNoPqRsTuVwXyZa1b2c3d4e5f6g7h8i9j0k
EOF

echo "1/3 Planted fake key in ${PLANTED_FILE}"

# 2. Run the same regex as ci.yml's secret-scan step
echo "2/3 Running secret-scan regex..."
if grep -R -E "sk-ant-|DATABASE_URL=|JWT_SECRET|LLM_API_KEY|sim-service-token" "$PLANTED_FILE" 2>/dev/null; then
    echo "  PASS: Secret-scan DETECTED the planted key (expected)"
    DETECTED=true
else
    echo "  FAIL: Secret-scan did NOT detect the planted key"
    DETECTED=false
fi

# 3. Clean up
rm -f "$PLANTED_FILE"
echo "3/3 Cleaned up planted file"

if [ "$DETECTED" = true ]; then
    echo ""
    echo "=== VERDICT: PASS — Secret scan catches planted credentials ==="
    exit 0
else
    echo ""
    echo "=== VERDICT: FAIL — Secret scan did not catch planted credential ==="
    exit 1
fi
