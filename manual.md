# CrewLink AI — Complete Operator & Evaluator Manual

Welcome to the definitive tester guide for CrewLink AI. Follow these simple steps to explore every capability of our platform designed for the FIFA World Cup 2026.

## 👥 1. Persona Dashboard Quick-Access
The platform relies on strict role-based data isolation via signed JWT tokens. Go to the live app at **https://crewlink-frontend.onrender.com/demo** and sign in using the badge codes below. The uniform PIN for all accounts is `demo`.

| Badge Code | System Role | Assigned Zone | Special Access Boundaries |
| :--- | :--- | :--- | :--- |
| **MARIA** | volunteer | East Concourse | Limited to East Concourse tasks/chats. |
| **JOHN** | volunteer | West Concourse | Limited to West Concourse tasks/chats. |
| **AMINA** | volunteer | North Concourse | Limited to North Concourse tasks/chats. |
| **CARLOS** | volunteer | South Concourse | Limited to South Concourse tasks/chats. |
| **SUPERVISOR** | supervisor | All Zones (Venue Global) | Full cross-zone visibility; can manually assign tasks. |

---

## 🛠️ 2. Core Functional Walkthroughs

### Feature A: Incident Reporting & Real-Time Task Feeds

**Overview:**
Volunteers report incidents (medical, lost fan, accessibility, crowd, etc.) via a POST. The system runs synchronous AI classification (Fast/Cheap tier) to determine category, severity, priority score, and emergency escalation. The result is immediately pushed to all connected task-feed WebSocket subscribers in that zone.

**Step-by-Step Testing:**
1. Log in as **MARIA** (or any volunteer) at `/demo`.
2. Navigate to Step 1 — you will see a multi-category, priority-ranked static demo feed showing 6 pre-seeded incidents with category icons, three-channel priority badges (⚠️ Urgent / ⚡ Moderate / ℹ️ Low), and `[SIMULATED]` source badges.
3. Advance to Step 2 — click any template button (e.g. "Medical emergency" or "Lost child"). The system POSTs to `/api/v1/incidents`.
4. Observe the returned JSON: it includes `category`, `priority_score`, `classification_confidence`, and `status`. If you chose a medical/emergency description, the incident auto-escalates.
5. The new incident appears in the task feed in real time (via `/ws/tasks` WebSocket push) for all volunteers in the same zone. Volunteers in other zones will NOT see it.
6. On the **TaskFeed** page (`/tasks`), incidents are color+icon+text coded (WCAG 2.1 AA), sorted by priority descending. An `aria-live="polite"` region announces new incidents with debounced burst-coalescing.

**Under-the-Hood Actions:**
- **Endpoint:** `POST /api/v1/incidents` → `backend/app/routers/incidents.py:125`
- **AI Tier:** `TaskType.INCIDENT_CLASSIFICATION` → Fast/Cheap via `backend/app/services/classifier.py:18`
- **Fallback:** If the AI call fails, the keyword-heuristic `_classify_fallback()` at `backend/backend/orchestration/fallbacks.py:29` runs instead — always 200 OK with `fallback_used: true`.
- **WebSocket:** `ws_manager.broadcast("tasks", "incident.created", ...)` at `incidents.py:196` pushes the new incident to all zone-scoped `/ws/tasks` subscribers.
- **Supervisor WS:** The same event is also pushed to `/ws/supervisor` at `incidents.py:197`.
- **FR-16 accessibility auto-surface:** If the classification returns `category == "accessibility"`, a Chroma KB retrieval is triggered and `kb_reference_ids` are attached to the incident model (`incidents.py:182`).

---

### Feature B: AI-Driven Dispatch Recommendations (Reasoning Tier)

**Overview:**
Given a classified incident, the Reasoning-tier LLM analyzes zone-eligible volunteers (skills, certifications, language) and returns a ranked recommendation of the 1–3 best-matched responders with a rationale. This is an explicit, on-demand action — dispatch is not automatic.

**Step-by-Step Testing:**
1. After creating an incident (Step 2 is complete), go to Step 3.
2. Click "Get Dispatch Recommendation". The frontend calls `POST /api/v1/incidents/{id}/dispatch-recommendation`.
3. Inspect the returned JSON: `recommended_volunteers` array with `volunteer_id`, `rank`, `rationale`, plus `requires_human_supervisor_review`, `confidence`, and `fallback_used`.
4. The recommendation is persisted to the incident's `dispatch_confidence` and `dispatch_rationale` columns.

**Under-the-Hood Actions:**
- **Endpoint:** `POST /api/v1/incidents/{id}/dispatch-recommendation` → `incidents.py:253`
- **AI Tier:** `TaskType.DISPATCH_RECOMMENDATION` → Reasoning via `backend/app/services/dispatch_recommender.py:22`
- **Candidate pool:** Volunteer roster filtered by zone (`_get_candidates_for_zone` at `incidents.py:367`).
- **Hallucinated-ID guard:** The `validation_context={"volunteer_id": candidate_ids}` at `dispatch_recommender.py:71` is checked in `complete_with_fallback` — if the LLM returns a volunteer_id not in the candidate list, the response is rejected and the fallback fires.
- **Emergency bypass (provable):** If `requires_emergency_escalation` is true, the provider is NEVER called — the check at `dispatch_recommender.py:32` returns the emergency fallback immediately. Verified by `test_reasoning_tier_not_called_for_emergency`.
- **Fallback:** `_dispatch_fallback()` at `fallbacks.py:118` returns a "nearest available in zone" stub with `requires_human_supervisor_review: true`.

---

### Feature C: Manual Supervisor Assignment (The Human-in-the-Loop Override)

**Overview:**
Supervisors can manually assign any incident to any volunteer — overriding or bypassing the AI recommendation entirely. Every override is logged to `ai_invocation_logs` with a specific `override_type` (HUMAN_REASSIGNMENT or HUMAN_RECLASSIFICATION) for audit trail.

**Step-by-Step Testing:**
1. Log in as **SUPERVISOR**.
2. From Step 7 or the Supervisor Dashboard, you see all zones' incidents.
3. Issue a `PATCH /api/v1/incidents/{id}/assign` with `{"volunteer_id": "vol_amina_walker"}`.
4. Verify: the incident's `assigned_volunteer_id` updates, a WebSocket broadcast refreshes all connected task feeds, and an `AIInvocationLog` entry is created with `override_type: "HUMAN_REASSIGNMENT"`.
5. For status reclassification (e.g. changing an incident's category), any status transition via `PATCH /api/v1/incidents/{id}/status` is logged as `HUMAN_RECLASSIFICATION`.

**Under-the-Hood Actions:**
- **Assign endpoint:** `PATCH /api/v1/incidents/{id}/assign` → `incidents.py:296` — supervisor-only (403 for volunteers).
- **Status endpoint:** `PATCH /api/v1/incidents/{id}/status` → `incidents.py:202` — state-machine validated via `apply_transition()`.
- **Override logging:** Both paths construct an `InvocationRecord.for_manual_override(...)` and call the `log_callback` to persist to `ai_invocation_logs` with `override_type` (`incidents.py:241` and `incidents.py:321`).
- **FR-9:** This fulfills the override-logging functional requirement.

---

### Feature D: Multilingual Chat Bridge & Intent Routing (Fast/Cheap Tier)

**Overview:**
Volunteers can open a chat session with a fan who speaks a different language. Every message is translated via the Fast/Cheap tier. High-stakes content (medical/accessibility keywords or emergency flags) triggers back-translation verification and a "Request human interpreter" button in the UI.

**Step-by-Step Testing:**
1. Log in as a volunteer (e.g. **MARIA**).
2. Go to Step 5. Click "Create Chat Session" → calls `POST /api/v1/chat-sessions` with `fan_language: "ja"`.
3. Send one of the pre-loaded scenarios (e.g. "Lost child (ja)"). The message is sent to `POST /chat-sessions/{id}/messages`.
4. Inspect the response JSON: `translated_text`, `confidence`, `back_translation`, `high_stakes`, `emergency_flag`, `fallback_used`.
5. In the UI, observe:
   - The original Japanese text and the English translation side-by-side.
   - A **Back-Translation Verified** badge when back-translation matches.
   - A confidence chip (yellow for medium, red for low) when `< 0.7`.
   - A **Request Human Interpreter** button when `high_stakes` is true.
   - A **Fallback** badge when `fallback_used: true`.
6. Try the "Medical help (es)" scenario — this will trigger the emergency path, auto-creating an escalated incident and an emergency broadcast.

**Under-the-Hood Actions:**
- **Create session:** `POST /api/v1/chat-sessions` → `backend/app/routers/chat.py:103` — stores zone, fan language, volunteer language.
- **Send message:** `POST /api/v1/chat-sessions/{id}/messages` → `chat.py:194` — calls `translate_message()`.
- **AI Tier:** `TaskType.TRANSLATION` → Fast/Cheap via `backend/app/services/translation.py:51`. Structural AST test (`test_translation_imports.py`) proves it never imports Reasoning-tier or RAG modules.
- **High-stakes override:** `_derive_high_stakes()` at `translation.py:35` is ALWAYS computed deterministically: `emergency_flag OR category in {medical, accessibility}` — the model output's `high_stakes` field is always overwritten. Low-confidence high-stakes translations produce a WARNING log.
- **Emergency auto-incident:** If `emergency_flag` is true, `chat.py:259-296` auto-creates an escalated Incident and calls the same `broadcast_emergency()` path used by incident reports.
- **WebSocket push:** `ws_manager.broadcast("chat/{session_id}", "message.sent", ...)` at `chat.py:303` pushes the translated message to all connected WS subscribers on that session channel.
- **Fallback:** `_translation_fallback()` at `fallbacks.py:105` returns the original text with confidence=0 and `detected_language="und"`.

---

### Feature E: "Ask CrewLink" Knowledge Base Assistant (RAG Grounding)

**Overview:**
Volunteers ask free-text questions about venue facilities, safety procedures, and accessibility resources. The system uses a 5-branch intent router (Fast/Cheap) to classify the query. Only `FACILITY_SAFETY_PROCEDURE` queries reach the Chroma vector store; the other 4 branches return templated replies. If Chroma returns relevant chunks above the `MIN_GROUNDING_SIMILARITY=0.75` threshold, the Reasoning tier synthesizes a grounded answer with source citations.

**Step-by-Step Testing:**
1. Log in as a volunteer.
2. Go to Step 6. Click a question button like "Where is the nearest first-aid station in the East Concourse?"
3. Observe the loading indicator: `[Querying Chroma Vector KB...]`.
4. The result shows:
   - `[✅ Confidence Score: 94% — Safe to Generate]` badge.
   - The answer text with source citations (document title + chunk ID).
   - The **R** (Reasoning-tier) badge.
5. Click the "Intentional Fallback Demo" button (asks "What is the secret code for the underground tunnel to the VIP lounge?") — this has no match in the KB.
6. Observe the fallback result shows `⚠️ Confidence Score: 23% — Below threshold. Fallback activated.` and a deterministic "no answer found" message with `grounded: false`.
7. Try non-facility queries (e.g. "How are you?") — these return templated responses without touching the KB or Reasoning tier.

**Under-the-Hood Actions:**
- **Endpoint:** `POST /api/v1/knowledge-base/ask` → `backend/app/routers/knowledge_base.py:51`
- **5-branch intent router:** `TaskType.INTENT_ROUTING` → Fast/Cheap via `backend/app/services/ask_crewlink.py:120`. Fallback defaults to `FACILITY_SAFETY_PROCEDURE` (ambiguity resolves toward caution).
- **Non-FACILITY branches** (`TRANSLATION_REQUEST`, `SMALL_TALK`, `STATUS_OR_LOGISTICS`, `OUT_OF_SCOPE`) return static `_TEMPLATED_REPLIES` — zero KB or Reasoning-tier calls. Verified by `test_no_reasoning_on_non_facility.py`.
- **FACILITY branch:**
  - **Retrieval:** `retrieve_chunks()` queries Chroma (`crewlink_kb` collection with cosine distance) — `backend/app/services/kb_retrieval.py`.
  - **Threshold gate:** `MIN_GROUNDING_SIMILARITY = 0.75` (`backend/app/core/config.py`). Chunks below this are discarded. If no chunks remain, the system returns `grounded: false` with a fallback message — never a hallucination.
  - **Synthesis:** `TaskType.ASK_CREWLINK_SYNTHESIS` → Reasoning tier. The prompt includes the LIVE EMERGENCY OVERRIDE instruction so the model checks for live emergencies before answering from KB.
  - **Source whitelist:** `validation_context={"sources": retrieved_chunk_ids}` at `ask_crewlink.py:253` — any hallucinated chunk ID is rejected.
- **Multilingual wrapper (Doc #8 §3.3):** If the volunteer's language is not English, the query is translated to English before retrieval, and the answer is translated back. Both use Fast/Cheap `complete_text` calls.
- **Fallback:** `_ask_crewlink_fallback()` at `fallbacks.py:136` returns a static "ask your supervisor / check the printed venue guide" message.
- **KB corpus:** 5 authored documents (venue map, medical escalation, crowd/evacuation, accessibility guide, FAQ) → 39 chunks total, seeded in Chroma by `seed/chroma_seed.py`.

---

### Feature F: Emergency Deterministic Bypass (Model-Free Safety Broadcast)

**Overview:**
When an incident is classified as requiring emergency escalation, or when a chat message carries an emergency flag, the system fires a fully deterministic broadcast with CRITICAL-level structured logging. The Reasoning-tier Dispatch Recommender is NEVER called — the emergency bypass is provable at the code level. No LLM call intervenes between the emergency signal and the broadcast.

**Step-by-Step Testing:**
1. Log in as a volunteer.
2. Go to Step 4. Click the pulsing red **🚨 Trigger Emergency Bypass** button.
3. The UI shows an alert banner: "Emergency Bypass Activated — Model-Free Safety Broadcast Fired. Normal dispatch routes are suspended."
4. The status transition buttons become disabled — the UI shows "Locked — Emergency Active".
5. To verify the provable bypass behavior, create an emergency incident in Step 2 (choose "Medical emergency" — chest pain) and then try Step 3. The dispatch recommendation will respond with `fallback_used: true` and the `recommended_volunteers` list containing `fallback_nearest_available` — the Reasoning-tier provider was never called.
6. Similarly, in Step 5, send a "Medical help (es)" chat message. This triggers the emergency_flag path, which:
   - Auto-creates an escalated Incident.
   - Calls `broadcast_emergency()` with CRITICAL logging.
   - Pushes the new incident to `/ws/tasks` and `/ws/supervisor`.

**Under-the-Hood Actions:**
- **Emergency Broadcast:** `broadcast_emergency()` at `backend/app/services/emergency.py:29` — zero LLM calls. Derives escalation channel (EMS/Security), urgency signal (`critical`), and emits `logger.critical(...)` with structured payload.
- **Dispatch bypass (provable):** `recommend_dispatch()` at `dispatch_recommender.py:32` checks `requires_emergency_escalation` BEFORE obtaining the provider. If true, returns `_dispatch_fallback()` immediately. Verified by `test_reasoning_tier_not_called_for_emergency` using a `CallCountingStub`.
- **Chat emergency path:** Identical `broadcast_emergency()` call at `chat.py:277` + auto-created Incident with `status: "Escalated"` + WS broadcast (`chat.py:284`).
- **Emergency-assertive live region:** In `TaskFeed.tsx:134`, when an emergency incident arrives via WS, the `aria-live` region switches from `"polite"` to `"assertive"` to immediately notify screen reader users.
- **No AI fallback in emergency path:** The emergency broadcast is fully deterministic — there is no fallback for the bypass because there is no AI call to fail.

---

## 📡 3. The Real-Time WebSocket Infrastructure

The system uses three WS channels for real-time push. Every channel supports polling fallback via the REST endpoints — the `useWebSocket` hook (`frontend/src/hooks/useWebSocket.ts`) uses the same `onUpdate` callback for both WS and polling, so consuming components cannot distinguish the transport.

| Channel | Path | Who streams it | Data propagates | Polling fallback |
| :--- | :--- | :--- | :--- | :--- |
| **Tasks** | `/api/v1/ws/tasks?ticket=...` | Volunteers in their assigned zone. The `ticket` param is a signed, single-use, 30-second-TTL JWT obtained from `POST /api/v1/auth/ws-ticket`. | `incident.created` and `incident.updated` events — only for incidents within the volunteer's zone (filtered server-side by JWT zone claim). The WebSocket handler is defined in `backend/backend/app/routers/incidents.py` (not in `main.py` directly, but routed via `ConectionManager`). The feed endpoint `GET /api/v1/incidents/feed` serves as the polling fallback, zone-scoped. | `GET /api/v1/incidents/feed` — zone-scoped, sorted by `created_at` desc, max 50. |
| **Supervisor** | `ws://host/api/v1/ws/supervisor?ticket=...` (defined in `backend/app/main.py:106`) | SUPERVISOR role only (verified via WS ticket). Subscribes to all zone events — no zone filtering since the supervisor's JWT role is `supervisor`. | `incident.*`, `volunteer.status_changed`, `zone.crowd_density_updated`, and `emergency.broadcast` events — a venue-wide rollup. The connection supports `{"type": "ping"}` keepalive → responds with `{"type": "pong"}`. | `GET /api/v1/supervisor/rollup` — returns aggregate zone stats. |
| **Chat** | `/api/v1/ws/chat/{session_id}?ticket=...` | All participants within that specific chat session (volunteer + supervisor). | `message.sent` events — every translated message is pushed to `chat/{session_id}` channel. The WebSocket broadcast happens at `backend/app/routers/chat.py:303`. | `GET /api/v1/chat-sessions/{id}/messages` — returns message history ordered by `sent_at` asc, max 100. |

**How to verify real-time streaming:**
1. Open two browser tabs: Tab A logged in as MARIA (East Concourse), Tab B logged in as JOHN (West Concourse).
2. In Tab A, report an incident via Step 2 → the new incident appears in Tab A's task feed immediately. Tab B's feed stays unchanged (cross-zone isolation).
3. Open Tab C logged in as SUPERVISOR, open the Supervisor Dashboard (Step 7) → both Tab A's new incident and all other zones' incidents are visible.
4. Open a chat session in one tab and send a message → the translated message appears in any other tab watching the same chat session.

---

## 🧠 4. AI Guardrails Reference Table

| Scenario | What happens | Where it's enforced |
| :--- | :--- | :--- |
| **RAG confidence score drops below 0.75 threshold** | The system returns `grounded: false`, `answer: null`, and a deterministic fallback message ("I couldn't find an answer in the venue guide..."). The Reasoning-tier synthesis call is NEVER made — proven by `test_no_reasoning_on_non_facility.py`. | `ask_crewlink.py:208-224` — `if not groundable: return AskCrewLinkResult(grounded=False, ...)`. The threshold comes from `settings.min_grounding_similarity = 0.75` in `config.py`. |
| **LLM output violates Pydantic schema** | `complete_with_fallback` catches `ValidationError` at `completion.py:149`, logs WARNING, and routes to the deterministic fallback for that TaskType. The response to the HTTP client is 200 OK with `fallback_used: true` — never a 5xx. | `backend/backend/orchestration/completion.py:177-219` — the `except Exception` block catches ValidationError, TimeoutError, etc., and calls `FALLBACK_MAP[task_type](**fallback_kwargs)`. |
| **Critical medical keyword appears in text** | For incident classification: if the keyword matches an emergency pattern ("chest pain", "unconscious", "bleeding"), `requires_emergency_escalation` is set to `true` by the LLM or the keyword-heuristic fallback. This triggers `broadcast_emergency()` and the dispatch-recommendation endpoint returns fallback immediately (provider never called). For translation: `emergency_flag` causes the deterministic `high_stakes=true` override, triggers a WARNING log for low confidence, shows the "Request human interpreter" button in the UI, and auto-creates an escalated Incident with a broadcast. | Incident path: `incidents.py:169-177` and `dispatch_recommender.py:32-41`. Translation path: `translation.py:90-109` and `chat.py:259-296`. |
| **LLM hallucinates a volunteer_id not in the candidate list** | `complete_with_fallback` calls `_validate_ids()` at `completion.py:152`. The recursive check walks the entire validated model tree for any field matching keys in `validation_context`. If a hallucinated ID is found, a `ValueError` is raised, caught by the except block, and the fallback runs. | `completion.py:50-97` (`_validate_ids` + `_check_field`). Example: dispatch recommender passes `{"volunteer_id": candidate_ids}` as `validation_context`. |
| **LLM hallucinates a chunk_id not in the retrieved set** | Same mechanism as above. The Ask CrewLink service passes `{"sources": retrieved_chunk_ids}` as `validation_context` at `ask_crewlink.py:253`. If the LLM cites a chunk that was not retrieved, the response is rejected and the fallback fires. | `ask_crewlink.py:253` + `completion.py:50-97`. Verified by `test_source_whitelist.py`. |
| **Translation LLM call times out or fails** | `complete_with_fallback` catches the error and returns `_translation_fallback()` — the original text is shown with `confidence=0.0`, `detected_language="und"`, and `fallback_used: true`. The UI displays a **Fallback** badge. | `fallbacks.py:105-115` + `completion.py:177-219`. |
| **Chat message has `emergency_flag: true` but low translation confidence** | The high-stakes override (`_derive_high_stakes`) sets `high_stakes=true` regardless. A WARNING log is emitted for low-confidence (<0.7) high-stakes translations. The UI shows the "Request human interpreter" button and the confidence chip (yellow/red). An escalated Incident is auto-created, and `broadcast_emergency()` fires. | `translation.py:90-109` (WARNING log) + `chat.py:259-296` (incident + broadcast). |
| **User attempts prompt injection in incident description** | The user text fills the `<incident_report>` slot in the prompt template (`classifier.py:30`), never the system prompt itself. The output is constrained to a Pydantic schema via forced tool choice. If the LLM follows an injection instruction, the schema validation or hallucination guard catches the malformed output and routes to the deterministic fallback. | `classifier.py:29-34` (isolated prompt slot) + `completion.py` (schema validation + hallucination guard). Golden-set case #7 specifically tests injection handling. |
| **Rate limit exceeded (AI_FAST or AI_REASONING tier)** | The in-memory `RateLimiter` (`backend/app/core/rate_limiting.py`) returns a 429 response with `Retry-After` header. Rate limit tiers are: AUTH (60/min), STANDARD (300/min), REALTIME_POLL (60/min per IP), AI_FAST (20/min per user), AI_REASONING (5/min per user). | `rate_limiting.py` + ADDENDUM G2 values. |
| **Unauthorized cross-zone access attempt** | A volunteer from Zone A tries to read an incident in Zone B. `_zone_filter()` at `incidents.py:64` adds `IncidentModel.zone_id == auth.zone_id` to the query. Cross-zone GET returns 404 (not 403) — the incident "doesn't exist" from the caller's perspective. Cross-zone POST returns 403. Verified by Integration Flow #5 (7 tests in `test_flow_5_cross_zone_auth.py`). | `incidents.py:64-68` (zone filter), `incidents.py:120-121` (404 hiding), `incidents.py:138-139` (403 on create). |
| **No provider registered for a tier** | `ModelRouter.for_task()` returns a `_MissingProvider` sentinel (not an exception). When `complete_structured()` is called, it raises `RuntimeError("No provider registered for this tier...")`. This is caught by `complete_with_fallback`'s exception handler, which routes to the deterministic fallback. The response is 200 OK with `fallback_used: true`. | `interfaces.py:159-170` (`_MissingProvider`) + `completion.py:177-219`. |
