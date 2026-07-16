# Doc #8: Accessibility & Multilingual Design Document

**Project:** CrewLink AI — FIFA World Cup 2026 Volunteer Command Assistant
**Status:** Complete
**Builds on:** Docs #1 (PRD), #2 (Architecture), #3 (Data Model), #4 (AI Orchestration), #5 (API Spec), #6 (Security & Privacy)

CrewLink AI's volunteers work standing up, often one-handed, in direct sun or stadium floodlight, sometimes gloved, beside crowd noise loud enough to swallow a phone chime — and they are frequently the only accessibility or language bridge a fan has. This document maps WCAG 2.1 AA to CrewLink's four actual screens rather than restating a generic checklist, extends Doc #4's AI orchestration boundaries with a translation-specific quality safety net, and closes the provisional accessibility/multilingual test gap Doc #7 flagged as pending this document. It assumes the personas (Maria, Kenji, Devon), architecture, and AI tiering already finalized in Docs #1–#6.

---

## 1. WCAG 2.1 AA Checklist

**Status legend — Pass:** already guaranteed by a design decision locked in an earlier doc. **Planned:** a new requirement specified here, to be built and verified through Doc #7's test pyramid before the demo. **Deferred:** consciously out of MVP scope, with reason given.

### 1.1 Task Feed

| WCAG 2.1 Success Criterion | Requirement in CrewLink Context | Status |
|---|---|---|
| 4.1.3 Status Messages (AA) | New/changed tasks from `/ws/tasks` (or its polling fallback) are exposed through a visually-hidden `aria-live="polite"` region, separate from the visual list, announcing only the delta ("New: Medical, East Concourse, Urgent"). `requires_emergency_escalation` arrivals alone use `aria-live="assertive"`. | **Planned** |
| 1.3.1 Info and Relationships (A) | The feed is a real list (`role="list"` / native `<ul>`), each card a `listitem` with an accessible name combining category, zone, and priority — not a visual stack of unstructured `<div>`s. | **Planned** |
| 1.4.1 Use of Color (A) | Priority is always icon + text label + color together, never color alone; all three render from the single deterministic priority score (Doc #3), so they can't drift out of sync. | **Pass** |
| 2.2.2 Pause, Stop, Hide (A) | A priority-driven re-sort never silently relocates a card currently in focus; the reorder queues and applies on the volunteer's next interaction instead. | **Planned** |
| 1.4.11 Non-text Contrast (AA) | Priority icon and card border meet 3:1 contrast against the card background, verified in both the standard and glare-tuned themes (§5). | **Planned** |
| 1.4.5 Images of Text (AA) | The mandatory SIMULATED / VOLUNTEER_REPORTED / SUPERVISOR_CREATED source badge (Doc #3) renders as real styled text, never a baked-in image — legible at any zoom and readable by AT. | **Pass** |

### 1.2 Incident Detail

| WCAG 2.1 Success Criterion | Requirement in CrewLink Context | Status |
|---|---|---|
| 4.1.2 Name, Role, Value (A) | The status chip (Reported → … → Resolved, with Escalated/Cancelled reachable per Doc #2) and action buttons expose correct role and current state via ARIA, not styling alone. | **Planned** |
| 2.4.6 Headings and Labels (AA) | Each detail section (Location, Category, Description, Source, Actions) has a unique, descriptive heading — not repeated generic "Details" headings. | **Planned** |
| 2.5.3 Label in Name (A) | Visible button text ("Escalate," "Resolve") is contained in the accessible name, so voice-control users can act hands-free (§5). | **Planned** |
| 3.3.1 / 3.3.2 Error Identification & Labels (A) | The resolution-notes field carries a persistent visible label, not placeholder-only text; an empty or invalid submission is flagged in text, not color alone. | **Planned** |
| 2.2.1 Timing Adjustable (A) | Expiry of a short-lived WS ticket (Doc #6) never silently drops an open incident-detail view; the volunteer gets a visible re-auth prompt with no loss of unsent input. | **Planned** |

### 1.3 Chat Bridge

| WCAG 2.1 Success Criterion | Requirement in CrewLink Context | Status |
|---|---|---|
| 3.1.2 Language of Parts (AA) | Every message bubble carries the correct `lang` attribute for its actual language (original or translated), so a screen reader switches voice and pronunciation per message. | **Planned** |
| 4.1.3 Status Messages (AA) | "Translating…" and delivery states announce via the same live-region pattern as the task feed (§2.1). | **Planned** |
| 1.4.10 Reflow (AA) | Translated text — which can run 20–30% longer (e.g. German) or much shorter (e.g. Mandarin) than the original — reflows inside the bubble without clipping or forced horizontal scroll. | **Planned** |
| 2.1.1 Keyboard (A) | Sending, reading, and scrolling history are fully keyboard-operable, with no drag-only controls. | **Planned** |

### 1.4 Ask CrewLink

| WCAG 2.1 Success Criterion | Requirement in CrewLink Context | Status |
|---|---|---|
| 2.4.6 Headings and Labels (AA) | The question field is explicitly labeled ("Ask a question about facility or procedures"), not placeholder-only. | **Planned** |
| 4.1.3 Status Messages (AA) | Retrieval-in-progress ("Looking that up…") and the below-threshold fallback (Doc #4's retrieval gate) are both announced text states, never a silent spinner or an icon-only glyph. | **Planned** |
| 3.3.1 Error Identification (A) | The gated fallback message is real text with a concrete next step (who to ask instead), not a bare "no results" icon. | **Planned** |
| 1.3.1 Info and Relationships (A) | Q&A history is structured as grouped question/answer pairs, so AT users can navigate by exchange rather than a flat wall of text. | **Planned** |

### 1.5 App-Wide

| WCAG 2.1 Success Criterion | Requirement in CrewLink Context | Status |
|---|---|---|
| 3.1.1 Language of Page (A) | The base `lang` attribute matches the volunteer's selected UI language (§3.2) on load, never hardcoded to `en`. | **Planned** |
| 2.4.7 Focus Visible (AA) | A high-contrast focus ring is visible app-wide, tuned to survive outdoor glare (§5), not left at the browser default. | **Planned** |
| 1.4.3 Contrast (Minimum) (AA) | 4.5:1 body text / 3:1 large text and UI components, verified against both the standard and glare-tuned themes. | **Planned** |
| 2.5.1 Pointer Gestures (A) | No feature (e.g. a swipe-to-acknowledge shortcut) is the *only* path to an action; every gesture has a single-tap equivalent. | **Planned** |
| 2.5.4 Motion Actuation (A) | No action triggers from device motion, shake, or tilt — relevant since a volunteer may be moving quickly across the concourse and shouldn't fire an action by accident. | **Pass** (no motion-actuated controls exist or are planned) |
| 2.1.4 Character Key Shortcuts (A) | Any single-key shortcut (e.g. a future desktop accelerator) must be remappable or disable-able. | **Deferred** (no single-key shortcuts exist in MVP scope; requirement applies if any are added) |
| 1.2.2–1.2.5 Captions & Audio Description (A/AA) | No prerecorded or live audio/video content exists in the MVP — the product is text-based by design (Key Assumptions). | **Deferred** (N/A today; applies if training video or the voice-to-voice stretch goal is added) |

---

## 2. Assistive Technology Considerations

### 2.1 Screen-reader behavior for the live-updating task feed

The task feed is fed by `/ws/tasks` with a REST polling fallback (Doc #5), so "live" here means either a WebSocket push or a poll-driven diff — the accessible behavior must be identical either way, since a screen-reader user shouldn't be able to tell which transport is active.

- **Announce the delta, not the list.** A visually-hidden `aria-live="polite"` region, separate from the visual list, receives a short templated string per change ("New task: Medical, East Concourse, Urgent" / "Task #4471 moved to Acknowledged"). The visual list is never itself wrapped in a live region — that would force a full re-read on every change.
- **Reserve `aria-live="assertive"` for `requires_emergency_escalation` only**, mirroring the special path Doc #4 already gives emergency-flagged incidents. Everything else stays polite so volunteers aren't interrupted mid-task by routine churn.
- **Batch bursts.** The mock generator's Poisson arrival model (Doc #3) can legitimately produce several incidents in a short window; firing several live-region updates back-to-back overwhelms a screen reader's announcement queue. Updates arriving inside a short debounce window coalesce into one summary ("3 new tasks added, highest priority: Urgent").
- **Preserve item identity across re-renders.** The list is keyed by incident ID (React key), not array index, so a re-sort or single-field update doesn't tear down and rebuild a card a screen reader is currently positioned on.
- **Don't relocate a card the volunteer is reading.** If a priority change would reorder a card currently in focus, the reorder queues instead of applying instantly; the volunteer sees a small "list order updated" affordance, and the reorder lands on their next interaction — so item 3 never silently becomes item 7 mid-read.

### 2.2 Full keyboard operability under stress

Two keyboard contexts exist: Maria's mobile PWA (an external Bluetooth keyboard, a switch device, or a mobile screen reader's virtual cursor, which behaves like sequential keyboard navigation) and Devon's supervisor rollup, more likely used on a desktop browser with a physical keyboard. Both get full support, but the design goals differ.

- **Mobile / under stress (Maria):** primary actions per incident card — Acknowledge, Start, Resolve, Escalate — sit within the first few stops of tab order for that card, not nested inside an overflow menu, since cognitive load is already high mid-incident. Escalate is fast to reach but still asks for one explicit confirmation step; the emergency broadcast path (Doc #5/#6) is unthrottled and idempotent, so a confirm step costs no time on a genuine emergency while preventing an accidental duplicate escalation from a stray keystroke.
- **Desktop / supervisor rollup (Devon):** standard desktop screen-reader and keyboard-only patterns apply in full — tab order matching visual/priority order, and a visible, high-contrast focus indicator at every stop (§1.5, §5).
- **No keyboard trap, anywhere.** Any modal, sheet, or confirmation dialog (incident detail, escalate confirmation) exits via Escape or an explicit close control, returning focus to the triggering element.

### 2.3 Color-independent status indicators for incident priority

Priority score is computed deterministically (Doc #3: "priority score is deterministic, not a raw model output"), which makes it straightforward to guarantee three synchronized channels rather than one: **color** (the familiar red/amber/grey treatment), **icon shape** (a filled triangle for Urgent, a filled circle for Moderate, an outline square for Low), and a **text label** ("Urgent" / "Moderate" / "Low") that is always rendered, never hidden behind a tooltip or icon-only glyph. All three read from the same deterministic score, so no code path can let them disagree. The same treatment applies to the incident status pill (Doc #2's state machine) and to the mandatory SIMULATED / VOLUNTEER_REPORTED / SUPERVISOR_CREATED source badge (Doc #3) — every one of these is icon-or-shape *and* text, with color as decoration on top, never the only signal.

---

## 3. Multilingual Architecture

### 3.1 Static vs. dynamic translation

Every user-facing string falls into exactly one of two buckets — pre-translated at build/config time, or translated live by the Fast/Cheap tier at the moment it's needed — and never wanders between the two.

| Content | Translation Method | Why |
|---|---|---|
| UI chrome (navigation, buttons, headings, empty states) | Static i18n, pre-translated resource bundles | Fixed, reviewable surface area that must never vary between renders |
| Category taxonomy labels (medical, lost fan, translation, accessibility, crowd/queue, lost item, general) | Static i18n | Fixed enum from Doc #3; the classifier writes the enum key, the UI looks up the label — the LLM never generates this text |
| Incident status labels (Reported → … → Cancelled) | Static i18n | Same reasoning; the state machine (Doc #2) is a fixed enum |
| SIMULATED / VOLUNTEER_REPORTED / SUPERVISOR_CREATED badges, legal/consent and disclosure text | Static i18n, translated once | Demo-integrity and compliance text can't be allowed to drift between languages or renders |
| Chat Bridge messages (volunteer ↔ fan) | Dynamic, Fast/Cheap tier | Freeform, two-way, real-time — no fixed set of strings to pre-translate |
| Freeform incident descriptions | Dynamic, Fast/Cheap tier | Same reasoning; also feeds the supervisor rollup in the reader's own language |
| Ask CrewLink question and final answer | Dynamic — question via Fast/Cheap; grounded answer synthesized in English by the Reasoning tier, then translated by Fast/Cheap | Keeps grounding and translation as two separate, auditable steps — see §3.3 |
| KB source documents (venue guide, safety-procedure docs, accessibility guide, FAQ) | Not translated at rest | Authored once in English (Doc #3); translation happens at the answer, not the source, keeping the KB a single source of truth |

### 3.2 Language detection and selection

**Volunteers** set a preferred UI language explicitly at onboarding — an addition this document proposes to the Volunteer entity from Doc #3 (`preferred_language`) — changeable any time from settings. Because a volunteer like Maria is bilingual by design, UI chrome language and conversation language are decoupled: her app shell renders in whatever she's set, while each Chat Bridge conversation renders each participant's messages in that participant's own language, independent of her UI setting.

**Fans** have no CrewLink account — per the project's key assumptions, there's no real ticketing/accreditation integration, so a fan like Kenji is never an authenticated user of the system. Fan-side language in the Chat Bridge is therefore auto-detected from their first message by the Fast/Cheap tier (the same tier already doing classification and intent routing per Doc #4), shown back as a correctable chip — "Detected: Japanese — wrong? Tap to change" — rather than a silent, unappealable guess.

**Bounded language list.** The MVP supports a fixed, configurable shortlist rather than "whatever the underlying model can handle," so Doc #7's golden-set testing stays scoped to a known set. An illustrative starting set — English, Spanish, Portuguese, French, German, Japanese, Korean, Arabic — is a config value, not hardcoded, matching the project's "venue specifics live in config, not code" principle; the real list should be revisited against the tournament's actual fan demographics.

**Implementation note.** Static i18n strings are recommended to run through a standard React i18n library (e.g. i18next or FormatJS) using ICU MessageFormat for pluralization, kept entirely separate from LLM call sites — no static string is ever passed through the model.

### 3.3 Ask CrewLink's multilingual pipeline

Ask CrewLink's grounding boundary (Doc #4) doesn't change for multilingual use — it's extended with a translation step on either side, deliberately kept separate from the grounded-synthesis step:

1. A fan or volunteer submits a question in Language X.
2. The Fast/Cheap tier detects Language X and translates the query into the KB's source language (English) for retrieval.
3. Chroma retrieval runs exactly as specified in Doc #4 — the same non-empty, above-threshold gate, unchanged.
4. Below threshold: the existing deterministic fallback message is translated into Language X (Fast/Cheap) and returned. Nothing is generated.
5. Above threshold: the Reasoning tier synthesizes the grounded answer in English only, strictly against the retrieved chunks — exactly as in Doc #4, with no multilingual variation at this step.
6. The Fast/Cheap tier translates the finished, already-grounded English answer into Language X as a separate, final call.

Splitting steps 5 and 6 keeps the Reasoning tier's only job as grounded synthesis, and keeps translation entirely inside the Fast/Cheap tier at every call site in the app, Chat Bridge included. No call site ever asks one model call to both ground an answer and translate it at once — that would make groundedness far harder to audit or grade against Doc #4 and Doc #7's golden sets.

---

## 4. Language Quality & Safety Net

Doc #4 draws its grounding boundary around *generation*: facility/safety/procedure answers must clear the Chroma retrieval gate before the Reasoning tier may generate, while translation, small talk, and status updates stay conversational with no retrieval path in code. That boundary is correct as written — a translation isn't inventing new facts, so it doesn't need a knowledge-base citation. But "no retrieval gate" is not the same as "no quality control," and translation is the one AI call site in CrewLink where a subtle error — a mistranslated dosage, a flipped negation, a wrong meeting point — can cause real harm without ever tripping a schema or retrieval check. This section adds a translation-specific safety net that sits *alongside*, not inside, Doc #4's grounding boundary.

### 4.1 Confidence signal

Every Fast/Cheap translation call already returns a forced-tool-choice, Pydantic-validated structure per Doc #4. This document extends that schema with three additional fields on the same call — no new model tier is introduced:

- `confidence`: high / medium / low
- `high_stakes`: boolean
- `back_translation`: the translated text, machine-translated back into the source language by a second Fast/Cheap call, for side-by-side comparison

Matching Doc #3's own rule that priority is "a deterministic score, not a raw model output," `high_stakes` is never left to the translation model's judgment of its own risk. It's set deterministically: true whenever a Chat Bridge message's own `emergency_flag` (Doc #4) is set, or, for translated incident descriptions, whenever the parent incident's category is `medical` or `accessibility` (Doc #3's taxonomy).

### 4.2 Human-in-the-loop behavior

| Confidence | High-stakes? | Behavior |
|---|---|---|
| High | Either | Send normally; no extra UI. |
| Medium / Low | No | Send normally; show a subtle confidence chip only. |
| Medium / Low | Yes | Send immediately — never delayed; show the confidence chip, the back-translation alongside the translated text, and a one-tap "Request human interpreter" action; log the exchange to `AIInvocationLog` for review. |

A low- or medium-confidence high-stakes translation is never delayed or blocked from sending — matching Doc #4's existing principle that a language barrier must never delay escalation — it simply surfaces extra signal so a human can catch what the model might have missed.

"Request human interpreter" isn't a new mechanism: it files a standard Incident in the existing `translation` category from Doc #3's taxonomy, which flows through the same Reported → Triaged → Dispatched pipeline (Doc #2) as any other request — tracked, prioritized, and dispatchable, not a special side-channel. The venue's actual interpreter-request procedure lives in the KB's accessibility guide (Doc #3), so the same Ask CrewLink retrieval path (§3.3) can surface it rather than CrewLink inventing its own interpreter-dispatch logic.

### 4.3 Logging and regression testing

Every translation's `confidence` / `high_stakes` / `back_translation` result writes to `AIInvocationLog` (Doc #3), so low-confidence high-stakes cases can be pulled for post-demo review. This document recommends Doc #7 extend its 15-case golden set (Doc #4 §6) with a parallel, small translation golden set — a fixed list of representative high-stakes phrases per supported language, graded on back-translation similarity plus confidence-schema conformance, using the same "hard schema gate, softer quality threshold" pattern already applied to the Dispatch Recommender and Ask CrewLink. This closes the provisional note in Doc #7 that accessibility/multilingual checks were scaffolded pending this document.

---

## 5. Field-Condition Usability

Maria works the East Concourse on her feet, often one-handed, sometimes gloved, in direct sun, next to a crowd loud enough to drown out a phone alert. The following accommodations are written for that reality rather than a seated desk user; several double as WCAG-relevant accommodations already listed in §1, but here they're motivated primarily by field conditions, not by a specific success criterion.

### 5.1 Glare
- An optional high-contrast "field" theme, tuned beyond the AA contrast floor (targeting closer to 7:1 for primary text and priority labels where feasible) rather than stopping at the 4.5:1 minimum.
- Both light and dark theme options, so a volunteer can pick whichever holds up better against direct sun versus stadium floodlight.
- Solid borders and outlines instead of subtle drop-shadows or low-contrast dividers, which wash out in bright ambient light.
- Bold, large typography on priority labels and primary actions by default — not only on user-triggered zoom.

### 5.2 One-handed use
- Primary actions and navigation anchored within thumb reach at the bottom of the screen, since a volunteer's other hand is often occupied — holding equipment, gesturing to a fan, steadying a clipboard.
- No core flow requires a two-finger or pinch gesture; every gesture-based shortcut (e.g. swipe-to-acknowledge) has an equivalent single-tap button, which is both a one-handed-use accommodation and satisfies WCAG 2.5.1 (§1.5).
- Large, thumb-sized tap targets on primary actions — a field-usability goal that goes beyond what WCAG 2.1 AA formally requires, adopted anyway because mis-taps cost time exactly when time matters most.

### 5.3 Gloves
- The same large-target guidance above also reduces mis-taps from gloved or reduced-sensitivity touch.
- No action depends solely on long-press or force-touch, since gloved input doesn't reliably register either.
- Standard mobile-OS dictation is offered as an input option for freeform text (incident descriptions, chat replies) — this is ordinary device-level voice-to-text for *typing*, unrelated to and not a substitute for the product's own voice-to-voice translation feature, which the key assumptions already mark as a stretch goal beyond MVP.
- Glove/touchscreen compatibility itself (e.g. conductive glove liners) is a volunteer-kit/equipment decision, not an app design one, and is noted here only as a boundary of this document's scope.

### 5.4 Noisy environments
- No alert — task arrival, chat message, emergency broadcast — depends on sound alone; every alert pairs a visual change with a distinguishable haptic pattern, with emergency-flagged alerts using a distinct pattern from routine ones.
- Push-notification preview text carries enough information to act on at a glance (category, zone, priority) without needing to unlock the phone and read further in a loud, distracting environment.
- The Chat Bridge is text-based end to end for the MVP; that decision (already made in the key assumptions, primarily for engineering-scope reasons) also happens to sidestep noise entirely — a fan and a volunteer can communicate over concourse noise that would defeat a voice-based bridge, reinforcing rather than conflicting with keeping voice-to-voice a stretch goal.

---

## 6. Accessibility for Fans (Secondary Persona)

Doc #3's incident category list includes `accessibility` as its own category, sitting alongside a separate `translation` category for language-only needs — the two often overlap (a fan can need both), but they're tracked independently so each gets matched to the right kind of help.

Here's what that means in practice. A fan doesn't file anything themselves — per the project's scope, fans aren't accounts in the system, so an accessibility need reaches CrewLink because a fan tells a volunteer directly, or says it over the Chat Bridge in their own language. Maybe it's "I use a wheelchair and can't find the accessible entrance," or "my son is autistic and needs somewhere quiet for a few minutes." The volunteer logs it as an incident — either picking `accessibility` directly, or having the Fast/Cheap classifier suggest it from the free-text description — and from that point on, it's treated exactly like any other incident: it gets a priority, it moves through Reported → Triaged → Dispatched → Resolved (Doc #2) like a medical call or a lost child would, and it can be escalated if it stalls. An accessibility request is never an informal, off-the-books favor a volunteer handles on the side; it's tracked with the same rigor as everything else in the system.

Classifying it is only half the job — the category has to lead somewhere real. That's what ties this back to the Knowledge Base (Doc #3): the accessibility guide is one of the five authored documents seeded into Chroma, so once an incident is tagged `accessibility`, the volunteer can ask CrewLink directly — "where's the nearest accessible restroom to East Concourse," "how do I request a companion escort" — and get a grounded answer from that guide (§3.3), rather than needing to already know the venue's accommodations by heart or guess. Typical accommodations this might surface include accessible and companion seating, quiet/sensory-friendly spaces, hearing-loop or assistive-listening locations, mobility escorts or cart transport, and service-animal relief areas — the specific list lives in the KB content itself, not in this document, so it stays venue-portable per the project's own design principle.

This document also recommends the Volunteer entity (Doc #3) carry an optional skills/equipment tag — e.g. wheelchair-cart-trained, sign-language — as a new, proposed field, so the dispatch recommender (Doc #2) can factor accessibility-specific fit into best-match responder selection the same way it already factors zone and category. This is a proposal introduced by this document, not something already specified elsewhere.

Kenji is the clearest illustration of why this matters as one system rather than two. A fan who needs both a translated conversation and an accessibility accommodation shouldn't have to find two different kinds of help — the same incident, the same Chat Bridge conversation, and the same grounded KB lookup serve both needs together.

---

--- INDEX UPDATE ---

**Suggested Document Log row (Section 5 of PROJECT_INDEX.md):**

| 8 | Accessibility & Multilingual Design Document | Complete | Screen-mapped WCAG 2.1 AA checklist, live-region/keyboard/color-independent AT design, static-vs-LLM multilingual architecture, translation confidence + human-in-the-loop safety net, field-condition usability, and fan accessibility-request handling. |

**Doc #8 (Accessibility & Multilingual Design Document): Complete.**
- WCAG 2.1 AA mapped screen-by-screen (task feed, incident detail, chat bridge, Ask CrewLink), not generically; live feed updates use status-message live regions, never silent repaint.
- Full keyboard operability specified for one-handed, stressed use; priority and status are always color + icon + text, never color alone.
- Multilingual split finalized: UI chrome and fixed enums are static i18n; chat, freeform descriptions, and Ask CrewLink answers are dynamically translated via the Fast/Cheap tier, kept separate from Reasoning-tier grounding.
- Adds a translation confidence + back-translation + human-interpreter safety net for medical/accessibility/emergency content, alongside (not inside) Doc #4's grounding gate — closes Doc #7's provisional test gap.
- Defines glare, one-handed/gloved, and noise accommodations; ties the `accessibility` incident category to real accommodations via the KB.
