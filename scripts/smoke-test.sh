#!/usr/bin/env bash
# path: scripts/smoke-test.sh
# Smoke test against the *deployed* (not local) environment.
# Usage: bash scripts/smoke-test.sh <BASE_URL>
#   BASE_URL defaults to https://crewlink-ai-backend.onrender.com
#
# TDD — Doc #7 §6, Phase 12 acceptance criteria.
set -euo pipefail

BASE_URL="${1:-https://crewlink-ai-backend.onrender.com}"
PASS=0
FAIL=0

green() { echo "  ✓ $1"; ((PASS++)); }
red()   { echo "  ✗ $1"; ((FAIL++)); }

echo "=== Smoke Test: $BASE_URL ==="

# ── 1. Health / readiness ──────────────────────────────────────────────────
HEALTH=$(curl -sf "${BASE_URL}/health" 2>&1 || true)
if echo "$HEALTH" | grep -q '"status":"ok"'; then
  green "GET /health returns status=ok"
else
  red "GET /health failed: $HEALTH"
fi

# ── 2. OpenAPI docs (debug mode off for prod) ──────────────────────────────
DOCS_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}/docs" 2>&1 || true)
if [ "$DOCS_STATUS" = "404" ]; then
  green "GET /docs returns 404 (debug disabled in production)"
else
  red "GET /docs returned $DOCS_STATUS (expected 404)"
fi

# ── 3. Login endpoint exists ───────────────────────────────────────────────
LOGIN_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
  -X POST "${BASE_URL}/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"badge_code":"test","pin":"0000"}' 2>&1 || true)
if [ "$LOGIN_STATUS" = "401" ] || [ "$LOGIN_STATUS" = "422" ]; then
  green "POST /api/v1/auth/login returns $LOGIN_STATUS (auth gate works)"
else
  red "POST /api/v1/auth/login unexpected status: $LOGIN_STATUS"
fi

# ── 4. 404 on unknown route ────────────────────────────────────────────────
UNKNOWN_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
  "${BASE_URL}/api/v1/nonexistent" 2>&1 || true)
if [ "$UNKNOWN_STATUS" = "404" ]; then
  green "Unknown route returns 404"
else
  red "Unknown route returned $UNKNOWN_STATUS (expected 404)"
fi

# ── 5. CORS headers present ────────────────────────────────────────────────
CORS_HEADER=$(curl -s -I -X OPTIONS \
  "${BASE_URL}/api/v1/auth/login" \
  -H "Origin: https://crewlink-ai-frontend.onrender.com" \
  -H "Access-Control-Request-Method: POST" 2>&1 || true)
if echo "$CORS_HEADER" | grep -qi "access-control-allow-origin"; then
  green "CORS preflight returns Access-Control-Allow-Origin"
else
  red "CORS preflight missing expected header"
fi

# ── Summary ────────────────────────────────────────────────────────────────
echo ""
echo "=== Results ==="
echo "  PASSED: $PASS"
echo "  FAILED: $FAIL"
[ "$FAIL" -eq 0 ] && echo "  STATUS: ALL CHECKS PASSED" || echo "  STATUS: SOME CHECKS FAILED"
exit $FAIL
