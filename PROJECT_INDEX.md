# PROJECT_INDEX.md

## 1. Project Snapshot
CrewLink AI is a mobile-first GenAI command assistant built for FIFA World Cup 2026 volunteers. It gives each volunteer a live, priority-ranked task feed; an AI triage-and-dispatch pipeline that classifies incoming incidents and recommends the best-matched responder; a real-time multilingual chat bridge for talking with fans who don't share a language; a retrieval-grounded "Ask CrewLink" assistant for facility and procedure questions; and a lightweight supervisor rollup for organizers. It targets the Volunteer vertical of Challenge 4: Smart Stadiums & Tournament Operations.

## 2. Chosen Vertical & Scope
- **Persona:** Volunteers (primary); Fans and Supervisors/Organizers benefit as secondary personas through the same system.
- **In scope:** real-time decision support, operational intelligence, multilingual assistance (primary focus areas); accessibility, crowd management, navigation (secondary).
- **Explicitly out of scope:** sustainability, transportation.

## 3. Tech Stack
- Frontend: React + TypeScript + Vite + Tailwind (mobile-first PWA)
- Backend: Python + FastAPI + Pydantic
- LLM orchestration: provider-agnostic adapter, fast/cheap tier + stronger reasoning tier
- RAG: Chroma vector store
- Database: PostgreSQL (prod) / SQLite (local & demo) via SQLAlchemy
- Real-time: WebSockets, polling fallback
- Auth: JWT, scoped by role and zone
- Testing: Pytest + mocked LLM fixtures + golden-set eval
- DevOps: Docker Compose, GitHub Actions, free-tier deploy for the demo

## 4. Key Assumptions
- The tournament hasn't happened yet — every "live" signal (incidents, crowd density, volunteer position) is simulated and clearly labeled as such everywhere it appears, including the README.
- The build targets one representative venue archetype; venue specifics live in config/knowledge-base content, not code, so it's portable to other venues.
- Multilingual support is text-based real-time translation for the MVP; voice-to-voice is a stretch goal.
- No integration with real FIFA ticketing/accreditation systems — identity is mocked via a simple auth scheme sufficient for a demo.
- The RAG knowledge base is seeded with a small set of representative venue documents written for this demo, not a real stadium's operations manual.

## 5. Document Log
All design docs live in `docs/`. Operational files (AGENTS.md, PROGRESS.md, this index) stay at root.

| Doc # | File | Status | One-line Summary |
|---|---|---|---|
| 0 | PROJECT_INDEX.md | Complete | This file — living summary index for the project. |
| 1 | `docs/01_Product_Requirements_Document.md` | Complete | Volunteer-vertical PRD — persona **Maria Alvarez** (bilingual Fan Experience volunteer), secondary personas Kenji (fan) & Devon (supervisor); 14 MoSCoW stories; 23 FRs; top Musts = task feed, AI triage/dispatch, multilingual chat bridge. |
| 2 | `docs/02_System_Architecture_Document.md` | Complete | The file details a decoupled, three-tier architecture—comprising a React frontend, a FastAPI backend, and a dedicated AI orchestration layer—built to provide stadium volunteers with real-time, low-latency task dispatching and multilingual translation during a live demo. |
| 3 | `docs/03_Data_Model_and_Mock_Data_Strategy.md` | Complete | This document defines the application's eleven-entity database schema, outlines the seeded knowledge base structure, and details a mock data generator that produces and strictly tags all simulated stadium incidents and crowd metrics for the demo. |
| 4 | `docs/04_AI_LLM_Orchestration_and_Prompt_Design.md` | Complete | This document establishes the "AI Orchestration Layer," detailing how the system routes tasks between a fast/cheap AI model (for tasks like categorization and translation) and a slower, more advanced reasoning model (for tasks like dispatching and answering procedure questions), while enforcing strict code-level safety boundaries to prevent the AI from giving medical advice or hallucinating information. |
| 5 | `docs/05_API_SPECIFICATION.md` | Complete | Doc #5 outlines the CrewLink AI API specification, establishing the contract for REST endpoints, WebSocket channels, error handling, rate limits, and AI-specific tool calls between the backend and frontend. |
| 6 | `docs/06_SECURITY_PRIVACY_DESIGN.md` | Complete | This document outlines CrewLink AI's comprehensive security and privacy framework, detailing threat mitigation strategies such as prompt injection defenses, JWT-based zone authorization, strict secrets management, rate limiting, and structured data retention policies |
| 7 | `docs/07_Testing_QA_Strategy.md` | Complete | **CrewLink AI Doc #7: Testing & QA Strategy** outlines the end-to-end testing framework for the system, establishing a modified test pyramid (~55% deterministic unit, ~25% LLM golden-set, ~12% integration, ~8% scripted E2E) designed to test the contracts and guardrails around non-deterministic generative outputs rather than asserting strict equality. |
| 8 | `docs/08_Accessibility_and_Multilingual_Design.md` | Complete | Screen-mapped WCAG 2.1 AA checklist, live-region/keyboard/color-independent AT design, static-vs-LLM multilingual architecture, translation confidence + human-in-the-loop safety net, field-condition usability, and fan accessibility-request handling. |
| 9 | `docs/CrewLink_AI_Blueprint.md` | Complete | Original project blueprint — founding document. |
| A | `docs/ADDENDUM_v1.md` | Complete | Post-design amendments: G1–G20 (override behaviour, En Route mapping, WS format, rollup endpoint, etc.). |
| — | `README.md` | Complete | Project front door — install, run, test instructions. |


Doc #1 (Product Requirements Document): Complete.
Restates Challenge 4 (Smart Stadiums & Tournament Operations) and justifies choosing the Volunteer vertical over Fan/Organizer/Venue-Staff as the highest-leverage persona.
Finalized primary persona: Maria Alvarez, bilingual (English/Spanish) Fan Experience & Guest Services volunteer, East Concourse zone, Founders Field.
Secondary personas defined: fan Kenji Watanabe (indirect beneficiary via the multilingual bridge) and supervisor Devon Price (rollup view).
14 MoSCoW user stories (5 Must / 4 Should / 5 Could) and 23 functional requirements, each traced to a story.
Top 3 Must-haves: (1) live priority-ranked task feed per volunteer/zone, (2) AI triage classification + best-match responder dispatch, (3) real-time multilingual chat bridge.
NFRs set demo-scoped latency (<2–6s by feature), uptime (100% of the scripted demo path), and concurrency (~50 volunteers) targets.
Confirms out-of-scope items and adds real-tournament success metrics for future measurement.

Doc #2 (System Architecture Document): Complete.
Architecture finalized: decoupled Frontend (React PWA) / Backend (FastAPI) / distinct AI Orchestration Layer, linked via JWT-scoped REST and a WebSocket channel with polling fallback.
AI Orchestration Layer: one provider-agnostic router exposing two tiers — Fast/Cheap (classification, translation) and Reasoning (dispatch judgment, Ask CrewLink synthesis).
Triage & Dispatch critical path: classification → Fast/Cheap tier; KB lookup → Chroma retrieval, conditional and non-generative; dispatch recommendation → Reasoning tier; notification → deterministic push, no model.
Chat Bridge: Fast/Cheap tier only, no RAG involvement.
Mock Real-Time Data Simulator: formalized as its own component, feeding the Backend only, schema-tagged source: simulated.
Incident lifecycle: Reported → Triaged → Dispatched → Acknowledged → InProgress → Resolved, with Escalated/Cancelled reachable from every non-terminal state.
Demo deployment: Vercel or Render (frontend), Render Starter or Railway (backend — protects the uptime NFR), embedded Chroma (vector store).

Doc #3 (Data Model & Mock-Data Strategy Document): Complete.
Eleven entities finalized: the six requested plus five architecture-implied additions (ChatMessage, KnowledgeBaseChunk, CrowdDensityReading, VolunteerPositionPing, AIInvocationLog); no separate Supervisor, Fan, or AskCrewLinkQuery entities.
source enum (SIMULATED / VOLUNTEER_REPORTED / SUPERVISOR_CREATED) made schema-level, not just UI copy, on Incident, CrowdDensityReading, and VolunteerPositionPing.
Incident category taxonomy (medical, lost fan, translation, accessibility, crowd/queue, lost item, general) mapped to classifier read/write fields; priority score is deterministic, not a raw model output.
KB corpus sized at 5 authored documents (~25–40 chunks): venue guide, 2 safety-procedure docs, accessibility guide, FAQ — explicitly not derived from any real venue's manual.
Mock generator fully specified: Poisson incident arrivals, mean-reverting crowd-density walk, sticky-zone volunteer pings; mandatory in-app SIMULATED badges and a required README disclosure section.
Retention defaults proposed for volunteer, chat, and position data, with real-vs-simulated content distinguished; full threat modeling deferred to Doc #6.

Doc #4 (AI/LLM Orchestration & Prompt Design Document): Complete.
Two-tier routing (Fast/Cheap vs. Reasoning) sits behind one provider-agnostic interface: classification, intent routing, and translation are Fast/Cheap; dispatch recommendation, Ask CrewLink synthesis, and shift-summary generation are Reasoning — nowhere else in the codebase names a model.
Grounding boundary: facility/safety/procedure intents MUST route through Chroma with a code-level gate — generation never runs without a non-empty, above-threshold retrieval result; translation, small talk, and status updates are conversational with no retrieval path in code.
requires_emergency_escalation bypasses the Reasoning-tier Dispatch Recommender entirely in favor of a deterministic EMS/security broadcast; the Translation Bridge carries a parallel emergency_flag so a language barrier never delays escalation.
All structured outputs are Pydantic-schema tool calls with forced tool choice, validated again in application code, backed by deterministic, visibly-badged fallbacks for every AI call site.
A 15-case golden set (Section 6) regression-tests all of the above in CI.

Doc #5 (API Specification) is complete. REST is versioned under /api/v1; JWT Bearer auth carries role + zone scope; pagination is cursor-based everywhere; five rate-limit tiers gate calls: AUTH, STANDARD, REALTIME_POLL, AI_FAST, AI_REASONING.
Six resource tables finalized — Volunteers, Zones, Incidents/Tasks, Shifts, Chat Sessions, Knowledge Base — plus a prerequisite Auth/ws-ticket table.
Incident pipeline: POST /incidents runs Fast/Cheap classification synchronously; POST /incidents/{id}/dispatch-recommendation runs the Reasoning-tier recommender; emergencies bypass dispatch for a deterministic EMS/security broadcast.
Chat bridge (POST /chat-sessions/{id}/messages) runs Fast/Cheap translation and carries its own emergency_flag.
Ask CrewLink (POST /knowledge-base/ask) is gated on non-empty Chroma retrieval.
Three WS channels — /ws/tasks, /ws/chat/{id}, /ws/supervisor — each with a documented REST polling fallback.
Error matrix separates soft, visibly-badged AI fallbacks (2xx + fallback_used) from true infrastructure failures (503).

Doc #6 (Security & Privacy Design): Complete.
Prompt injection contained — user text always fills an isolated prompt slot, never the system/instruction portion; the KB has no live ingestion path yet, closing indirect injection for the MVP; Doc #4's retrieval gate and schema-forced outputs remain the generation-side backstop.
Cross-volunteer/zone access blocked — every REST and WS call carries a JWT with role/zone claims checked server-side; task feed and supervisor rollup are claim-filtered, never client-parameterized.
Dispatch-recommendation abuse/replay closed — the endpoint is idempotent per incident-state and sits behind the AI_REASONING tier; the emergency broadcast path bypasses it entirely and is never throttled.
Secrets & auth — keys and DB credentials load only from env vars (local .env, gitignored, .env.example checked in) or the deploy platform's secrets manager; the frontend bundle never touches an LLM key. JWT role/zone scope gates every request; WS uses short-lived, single-use tickets.

Doc #7 (Testing & QA Strategy): Complete.
- Test pyramid reshaped for the AI layer: ~55% deterministic unit / ~25% LLM golden-set / ~12% integration / ~8% scripted E2E — golden-set testing is a distinct new layer, not just more unit tests.
- Deterministic units (no LLM calls) cover dispatch-candidate filtering, the full incident state machine, schema/retrieval-gate validators, source-tag enforcement, and rate-limit tiers.
- Classifier, Dispatch Recommender, and Ask CrewLink graded against Doc #4's 15-case golden set via schema-conformance (hard 100% gate) plus category-accuracy/groundedness thresholds — never exact-match; mocked/recorded fixtures run in CI, live-model regression is manual/nightly and never blocks a merge.
- 5 integration flows defined at the API boundary: golden dispatch path, emergency-escalation bypass, chat bridge, Ask CrewLink retrieval gate, cross-zone auth/rollup.
- Accessibility/multilingual checks scaffolded provisionally pending Doc #8.
- GitHub Actions: lint/typecheck/secret-scan/unit/mocked-integration/golden-set-mocked block merges; live-model eval is workflow_dispatch + nightly only.

**Doc #8 (Accessibility & Multilingual Design Document): Complete.**
- WCAG 2.1 AA mapped screen-by-screen (task feed, incident detail, chat bridge, Ask CrewLink), not generically; live feed updates use status-message live regions, never silent repaint.
- Full keyboard operability specified for one-handed, stressed use; priority and status are always color + icon + text, never color alone.
- Multilingual split finalized: UI chrome and fixed enums are static i18n; chat, freeform descriptions, and Ask CrewLink answers are dynamically translated via the Fast/Cheap tier, kept separate from Reasoning-tier grounding.
- Adds a translation confidence + back-translation + human-interpreter safety net for medical/accessibility/emergency content, alongside (not inside) Doc #4's grounding gate — closes Doc #7's provisional test gap.
- Defines glare, one-handed/gloved, and noise accommodations; ties the `accessibility` incident category to real accommodations via the KB.