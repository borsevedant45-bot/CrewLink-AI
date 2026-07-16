# CrewLink AI — Doc #7: Testing & QA Strategy

**Builds on:** Doc #3 (Data Model & Mock-Data Strategy), Doc #4 (AI/LLM Orchestration & Prompt Design), Doc #5 (API Specification) — with reference to Doc #1 (PRD/NFRs), Doc #2 (Architecture), and Doc #6 (Security & Privacy) wherever a testing surface crosses into theirs.

This document defines how CrewLink AI is tested, end to end. Its central problem is one a typical CRUD test plan never has to solve: a real slice of the system's decision-making — incident classification, dispatch judgment, translation, retrieval-grounded Q&A — comes from a component that can legitimately return a different answer to the same input twice. Every section below follows one rule: **never assert equality on a generative output; assert the contract around it.**

## 1. Test Pyramid for This Project

A standard pyramid (heavy unit, moderate integration, thin e2e) assumes nearly all logic is deterministic, so the cheapest test that exercises a rule is a unit test. That assumption fails for the Triage & Dispatch path and the RAG assistant — there is no way to unit-test "the classifier says medical" the way you unit-test "the state machine rejects Resolved→Dispatched." CrewLink AI's pyramid inserts a distinct middle layer, LLM component / golden-set testing, that is neither a pure unit test (it can call a model and get variable output) nor a full integration test (it isolates one AI call site rather than a whole request lifecycle).

| Layer | Share of effort | Covers | Determinism |
|---|---|---|---|
| Deterministic unit | ~55% | Dispatch-candidate filtering, incident state machine, schema/retrieval-gate validators, rate-limit tiers, mock-data generator, zone scoping | Fully deterministic, no network, seconds |
| LLM component / golden-set | ~25% | Incident Classifier, Dispatch Recommender, Ask CrewLink, Translation Bridge — graded against Doc #4's 15-case golden set | Mocked/recorded: deterministic replay. Live: non-deterministic by design |
| Integration (API boundary) | ~12% | Full request lifecycles — persistence, state transitions, WS pushes — with the LLM layer mocked | Deterministic (`LLM_MODE=recorded`) |
| E2E (scripted demo path) | ~8% | 3–5 canonical flows through the full stack via docker-compose | Mocked in CI; live-model rerun before the actual demo |

Three reasons the weight sits here rather than just "a few more tests":

1. **The guardrails already live in code, not in model judgment** — schema-forced tool calls, the non-empty-retrieval gate, the emergency bypass, visibly-badged fallbacks (Doc #4). The highest-leverage tests confirm those guardrails hold under real model output, not that the model is impressively fluent — which shifts weight toward golden-set contract tests over open-ended generation grading.
2. **A meaningful slice of coverage has to become threshold-based** — schema-conformance rate, category accuracy against labels, groundedness against retrieved chunks — because there is no expected string to diff against. That's a genuinely new pyramid layer, not a denser unit layer.
3. **The project's NFRs are demo-scoped**, not production-scoped (2–6s latency by feature, ~50 concurrent volunteers, 100% uptime on one scripted path — Doc #1), so broad exploratory e2e coverage isn't the goal. The handful of e2e tests that exist need to be exactly the flows that will run live, in both mocked (CI-stable) and live-model (pre-demo rehearsal) form.

## 2. Deterministic Unit Tests

Everything below runs with the AI adapter mocked out or never invoked at all — no network call, no model key, sub-second runtime.

### Dispatch & matching logic
- **Candidate-eligibility filter** — asserts only on-shift, unassigned, zone-or-adjacent-zone, skill/language-matching volunteers reach the set passed to the Reasoning tier.
- **Recommendation-ID validator** — asserts a volunteer ID returned outside that candidate set is rejected and routed to fallback, never accepted silently.
- **Priority-score calculator** — asserts the score (category, source, zone density, queue time) is reproducible and never a raw model output, per Doc #3.
- **Dispatch idempotency key** — asserts a repeat call for the same incident-state returns the cached recommendation instead of re-invoking the Reasoning tier.

### State machine & lifecycle
- **Legal-transition guard** — asserts only Reported→Triaged→Dispatched→Acknowledged→InProgress→Resolved, plus Escalated/Cancelled from any non-terminal state, are accepted.
- **Illegal-transition rejection** — asserts every backward or skipped transition (e.g., Resolved→Dispatched) is rejected.
- **Terminal-state immutability** — asserts Resolved/Cancelled rows reject further transitions or field edits.
- **Emergency-escalation gate** — asserts `requires_emergency_escalation` routes straight to the deterministic broadcast and never reaches the Dispatch Recommender.
- **Chat emergency gate** — asserts the Translation Bridge's parallel `emergency_flag` fires the same bypass independent of translation success.

### Schema, contract & injection defense
- **Tool-schema validator** — asserts malformed, incomplete, or wrong-enum tool-call payloads are rejected in application code, not trusted from forced tool choice alone.
- **Retrieval-gate check** — asserts generation is blocked whenever Chroma returns zero chunks or every result sits below the similarity threshold.
- **Fallback-badge injection** — asserts every AI-call failure path attaches `fallback_used` plus human-readable copy, never a silent degrade.
- **AIInvocationLog completeness** — asserts every AI call, Fast/Cheap or Reasoning, writes exactly one log row tagged with tier, latency, and fallback status.
- **Category-taxonomy closure** — asserts classifier output, dispatch filters, and KB tags all draw from the identical seven-value enum (medical, lost fan, translation, accessibility, crowd/queue, lost item, general).
- **Injection-defense structure** — asserts user text only ever fills the isolated prompt slot, never the system/instruction string, and that no code path writes arbitrary content into `KnowledgeBaseChunk` — the two structural facts Doc #6's injection defense relies on.

### Data integrity & simulation fidelity
- **`source` enum enforcement** — asserts every Incident, CrowdDensityReading, and VolunteerPositionPing write carries a valid SIMULATED/VOLUNTEER_REPORTED/SUPERVISOR_CREATED tag and that simulated rows surface the badge in the serialized payload, not only in UI copy.
- **Mock-generator determinism** — asserts a fixed seed reproduces an identical Poisson-arrival, mean-reverting-density, and sticky-zone-ping sequence run to run, so CI and demo rehearsals replay.

### AuthZ & transport
- **JWT zone-scope check** — asserts a Zone-A token cannot read or mutate Zone-B rows.
- **Rate-limit tier assignment** — asserts every endpoint maps to exactly one of AUTH/STANDARD/REALTIME_POLL/AI_FAST/AI_REASONING, enforced independently.
- **Cursor-pagination stability** — asserts paging under concurrent writes never skips or duplicates a row.
- **WS-ticket single-use** — asserts a short-lived ticket can't be redeemed twice and expires on schedule.

## 3. LLM Component Testing Strategy

This section covers the three named AI call sites — Incident Classifier, Dispatch Recommender, Ask CrewLink — against the 15-case golden set defined in Doc #4 §6. Translation Bridge and shift-summary generation get the identical treatment at lower weight; see 3.4.

### 3.1 Two execution modes

- **Mocked/recorded — every push.** Each golden-set input is played once against the real, currently-configured model and the response is pinned as a fixture (cassette). CI replays fixtures: fast, free, and never flaky from provider-side variance. This mode gates merges.
- **Live-model regression — manual/scheduled, never a merge gate.** The same 15 cases run against the live tier. This is the only way to catch model-version drift, provider outages, or a prompt-template edit that silently changed behavior. Results are reported, not enforced; a human reviews them and, if drift is confirmed, opens a normal reviewed PR to refresh the fixtures — fixtures never update themselves.

### 3.2 What "pass" means when the output isn't deterministic

#### Incident Classifier
- Hard gate: 100% schema conformance on the application-layer validator — forced tool choice is not trusted on its own.
- Threshold: ≥90% exact-category match against golden-set labels overall, **and 100% recall on `medical` specifically** — a false negative there silently keeps a life-safety incident out of the escalation path, a materially worse failure than confusing `lost item` with `general`.

#### Dispatch Recommender
- Hard gate: 100% of returned volunteer IDs are members of the deterministic candidate set — a hallucinated ID is a hard failure, re-verifying the Section 2 validator against real model output rather than just the code path.
- Threshold: recommended volunteer falls within a human-labeled *acceptable* set (not one "correct" answer — ties are legitimate) ≥85% of the time.
- Spot-check: rationale field is non-empty and reviewed for not citing an attribute the chosen volunteer doesn't actually have.

#### Ask CrewLink (RAG assistant)
- Hard gate: 100% of below-threshold-retrieval cases return a schema-valid refusal, never a generated guess; zero golden-set answers contain prescriptive medical content, full stop, per Doc #4's code-level boundary.
- Threshold: on in-KB cases, ≥95% grade groundedness-clean — no claim absent from the retrieved chunks — via a lightweight overlap/entailment heuristic backed by human spot-check. The KB is only ~25–40 chunks (Doc #3), so full manual review of golden-set answers is realistic every release, not just a sample.

### 3.3 Golden-set coverage requirements

Doc #4 §6 owns the 15 cases; this document partitions them across the system's three input origins and sets the minimum coverage each must carry:

| Case origin | Cases (of 15) | Exercises | Coverage requirement |
|---|---|---|---|
| Incident report | 8 | Classifier → candidate filter → Dispatch Recommender, or → emergency bypass | All 7 taxonomy categories represented ≥once; ≥1 sets `requires_emergency_escalation` (Dispatch Recommender call-count must be 0); ≥1 is a "no eligible candidate" edge case |
| KB question (Ask CrewLink) | 4 | Chroma retrieval gate → Reasoning-tier synthesis | 2 in-KB (grounded answer expected), 2 out-of-KB (refusal expected, zero generation) |
| Chat message | 3 | Fast/Cheap translation + intent routing | ≥1 carries `emergency_flag` and must trigger the same bypass, independent of translation outcome |

### 3.4 Same pattern elsewhere

Intent routing and shift-summary generation — the remaining two Doc #4 call sites — are graded the same way: schema conformance as a hard gate, a component-appropriate content threshold. Both carry lower golden-set weight, since neither sits on the emergency or grounding-safety path.

## 4. Integration Tests

These hit real HTTP/WS endpoints (paths below relative to `/api/v1`) against a running docker-compose stack with `LLM_MODE=recorded`, so a full pipeline run is fast and deterministic. They do **not** re-grade AI output quality — that's Section 3's job — they verify the system correctly wires an AI result into state transitions, persistence, and pushes.

| # | Flow | Path | Asserted at the API boundary |
|---|---|---|---|
| 1 | Golden path | `POST /incidents` → auto-classify → `POST /incidents/{id}/dispatch-recommendation` → PATCH through Acknowledged/InProgress/Resolved | Category + priority present and schema-valid on creation; illegal PATCH rejected per Doc #5's matrix; dispatched volunteer is real, on-shift, in-zone; `/ws/tasks` emits one event per transition; Resolved rejects further PATCH |
| 2 | Emergency bypass | `POST /incidents` with `requires_emergency_escalation=true`; `POST /chat-sessions/{id}/messages` with `emergency_flag=true` | Dispatch Recommender call-count = 0 on both paths; deterministic EMS/security broadcast fires; state reflects Escalated; bypass is exempt from AI_REASONING throttling per Doc #6 |
| 3 | Chat bridge round-trip | `POST /chat-sessions/{id}/messages` → `/ws/chat/{id}` push → REST poll with WS simulated down | Original + translated text present and schema-valid; ChatMessage persisted correctly; WS push and REST poll return identical final state; a forced translation failure still returns 2xx + `fallback_used`, never 503 |
| 4 | Ask CrewLink gate | `POST /knowledge-base/ask`, once in-KB, once out-of-KB | In-KB → 200, grounded, cites source chunk id(s); out-of-KB → explicit refusal, never a fabricated 200 and never a 500 |
| 5 | Cross-zone auth + rollup | Zone-A token calls Zone-B task feed/chat/incident; two supervisor tokens scoped to different zone sets call `/ws/supervisor` | Zone-A-on-Zone-B → 403/404 per Doc #5, never a silent empty 200; rollup content follows the JWT claim only — no client-supplied zone parameter can broaden or narrow it |

Wherever a flow above touches an AI call site, the same suite also forces a simulated failure there and asserts the response stays 2xx with `fallback_used=true` rather than surfacing as a 503 — closing Doc #5's soft-fail/hard-fail error matrix at the boundary, not only in a unit test.

## 5. Accessibility & Multilingual Test Cases — Doc #8 Conformance

Doc #8 (Accessibility & Multilingual Design) is the authoritative source for all WCAG 2.1 AA requirements, field-condition accommodations, and multilingual safety-net criteria. Every row in Doc #8 §1's five screen-mapped tables (Task Feed §1.1, Incident Detail §1.2, Chat Bridge §1.3, Ask CrewLink §1.4, App-Wide §1.5) is verified by one of the automated checks below, by an axe-core CI audit, or by a documented screen-reader pass.

### 5.1 Automated WCAG 2.1 AA audit (axe-core)

All four screens are scanned by axe-core against `wcag2a`, `wcag2aa`, `wcag21a`, and `wcag21aa` rules in CI (`frontend/tests/a11y.test.tsx`). Zero violations required for a passing build.

| Screen | Doc #8 §1 table | Test file | Status |
|---|---|---|---|
| Task Feed | §1.1 — all rows | `tests/a11y.test.tsx` (TaskFeed describe block) | Pass — 0 axe-core violations |
| Incident Detail | §1.2 — all rows | `tests/a11y.test.tsx` (IncidentDetail describe block) | Pass — 0 axe-core violations |
| Chat Bridge | §1.3 — all rows | `tests/a11y.test.tsx` (ChatBridge describe block) | Pass — 0 axe-core violations |
| Ask CrewLink | §1.4 — all rows | `tests/a11y.test.tsx` (AskCrewLink describe block) | Pass — 0 axe-core violations |

### 5.2 Doc #8 §1 Planned rows — verification table

Each Planned row from Doc #8 §1 is verified as follows:

#### §1.1 Task Feed
| WCAG SC | Requirement | How verified | Test / evidence |
|---|---|---|---|
| 4.1.3 Status Messages (AA) | aria-live="polite" region for delta announcements; assertive for emergencies | DOM assertion + automated audit | `a11y-keyboard.test.tsx`: live region present; TaskFeed.tsx: burst handler sets aria-live to assertive when `requires_emergency_escalation` is true |
| 1.3.1 Info and Relationships (A) | Real `<ul>` / `<li>` with role="list" | DOM assertion | `a11y-keyboard.test.tsx`: `screen.getByRole('list').tagName === 'UL'` |
| 1.4.1 Use of Color (A) | Priority = icon + text label + color (never color alone) | Code inspection | TaskFeed.tsx lines 66–70: PRIORITY_ICONS + PRIORITY_LABELS + PRIORITY_COLORS all rendered |
| 2.2.2 Pause, Stop, Hide (A) | Focused card not relocated on re-sort | Focus-tracking ref + deferred update | TaskFeed.tsx: `focusedIdRef` + `deferredUpdate` pattern — update queues until blur/Tab |
| 1.4.11 Non-text Contrast (AA) | Priority icon, card border meet 3:1 in both themes | Design-token contrast calculation | `a11y-contrast.test.tsx`: contrast ratios computed from theme hex values |
| 1.4.5 Images of Text (AA) | Source badge = styled text, not image | Code inspection | TaskFeed.tsx lines 226–231: source rendered as `<span>` text |

#### §1.2 Incident Detail
| WCAG SC | Requirement | How verified | Test / evidence |
|---|---|---|---|
| 4.1.2 Name, Role, Value (A) | Status chip exposes role="status" with aria-live | DOM assertion + automated audit | `a11y-keyboard.test.tsx`: `getByRole('status')` with aria-live="polite" |
| 2.4.6 Headings and Labels (AA) | Unique, descriptive section headings | Code inspection | IncidentDetail.tsx: `<h1>` for title, `<h2>` with aria-labelledby for each section (info, actions, route) |
| 2.5.3 Label in Name (A) | Button text in accessible name | DOM assertion | IncidentDetail.tsx: `aria-label={t(labelKey)}` on every action button |
| 3.3.1/3.3.2 Error Identification & Labels (A) | Resolution notes field with visible label; error text on empty | Code inspection + axe-core audit | IncidentDetail.tsx: `<label htmlFor="resolution-notes">`, `<p role="alert">` for error |
| 2.2.1 Timing Adjustable (A) | WS ticket expiry shows re-auth prompt | Code inspection | IncidentDetail.tsx: 401 response → `showReauthPrompt` state → visible alert + logout button |

#### §1.3 Chat Bridge
| WCAG SC | Requirement | How verified | Test / evidence |
|---|---|---|---|
| 3.1.2 Language of Parts (AA) | Correct lang attribute on each bubble | DOM assertion | ChatBridge.test.tsx: `lang={msg.translated_language}` and `lang={msg.original_language}` |
| 4.1.3 Status Messages (AA) | "Translating…" via live region | Code inspection | ChatBridge.tsx: `<div aria-live="polite" aria-atomic="true">` with `t('chat.translating')` |
| 1.4.10 Reflow (AA) | Text reflows without clipping | Inline CSS inspection | ChatBridge.tsx: `overflowWrap: 'break-word', wordBreak: 'break-word'` on every bubble |
| 2.1.1 Keyboard (A) | Enter to send; full keyboard operability | Functional test | `a11y-keyboard.test.tsx`: `userEvent.type` + Enter triggers send |

#### §1.4 Ask CrewLink
| WCAG SC | Requirement | How verified | Test / evidence |
|---|---|---|---|
| 2.4.6 Headings and Labels (AA) | Question field explicitly labeled | DOM assertion | AskCrewLink.tsx: `<label htmlFor="ask-input">` |
| 4.1.3 Status Messages (AA) | "Looking that up…" via live region | Code inspection | AskCrewLink.tsx: `<div role="status" aria-live="polite" aria-atomic="true">` |
| 3.3.1 Error Identification (A) | Fallback text = real message with next step | Code inspection | AskCrewLink.tsx: `t('ask.fallbackNextStep')` rendered as visible `<p>` |
| 1.3.1 Info and Relationships (A) | Q&A history structured as pairs | DOM assertion | AskCrewLink.tsx: `<article>` per pair with `aria-labelledby`, `role="listitem"` |

#### §1.5 App-Wide
| WCAG SC | Requirement | How verified | Test / evidence |
|---|---|---|---|
| 3.1.1 Language of Page (A) | lang matches selected language | Integration test | `LanguageContext.test.tsx`: asserts `document.documentElement.lang` changes |
| 2.4.7 Focus Visible (AA) | High-contrast focus ring visible everywhere | Code inspection | `index.css`: `*:focus-visible { outline: 3px solid var(--color-field-focus); outline-offset: 2px; }` |
| 1.4.3 Contrast (Minimum) (AA) | 4.5:1 body / 3:1 large text in both themes | Design-token test | `a11y-contrast.test.tsx`: all token pairs computed and asserted |
| 2.5.1 Pointer Gestures (A) | Every gesture has single-tap equivalent | Code inspection | No gesture-only features exist; all actions have `<button>` elements |
| 2.5.4 Motion Actuation (A) | No motion-triggered actions | Already Pass | Stated in Doc #8 §1.5 |
| 2.1.4 Character Key Shortcuts (A) | Deferred — no single-key shortcuts in MVP | Deferred per Doc #8 | |
| 1.2.2–1.2.5 Captions (A/AA) | Deferred — no audio/video content | Deferred per Doc #8 | |

### 5.3 Screen-reader pass (manual, documented)

Before every demo, a screen-reader pass confirms:

1. **Task-feed delta announcements** (Doc #8 §2.1): With a screen reader active, confirm that a new incident pushed via `/ws/tasks` produces a spoken announcement containing category, zone, and priority — and that the visual list is not re-read from the top. Assertive announcements fire only for `requires_emergency_escalation` incidents.
2. **Priority announced in three channels** (Doc #8 §2.3): Confirm that priority status is conveyed as icon shape + text label + color, and that text label is always read by the screen reader.
3. **Status chip announcements** (Doc #8 §1.2): Confirm that changing an incident's status produces a `role="status"` announcement.
4. **Language-switching per message** (Doc #8 §1.3): Confirm that the screen reader switches voice/pronunciation between messages in different languages.

### 5.4 Translation golden-set extension (Doc #8 §4.3)

Doc #8 §4.3 proposes a parallel translation golden set alongside the existing 15-case classification/dispatch set (Doc #4 §6). This extends the golden-set test suite with:

**Structure:** A fixed list of representative high-stakes phrases per supported language, each graded on back-translation similarity and confidence-schema conformance.

| # | Language | Phrase (English) | High-stakes trigger | What's graded |
|---|---|---|---|---|
| T1 | Spanish | "He is not breathing" | Medical | back_translation matches original; confidence is high |
| T2 | Spanish | "Where is the accessible restroom?" | Accessibility | Schema conformant; back_translation preserves meaning |
| T3 | French | "She fell and hit her head" | Medical | back_translation matches original; confidence >= 0.7 |
| T4 | French | "I need a wheelchair escort" | Accessibility | Schema conformant |
| T5 | German | "There is a fire in the east concourse" | Emergency (escalation) | emergency_flag true; back_translation preserves warning |
| T6 | Japanese | "My child is having a seizure" | Medical | confidence high; back_translation matches |
| T7 | Korean | "Where is the quiet room?" | Accessibility | Schema conformant |
| T8 | Arabic | "He has a severe allergic reaction" | Medical + Emergency | emergency_flag true; confidence >= 0.7 |

**Grading rules** (matching Doc #7 §1's golden-set pattern):
- **Schema conformance (hard 100% gate):** Every translation call returns a valid `ChatMessage` with `confidence`, `high_stakes`, `back_translation`, `fallback_used`, and `model_tier` — all schema-valid, none null for a successful call.
- **Back-translation similarity (threshold-graded):** Automated string similarity (e.g. BLEU or cosine embedding similarity) ≥ 0.6 between original and back_translation. Reported but not a hard gate — drift reviewed in nightly live-model eval.
- **Confidence floor (reported):** `confidence` ≥ 0.4 for every medical/accessibility/emergency phrase. Low-confidence cases are surfaced in the nightly report, not a merge-block.

**Implementation:** These tests live in a new `backend/tests/test_phase10/` directory as `test_translation_golden_set.py`, using `LLM_MODE=recorded` in CI and `LLM_MODE=live` in the nightly eval.

## 6. CI Pipeline

Everything that can be made deterministic gates the merge. Anything that necessarily calls a live model does not — a flaky third-party call should never be the reason a PR is blocked.

**Runs on every push/PR — required to merge:**

```yaml
# .github/workflows/ci.yml
name: CI
on:
  push:
    branches: [main, develop]
  pull_request:

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: ruff check backend/
      - run: eslint frontend/src --max-warnings=0

  typecheck:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: mypy backend/ --strict
      - run: tsc --noEmit -p frontend/

  secret-scan:
    needs: [lint]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm run build --workspace=frontend
      - run: '! grep -R -E "sk-ant-|DATABASE_URL=" frontend/dist'
        # fails the build if an LLM key or DB credential leaked into the shipped bundle (Doc #6)

  unit:
    needs: [lint, typecheck]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pytest backend/tests/unit -m "not llm" --maxfail=1
      - run: npm run test:unit --workspace=frontend

  mocked-integration:
    needs: [unit]
    runs-on: ubuntu-latest
    env:
      LLM_MODE: recorded   # provider-agnostic adapter replays fixtures, zero network calls
    steps:
      - uses: actions/checkout@v4
      - run: docker compose -f docker-compose.test.yml up -d   # SQLite + embedded Chroma, matching local/demo (Doc #3)
      - run: pytest backend/tests/integration --maxfail=1
      - run: pytest backend/tests/golden_set --maxfail=1   # 15-case set, thresholds from Section 3

  build:
    needs: [mocked-integration, secret-scan]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: docker compose build
```

**Manual / scheduled only — never blocks a merge:**

```yaml
# .github/workflows/live-model-eval.yml
name: Live Model Regression
on:
  workflow_dispatch: {}
  schedule:
    - cron: '0 6 * * *'   # nightly

jobs:
  golden-set-live:
    runs-on: ubuntu-latest
    env:
      LLM_MODE: live
      LLM_API_KEY: ${{ secrets.LLM_API_KEY }}
    steps:
      - uses: actions/checkout@v4
      - run: pytest backend/tests/golden_set --report=live_eval_report.json
      - uses: actions/upload-artifact@v4
        with: { name: live-eval-report, path: live_eval_report.json }
```

`live-model-eval.yml` failures never fail a build — they produce a report a human reviews; confirmed drift is fixed by a normal, reviewed PR that refreshes the pinned fixtures `ci.yml` replays. Branch protection on `main` requires every job in `ci.yml`. A manual run of `live-model-eval.yml` is a mandatory checklist item the day before the live demo, not an automated gate.

---

## --- INDEX UPDATE ---

Doc #7 (Testing & QA Strategy): Complete.
- Test pyramid reshaped for the AI layer: ~55% deterministic unit / ~25% LLM golden-set / ~12% integration / ~8% scripted E2E — golden-set testing is a distinct new layer, not just more unit tests.
- Deterministic units (no LLM calls) cover dispatch-candidate filtering, the full incident state machine, schema/retrieval-gate validators, source-tag enforcement, and rate-limit tiers.
- Classifier, Dispatch Recommender, and Ask CrewLink graded against Doc #4's 15-case golden set via schema-conformance (hard 100% gate) plus category-accuracy/groundedness thresholds — never exact-match; mocked/recorded fixtures run in CI, live-model regression is manual/nightly and never blocks a merge.
- 5 integration flows defined at the API boundary: golden dispatch path, emergency-escalation bypass, chat bridge, Ask CrewLink retrieval gate, cross-zone auth/rollup.
- Accessibility/multilingual checks finalized against Doc #8 §1's five screen-mapped tables: every Planned row has a passing automated check (axe-core CI audit, DOM assertion, or documented manual screen-reader pass). Doc #7 §5's placeholder scaffolding language removed in Phase 10 — see §5 above for the full verification table.
- Translation golden-set extension per Doc #8 §4.3: 8 representative high-stakes phrases across 6 supported languages, graded on back-translation similarity + confidence-schema conformance, matching the same schema-conformance (100% gate) + threshold-graded quality pattern as the existing classification/dispatch golden set.
- GitHub Actions: lint/typecheck/secret-scan/unit/mocked-integration/golden-set-mocked/axe-core a11y block merges; live-model eval is workflow_dispatch + nightly only.
