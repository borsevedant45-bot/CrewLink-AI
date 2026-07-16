# CrewLink AI — Documentation Pipeline Blueprint
### Challenge 4: Smart Stadiums & Tournament Operations — FIFA World Cup 2026

This is the planning layer only — no project code or final documents are generated here. It contains the concept, the tech stack, the documentation sequence, and every master prompt you'll need to generate each real document later, one at a time, using only that prompt plus the current `PROJECT_INDEX.md`.

**Contents:** 1. Deep-Dive Analysis & Concept Validation · 2. Tailored Documentation Checklist · 3. Master Prompts for Document Generation · Appendix: Ready-to-Use `PROJECT_INDEX.md` Seed · How to Run This Pipeline

---

## 1. Deep-Dive Analysis & Concept Validation

### Proposed Concept: CrewLink AI

**Chosen vertical: Volunteers.** Of the four personas, a Fan-facing assistant is the default almost every team will submit — a wayfinding/FAQ chatbot is easy to build but hard to differentiate, and it mostly shows off retrieval, not reasoning. An Organizer-facing dashboard demonstrates operational intelligence well but tends to read as a BI tool with an LLM bolted on, and rarely feels like "an assistant." Volunteers sit at the intersection of nearly everything the brief cares about — they need navigation help themselves, they *are* the mechanism of crowd management and accessibility support, they're the front line for transportation questions, and they're literally the humans that "real-time decision support" has to reach in under a few seconds. That's what makes the persona choice defensible under Problem Statement Alignment, not just convenient.

**The concept:** CrewLink AI is a mobile-first GenAI command assistant for on-ground volunteers, with five parts:
1. **Contextual Task Feed** — a live, priority-ranked list of tasks/incidents scoped to the volunteer's zone, role, and language skills.
2. **AI Triage & Dispatch** — an incoming incident (medical, lost fan, translation request, accessibility request, crowd/queue issue, lost item, general query) is classified and routed to the best-matched available volunteer, with a plain-language justification for the recommendation.
3. **Multilingual Chat Bridge** — real-time translated text chat so a volunteer can converse with a fan who doesn't share a language.
4. **Ask CrewLink** — a retrieval-grounded Q&A assistant for facility, procedure, and accessibility questions, answered only from a curated knowledge base — never freeform-generated for anything safety-relevant.
5. **Supervisor Rollup** — a lightweight organizer-facing view of open incidents and AI-generated shift summaries, so the same system naturally extends to a second persona without becoming a second project.

Primary focus areas: **real-time decision support, operational intelligence, multilingual assistance.** Secondary: **accessibility, crowd management, navigation.** Sustainability and transportation are intentionally out of scope, stated up front so the documentation never has to awkwardly justify their absence later.

### Core Challenge Breakdown

- **The rubric rewards depth over breadth, and this brief is a breadth trap.** Four personas × eight focus areas is 32 plausible directions. "Problem Statement Alignment" is explicitly High Impact and measures accuracy of targeting, not coverage — a submission that nails three focus areas will outscore one that gestures at all eight shallowly.
- **"Smart, dynamic assistant" is a reasoning claim, not a UI claim.** Most competing submissions will be a chat UI in front of one system prompt. The differentiator judges can actually verify is a decision the assistant makes that requires combining several live context signals at once — that's the concrete, gradable version of "logical decision making based on user context."
- **There is no real tournament yet, so "real-time" has to be honestly synthetic.** Every "live" signal (incident volume, crowd density, volunteer position) must be simulated. The engineering task is building the simulator behind the same interface a real feed would use, and disclosing it clearly — undisclosed fake data reads as deceptive; disclosed fake data reads as good judgment, and the brief explicitly asks for "assumptions made."
- **Hallucination risk is asymmetric across question types.** A wrong merch-stand suggestion is harmless. A wrong emergency-exit or medical-station location is not. This has to become a structural decision — two different code paths — not a prompt-wording decision, or it won't survive a judge probing it.
- **Multilingual assistance, done properly, is a live-communication problem, not a translate button.** A volunteer mid-incident needs urgency and tone preserved, has to handle imperfect non-native input on both sides, and needs some signal when a translation might be unreliable in a high-stakes exchange.
- **The "boring" criteria are the tie-breakers.** Security and Testing are Medium/Low Impact, but they're exactly where a flashier, less disciplined competing demo will quietly lose points it doesn't know it's losing. A visible test suite and an absence of hardcoded secrets cost little time relative to the score they protect.

### Architectural Considerations

- **A single typed context object, assembled once per turn** (role, zone, language, current task queue, retrieved knowledge snippets) — not ad hoc string concatenation scattered across the codebase. This is both a code-quality and an efficiency concern, since context shouldn't be re-derived per LLM call.
- **Two distinct pipelines, not one mega-prompt:** a grounded/RAG path for anything facility-, safety-, or procedure-related, and a conversational path for translation, small talk, and status updates. The split must be enforced in code — which function gets called — not just requested in a prompt.
- **Model tiering for latency.** A volunteer standing next to a distressed fan cannot wait several seconds for a large model's reasoning. Cheap/fast models (or plain rules) handle classification; a stronger model is reserved for open-ended generation, and anything user-facing streams.
- **An explicit incident/task state machine** (reported → triaged → assigned → in-progress → resolved), not implicit chat-history soup — otherwise "logical decision making" isn't inspectable, and it won't hold up under a judge's follow-up question.
- **Design for hostile stadium connectivity.** Tens of thousands of phones on shared wifi/cellular is a genuinely bad network environment. The client needs optimistic UI, retry/backoff, and a cached offline-FAQ fallback so a demo doesn't visibly break if the network hiccups during judging.
- **Treat mock personal data like real personal data.** Accessibility accommodation requests and chat transcripts are sensitive even in a simulated system. No plaintext PII in logs, and a stated retention policy, cost nothing to build in now and are free credibility later.
- **Config-driven venue knowledge, never hardcoded.** Zone layouts, facility lists, and procedures should live in data/config, not in code, so the answer to "does this only work for one stadium?" is visibly "no."

### Proposed Tech Stack & Rationale

| Layer | Choice | Why |
|---|---|---|
| Frontend | React + TypeScript + Vite + Tailwind | Fast to scaffold, typed, mobile-first/PWA-capable — volunteers are standing up, on a phone, in the field |
| Backend | Python + FastAPI + Pydantic | Async-native (streaming + websockets), typed request/response validation doubles as input security, strong AI/ML ecosystem |
| LLM orchestration | A thin provider-agnostic adapter over Claude and/or GPT-class models | Lets you swap models/providers based on whatever API credits you actually have without touching business logic; fast/cheap tier for classification and translation, stronger tier only for open-ended reasoning |
| RAG / knowledge base | Chroma (local vector store) + your provider's embeddings model | Zero infrastructure cost, file-based, trivial to seed with venue documents — the thing that keeps safety-relevant answers grounded |
| Database | PostgreSQL in production / SQLite for local + demo, via SQLAlchemy | Structured, typed state for volunteers/zones/incidents/shifts; an ORM keeps this layer clean and reviewable |
| Real-time | WebSockets (native in FastAPI), polling as a fallback | Live task-feed updates without heavy infrastructure |
| Auth | JWT, scoped by role and zone | Simple, standard, no server-side session state beyond the token |
| Testing | Pytest + recorded/mocked LLM fixtures + a small golden-set eval script | Deterministic tests that don't burn API credits or flake on model nondeterminism |
| DevOps | Docker Compose locally, GitHub Actions for lint+test on push, demo deployed to a free-tier host (Render/Railway/Vercel) | Reproducibility, a live link for judges, visible CI as a code-quality signal |
| Observability | Structured logging + a simple per-request token/cost counter | Turns "efficient use of resources" from a claim into something you can show |

---

## 2. Tailored Documentation Checklist

Sequenced so each document only needs the index *summaries* of the documents before it — never the full text of any of them.

| # | Document | Purpose | Primarily supports |
|---|---|---|---|
| 0 | `PROJECT_INDEX.md` | The living summary index itself — bootstrapped first, appended after every document that follows | Everything (meta) |
| 1 | Product Requirements Document (PRD) | Locks personas, user stories, MVP vs. stretch scope | Problem Statement Alignment (High) |
| 2 | System Architecture Document | Component map, critical-path data flow, deployment view | Code Quality (High), Efficiency (Medium) |
| 3 | Data Model & Mock-Data Strategy | Schema, plus exactly how "real-time" data is simulated and disclosed | Code Quality (High), Problem Statement Alignment (High) |
| 4 | AI/LLM Orchestration & Prompt Design Document | The GenAI core: model tiering, grounding boundary, system prompts, guardrails | Problem Statement Alignment (High), Efficiency (Medium) |
| 5 | API Specification | The contract between frontend, backend, and AI layer | Code Quality (High) |
| 6 | Security & Privacy Design Document | Threat model, secrets handling, auth, input handling | Security (Medium) |
| 7 | Testing & QA Strategy Document | Test pyramid, including how non-deterministic LLM components get tested | Testing (Low) |
| 8 | Accessibility & Multilingual Design Document | WCAG mapping and language-handling approach for this app specifically | Accessibility (Low), Problem Statement Alignment (High) |
| 9 | Final Submission `README.md` | The literal hackathon deliverable, synthesized from everything above | All criteria — this is what's actually graded |

**If you're short on time:** documents 1, 2, 4, and 9 are non-negotiable — they make the submission coherent and map directly to the two High Impact criteria. Documents 3, 5, 6, 7, and 8 can be run as shorter passes (add "keep each section to 3-4 bullets" to the prompt) rather than skipped outright, since each still maps to a graded criterion.

---

## 3. Master Prompts for Document Generation

Each prompt is self-contained and copy-pasteable. Paste the prompt text together with your current `PROJECT_INDEX.md` (as a file or pasted content) into a fresh conversation.

**One structural note: Document 0 is the exception.** Every other prompt follows the same three-part shape — read the index, generate the document, append a summary to the index. Document 0 can't read an index that doesn't exist yet, and its output *is* the index, so its prompt is seeded directly with the concept and stack from Section 1 instead, and it initializes the Document Log that every later prompt writes into.

### Document 0: `PROJECT_INDEX.md` (Bootstrap)

**The Master Prompt:**
```text
You are a Technical Program Manager setting up the master context file for a multi-document, AI-assisted build. There is no existing PROJECT_INDEX.md yet — you are creating the first version from the compiled project analysis below. Do not invent new requirements; only structure what's given.

PROJECT CONCEPT: CrewLink AI is a mobile-first GenAI command assistant for FIFA World Cup 2026 volunteers. It has five parts: (1) a live, priority-ranked Contextual Task Feed scoped to the volunteer's zone, role, and language skills; (2) an AI Triage & Dispatch pipeline that classifies incoming incidents (medical, lost fan, translation request, accessibility request, crowd/queue issue, lost item, general query) and recommends the best-matched available volunteer with a plain-language justification; (3) a Multilingual Chat Bridge for real-time translated text chat between a volunteer and a fan who doesn't share a language; (4) "Ask CrewLink," a retrieval-grounded Q&A assistant that answers facility/procedure/accessibility questions only from a curated knowledge base, never freeform-generated for safety-relevant topics; and (5) a Supervisor Rollup giving organizers a lightweight view of open incidents and AI-generated shift summaries.

VERTICAL: Volunteers (primary). Focus areas: real-time decision support, operational intelligence, multilingual assistance (primary); accessibility, crowd management, navigation (secondary). Sustainability and transportation are explicitly out of scope.

TECH STACK: React/TypeScript/Vite/Tailwind frontend; FastAPI/Pydantic backend; provider-agnostic LLM adapter (fast/cheap tier for classification & translation, stronger tier for reasoning) over Claude and/or GPT-class models; Chroma for RAG; PostgreSQL/SQLite via SQLAlchemy; WebSockets for real-time; JWT auth; Pytest with mocked LLM fixtures; Docker Compose + GitHub Actions.

KEY ASSUMPTIONS TO CARRY FORWARD: (a) the tournament hasn't happened yet, so every "live" feed — incident volume, crowd density, volunteer position — is simulated and must be clearly labeled as such everywhere it appears, including the README; (b) the app targets one representative venue archetype, with venue specifics (maps, zones, procedures) stored as config/knowledge-base content, not hardcoded, so it is portable to other venues without code changes; (c) multilingual support targets text-based real-time translation for the MVP — voice-to-voice is a stretch goal; (d) there is no integration with real FIFA ticketing/accreditation systems — identity is mocked via a simple auth scheme sufficient for a demo; (e) the RAG knowledge base is seeded with a small set of representative venue documents written for this demo, not sourced from an actual stadium's operations manual.

Create the FIRST version of PROJECT_INDEX.md, structured exactly as:

# PROJECT_INDEX.md
## 1. Project Snapshot
One paragraph: what this is, who it's for, what problem it solves.
## 2. Chosen Vertical & Scope
Persona, in-scope focus areas, and explicitly out-of-scope items.
## 3. Tech Stack
One bullet per layer.
## 4. Key Assumptions
Bulleted, carried forward from above — do not drop any of them.
## 5. Document Log
A markdown table: Doc # | Document Name | Status | One-line Summary. Pre-fill row 0 for this file as "Complete." List rows 1-9 (PRD, System Architecture, Data Model & Mock-Data Strategy, AI/LLM Orchestration & Prompt Design, API Specification, Security & Privacy Design, Testing & QA Strategy, Accessibility & Multilingual Design, Final README) as "Not started."

Output ONLY the PROJECT_INDEX.md content, ready to save as-is — no commentary before or after it.
```

### Document 1: Product Requirements Document (PRD)

**The Master Prompt:**
```text
You are a Senior Product Manager who specializes in turning hackathon problem statements into rigorous, judge-ready PRDs.

Read the attached PROJECT_INDEX.md fully before writing anything — it contains the chosen vertical, concept, tech stack, and assumptions for CrewLink AI. Do not restate it at length; reference it.

Write a complete Product Requirements Document for CrewLink AI, structured exactly as:

1. Problem & Opportunity — restate the original challenge in your own words, then explain in 3-4 sentences why the Volunteer vertical was chosen over Fan/Organizer/Venue-Staff alternatives.
2. Primary Persona — a detailed volunteer persona (name, tournament role, technical comfort level, language needs) plus one representative "day in the life" scenario during a live match.
3. Secondary Personas — 2-3 sentences each for the fan who benefits indirectly and the supervisor who uses the rollup view.
4. User Stories — at least 8, in "As a [persona], I want [capability], so that [outcome]" format, each tagged Must / Should / Could (MoSCoW).
5. Functional Requirements — numbered, each traceable to a user story number.
6. Non-Functional Requirements — latency targets, uptime expectations for a live demo, and a stated, justified concurrency assumption.
7. Explicit Out-of-Scope — what is intentionally not being built, and why.
8. Success Metrics — how you'd know this worked in a real tournament, even though measuring it is out of scope for the hackathon build.
9. Assumptions — expand on the Key Assumptions already logged in PROJECT_INDEX.md without contradicting them.

At the very end, under a heading `--- INDEX UPDATE ---`, give a concise bulleted summary (max 150 words) of this PRD for PROJECT_INDEX.md's Document Log — include the finalized persona name and the top 3 Must-have requirements.
```

### Document 2: System Architecture Document

**The Master Prompt:**
```text
You are a Principal Software Architect specializing in GenAI-native application design.

Read the attached PROJECT_INDEX.md (including the PRD summary) before writing anything. Reference it; do not restate it.

Write a complete System Architecture Document for CrewLink AI, structured exactly as:

1. Architecture Style & Rationale — justify a decoupled frontend/backend split with a distinct AI-orchestration layer, tying the justification to the latency and grounding concerns already logged in the index.
2. Component Diagram — a Mermaid `graph TD` block showing: Frontend (React PWA), Backend (FastAPI), AI Orchestration Layer, RAG/Vector Store, Primary Database, Real-Time/WebSocket channel, and the Mock Real-Time Data Simulator as its own clearly labeled component — never disguised as a real feed.
3. Critical Path Walkthrough — trace ONE full request end-to-end for AI Triage & Dispatch: incident reported → classification → knowledge-base lookup (if applicable) → dispatch recommendation → volunteer notified. State which model tier handles each step and why.
4. Multilingual Chat Bridge Data Flow — a second, shorter walkthrough for real-time translation.
5. State Management — the incident/task lifecycle as an explicit state machine (states + valid transitions).
6. Deployment View — local dev (Docker Compose) vs. demo deployment, naming specific low-cost hosts for frontend, backend, and vector store.
7. Scalability & Multi-Venue Note — one paragraph on what would need to change (config only, not code) to point this at a second stadium.
8. Key Architectural Risks — 3-5 risks, one-line mitigation each.

At the very end, under `--- INDEX UPDATE ---`, give a concise bulleted summary (max 150 words) of the finalized components and the model-tier decision per critical-path step, for PROJECT_INDEX.md.
```

### Document 3: Data Model & Mock-Data Strategy Document

**The Master Prompt:**
```text
You are a Staff Data Engineer who is meticulous about disclosing synthetic data as synthetic.

Read the attached PROJECT_INDEX.md (PRD and Architecture summaries) before writing anything.

Write a complete Data Model & Mock-Data Strategy Document for CrewLink AI, structured exactly as:

1. Entity List & Relationships — Volunteer, Zone, Incident/Task, Shift, KnowledgeBaseDocument, ChatSession (add others only if the Architecture summary implies them). Fields, types, relationships, as a Mermaid `erDiagram` block.
2. Incident/Task Schema Deep-Dive — every field the AI triage classifier reads or writes, matched to the categories already named in PROJECT_INDEX.md (medical, lost fan, translation, accessibility, crowd/queue, lost item, general).
3. Knowledge Base Corpus Plan — which documents make up the demo's RAG corpus (venue map descriptions, safety procedures, accessibility facilities, FAQ), how they're chunked, and how many are enough for a credible demo without over-building.
4. Mock Real-Time Data Generator Spec — exactly how simulated incidents, crowd density readings, and volunteer positions are generated (rate, distribution, realistic variability), and precisely how this is labeled in the running app and README so it's never mistaken for a live feed.
5. Data Retention & Minimization Notes — for anything resembling personal or accessibility-related data, even mocked, state what's stored, for how long, and why. State facts only here — full threat modeling belongs in the Security document.

At the very end, under `--- INDEX UPDATE ---`, give a concise bulleted summary (max 150 words) of the finalized schema entities and the mock-data disclosure approach, for PROJECT_INDEX.md.
```

### Document 4: AI/LLM Orchestration & Prompt Design Document

**The Master Prompt:**
```text
You are a Staff AI Engineer specializing in production LLM orchestration, prompt design, and hallucination mitigation for safety-adjacent applications.

Read the attached PROJECT_INDEX.md (PRD, Architecture, and Data Model summaries) before writing anything.

Write a complete AI/LLM Orchestration & Prompt Design Document for CrewLink AI, structured exactly as:

1. Model Tiering Strategy — which task uses a fast/cheap model vs. a stronger reasoning model (incident classification, dispatch recommendation, translation, RAG-grounded Q&A, supervisor shift-summary generation), one-sentence justification each. Keep the provider abstracted behind an interface so models can be swapped without touching business logic.
2. The Grounding Boundary — which intents MUST go through the RAG pipeline (anything facility-, safety-, or procedure-related) vs. which may be handled conversationally (translation, small talk, status updates), and how the code enforces the split — not just the prompt wording.
3. System Prompts — the actual system prompt text for: (a) the Incident Classifier, (b) the Dispatch Recommender, (c) the Translation Bridge, (d) the "Ask CrewLink" RAG assistant. Each must specify role, allowed output format, and explicit escalation instructions for emergencies (e.g., always instruct immediate human/EMS escalation for medical situations rather than letting the model attempt to help medically).
4. Structured Output Schemas — the exact JSON schema the Classifier and Dispatch Recommender must return, and the tool/function-calling mechanism used to enforce it.
5. Guardrails — prompt-injection handling for free-text incident descriptions and chat messages, output validation before anything reaches a volunteer's screen, and fallback behavior if a model call fails or times out.
6. Evaluation Approach — a golden set of 10-15 example incidents/questions with expected classification/behavior, to regression-test future prompt changes.

At the very end, under `--- INDEX UPDATE ---`, give a concise bulleted summary (max 150 words) of the model-tiering decisions and the grounding-boundary rule, for PROJECT_INDEX.md.
```

### Document 5: API Specification

**The Master Prompt:**
```text
You are a Senior Backend Engineer who writes API specifications precise enough for a frontend developer to build against without ever reading the backend code.

Read the attached PROJECT_INDEX.md (Architecture, Data Model, and AI Orchestration summaries) before writing anything.

Write a complete API Specification for CrewLink AI, structured exactly as:

1. Conventions — base URL pattern, auth header format, error envelope shape, pagination style (pick one, apply it consistently below).
2. REST Endpoints — one table per resource (Volunteers, Zones, Incidents/Tasks, Shifts, Chat Sessions, Knowledge Base): method, path, purpose, request schema, response schema, auth requirement, rate-limit tier.
3. WebSocket Channels — event names, payload schemas, and which client roles subscribe to which channel (volunteer task feed vs. supervisor dashboard).
4. AI-Specific Endpoints — the endpoint(s) triggering the incident classifier/dispatch recommender and the translation bridge, with one full example request/response pair each, matching the structured output schema from the AI Orchestration document.
5. Error Handling Matrix — every error case that matters for a live demo (LLM timeout, RAG store unavailable, invalid auth, rate limit hit), mapped to an HTTP status and a user-facing fallback message.

At the very end, under `--- INDEX UPDATE ---`, give a concise bulleted summary (max 150 words) of the finalized endpoint list and the auth/rate-limit scheme, for PROJECT_INDEX.md.
```

### Document 6: Security & Privacy Design Document

**The Master Prompt:**
```text
You are a Staff Security Engineer who specializes in threat-modeling LLM-integrated applications, not just traditional web apps.

Read the attached PROJECT_INDEX.md (Architecture, Data Model, API Spec, and AI Orchestration summaries) before writing anything.

Write a complete Security & Privacy Design Document for CrewLink AI, structured exactly as:

1. Threat Model — a table of Asset | Threat | Likelihood | Impact | Mitigation, explicitly covering: prompt injection via free-text incident/chat fields, LLM API key exposure, unauthorized access to another volunteer's task feed, abuse/replay of the dispatch-recommendation endpoint, and scraping of the accessibility/PII-adjacent fields identified in the Data Model document.
2. Secrets Management — exactly how API keys and DB credentials are loaded (env vars / secrets manager), with an explicit statement that nothing is hardcoded or committed, and what the `.gitignore`/`.env.example` pattern looks like.
3. AuthN/AuthZ — how a volunteer's identity and role/zone scope is verified on every request, and how the supervisor view is restricted from regular volunteers.
4. Input Handling — validation/sanitization applied before any user-supplied text reaches a prompt, referencing (not re-deriving) the guardrails from the AI Orchestration document.
5. Rate Limiting & Abuse Prevention — limits per endpoint, especially the AI-calling ones, and the user-facing behavior when a limit is hit.
6. Data Minimization & Retention — restate and finalize (without contradicting) the retention notes from the Data Model document, specifically for chat transcripts and accessibility-related requests.
7. Dependency & Supply-Chain Note — one paragraph on how third-party package versions are pinned and reviewed.

At the very end, under `--- INDEX UPDATE ---`, give a concise bulleted summary (max 150 words) of the top 3 mitigated threats and the secrets/auth approach, for PROJECT_INDEX.md.
```

### Document 7: Testing & QA Strategy Document

**The Master Prompt:**
```text
You are a Staff QA/Test Engineer who specializes in testing systems that include non-deterministic LLM components.

Read the attached PROJECT_INDEX.md (Data Model, AI Orchestration, and API Spec summaries) before writing anything.

Write a complete Testing & QA Strategy Document for CrewLink AI, structured exactly as:

1. Test Pyramid for This Project — the effort split across unit/integration/end-to-end, and why it's shaped differently than a typical CRUD app because of the AI layer.
2. Deterministic Unit Tests — the core business-logic units tested without ever calling a real LLM (dispatch-matching algorithm, state-machine transitions, schema validation), one line each on what's asserted.
3. LLM Component Testing Strategy — how the Incident Classifier, Dispatch Recommender, and RAG assistant are tested using the golden set from the AI Orchestration document: mocked/recorded responses for CI, plus an optional live-model regression run, and what "pass" means when outputs are non-deterministic (schema conformance + category-accuracy threshold, not exact string match).
4. Integration Tests — the 3-5 most important end-to-end flows (e.g., incident reported → classified → dispatched → resolved) and what each asserts at the API boundary.
5. Accessibility & Multilingual Test Cases — a short list of checks, flagged as a dependency on the next document (finalized there).
6. CI Pipeline — what runs on every push (lint, type-check, unit, mocked-integration) vs. what stays manual/optional (live-model eval), described as it would appear in a GitHub Actions workflow.

At the very end, under `--- INDEX UPDATE ---`, give a concise bulleted summary (max 150 words) of the testing approach and what CI enforces automatically, for PROJECT_INDEX.md.
```

### Document 8: Accessibility & Multilingual Design Document

**The Master Prompt:**
```text
You are a Senior Accessibility Engineer and Localization Specialist who has shipped inclusive products for large public events.

Read the attached PROJECT_INDEX.md (PRD and API Spec summaries) before writing anything.

Write a complete Accessibility & Multilingual Design Document for CrewLink AI, structured exactly as:

1. WCAG 2.1 AA Checklist — mapped specifically to CrewLink AI's actual screens/flows (task feed, incident detail, chat bridge, Ask CrewLink), not a generic checklist. Mark each item pass / planned / deferred.
2. Assistive Technology Considerations — screen-reader behavior for the live-updating task feed (updates must be announced, not silently repainted), full keyboard operability for a volunteer under stress, and color-independent status indicators for incident priority.
3. Multilingual Architecture — which UI strings are static-translated (i18n files) vs. dynamically translated via the LLM (chat bridge, freeform incident descriptions), and how language is detected/selected per user.
4. Language Quality & Safety Net — how a mistranslation in a safety-relevant exchange gets caught or flagged (confidence signal, human-in-the-loop confirmation for high-stakes phrases), referencing the grounding boundary already defined in the AI Orchestration document.
5. Field-Condition Usability — accommodations for glare, one-handed use, gloves, and noisy environments, since the primary user is standing outdoors or in a concourse, not seated at a desk.
6. Accessibility for Fans (Secondary Persona) — how the accessibility-request incident category from the Data Model document ties back to real accommodations, in plain language.

At the very end, under `--- INDEX UPDATE ---`, give a concise bulleted summary (max 150 words) of the accessibility commitments and multilingual approach, for PROJECT_INDEX.md.
```

### Document 9: Final Submission README.md

**The Master Prompt:**
```text
You are a Technical Writer who specializes in hackathon submission documents a judge can evaluate in under 5 minutes.

Read the attached PROJECT_INDEX.md in full — by now it holds summaries of every prior document (PRD, Architecture, Data Model, AI Orchestration, API Spec, Security, Testing, Accessibility). Synthesize across all of them; do not just restate the index verbatim.

Write the final submission README.md for CrewLink AI, structured exactly as:

1. Title & One-Line Pitch
2. Chosen Vertical — state Volunteers explicitly, and justify it in 2-3 sentences (why this over Fan/Organizer/Venue-Staff).
3. Approach & Logic — a judge-readable walkthrough of how the AI actually makes decisions (model tiering, grounding boundary, dispatch logic), written for a technical reviewer who has not read the other documents.
4. How the Solution Works — a numbered, end-to-end walkthrough of the primary demo flow (incident reported → AI triage → dispatch → resolution) plus the multilingual chat bridge, written so someone could follow along while watching a live demo.
5. Architecture at a Glance — a simplified version of the Architecture document's diagram (simplify; do not paste the full detailed one).
6. Tech Stack — a concise bullet list.
7. Assumptions Made — pulled honestly and completely from every assumptions/mock-data/out-of-scope note logged across the index. This section must be complete; the brief explicitly grades on it.
8. Security & Testing Highlights — 3-4 bullets each, written for a non-specialist judge.
9. Accessibility Highlights — 2-3 bullets.
10. Setup/Run Instructions — placeholder section with exact headers (Prerequisites, Installation, Environment Variables, Running Locally, Running Tests), to be filled in once code exists.
11. Team & Acknowledgments — placeholder.

At the very end, under `--- INDEX UPDATE ---`, give a concise bulleted summary (max 100 words) marking this as the final document and closing out the Document Log — useful if you later generate a demo script or pitch deck from this same index.
```

---

## Appendix: Ready-to-Use `PROJECT_INDEX.md` Seed

Since the concept and stack are already locked in above, here's the actual bootstrapped file — save this directly as `PROJECT_INDEX.md` and skip Document 0's prompt unless you want to regenerate it from scratch in a fresh session.

```markdown
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
| Doc # | Document Name | Status | One-line Summary |
|---|---|---|---|
| 0 | PROJECT_INDEX.md | Complete | This file — living summary index for the project. |
| 1 | Product Requirements Document | Not started | — |
| 2 | System Architecture Document | Not started | — |
| 3 | Data Model & Mock-Data Strategy | Not started | — |
| 4 | AI/LLM Orchestration & Prompt Design | Not started | — |
| 5 | API Specification | Not started | — |
| 6 | Security & Privacy Design | Not started | — |
| 7 | Testing & QA Strategy | Not started | — |
| 8 | Accessibility & Multilingual Design | Not started | — |
| 9 | Final README.md | Not started | — |
```

---

## How to Run This Pipeline

1. Save the Appendix block above as `PROJECT_INDEX.md` right now — it's already seeded, so you can skip Document 0's prompt unless you want to regenerate it from scratch in a fresh session.
2. For each remaining document, start a new conversation (or a fresh Claude Code session) and provide only: that document's Master Prompt + your current `PROJECT_INDEX.md`.
3. Save the generated document, then copy its `--- INDEX UPDATE ---` block into `PROJECT_INDEX.md` under Section 5, and flip that row's Status to Complete.
4. Move to the next document in order — the sequence in Section 2 is dependency-ordered, so don't skip ahead.
5. Document 9 (README.md) is the actual hackathon deliverable — everything before it exists to make that document accurate and defensible.
