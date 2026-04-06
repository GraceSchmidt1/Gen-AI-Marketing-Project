from .base import BaseSkill

CTA_GUIDANCE = {
    "question": (
        "End the post with an open-ended question that invites the reader to share their perspective "
        "or experience in the comments."
    ),
    "engagement": (
        "End with a clear engagement prompt — ask readers to like, share, tag a friend, "
        "or answer a simple poll question."
    ),
    "link": (
        "End with a concise call to action directing readers to click a link in the bio or post "
        "(use '[link]' as a placeholder for the actual URL)."
    ),
    "follow": (
        "End with an invitation to follow the account for more content on this topic."
    ),
}


class CTASkill(BaseSkill):
    """Injects a call-to-action instruction into the system prompt."""

    name = "cta"

    def __init__(self, cta_type: str = "question"):
        if cta_type not in CTA_GUIDANCE:
            raise ValueError(f"Unknown CTA type '{cta_type}'. Choose from: {list(CTA_GUIDANCE)}")
        self.cta_type = cta_type

    def inject_system_prompt(self, system_prompt: str) -> str:
        guidance = CTA_GUIDANCE[self.cta_type]
        return f"{system_prompt}\n\nCall-to-action instruction: {guidance}"
