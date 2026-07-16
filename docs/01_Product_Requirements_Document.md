# Product Requirements Document — CrewLink AI

*Doc #1 in the CrewLink AI Document Log · Status: Complete (v1) · Builds on PROJECT_INDEX.md (Doc 0), which is referenced throughout but not restated.*

---

## 1. Problem & Opportunity

**The challenge, restated.** Challenge 4 — Smart Stadiums & Tournament Operations — asks teams to build AI-enabled tools that make a major tournament venue run faster, safer, and more coherently, across a broad menu of possible focus areas: real-time decision support, operational intelligence, multilingual communication, accessibility, crowd management, navigation, sustainability, and transportation. Stripped of the menu, the underlying problem is simple to state and hard to solve: a World Cup venue runs on thousands of people — many of them volunteers doing the job for the first time — making fast, high-stakes decisions on fragmented information, often across a language barrier, and the tooling most venues still lean on (handheld radios, paper runsheets, ad hoc group chats) was never built for that scale or that language mix.

**Why the Volunteer vertical, and not Fan, Organizer, or Venue-Staff.** Volunteers are the largest and most physically distributed human layer in stadium operations, and — unlike paid venue staff — they typically arrive with the least specialized training relative to how much they're relied on as the first point of contact for almost everything a fan or an organizer needs; that combination makes the marginal value of AI decision support highest here, not lowest. Volunteers also sit structurally between the other two personas: they're the literal interface between a fan's in-the-moment problem and an organizer's need for situational awareness, so a tool built for volunteers creates second-order value for both without the team needing to design, build, and demo three separate products on a hackathon timeline. Only the volunteer vertical exercises all four core capabilities — the task feed, the triage-and-dispatch pipeline, the multilingual bridge, and Ask CrewLink — inside one coherent daily workflow, which matters enormously for telling a believable, single-persona demo story rather than a scattered tour of disconnected screens.

## 2. Primary Persona

**Maria Alvarez** — Volunteer, Fan Experience & Guest Services team, assigned to the East Concourse (Sections 100–120) at **Founders Field**, a fictional composite ~65,000-seat venue used as this build's single representative archetype (Key Assumption 2).

| Attribute | Detail |
|---|---|
| Age / background | 34; works as a school administrative coordinator; this is her second major event (previously volunteered at a regional marathon) |
| Tournament role | Fan Experience & Guest Services, East Concourse zone, 4-hour matchday shifts |
| Technical comfort | Moderate — daily smartphone user (maps, messaging, banking) but has never used dispatch or operations software; needs a near-zero learning curve |
| Language needs | Fluent English and Spanish; no other languages — fully dependent on the multilingual bridge for everything else |
| Equipment | Personal smartphone running the PWA; shared analog radio channel with 6 zone volunteers and 1 supervisor as backup |

**A day in the life — matchday, second group-stage fixture**

- **T-45 min:** Maria checks in through the app. Her feed shows her zone assignment and two low-priority wayfinding tasks. Ask CrewLink surfaces an unprompted shift-briefing card summarizing the day's gate and closure notes (simulated).
- **23′:** A visibly distressed fan — Kenji, visiting from Osaka — approaches her. Neither shares a strong second language. She opens the multilingual chat bridge; Kenji types in Japanese, Maria reads it in English and replies, and Kenji sees a back-translated confirmation of what she'll receive before it sends.
- Once the system classifies this as a lost-child report, the triage pipeline tags it **Critical**, recommends immediate co-assignment to the nearest security-trained responder rather than Maria alone, and pushes it to the supervisor rollup the instant it reaches Maria's feed.
- While Maria waits with Kenji, she asks Ask CrewLink for the venue's lost-child procedure and gets the meeting point and PA-announcement steps with a source reference, instead of guessing or radioing her supervisor for something routine.
- The child is found at Guest Services a few minutes later (simulated resolution). Maria marks the task **Resolved** in one tap; the change reaches the supervisor rollup immediately.
- **Halftime:** A fan using a wheelchair needs the accessible route to a concourse restroom. Because Maria tags the incident as accessibility-related, the correct procedure surfaces automatically instead of requiring her to search for it.
- **Second half:** The feed keeps re-ranking as new items arrive; radio chatter on her channel drops noticeably because status changes now travel through the app instead.
- **Full-time:** Her shift ends. The supervisor's end-of-shift rollup shows her total tasks handled and average resolution time, and flags one open item for handoff to the next shift.

## 3. Secondary Personas

**Fan — Kenji Watanabe.** Kenji is a 41-year-old fan visiting from Osaka for his first World Cup match. He reads conversational English but isn't confident using it under stress, and has no Spanish. He never opens CrewLink AI himself — he experiences it only through Maria, the volunteer he flags down — and his entire measure of success is experiential: fast, competent help in a stressful moment, without ever needing to know an AI translation and dispatch system made it possible.

**Supervisor — Devon Price.** Devon is a Zone Operations Supervisor responsible for roughly 35–40 volunteers across the East Concourse and adjacent gates during a single match. He isn't in the concourse — he's at a zone command post with a tablet — and his job is to hold situational awareness over an area no one person could track by radio alone. The supervisor rollup gives him an at-a-glance read on open incidents by severity, which volunteers are overloaded versus idle, and simulated crowd-density hot spots, so he can redeploy people before a bottleneck becomes an incident instead of after.

## 4. User Stories

Must-tier stories map to the three primary in-scope focus areas named in PROJECT_INDEX.md — real-time decision support, operational intelligence, and multilingual assistance. Should/Could-tier stories cover the secondary focus areas — accessibility, crowd management, and navigation.

| ID | Priority | Persona | User Story |
|---|---|---|---|
| US-1 | Must | Volunteer | As a volunteer, I want a live, priority-ranked feed of my assigned tasks and incidents, so that I always know what to do next without waiting on radio instructions. |
| US-2 | Must | Volunteer | As a volunteer, I want incoming incidents automatically classified by type and severity and routed to the best-matched responder, so that urgent issues reach the right person immediately instead of sitting in a general queue. |
| US-3 | Must | Volunteer | As a volunteer, I want a real-time translation chat bridge with a fan who doesn't share my language, so that I can understand their need and respond without a human interpreter. |
| US-4 | Must | Volunteer | As a volunteer, I want to ask a natural-language question about venue procedures and get an answer grounded in the knowledge base with its source shown, so that I never pass along incorrect information or interrupt my supervisor for something routine. |
| US-5 | Must | Supervisor | As a supervisor, I want a rollup of open incidents, task load, and volunteer coverage across my zone, so that I can spot bottlenecks and redeploy people before small issues escalate. |
| US-6 | Should | Volunteer | As a volunteer, I want to update a task's status (Acknowledged / En Route / Resolved) in one tap, so that my supervisor and teammates have accurate visibility without me writing a report. |
| US-7 | Should | Volunteer | As a volunteer, I want the app to keep showing my last-known task list when connectivity drops, so that a stadium dead zone doesn't leave me with nothing. |
| US-8 | Should | Fan | As a fan using the multilingual bridge, I want to see a back-translation confirming what the volunteer will read, so that I can trust my message was understood even though I can't read their language. |
| US-9 | Should | Volunteer | As a volunteer, I want to override the AI's suggested priority or classification, so that I keep judgment in ambiguous or sensitive situations rather than being forced to follow an automated ranking. |
| US-10 | Could | Volunteer | As a volunteer, I want a suggested route to an incident's location inside the venue, so that I can respond faster in a stadium I may not have memorized. |
| US-11 | Could | Supervisor | As a supervisor, I want to see which zones are trending toward overload before incidents pile up, so that I can reassign volunteers proactively rather than reactively. |
| US-12 | Could | Volunteer | As a volunteer, I want the correct accessibility procedure to surface automatically when I tag an incident as accessibility-related, so that I follow it correctly without searching mid-incident. |
| US-13 | Could | Supervisor | As a supervisor, I want an aggregate, simulated crowd-density view by concourse zone, so that I can anticipate congestion and pre-position volunteers ahead of a bottleneck. |
| US-14 | Could | Volunteer | As a volunteer, I want to speak instead of type and have it translated aloud, so that neither the fan nor I has to read a screen mid-conversation in a loud stadium. |

## 5. Functional Requirements

Each requirement traces to at least one user story above; two (FR-22, FR-23) are cross-cutting foundations that enable multiple stories rather than one.

### 5.1 Task Feed & Prioritization
| ID | Requirement | Traces to | Priority |
|---|---|---|---|
| FR-1 | Show each volunteer a live feed of tasks/incidents scoped to their role and zone, ranked by a priority score. | US-1 | Must |
| FR-2 | Each feed item displays category, location, priority tier, and time since creation. | US-1 | Must |
| FR-3 | Deliver feed updates in real time over WebSocket, falling back to polling (≤10s interval) if the socket connection drops. | US-1, US-7 | Must |
| FR-4 | Let a volunteer change a task's status (Acknowledged / En Route / Resolved) in one tap; propagate the change to the supervisor rollup within 5 seconds. | US-6 | Should |
| FR-5 | On full connectivity loss, show the last-synced list in a clearly labeled read-only offline state, and resume live updates automatically on reconnect. | US-7 | Should |

### 5.2 Triage & Dispatch
| ID | Requirement | Traces to | Priority |
|---|---|---|---|
| FR-6 | Classify each incoming incident into a category and severity tier using the LLM orchestration layer's fast/cheap tier. | US-2 | Must |
| FR-7 | Recommend the best-matched responder by role, zone proximity, and current task load; auto-assign or suggest per a configurable policy. | US-2 | Must |
| FR-8 | Display a visible confidence indicator with each classification/recommendation and support one-tap manual override. | US-2, US-9 | Must |
| FR-9 | Log every triage decision and override — who, what, when, model output vs. human choice — for the golden-set eval (Doc #7). | US-2, US-9 | Should |

### 5.3 Multilingual Chat Bridge
| ID | Requirement | Traces to | Priority |
|---|---|---|---|
| FR-10 | Provide real-time, two-way translated chat between a volunteer and a fan across an initial supported-language set (full list owned by Doc #8). | US-3 | Must |
| FR-11 | Auto-detect the fan's input language where confidence allows; let the volunteer manually select or override the language pair. | US-3 | Must |
| FR-12 | Show the fan a confirmation / back-translation of the message the volunteer will receive. | US-8 | Should |
| FR-13 | Support voice input that is transcribed, translated, and read aloud, layered on top of — not replacing — the text bridge. | US-14 | Could |

### 5.4 Ask CrewLink (RAG Assistant)
| ID | Requirement | Traces to | Priority |
|---|---|---|---|
| FR-14 | Answer natural-language questions grounded in the seeded venue knowledge base (Chroma), showing the source document. | US-4 | Must |
| FR-15 | If no sufficiently relevant knowledge-base match exists, say so plainly and suggest escalation rather than fabricating an answer. | US-4 | Must |
| FR-16 | Auto-surface the relevant accessibility procedure whenever an incident is tagged accessibility-related. | US-12 | Could |

### 5.5 Supervisor Rollup
| ID | Requirement | Traces to | Priority |
|---|---|---|---|
| FR-17 | Show a zone-scoped rollup of open incidents by severity and category. | US-5 | Must |
| FR-18 | Show per-zone volunteer coverage versus task load, flagging over/under-resourced zones and overload trends. | US-5, US-11 | Must |
| FR-19 | Show simulated crowd-density signal by concourse zone as supporting context, not the primary view. | US-13 | Could |
| FR-20 | Refresh the rollup over the same real-time channel (WebSocket/polling) as the volunteer feed, without material lag. | US-5 | Must |

### 5.6 Navigation (secondary scope)
| ID | Requirement | Traces to | Priority |
|---|---|---|---|
| FR-21 | Provide a simple in-venue map view with a suggested route from the volunteer's current zone to an incident location. | US-10 | Could |

### 5.7 Access, Identity & Data Integrity (cross-cutting)
| ID | Requirement | Traces to | Priority |
|---|---|---|---|
| FR-22 | Authenticate via JWT and scope all visible tasks, zones, and rollups by role and assigned zone. | Enables US-1, US-5 | Must |
| FR-23 | Generate every "live" signal through a documented mock-data/simulation layer, visibly labeled as simulated throughout the UI. | Supports Key Assumption 1 | Must |

## 6. Non-Functional Requirements

### 6.1 Latency Targets (p95, demo hardware/network)

| Interaction | Target | Why |
|---|---|---|
| Task feed push (event → volunteer screen) | < 2s | Must feel instantaneous for anything tagged Critical/High |
| Triage classification + responder recommendation | < 3s | Uses the fast/cheap LLM tier specifically so dispatch never bottlenecks on model latency |
| Multilingual chat message round-trip | < 2s | Needs to sustain a natural back-and-forth conversation, not feel like a translation tool |
| Ask CrewLink answer (retrieval + generation) | < 6s | Uses the stronger reasoning tier since correctness matters more than speed for a non-emergency lookup |
| Supervisor rollup staleness | < 5s | Needs to track the volunteer feed closely enough to act on, not to the same millisecond |

### 6.2 Reliability & Uptime for the Live Demo

This is a hackathon build, not a production service, so a formal SLA (e.g., "99.9% uptime") would be the wrong target. Instead:
- **100% success** across the scripted judge walkthrough (task feed → triage → multilingual chat → Ask CrewLink → supervisor rollup) during the actual judging session.
- **≥99.5% uptime** across any rehearsal/demo windows in the run-up to judging.
- **Graceful degradation, not crashes:** if any single external dependency fails mid-demo (LLM API timeout or rate limit, WebSocket drop), the affected feature should degrade to a cached/last-known-good state or a clear "temporarily unavailable" message — never a blank screen or an unhandled error visible to a judge.

### 6.3 Concurrency Assumption

**Design and load-test for ~50 concurrent volunteer sessions and ~5 concurrent supervisor sessions** — representing one zone/gate cluster of a single venue for a single match, not full-venue or full-tournament scale.

Justification: a real World Cup venue's volunteer corps for a given zone during a given match is on the order of tens of active people, not thousands, even though the tournament-wide volunteer program is far larger; the hackathon's own infrastructure choice (Docker Compose, free-tier deploy) realistically supports this scale for a live demo without needing production autoscaling; and the architecture (WebSocket fan-out, stateless FastAPI, Postgres/SQLite) is deliberately chosen so this number is a demo-scoped floor, not an architectural ceiling. Scaling to hundreds or low thousands of concurrent volunteers per venue is a horizontal-scaling question for the System Architecture doc (#2), not something this PRD needs to resolve.

## 7. Explicit Out-of-Scope

| Not building | Why |
|---|---|
| Sustainability tooling (energy, waste, carbon tracking) | Excluded from this vertical's scope in PROJECT_INDEX; a different operational domain with different stakeholders than volunteer task support. |
| Transportation (transit, shuttles, parking) | Excluded from this vertical's scope in PROJECT_INDEX; owned by different personas and would dilute focus from the volunteer workflow. |
| Real FIFA ticketing/accreditation integration | No hackathon team has access to real tournament identity systems, and building against them would create real security/compliance obligations a demo shouldn't take on; a mocked auth scheme demonstrates the pattern instead (Key Assumption 4). |
| Voice-to-voice translation | Deferred to a stretch goal (US-14 / FR-13) so the MVP can ship a reliable text-based bridge within the hackathon timeline (Key Assumption 3). |
| Multi-venue / multi-city concurrent operation | The build targets one representative venue archetype (Key Assumption 2); running several venues at once in the same tournament is a later scaling problem, not an MVP one. |
| Real crowd sensors / IoT hardware integration | Crowd density is simulated, not sourced from turnstile or camera feeds, since no hackathon team has access to a real stadium's sensor network. |
| Production-grade security certification | Appropriate for a real deployment, not a hackathon MVP; role/zone-scoped JWT auth demonstrates the right pattern without claiming production hardening. |
| Native iOS/Android app-store distribution | The frontend is a mobile-first PWA specifically to avoid app-store review timelines and multi-codebase overhead during a hackathon build. |
| Volunteer training / change-management program | A real rollout would need one; this hackathon delivers the tool the training would be built around, not the training itself. |

## 8. Success Metrics

None of these are measurable from the hackathon build itself — there's no real tournament, no real incidents, and no real fans in it (Key Assumption 1). They describe what a pilot deployment would need to instrument to know whether CrewLink AI actually worked.

### Speed of response
- Median time from incident report to first-responder acknowledgment, benchmarked against the venue's prior radio/paper baseline.

### AI quality
- Triage classification agreement rate between the model's severity/category call and a supervisor's post-hoc review, tracked the way the golden-set eval already works in the hackathon build (Doc #7).
- Ask CrewLink helpfulness rate (volunteer-rated) and a near-zero incorrect-answer rate under QA sampling.

### Multilingual outcomes
- Share of cross-language interactions resolved without escalating to a live human interpreter.
- Fan-reported satisfaction for cross-language interactions specifically, via a simple one-tap rating after the interaction closes.

### Supervisor and volunteer experience
- Reduction in radio/escalation volume reaching a supervisor for things a volunteer could self-serve.
- Volunteer-reported confidence/stress, pre- and post-shift, on a simple pulse survey.
- Voluntary adoption: whether trained volunteers keep choosing the app over falling back to radio once the novelty wears off.

### Operational reliability
- Real-world uptime during live match windows — a stricter bar than anything in Section 6, which only covers a hackathon demo.

## 9. Assumptions

The five Key Assumptions in PROJECT_INDEX.md hold exactly as written; this section expands what each implies for the build, without changing any of them.

**1. The tournament hasn't happened yet; all "live" signals are simulated and labeled as such everywhere.** The simulation/mock-data generator is a first-class component of the system, not a test fixture bolted on afterward — it gets documented in its own right (Doc #3). Labeling can't be a one-time disclaimer; it needs a persistent, consistent UI treatment (a visible banner or watermark) everywhere simulated data appears, and the README leads with it, exactly as PROJECT_INDEX.md already states. Practically, it also means the Success Metrics in Section 8 are aspirational by construction — they describe what a pilot would measure, not what this build can prove.

**2. The build targets one representative venue archetype, kept portable via config rather than code.** This PRD names that archetype — **Founders Field**, a fictional composite ~65,000-seat venue — purely so the persona narrative has somewhere concrete to happen; it isn't modeling any real World Cup 2026 host venue. The portability requirement means zone maps, gate lists, procedure documents, and the supported-language list all live in config/knowledge-base content (owned by Doc #3), so swapping in a second venue archetype later is a data change, not a code change.

**3. Multilingual support is text-based for the MVP; voice-to-voice is a stretch goal.** Because typing mid-incident is slower than talking, the text UI needs quick-reply phrase chips alongside free text to keep the bridge usable in a fast-moving situation, not just a bare chat box. The initial supported-language set is illustrative here — something like English, Spanish, Portuguese, French, Arabic, Mandarin, and Japanese, covering large ticket-holding fan bases in an expanded 48-team field — with the definitive list and translation UX owned by Doc #8.

**4. No integration with real FIFA ticketing/accreditation systems; identity is mocked.** Role and zone claims (Volunteer vs. Supervisor, assigned zone) are provisioned through a seed script rather than pulled from any real HR or accreditation source. Anywhere a scenario references "checking accreditation," that's illustrative only. Doc #6 treats the auth layer as demonstrating the right pattern, not as production-hardened.

**5. The RAG knowledge base is seeded with a small, representative set of demo documents, not a real stadium's operations manual.** Retrieval quality gets evaluated against this known, small corpus through the golden-set eval, not against the messiness of a real manual. A judge asking Ask CrewLink something outside the seeded topics should get an honest "I don't know, here's who to ask" (FR-15) — that's a feature to demo, not a gap to hide.

**New assumptions this PRD introduces (consistent with, not contradicting, the above):**
- Maria, Kenji, and Devon are representative, not exhaustive — the real volunteer/fan/supervisor population is more varied in language mix, tech comfort, and role than three personas can capture.
- The concurrency target in Section 6.3 (~50 volunteers, ~5 supervisors) is a demo-scoped floor; it is explicitly not a claim about full-tournament scale.
- Must-tier user stories define the critical path judges will see in the live demo; Should/Could stories are polish and stretch goals that can slip without threatening the core story.

---

## --- INDEX UPDATE ---

- **Doc #1 (Product Requirements Document): Complete.**
- Restates Challenge 4 (Smart Stadiums & Tournament Operations) and justifies choosing the Volunteer vertical over Fan/Organizer/Venue-Staff as the highest-leverage persona.
- Finalized primary persona: **Maria Alvarez**, bilingual (English/Spanish) Fan Experience & Guest Services volunteer, East Concourse zone, Founders Field.
- Secondary personas defined: fan **Kenji Watanabe** (indirect beneficiary via the multilingual bridge) and supervisor **Devon Price** (rollup view).
- 14 MoSCoW user stories (5 Must / 4 Should / 5 Could) and 23 functional requirements, each traced to a story.
- **Top 3 Must-haves:** (1) live priority-ranked task feed per volunteer/zone, (2) AI triage classification + best-match responder dispatch, (3) real-time multilingual chat bridge.
- NFRs set demo-scoped latency (<2–6s by feature), uptime (100% of the scripted demo path), and concurrency (~50 volunteers) targets.
- Confirms out-of-scope items and adds real-tournament success metrics for future measurement.
