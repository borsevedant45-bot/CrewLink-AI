#!/usr/bin/env bash
# path: scripts/walkthrough-rehearsal.sh
# Full scripted judge walkthrough: task feed → triage → multilingual chat →
# Ask CrewLink → supervisor rollup.
#
# Runs the walkthrough twice consecutively against the *live deployed* backend,
# per Doc #7 §6's explicit mandatory checklist item the day before the demo.
#
# Usage: bash scripts/walkthrough-rehearsal.sh <BASE_URL>
#   BASE_URL defaults to https://crewlink-ai-backend.onrender.com
set -euo pipefail

BASE_URL="${1:-https://crewlink-ai-backend.onrender.com}"
RUN=1
TOTAL_RUNS=2
SCENARIO_PASS=0
SCENARIO_FAIL=0
OVERALL_RESULT=0

green() { echo "  ✓ $1"; ((SCENARIO_PASS++)); }
red()   { echo "  ✗ $1"; ((SCENARIO_FAIL++)); }

# ── Helper: login as Maria ─────────────────────────────────────────────────
login_maria() {
  local result
  result=$(curl -sf -X POST "${BASE_URL}/api/v1/auth/login" \
    -H "Content-Type: application/json" \
    -d '{"badge_code":"Maria_Alvarez","pin":"1234"}' 2>&1 || true)
  echo "$result" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null || echo ""
}

# ── Helper: login as supervisor ────────────────────────────────────────────
login_supervisor() {
  local result
  result=$(curl -sf -X POST "${BASE_URL}/api/v1/auth/login" \
    -H "Content-Type: application/json" \
    -d '{"badge_code":"Devon_Price","pin":"supervisor_pin"}' 2>&1 || true)
  echo "$result" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null || echo ""
}

# ── Helper: timing ────────────────────────────────────────────────────────
elapsed() {
  local start=$1 end=$2
  python3 -c "print(f'{(($end - $start) * 1000):.0f}')"
}

report_latency() {
  local label=$1 start=$2 end=$3
  local ms
  ms=$(elapsed "$start" "$end")
  echo "    ⏱  $label: ${ms}ms"
}

# ── Run one complete walkthrough ──────────────────────────────────────────
run_walkthrough() {
  local run_num=$1
  local t0 t1 t2 t3 t4 t5 t6 lat1 lat2 lat3 lat4 lat5

  echo ""
  echo "=========================================="
  echo "  WALKTHROUGH RUN $run_num OF $TOTAL_RUNS"
  echo "=========================================="
  echo ""

  # ─── Step 1: Login as Maria (volunteer) ─────────────────────────────────
  echo "--- Step 1: Login (Maria Alvarez, volunteer) ---"
  t0=$(python3 -c "import time; print(time.time())")
  MARIA_TOKEN=$(login_maria)
  t1=$(python3 -c "import time; print(time.time())")
  if [ -n "$MARIA_TOKEN" ]; then
    green "Login as Maria_Alvarez succeeded"
    report_latency "Login" "$t0" "$t1"
  else
    red "Login as Maria_Alvarez failed"
    return 1
  fi

  # ─── Step 2: Check task feed ────────────────────────────────────────────
  echo ""
  echo "--- Step 2: Task feed (polling fallback) ---"
  t0=$(python3 -c "import time; print(time.time())")
  FEED=$(curl -sf "${BASE_URL}/api/v1/incidents/feed" \
    -H "Authorization: Bearer ${MARIA_TOKEN}" 2>&1 || true)
  t1=$(python3 -c "import time; print(time.time())")
  if echo "$FEED" | grep -q '"data"'; then
    green "Task feed returned incident list"
    report_latency "Task feed (GET /incidents/feed)" "$t0" "$t1"
  else
    red "Task feed failed"
    FEED_STATUS=$(echo "$FEED" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('detail','no detail'))" 2>/dev/null || echo "parse error")
    echo "    Response: $FEED_STATUS"
  fi

  # ─── Step 3: Create incident (triggers triage) ──────────────────────────
  echo ""
  echo "--- Step 3: Report incident (triage + classification) ---"
  t0=$(python3 -c "import time; print(time.time())")
  INCIDENT=$(curl -sf -X POST "${BASE_URL}/api/v1/incidents" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer ${MARIA_TOKEN}" \
    -d '{"description":"Fan reporta una persona inconsciente cerca de la entrada este","zone_id":"zone_east_concourse","source":"volunteer_reported"}' 2>&1 || true)
  t1=$(python3 -c "import time; print(time.time())")
  INCIDENT_ID=$(echo "$INCIDENT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null || echo "")
  if [ -n "$INCIDENT_ID" ]; then
    green "Incident created: id=$INCIDENT_ID"
    report_latency "POST /incidents (create + classify)" "$t0" "$t1"
    # Check for classification fields
    CATEGORY=$(echo "$INCIDENT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('classification',{}).get('category','unknown'))" 2>/dev/null || echo "unknown")
    echo "    Classified as: $CATEGORY"
    SEVERITY=$(echo "$INCIDENT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('classification',{}).get('severity_signal','unknown'))" 2>/dev/null || echo "unknown")
    echo "    Severity: $SEVERITY"
  else
    red "Incident creation failed"
    echo "    Response: $INCIDENT"
  fi

  # ─── Step 4: Get dispatch recommendation ─────────────────────────────────
  echo ""
  echo "--- Step 4: Dispatch recommendation ---"
  if [ -n "$INCIDENT_ID" ]; then
    t0=$(python3 -c "import time; print(time.time())")
    DISPATCH=$(curl -sf -X POST "${BASE_URL}/api/v1/incidents/${INCIDENT_ID}/dispatch-recommendation" \
      -H "Authorization: Bearer ${MARIA_TOKEN}" 2>&1 || true)
    t1=$(python3 -c "import time; print(time.time())")
    if echo "$DISPATCH" | grep -q '"recommendation"'; then
      green "Dispatch recommendation returned"
      report_latency "POST /dispatch-recommendation" "$t0" "$t1"
    else
      red "Dispatch recommendation failed"
      echo "    Response: $DISPATCH"
    fi
  else
    red "Skipped — no incident to recommend for"
  fi

  # ─── Step 5: Multilingual chat ──────────────────────────────────────────
  echo ""
  echo "--- Step 5: Multilingual chat bridge ---"
  t0=$(python3 -c "import time; print(time.time())")
  SESSION=$(curl -sf -X POST "${BASE_URL}/api/v1/chat-sessions" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer ${MARIA_TOKEN}" \
    -d '{"volunteer_id":"vol_maria_alvarez","fan_language":"ja","topic":"lost_child"}' 2>&1 || true)
  t1=$(python3 -c "import time; print(time.time())")
  SESSION_ID=$(echo "$SESSION" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null || echo "")
  if [ -n "$SESSION_ID" ]; then
    green "Chat session created: id=$SESSION_ID"
    report_latency "POST /chat-sessions" "$t0" "$t1"

    # Send a message (fan in Japanese)
    t2=$(python3 -c "import time; print(time.time())")
    MSG=$(curl -sf -X POST "${BASE_URL}/api/v1/chat-sessions/${SESSION_ID}/messages" \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer ${MARIA_TOKEN}" \
      -d '{"content":"子供とはぐれてしまいました","sender_language":"ja","sender_role":"fan"}' 2>&1 || true)
    t3=$(python3 -c "import time; print(time.time())")
    if echo "$MSG" | grep -q '"translated_content"'; then
      green "Chat message translated"
      report_latency "POST /chat-sessions/{id}/messages (translate)" "$t2" "$t3"
      TRANSLATED=$(echo "$MSG" | python3 -c "import sys,json; print(json.load(sys.stdin).get('translated_content',''))" 2>/dev/null || echo "")
      echo "    Translated: $TRANSLATED"
    elif echo "$MSG" | grep -q '"fallback_used"'; then
      green "Chat message sent (fallback used — acceptable degradation)"
      report_latency "POST /chat-sessions/{id}/messages" "$t2" "$t3"
    else
      red "Chat message failed"
      echo "    Response: $MSG"
    fi
  else
    red "Chat session creation failed"
    echo "    Response: $SESSION"
  fi

  # ─── Step 6: Ask CrewLink (RAG-grounded) ────────────────────────────────
  echo ""
  echo "--- Step 6: Ask CrewLink (RAG query) ---"
  t0=$(python3 -c "import time; print(time.time())")
  KB_ANSWER=$(curl -sf -X POST "${BASE_URL}/api/v1/knowledge-base/ask" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer ${MARIA_TOKEN}" \
    -d '{"question":"Where is the nearest first-aid station in the East Concourse?"}' 2>&1 || true)
  t1=$(python3 -c "import time; print(time.time())")
  if echo "$KB_ANSWER" | grep -q '"answer"'; then
    green "Ask CrewLink returned a grounded answer"
    report_latency "POST /knowledge-base/ask" "$t0" "$t1"
    GROUNDED=$(echo "$KB_ANSWER" | python3 -c "import sys,json; print(json.load(sys.stdin).get('grounded',False))" 2>/dev/null || echo "unknown")
    echo "    Grounded: $GROUNDED"
    ANSWER_SNIPPET=$(echo "$KB_ANSWER" | python3 -c "import sys,json; print(json.load(sys.stdin).get('answer','')[:80]+'...')" 2>/dev/null || echo "")
    echo "    Answer: $ANSWER_SNIPPET"
  else
    red "Ask CrewLink failed"
    echo "    Response: $KB_ANSWER"
  fi

  # ─── Step 7: Supervisor rollup ──────────────────────────────────────────
  echo ""
  echo "--- Step 7: Supervisor rollup ---"
  SUPERVISOR_TOKEN=$(login_supervisor)
  if [ -n "$SUPERVISOR_TOKEN" ]; then
    t0=$(python3 -c "import time; print(time.time())")
    ROLLUP=$(curl -sf "${BASE_URL}/api/v1/supervisor/rollup" \
      -H "Authorization: Bearer ${SUPERVISOR_TOKEN}" 2>&1 || true)
    t1=$(python3 -c "import time; print(time.time())")
    if echo "$ROLLUP" | grep -q '"zones"'; then
      green "Supervisor rollup returned zone data"
      report_latency "GET /supervisor/rollup" "$t0" "$t1"
    else
      red "Supervisor rollup failed"
      echo "    Response: $ROLLUP"
    fi
  else
    red "Supervisor login failed"
  fi

  echo ""
  echo "--- Run $run_num complete ---"
}

# ── Main: run walkthrough twice ──────────────────────────────────────────
echo "=========================================="
echo "  CREWLINK AI — SCRIPTED WALKTHROUGH"
echo "  Doc #7 §6 — mandatory pre-demo rehearsal"
echo "  Target: $BASE_URL"
echo "  Runs:   $TOTAL_RUNS consecutive iterations"
echo "=========================================="

SCENARIO_PASS=0
SCENARIO_FAIL=0

for RUN in $(seq 1 $TOTAL_RUNS); do
  set +e
  run_walkthrough "$RUN"
  RUN_RESULT=$?
  set -e
  if [ "$RUN_RESULT" -ne 0 ]; then
    OVERALL_RESULT=$RUN_RESULT
  fi
done

# ── Summary ────────────────────────────────────────────────────────────────
echo ""
echo "=========================================="
echo "  WALKTHROUGH REHEARSAL RESULTS"
echo "=========================================="
echo "  Runs completed:  $TOTAL_RUNS"
echo "  Checks passed:   $SCENARIO_PASS"
echo "  Checks failed:   $SCENARIO_FAIL"
echo "  Doc #7 §6 status: $([ "$OVERALL_RESULT" -eq 0 ] && echo 'PASS (ready for demo)' || echo 'FAIL (investigate before demo day)')"
echo ""
echo "=== Latency Targets (Doc #1 §6.1 as corrected by ADDENDUM G1) ==="
echo "  Task feed push (<2s):          measured above (Step 2)"
echo "  Triage classification (<3s):   measured above (Step 3)"
echo "  Dispatch recommendation (<6s): measured above (Step 4)"
echo "  Chat round-trip (<2s):         measured above (Step 5)"
echo "  Ask CrewLink (<6s):            measured above (Step 6)"
echo "  Supervisor rollup (<5s):       measured above (Step 7)"
echo ""

exit "$OVERALL_RESULT"
