"""Doc #3 §2.3 / ADDENDUM G3 — Static KB-eligibility table.

Incident categories are pre-mapped to KB eligibility based on whether
knowledge-base lookup can provide useful procedure/guidance for them.
"""

KB_ELIGIBILITY: dict[str, bool] = {
    'medical': True,
    'lost_fan': True,
    'translation': False,
    'accessibility': True,
    'crowd_queue': True,
    'lost_item': False,
    'general': False,
}


def is_kb_eligible(category: str) -> bool:
    return KB_ELIGIBILITY.get(category, False)
