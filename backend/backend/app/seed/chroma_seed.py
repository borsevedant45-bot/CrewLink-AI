"""Seed Chroma with KB document chunks per Doc #3 §3.2.

Heading-based chunking, ~150–300 tokens per chunk, one chunk per FAQ pair.
"""

import hashlib
from typing import Any

import chromadb
from backend.app.core.config import settings
from chromadb.api import ClientAPI


def _estimate_tokens(text: str) -> int:
    return len(text.split())


def _heading_chunks(sections: list[dict[str, str]]) -> list[dict[str, Any]]:
    chunks = []
    for sec in sections:
        tokens = _estimate_tokens(sec["text"])
        chunks.append({
            "heading": sec["heading"],
            "text": sec["text"],
            "token_count": tokens,
        })
    return chunks


FOUNDERS_FIELD_ZONE_GUIDE = _heading_chunks([
    {"heading": "East Concourse (Sections 100–120)", "text": (
        "The East Concourse serves Sections 100 through 120 on the east side of Founders Field. "
        "It contains two main concession stands, four restroom facilities (two accessible), "
        "Guest Services Desk East, and a first-aid station at the north end. "
        "Gate 4 provides the primary entry point. Elevator access is available near the north stairwell."
    )},
    {"heading": "West Concourse (Sections 121–140)", "text": (
        "The West Concourse serves Sections 121 through 140. "
        "It contains three concession stands, two restroom facilities, Guest Services Desk West, "
        "and a medical station near the south end. Gate 7 is the primary entry point. "
        "Accessible seating sections are located in 134A–136A."
    )},
    {"heading": "North Concourse (Sections 200–220)", "text": (
        "The North Concourse serves Sections 200 through 220 on the upper bowl's north side. "
        "It contains two concession stands, restrooms, and a direct ramp to the main plaza. "
        "Gate 2 provides entry. This concourse connects to the Fan Zone and public transportation drop-off area."
    )},
    {"heading": "South Concourse (Sections 221–240)", "text": (
        "The South Concourse serves Sections 221 through 240. "
        "It contains the main first-aid room, a dedicated accessible entrance, "
        "and a quiet room for sensory-sensitive guests. Gate 10 is the entry point. "
        "Lost and Found is adjacent to Guest Services Desk South."
    )},
    {"heading": "Medical Stations", "text": (
        "Founders Field has four medical stations: North (near Section 205), "
        "East (near Section 108 concourse), South (near Section 230), "
        "and West (near Section 130). All stations are staffed with certified medical personnel. "
        "Volunteers should direct any medical concern to the nearest station immediately and "
        "wait for a certified responder — do not attempt treatment."
    )},
    {"heading": "Lost and Found", "text": (
        "The main Lost and Found office is located on the main concourse behind Section 118, "
        "adjacent to Guest Services Desk East. A secondary drop point is at Guest Services Desk West. "
        "Found items are logged and stored for 30 days. High-value items (phones, wallets, passports) "
        "are secured in a locked cabinet and logged separately."
    )},
    {"heading": "Accessible Routes", "text": (
        "Wheelchair-accessible routes connect all concourses via ramps and elevators. "
        "Key elevator locations: North stairwell (East Concourse), Section 126 (West Concourse), "
        "main lobby (Gate 1). Accessible seating blocks are in Sections 18A–20A, 134A–136A, and 220A. "
        "A companion restroom is located near each accessible seating block."
    )},
    {"heading": "Guest Services Desks", "text": (
        "Guest Services Desks are located at East Concourse (near Gate 4), West Concourse (near Gate 7), "
        "and Main Lobby (Gate 1). All desks offer multilingual assistance via the CrewLink chat bridge, "
        "wheelchair checkout, hearing-assistance device checkout, and general information. "
        "Desks are staffed from T-2 hours through 1 hour after final whistle."
    )},
])


MEDICAL_ESCALATION_GUIDE = _heading_chunks([
    {"heading": "When to escalate to the medical station", "text": (
        "Volunteers must escalate to the nearest medical station immediately when any of the following "
        "is observed: unconsciousness or altered mental state, difficulty breathing or choking, "
        "chest pain or pressure, severe bleeding that does not stop with direct pressure, "
        "seizure, allergic reaction with swelling or breathing difficulty, suspected heat stroke, "
        "or any injury the volunteer feels is beyond their training. Do not move a person with a "
        "suspected spinal injury unless they are in immediate danger."
    )},
    {"heading": "How to escalate — procedure", "text": (
        "When escalating a medical concern: (1) Call the nearest medical station directly — "
        "dial *MED from any staff phone or use the emergency channel on the radio. "
        "(2) State your name, your zone, and your location. (3) Describe what you see — "
        "use the volunteer's own words from the affected person if possible. "
        "(4) State what has already been done (e.g., \"person is seated, conscious, speaking\"). "
        "(5) Stay on the line until medical personnel arrive or dispatch confirms the handoff. "
        "Never attempt to provide medical treatment beyond basic first aid."
    )},
    {"heading": "What to relay to medical responders", "text": (
        "When medical responders arrive, relay: the person's current conscious state, "
        "any known allergies or medical conditions if the person has communicated them, "
        "what happened leading up to the incident (from the person or witnesses), "
        "and any first aid already given. Write down the responder's name and unit number "
        "for the incident log. If the person is non-responsive, check for a medical ID "
        "bracelet or necklace and relay any information found."
    )},
    {"heading": "After escalation — your role", "text": (
        "Once medical personnel have taken over: (1) clear the immediate area of bystanders, "
        "giving the response team space to work. (2) Note the incident in the CrewLink app — "
        "mark the task as In Progress until responders release you, then Resolved. "
        "(3) If asked, assist with language interpretation via the CrewLink chat bridge. "
        "(4) Do not share details about the person's condition with anyone except the "
        "supervisor or medical team — respect patient privacy."
    )},
])


CROWD_EVACUATION_GUIDE = _heading_chunks([
    {"heading": "Crowd density awareness", "text": (
        "Volunteers should monitor crowd density in their zone via the CrewLink app's live feed. "
        "When density reaches HIGH (70–90%) in a concourse or gate area, begin proactive "
        "crowd-management messaging: direct people to less congested routes, open additional "
        "concession stations if available, and position yourself at choke points to smooth flow. "
        "At CRITICAL (>90%), immediately notify your supervisor and follow the evacuation "
        "procedures below if an evacuation order is given."
    )},
    {"heading": "Evacuation trigger and announcement", "text": (
        "An evacuation is ordered only by venue command staff or the fire marshal. "
        "If you hear the evacuation siren (repeating three-tone pattern) or receive an "
        "evacuation order through CrewLink or radio: (1) direct所有人 (everyone) to the "
        "nearest exit — do not wait for a second confirmation. (2) Use the emergency "
        "megaphone or your voice: clear, loud, simple commands. (3) Point to the exit "
        "route, do not just describe it. (4) People with mobility impairments: direct to "
        "the nearest evacuation elevator or area of refuge and notify the response team."
    )},
    {"heading": "Evacuation routes by zone", "text": (
        "East Concourse (Sections 100–120): evacuate via Gate 4 or Gate 5. "
        "West Concourse (Sections 121–140): evacuate via Gate 7 or Gate 8. "
        "North Concourse (Sections 200–220): evacuate via Gate 2. "
        "South Concourse (Sections 221–240): evacuate via Gate 10. "
        "Field level: evacuate through the tunnel under Section 110 (East) or Section 130 (West). "
        "VIP/suite level: use the dedicated stairwells at the north and south ends."
    )},
    {"heading": "Post-evacuation accountability", "text": (
        "Once outside the venue: (1) move to your zone's designated assembly point — "
        "check the CrewLink app for the mapped location. (2) Check that all members of "
        "your party/group are accounted for. (3) Report any missing persons to the "
        "supervisor or emergency services immediately. (4) Do not re-enter the venue "
        "until the all-clear is given by venue command or the fire marshal. "
        "(5) Log the evacuation event in CrewLink for the incident record."
    )},
])


ACCESSIBILITY_GUIDE = _heading_chunks([
    {"heading": "Wheelchair and mobility services", "text": (
        "Wheelchair checkout is available at all three Guest Services Desks. "
        "A limited number of mobility scooters are available at the Main Lobby Desk (Gate 1). "
        "Valid ID is required for checkout. Reserved accessible parking is in Lots A and B, "
        "adjacent to Gates 1 and 10 respectively. Accessible drop-off zones are at all gate entrances. "
        "Wheelchair-accessible restrooms are located on every concourse adjacent to standard restrooms."
    )},
    {"heading": "Assistive listening devices", "text": (
        "Assistive listening devices (ALD) are available for checkout at Guest Services Desk East "
        "and the Main Lobby Desk. Devices are compatible with the venue's PA system and support "
        "telecoil. Valid ID is required. Devices should be returned to the same desk after the match. "
        "For groups, pre-arranged pickup is available by contacting accessibility services at "
        "accessibility@foundersfield.demo."
    )},
    {"heading": "Sensory-friendly accommodations", "text": (
        "A quiet room for sensory-sensitive guests is located on the South Concourse near Section 230. "
        "The room features dimmed lighting, reduced noise, and comfortable seating. "
        "Sensory bags containing noise-canceling headphones, fidget tools, and a weighted lap pad "
        "are available at all Guest Services Desks. Volunteers should direct guests to these resources "
        "when flagged as an ACCESSIBILITY incident."
    )},
    {"heading": "Service animal and mobility aid policy", "text": (
        "Trained service animals are welcome throughout Founders Field. A designated relief area "
        "for service animals is located outside Gate 4 on the East Concourse. "
        "Mobility aids including canes, walkers, and crutches are permitted in all areas. "
        "The venue does not provide storage for mobility aids — guests should keep them at their seat "
        "or in the accessible companion space. Emotional support animals are not permitted inside the bowl."
    )},
    {"heading": "Accessible seating and companion spaces", "text": (
        "Accessible wheelchair seating is available in Sections 18A–20A, 134A–136A, and 220A. "
        "Each accessible seat has an adjacent companion seat. Tickets for these sections are "
        "available through the venue's ticketing system. Volunteers should verify that guests "
        "with accessible seating needs are directed to these sections and not to standard seating "
        "areas. Elevator access to upper-level accessible seating is near all main stairwells."
    )},
    {"heading": "Communication access for deaf and hard-of-hearing guests", "text": (
        "ASL interpreters are available upon request for major announcements and during incidents. "
        "Request via the CrewLink chat bridge or by flagging an ACCESSIBILITY incident. "
        "The CrewLink app's chat bridge provides real-time text translation for any conversation "
        "between a volunteer and a deaf or hard-of-hearing guest who prefers written communication. "
        "Captioning is displayed on the venue's video boards for all PA announcements."
    )},
])


GUEST_FAQ = _heading_chunks([
    {"heading": "What is the bag policy?", "text": (
        "Founders Field enforces a clear-bag policy. Bags must be clear plastic, vinyl, or PVC "
        "and no larger than 12\" x 6\" x 12\". Small clutch bags (4.5\" x 6.5\") are permitted. "
        "All bags are subject to search at entry gates. Diaper bags and medical-necessary bags "
        "are permitted after inspection. There is no bag storage or check-in at the venue."
    )},
    {"heading": "Is re-entry permitted?", "text": (
        "Re-entry is permitted only for guests exiting to the designated smoking areas located "
        "outside Gates 1 and 7. Full re-entry (leaving the venue and returning) is not permitted "
        "for standard tickets. Guests with wristbands for all-day access or suite-level tickets "
        "may have re-entry privileges — check with Guest Services. In case of emergency evacuation, "
        "re-entry requires a valid ticket for scanning at any gate."
    )},
    {"heading": "Where is Lost and Found?", "text": (
        "The main Lost and Found office is on the main concourse behind Section 118, "
        "next to Guest Services Desk East. A secondary location is at Guest Services Desk West. "
        "Lost items are held for 30 days. High-value items are stored in a secured cabinet. "
        "Guests may inquire about lost items at any Guest Services Desk or via CrewLink."
    )},
    {"heading": "Is Wi-Fi available?", "text": (
        "Free Wi-Fi is available throughout Founders Field. Network name: FoundersField_Free. "
        "No password is required. The network supports streaming, messaging, and CrewLink AI access. "
        "Bandwidth is prioritized for venue operations — streaming video quality may vary during "
        "peak crowd periods. Wired ethernet is available in suites and media areas."
    )},
    {"heading": "What items are prohibited?", "text": (
        "Prohibited items include: weapons of any kind, outside food and beverages (except "
        "medical-necessary and infant supplies), alcohol not purchased at the venue, "
        "laser pointers, drones, selfie sticks, tripods, recording equipment with detachable lenses "
        "longer than 6 inches, signs on poles, and any item that could be used as a projectile. "
        "Smoking is only permitted in designated outdoor areas outside Gates 1 and 7. "
        "E-cigarettes and vapes are prohibited inside the bowl."
    )},
    {"heading": "How do I report a lost child?", "text": (
        "If a guest reports a lost child: (1) immediately notify the nearest security personnel "
        "or volunteer supervisor via radio. (2) Escort the reporting person to the nearest "
        "Guest Services Desk. (3) Note the child's description, last known location, "
        "and clothing in the CrewLink app. (4) A venue-wide announcement will be made through "
        "the PA system for children. (5) Ensure the reporting person stays at a designated "
        "meeting point. (6) Do not transport the child yourself — wait for security or "
        "medical personnel."
    )},
    {"heading": "Where are the nearest restrooms?", "text": (
        "Restrooms are located on every concourse at regular intervals. Accessible/family "
        "restrooms are adjacent to each standard restroom block. Companion restrooms with "
        "extra space for a caregiver are located near accessible seating sections. "
        "Baby-changing stations are available in all restrooms. Gender-neutral restrooms "
        "are located on the Main Concourse near Gate 1 and on the South Concourse near Section 230."
    )},
    {"heading": "What accessibility services are available?", "text": (
        "Founders Field offers: wheelchair checkout, mobility scooter checkout (limited), "
        "assistive listening devices, sensory bags, a quiet room (South Concourse near Section 230), "
        "ASL interpretation upon request, accessible seating with companion spaces, "
        "wheelchair-accessible routes throughout the venue, companion restrooms, "
        "and the CrewLink AI chat bridge for real-time multilingual communication. "
        "For pre-arranged accessibility needs, contact accessibility@foundersfield.demo."
    )},
    {"heading": "Is there first aid available?", "text": (
        "Four medical stations are located throughout Founders Field: North (near Section 205), "
        "East (near Section 108 concourse), South (near Section 230), and West (near Section 130). "
        "Automated External Defibrillators (AEDs) are located at every medical station and "
        "at each Guest Services Desk. First aid kits are available at all concession stands. "
        "In an emergency, flag down the nearest volunteer or dial *MED from any staff phone."
    )},
    {"heading": "Can I leave and come back?", "text": (
        "Founders Field does not permit re-entry once you have exited the venue through a gate. "
        "Designated smoking areas outside Gates 1 and 7 allow short re-entry. "
        "Suite and all-day wristband holders — check with Guest Services for your specific access level. "
        "Anyone leaving during an emergency evacuation will need a valid ticket to re-enter."
    )},
    {"heading": "What happens if it rains?", "text": (
        "Founders Field has a retractable roof that closes in approximately 12 minutes. "
        "In case of rain, the roof will be closed — no evacuation is needed for precipitation alone. "
        "Lightning within a 10-mile radius triggers a delay; guests are directed to concourse areas "
        "until the storm passes. Severe weather evacuations follow the standard evacuation procedure. "
        "All CrewLink features continue to function normally during weather events."
    )},
])


def get_seed_documents() -> list[dict[str, Any]]:
    return [
        {
            "title": "Founders Field Zone Guide",
            "doc_type": "VENUE_MAP",
            "sections": FOUNDERS_FIELD_ZONE_GUIDE,
        },
        {
            "title": "Medical Escalation Overview",
            "doc_type": "SAFETY_PROCEDURE",
            "sections": MEDICAL_ESCALATION_GUIDE,
        },
        {
            "title": "Crowd & Evacuation Overview",
            "doc_type": "SAFETY_PROCEDURE",
            "sections": CROWD_EVACUATION_GUIDE,
        },
        {
            "title": "Accessibility Services & Facilities Guide",
            "doc_type": "ACCESSIBILITY_FACILITIES",
            "sections": ACCESSIBILITY_GUIDE,
        },
        {
            "title": "Founders Field Guest FAQ",
            "doc_type": "FAQ",
            "sections": GUEST_FAQ,
        },
    ]


def seed_chroma(client: ClientAPI | None = None) -> ClientAPI:
    if client is None:
        client = chromadb.PersistentClient(path=settings.chroma_persist_dir)

    collection = client.get_or_create_collection(
        name="crewlink_kb",
        metadata={"hnsw:space": "cosine"},
    )

    documents = get_seed_documents()
    all_chunks = []

    for doc in documents:
        for chunk in doc["sections"]:
            chunk_id = hashlib.sha256(
                f"{doc['title']}:{chunk['heading']}".encode()
            ).hexdigest()[:32]
            all_chunks.append({
                "id": chunk_id,
                "text": chunk["text"],
                "metadata": {
                    "doc_title": doc["title"],
                    "doc_type": doc["doc_type"],
                    "section_heading": chunk["heading"],
                    "token_count": str(chunk["token_count"]),
                },
            })

    ids = [c["id"] for c in all_chunks]
    texts = [c["text"] for c in all_chunks]
    metadatas = [c["metadata"] for c in all_chunks]

    collection.upsert(ids=ids, documents=texts, metadatas=metadatas)

    return client
