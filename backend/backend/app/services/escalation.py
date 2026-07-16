"""ADDENDUM G7 — escalation_channel derivation.

Deterministic mapping from incident properties to which
escalation channel should be paged.
"""

import enum


class EscalationChannel(enum.StrEnum):
    ems = 'ems'
    security = 'security'


def derive_escalation_channel(
    category: str,
    description: str,
) -> EscalationChannel:
    desc_lower = description.casefold()
    category_lower = category.strip().lower()

    # EMS triggers — medical or health-safety content
    medical_keywords = [
        'bleeding', 'unconscious', 'not breathing', 'choking',
        'seizure', 'chest pain', 'allergic reaction',
    ]
    if category_lower == 'medical':
        for kw in medical_keywords:
            if kw in desc_lower:
                return EscalationChannel.ems

    # Security triggers — violence, weapon, fire, structural
    security_keywords = [
        'weapon', 'fire', 'smoke', 'violence', 'fight',
        'structural hazard', 'collapse', 'active shooter',
    ]
    for kw in security_keywords:
        if kw in desc_lower:
            return EscalationChannel.security

    # Fallback: medical = EMS, anything else = security
    if category_lower == 'medical':
        return EscalationChannel.ems
    return EscalationChannel.security
