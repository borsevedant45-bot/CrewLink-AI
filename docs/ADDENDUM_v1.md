# ADDENDUM v1 — CrewLink AI Documentation Set

**Version:** v1 · **Date:** 2026-07-14 · **Status:** Governing

Resolves 13 conflicts/gaps identified across Docs #1–#8. Where a resolution below differs from a doc's current text, this addendum controls until that doc is edited directly.

### G1 — Dispatch tier & latency

**Conflict:** Doc #1 §6.1 merges classification and dispatch into a single NFR row — "Triage classification + responder recommendation," <3s, "the fast/cheap LLM tier." Docs #2 §3, #4 §1, and #5 §1.6 all independently treat dispatch as Reasoning-tier.

**Resolution:** Split the row. Incident classification: <3s, Fast/Cheap tier (unchanged). Dispatch recommendation: <6s p95 target, Reasoning tier (matches Doc #5 §1.6's AI_REASONING target and Doc #2 §3's "top of the 2–6s band"); 8s hard timeout before the deterministic fallback fires (Doc #4 §5.3).

**Reason:** Doc #1's merged row is the lone outlier. A p95 target and a hard timeout are different controls and shouldn't collapse into one number.

### G2 — Rate limits

**Conflict:** Doc #5 §1.6 vs Doc #6 §5 disagree on three tiers: AUTH 5 vs 10 req/min; STANDARD 60 vs 120 req/min; AI_REASONING 10 vs 6 req/min. (REALTIME_POLL and AI_FAST already agree in both docs.)

**Resolution:** AUTH = 5 req/min per IP + backoff after 5 failed attempts (number from Doc #5, backoff from Doc #6). STANDARD = 120 req/min per user (Doc #6). AI_REASONING = 6 req/min per user, idempotency-keyed per incident state (Doc #6).

**Reason:** Doc #6 is the later, dedicated threat-modeling pass and supersedes Doc #5's numbers as the more deliberate analysis — except AUTH, where Doc #5's stricter number is kept for brute-force protection and merged with Doc #6's backoff detail.

### G3 — Phantom field: `needs_grounding`

**Conflict:** Doc #2 §3 (Steps 1–2) says the classifier emits a `needs_grounding` flag gating KB lookup. Doc #4 §4's `IncidentClassification` schema has no such field.

**Resolution:** KB-lookup gating is category-based, per Doc #3 §2.3's fixed table (`ACCESSIBILITY` → always; `MEDICAL`/`TRANSLATION`/`CROWD_QUEUE` → never; `LOST_FAN`/`LOST_ITEM`/`GENERAL` → conditional). Correct Doc #2 §3's prose to remove `needs_grounding`.

**Reason:** Doc #4's schema is the enforced, forced-tool-choice contract; Doc #2's prose predates it and was never synced.

### G4 — `severity_signal` vs `urgency_signal`

**Conflict:** Doc #4 §4's `IncidentClassification.severity_signal` = `low|medium|high`. Doc #5 §2.5/§4.1's wire field `classification.urgency_signal` = `critical|high|medium|low` — different name, different value set.

**Resolution:** `severity_signal` is the only model output. At serialization, rename to `urgency_signal` and derive: `"critical"` iff `severity_signal=="high"` AND `requires_emergency_escalation==true`; otherwise pass `severity_signal` through unchanged.

**Reason:** Matches every worked example already in the docs — Doc #5 §4.1's emergency variant (high+escalated→critical) and its medium accessibility example (pass-through). The rule already exists implicitly; it just wasn't written down.

### G5 — Category literal: `translation`

**Conflict:** Doc #3 §2.3/§2.4 use `TRANSLATION_REQUEST`. Doc #4 §4's `Category` enum and Doc #5's wire schema use `translation`.

**Resolution:** `translation` is canonical; patch Doc #3's literal only.

**Reason:** Doc #3's other six category labels already match Doc #4/#5 once case-normalized (its tables display caps stylistically, e.g. `MEDICAL`→`medical`) — this is a real naming conflict, not a casing convention, and it's isolated to one document.

### G6 — `language_context` vs `detected_language`

**Conflict:** Doc #3 §2.2's `language_context` is written only when `category` is `LOST_FAN`/`TRANSLATION`. Doc #4 §4's `detected_language` is broader — golden case 8 (§6) populates it on a `MEDICAL` incident.

**Resolution:** Keep both, distinct: `detected_language` = general language-of-input signal, any category; `language_context` = dispatch-relevant language *need*, conditional as already specified. Gap found: Doc #3 §1.2's INCIDENT entity has no `detected_language` column — add it (string, nullable, classifier-written) to the ERD and the §2.2 field table.

**Reason:** The conceptual split is correct but incomplete — `detected_language` is a real, golden-set-verified classifier output with nowhere to persist today.

### G7 — Undefined `escalation_channel`

**Conflict:** Doc #4 §3(a)'s emergency rule lists medical triggers (unconsciousness, breathing, bleeding, chest pain, choking, seizure, allergic reaction) alongside non-medical hazard triggers (fire/smoke, weapon, violence/threat, structural hazard), but none of the 7 taxonomy categories is "security." Doc #5 §3.5's `escalation_channel: EMS|SECURITY` has no assignment rule.

**Resolution:** Derive `escalation_channel` deterministically in code, never model-assigned, by matching `raw_description` against Doc #4 §3(a)'s own two trigger groups: `SECURITY` if fire/smoke, weapon, violence/threat, or structural-hazard language matched; `EMS` by default otherwise, for any `requires_emergency_escalation=true` case.

**Reason:** Reuses the doc's existing trigger list instead of inventing new keywords; keeps a safety-critical decision deterministic and auditable, matching Doc #3 §2.1's `priority_score` precedent.

### G8 — Unset thresholds

**Conflict:** `MIN_GROUNDING_SIMILARITY` (Doc #4 §2), the classification human-review threshold (Doc #3 §2.2), and the acknowledgment SLA (Doc #2 §5) are all referenced but never assigned values.

**Resolution:** `MIN_GROUNDING_SIMILARITY = 0.75`. Classification human-review threshold = `0.6` (below this, route to human review instead of auto-dispatch). Acknowledgment SLA = `90s` (Critical/High priority), `240s` / 4 min (Medium/Low). All four are config-driven; these are the stated defaults.

**Reason:** Distinct signals — retrieval similarity, classification confidence, elapsed time — kept separate from Doc #5 §2.5's own `0.75` dispatch `auto_assigned` threshold. Single numbers chosen over ranges so nothing here reads as unresolved.

### G9 — Doc #8's proposed Volunteer fields

**Conflict:** Doc #8 proposes `Volunteer.preferred_language` (§3.2) and an accessibility/equipment skill tag (§6), both self-flagged as new, not yet in Doc #3.

**Resolution:** `preferred_language` accepted as a new Volunteer field (UI-chrome language; distinct from `primary_language`/`secondary_languages`, which drive dispatch matching). The accessibility tag is *not* a new column — accept `wheelchair_cart_trained` and `sign_language` as additional example values inside Doc #3 §1.2's existing `skills_tags` list.

**Reason:** `preferred_language` fills a real gap. The skill tag doesn't — `skills_tags` was already designed as an open, extensible tag set ("e.g. medical_basic, translation_es"); a parallel column would duplicate it.

### G10 — Stale Doc #7 §5 reference

**Conflict:** Doc #7 §5 still states Doc #8 "is not yet started"; Doc #8 is Complete, and its own index note says it closes exactly the gap Doc #7 §5 flagged.

**Resolution:** Not resolved here — Doc #7 §5 is rewritten directly (replacing placeholder scaffolding with Doc #8 §1's screen-mapped criteria) in Phase 10.

**Reason:** A stale reference belongs fixed at the source; an addendum override would just create a second place to maintain.

### G11 — PROJECT_INDEX.md (Doc #0) not provided

**Conflict:** Doc #0 is cited by every attached document (five Key Assumptions, persona/scope framing) but wasn't included in this set.

**Resolution:** Treated as unverified throughout this addendum. No item above should be read as confirming or amending a Key Assumption.

**Reason:** Citations can't be checked against a document not in evidence. Re-check all thirteen resolutions — especially G1/G8's NFR numbers and G12's language list — against Doc #0 once available.

### G12 — Supported-language list drift

**Conflict:** Doc #1 §9 (Assumption 3) lists 7 languages (English, Spanish, Portuguese, French, Arabic, Mandarin, Japanese); Doc #8 §3.2 lists 8 (English, Spanish, Portuguese, French, German, Japanese, Korean, Arabic) — German and Korean added, Mandarin dropped.

**Resolution:** Doc #8's 8-language list governs, per Doc #1's own deferral ("definitive list...owned by Doc #8"). Flagged, not silently accepted: Mandarin's removal is unexplained and cuts against Doc #1's own stated selection rationale ("large ticket-holding fan bases") — confirm intentionally before build.

**Reason:** Doc #1 hands ownership to Doc #8 by design, so Doc #8 wins — but dropping a major-population language against the doc's own stated criterion, with no reason given, deserves a human check, not an assumption of intent.

### G13 — Simulator ingestion path

**Conflict:** Doc #2 §1/§6 describes the simulator — a standalone container — "posting" to "the backend's ingestion endpoint," implying a network call. Doc #5 §2.1 says it "writes...directly into the service layer...not through this API," with "no public endpoint."

**Resolution:** Internal-only route family — `POST /internal/ingest/{incidents|crowd-density|position-pings}` — outside the `/api/v1` namespace Doc #5 documents; authenticated by a static service credential distinct from user JWTs (not yet in Doc #6 — add it there).

**Reason:** Doc #5 is explicitly scoped as "the contract between the backend and the frontend" — an internal service-to-service route is out of that scope, not contradicted by it. Doc #2's "same ingestion surface" claim still requires some networked endpoint, since the simulator is a separate container.

---

*Doc #0 (PROJECT_INDEX.md) unavailable at time of writing — see G11.*

---

### G14 — UI label / state-model mapping for FR-4 one-tap status

**Conflict:** Doc #1 §5.1 FR-4 names three one-tap actions — "Acknowledged / En Route / Resolved" — while Doc #5 §2.5's Incident lifecycle uses `acknowledged`, `in_progress`, `resolved`. There is no `en_route` state.

**Resolution:** "En Route" button → status `in_progress`. The UI label describes what the volunteer is doing (heading to the incident); the state model captures the operational meaning (actively responding). `acknowledged` → `acknowledged`, `Resolved` → `resolved`. Document this mapping in the button component's comment and in the test that asserts the transition reaches the supervisor rollup.

**Reason:** The volunteer never needs to know the model-state name — "En Route" is the right instruction for a button; `in_progress` is the right state for a rollup to display. Adding a separate `en_route` state would fragment the lifecycle without operational value.

### G15 — AIInvocationLog override marker (Phase 9 FR-9)

**Conflict:** Doc #3's `AIInvocationLog` model has `purpose: Enum(CLASSIFICATION, DISPATCH_RECOMMENDATION, TRANSLATION, ASK_CREWLINK_SYNTHESIS)` — four AI-call purposes — but no field to distinguish a human override from an AI model output. FR-9 requires every triage decision and override to be logged with "model output vs. human choice."

**Resolution:** Add `override_type: Enum(NONE, HUMAN_RECLASSIFICATION, HUMAN_REASSIGNMENT) | None` to `AIInvocationLog` (nullable, default `NONE`). When a human manually reclassifies an incident (`PATCH /incidents/{id}/status`) or reassigns a volunteer (`PATCH /incidents/{id}/assign`), the logging path writes a row with `override_type` set to the appropriate value and `confidence: null` (no AI produced it). AI-called paths leave `override_type=NONE`.

**Reason:** A single nullable enum is simpler than a new table or a schema migration for a demo-scoped audit trail. The golden-set eval filters on `override_type=NONE` plus a date range when scoring model-output rows, and ignores override rows.

### G16 — Supervisor WS broadcast format

**Conflict:** Doc #5 §3.4 says `/ws/supervisor` fires `incident.created`, `incident.updated`, `incident.resolved` but doesn't specify whether the payload is the full Incident object or a delta.

**Resolution:** Full Incident object on every event. The supervisor dashboard needs all fields to re-render (status badge, priority, assignment). This matches the existing `/ws/tasks` broadcast pattern in `incidents.py`. No delta encoding for the MVP.

**Reason:** Consistency with the existing WS broadcast implementation, and the supervisor dashboard has no performance reason to request deltas at ~50-volunteer concurrency.

### G17 — Rollup endpoint: zone-level aggregation

**Conflict:** Doc #5 §2.4 defines `GET /zones/{zone_id}` returning `Zone` with `open_incident_count` and `active_volunteer_count` but doesn't define a multi-zone aggregate endpoint that a supervisor's dashboard can call once instead of N+1 queries.

**Resolution:** `GET /api/v1/supervisor/rollup` returns a single response aggregating every zone. See Phase 9 FR-4 implementation code for the exact schema. This lives in a new `supervisor` router, not added to `zones`.

**Reason:** An N+1-free aggregate view is the minimal backend the dashboard needs.

### G18 — Shift-summary fallback shape

**Conflict:** Doc #4 §5.3 specifies fallbacks per TaskType but only provides a stub `_shift_summary_fallback` with no defined return shape.

**Resolution:** Shift-summary fallback returns schema-conformant `ShiftSummary` with `summary="Shift summary temporarily unavailable."` and `fallback_used=True`. The golden-set test asserts schema conformance (100% gate), not content, so an empty fallback satisfies it.

**Reason:** Per Doc #4's "model proposes, deterministic code disposes" — the fallback is a code path, not a model output, so it must conform to the same schema as the real path.

### G19 — FR-21 navigation route: static stub, not real pathfinding

**Conflict:** Doc #1 §5.6 FR-21 says "a simple in-venue map view with a suggested route" but no doc specifies a pathfinding algorithm, coordinate system, or venue map data.

**Resolution:** FR-21 ships as a static route card inside the incident detail view: hardcoded "From your current zone to [incident zone]" with a human-readable path. The KB corpus gains one document entry (`venue_navigation`) with representative route snippets. No coordinate math, no map renderer.

**Reason:** True pathfinding requires a venue graph that doesn't exist in the seeded KB. A static example demonstrates the UI surface without building infrastructure that would be replaced in a real deployment.

### G20 — Task feed offline state: sessionStorage, not localStorage

**Conflict:** FR-5 requires "show the last-synced list in a clearly labeled read-only offline state" but doesn't specify the storage mechanism.

**Resolution:** `sessionStorage` (cleared on tab close). The feed component snapshots its displayed incident list on every WS/poll update. On connectivity loss, it reads from `sessionStorage` and overlays a banner: "OFFLINE — showing cached data (last synced [timestamp])".

**Reason:** `sessionStorage` is automatically cleared when the volunteer closes the tab, avoiding stale-data confusion. The feed is already ephemeral — no value in persisting task state across sessions.
