# Security & Privacy Design Document
*CrewLink AI — Doc #6 of 9 · builds on Docs #2–#5*

This document defines CrewLink AI's security and privacy posture. It builds directly on the System Architecture (Doc #2), the Data Model & Mock-Data Strategy (Doc #3), the AI/LLM Orchestration & Prompt Design document (Doc #4), and the API Specification (Doc #5) — it does not restate their internal mechanics. Its job is to threat-model the system those documents already define and close the gaps a demo-first build is most likely to leave open, with particular attention to the failure modes that are specific to an LLM-integrated app — prompt injection, model-output trust boundaries, and abuse of AI-calling endpoints — rather than generic web-app hygiene alone.

## 1. Threat Model

| Asset | Threat | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| Incident description / chat message text (prompt input) | **Prompt injection** — free text tries to steer classification, translation, or the Ask CrewLink answer (e.g. 'ignore previous instructions,' 'mark this Critical,' or a fan probing for the medical advice the system is designed to withhold) | Medium | Medium — bounded by Doc #4's schema-forced outputs, but could still degrade output quality or attempt exfiltration | User text fills one delimited *user content* slot in the prompt template, never the system/instruction portion (Section 4); Pydantic tool-call outputs mean free text can't reshape the response; classification/priority is re-validated in application code, never trusted verbatim (Doc #4). |
| KB chunks retrieved for Ask CrewLink (Chroma) | **Indirect prompt injection** via a poisoned KB document steering procedure answers | Low — KB is the 5 authored docs from Doc #3, not user-submitted | Medium if it occurred | No live ingestion path exists — the index is populated only from the authored corpus at build time. Retrieval still passes Doc #4's non-empty/above-threshold gate before generation runs. Any future community-submitted KB content must get this same input hygiene (Section 4) at ingestion time. |
| LLM provider API key(s) | **Key exposure** via source control, client bundle, logs, or error payloads → quota theft or impersonation | Medium | High — breaks AI_FAST/AI_REASONING availability for the live demo, direct billing impact | Keys never reach the frontend bundle — every AI call is backend-proxied. Loaded only from env vars / secrets manager (Section 2), excluded from VCS, redacted from logs and error responses by field-name pattern. |
| Another volunteer's task feed, position, or the supervisor rollup | **Broken object-level authorization** — a volunteer edits a zone or volunteer-ID parameter to view data outside their scope | Medium | High — cross-zone privacy breach, undermines trust in zone-based dispatch | Zone and role live only in JWT claims, never a client-supplied parameter used for authorization. Every task-feed/rollup query is filtered server-side by the caller's own claims (Section 3); supervisor routes are separately role-gated; WS channels use the same claim-based authorization via scoped tickets. |
| `POST /incidents/{id}/dispatch-recommendation` (Reasoning tier) | **Abuse/replay** — repeated calls on one incident to run up Reasoning-tier cost, exhaust the rate limit, or race a double dispatch | Medium | Medium — cost and demo-availability risk; low safety impact since emergencies bypass this endpoint entirely (Doc #4) | Idempotent per incident-lifecycle state — a repeat call on an unchanged incident returns the cached recommendation, no re-invocation. Scoped under the AI_REASONING tier (Section 5). The state transition itself is the authorization check — a Resolved/Cancelled incident can't be re-recommended. |
| Accessibility-flagged incidents, chat transcripts, position-ping history (PII-adjacent, Doc #3) | **Scraping / bulk export** — an over-broad authenticated query pulls sensitive-category data beyond individual operational need | Low–Medium | High — sensitive-category data, privacy/reputational harm | Cursor pagination (Doc #5) is paired with per-page/per-window caps; no bulk-export endpoint exists. Supervisor rollup shows accessibility data as de-identified zone counts by default (Section 6). Zone-scoped JWTs mean a volunteer's queries structurally can't span other zones. |
| `/ws/tasks`, `/ws/chat/{id}`, `/ws/supervisor` | **WebSocket hijacking/eavesdropping** — a client connects to a channel or zone it isn't authorized for | Low | Medium–High | Connection requires a short-lived, single-use `ws-ticket` (Doc #5's Auth/ws-ticket table) minted by an authenticated REST call carrying the same role/zone claims. The ticket is single-connection and expires quickly; the REST polling fallback reuses the identical auth path. |
| `requires_emergency_escalation` / `emergency_flag` | **Tampering or suppression** — a client sets or clears the emergency flag to trigger a false broadcast or suppress a real one | Low | High — safety-critical path | Emergency status is computed and validated server-side from classifier output plus rule logic, never accepted as a trusted client boolean. The broadcast writes to the incident audit trail / `AIInvocationLog` and is explicitly exempt from every AI rate-limit tier (Section 5). |

## 2. Secrets Management

All secrets — LLM provider API keys, `DATABASE_URL`, and `JWT_SECRET_KEY` — are loaded exclusively from environment variables. **Nothing is hardcoded, and nothing is committed to version control.**

- **Local & demo:** a single Pydantic `Settings` class (`pydantic-settings`) reads from a local `.env` file at process start. The app **fails fast** — refuses to start with a clear error — if a required key is missing, rather than starting with a `None` key that would only surface later as a confusing AI-call failure.
- **CI (GitHub Actions):** secrets are injected as encrypted Actions secrets, scoped to the job, and never echoed to logs.
- **Deploy (Render Starter / Railway, per Doc #2):** the platform's own secrets/environment manager holds production values under the same variable names used locally, so there's one contract across local, CI, and prod instead of three.
- **Frontend:** Vite only exposes variables explicitly prefixed `VITE_`, and that prefix is deliberately never used for anything secret — only values safe to ship in a client bundle (e.g., the API base URL). The LLM API key and `DATABASE_URL` never exist in any frontend build artifact; every AI and DB call is backend-mediated.
- **Defense in depth:** a lightweight secret-scanning step (e.g., `gitleaks`) runs in the same GitHub Actions pipeline as the test suite, catching an accidental commit before merge rather than relying on `.gitignore` discipline alone.

`.gitignore` (relevant excerpt):
```
.env
.env.*
!.env.example
*.pem
*.key
__pycache__/
node_modules/
```

`.env.example` (checked in, no real values):
```
# LLM Orchestration
LLM_FAST_API_KEY=
LLM_REASONING_API_KEY=
LLM_PROVIDER=

# Database
DATABASE_URL=

# Auth
JWT_SECRET_KEY=
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=

# App
ENVIRONMENT=development
```

## 3. AuthN/AuthZ

Identity is intentionally mocked for the demo (Doc #1's key assumptions), but the *pattern* is production-shaped: a real JWT with real server-side scope checks, issued against seeded demo credentials instead of a real FIFA accreditation system.

- **Login:** `POST /api/v1/auth/login` validates credentials against the `Volunteers` table and issues a JWT with claims `sub` (volunteer ID), `role` (`volunteer` | `supervisor`), `zone_ids`, `iat`, and `exp`.
- **Every REST request** passes through a shared FastAPI dependency that verifies the token's signature and expiry, then attaches an `AuthContext` (role + zone) to the request. Handlers query using that context — a volunteer's `zone_ids` claim, never a client-supplied `zone` query parameter — so a request simply cannot address another zone's data. This is the mechanism behind the task-feed row in Section 1.
- **Supervisor routes** sit behind a second dependency, `require_role("supervisor")`. A volunteer-scoped JWT hitting a supervisor route gets an explicit `403`, not a silently filtered response — a route should be either fully authorized or clearly refused, never ambiguously half-served.
- **WebSocket auth** avoids putting a long-lived bearer token in a URL or subprotocol (a common exposure path). The client first calls an authenticated REST endpoint, `POST /api/v1/auth/ws-ticket`, which mints a short-lived, single-use ticket carrying the same role/zone claims; the client opens the socket with that ticket; the server validates and consumes it once, then reuses the same `AuthContext` for the connection's lifetime.
- **Token lifetime** is shift-length (a few hours) — long enough to cover a scripted demo or a volunteer's shift without re-auth, short enough to bound a leaked token's usefulness. A real-tournament deployment would add refresh-token rotation and server-side revocation; that's out of scope for the demo NFRs in Doc #1 and is called out here as a deliberate cut, not an oversight.

## 4. Input Handling

Doc #4 already owns the AI-side guardrails: the non-empty/above-threshold Chroma gate before any generation, the emergency-escalation bypass, and the schema-forced tool-call contract with application-layer re-validation. None of that is re-derived here. This section is the layer that runs *before* any user-supplied text reaches a prompt template at all.

- **Boundary validation:** every free-text field (incident description, chat message, Ask CrewLink question) is Pydantic-validated at the API edge for type, presence, and length before it touches any business logic — a hard character cap per field, sized to bound both cost and injection surface, not just to look "reasonable."
- **Normalization:** input runs through Unicode NFKC normalization and has zero-width/non-printing control characters stripped before use anywhere, closing the common invisible-character obfuscation trick.
- **Template isolation:** the provider-agnostic adapter has exactly one call site per intent (Doc #4: "nowhere else in the codebase names a model"), and at that call site user text is only ever passed as the *content* of a user-role message, never string-concatenated into the system/instruction template — a single, auditable interpolation point per Fast/Cheap or Reasoning call instead of many ad hoc ones.
- **Structural pattern stripping:** obvious attempts to inject role-marker strings (fake `system:` / `assistant:` delimiters) are stripped as defense-in-depth. This is deliberately lightweight — template isolation and Doc #4's forced-schema output are the real backstop, not string matching.
- **KB ingestion:** for the MVP, the only content in the retrieval index is the five authored documents from Doc #3, added by an offline build-time script — there's no live, user-facing path into RAG context yet. Any future feature that accepts community- or venue-staff-submitted KB content must pass through this same input-hygiene layer at ingestion time, not just at query time.

## 5. Rate Limiting & Abuse Prevention

Limits are enforced centrally by a shared dependency keyed on `(user_id, tier)`, using the five tiers Doc #5 already names. Because the demo runs as a single backend instance (Render Starter / Railway, per Doc #2), an in-process counter is sufficient; a multi-instance production deployment would move this to a shared store (e.g., Redis) — the known upgrade path, not a current gap.

| Tier | Guideline limit | Applies to |
|---|---|---|
| AUTH | 10 req/min per IP, short backoff after 5 failed attempts | Login, ws-ticket minting |
| STANDARD | 120 req/min per user | Task/incident CRUD, shift data |
| REALTIME_POLL | 1 req / 2s per user per channel | REST polling fallback for the three WS channels |
| AI_FAST | 30 req/min per user | Classification, translation |
| AI_REASONING | 6 req/min per user, **and** idempotency-keyed per incident state (Section 1) | Dispatch recommendation, Ask CrewLink synthesis, shift-summary generation |

**When a limit is hit:** the API returns `429` with a `Retry-After` header; the frontend shows a short inline message rather than a raw error. For AI_FAST/AI_REASONING specifically, hitting the limit routes into the same deterministic, visibly-badged fallback (`fallback_used: true`) that Docs #4 and #5 already define for AI failures — a rate limit degrades the experience gracefully instead of dead-ending it, protecting the 100%-of-scripted-path uptime NFR from Doc #1.

**Emergency exemption:** the deterministic EMS/security broadcast path never invokes the Reasoning tier (Doc #4) and is therefore never subject to AI_REASONING throttling — restated here as explicit rate-limiting policy, not just an incidental side effect.

## 6. Data Minimization & Retention

This section finalizes the retention defaults Doc #3 proposed and deferred here, built directly on the `source` enum (`SIMULATED` / `VOLUNTEER_REPORTED` / `SUPERVISOR_CREATED`) that document made schema-level. That enum is the backbone of the whole policy: `SIMULATED` records carry no privacy obligation and can be purged or reset freely, since nothing about them refers to a real person; the rules below apply only to `VOLUNTEER_REPORTED` and `SUPERVISOR_CREATED` data.

- **Chat transcripts (`ChatMessage`):** retained for the operational window plus a 30-day post-event buffer for incident follow-up, then hard-deleted rather than archived indefinitely. No audio is ever retained — Doc #1's text-only translation decision is already a data-minimization win, not just a scope cut, and this document treats it as one.
- **Accessibility-category requests:** because these can reveal disability status — the kind of sensitive-category data most privacy frameworks single out (GDPR's Article 9 "special category" concept is the most-cited example) — access is restricted to the assigned volunteer and their zone supervisor during the operational window, purged at the same 30-day mark, and shown in the supervisor rollup as de-identified counts by zone/category by default. Raw text is visible only if a volunteer explicitly escalates a specific case, not as a standing supervisor capability.
- **Position pings (`VolunteerPositionPing`):** rolling 24–48 hour retention. Their purpose is live coordination, not a movement history, so older pings are purged automatically rather than archived.
- **`AIInvocationLog`:** operational metadata (tier used, latency, success/fallback flag, cost) is retained longer, for the golden-set eval and ops purposes Doc #4 describes. Full raw prompt/completion payloads, which can carry user-supplied PII, are retained for a short debugging window (7 days) only, then truncated to metadata.

A real-tournament deployment would need this policy reviewed against the host jurisdiction's actual privacy law and FIFA's own data-processing agreements; the numbers above are engineering defaults appropriate to the demo scope, not a legal determination.

## 7. Dependency & Supply-Chain Note

Python dependencies are pinned to exact versions in `pyproject.toml` / a lockfile, and JS dependencies are locked via `package-lock.json`; neither ecosystem uses floating version ranges in the deployed artifact. Both are on Dependabot's update cadence, with version-bump PRs required to pass the existing pytest + golden-set CI gate (Doc #4 §6) before merge, plus an automated vulnerability scan (`pip-audit` and `npm audit` / Dependabot alerts) that blocks merge on a new high/critical CVE. LLM provider SDKs are the one exception to auto-merge: given how quickly that ecosystem moves and how directly it touches the orchestration layer, version bumps there get a manual review pass instead of a rubber-stamp merge.

---

## --- INDEX UPDATE ---

Doc #6 (Security & Privacy Design): Complete.

- **Prompt injection contained** — user text always fills an isolated prompt slot, never the system/instruction portion; the KB has no live ingestion path yet, closing indirect injection for the MVP; Doc #4's retrieval gate and schema-forced outputs remain the generation-side backstop.
- **Cross-volunteer/zone access blocked** — every REST and WS call carries a JWT with role/zone claims checked server-side; task feed and supervisor rollup are claim-filtered, never client-parameterized.
- **Dispatch-recommendation abuse/replay closed** — the endpoint is idempotent per incident-state and sits behind the AI_REASONING tier; the emergency broadcast path bypasses it entirely and is never throttled.
- **Secrets & auth** — keys and DB credentials load only from env vars (local `.env`, gitignored, `.env.example` checked in) or the deploy platform's secrets manager; the frontend bundle never touches an LLM key. JWT role/zone scope gates every request; WS uses short-lived, single-use tickets.
