from .base import BaseSkill

TONE_GUIDANCE = {
    "professional": (
        "Maintain a confident, authoritative tone throughout. "
        "Use industry-appropriate vocabulary. Avoid slang or overly casual phrasing."
    ),
    "conversational": (
        "Write as if speaking directly to a friend. "
        "Use contractions, everyday language, and a warm, approachable voice."
    ),
    "visual": (
        "Write with visual imagery in mind — the reader is pairing this caption with a photo or video. "
        "Be evocative, sensory, and concise."
    ),
    "inspirational": (
        "Use uplifting, motivational language. "
        "Focus on possibility, transformation, and positive outcomes."
    ),
}


class ToneSkill(BaseSkill):
    """Injects tone guidance into the system prompt."""

    name = "tone"

    def __init__(self, tone: str = "professional"):
        if tone not in TONE_GUIDANCE:
            raise ValueError(f"Unknown tone '{tone}'. Choose from: {list(TONE_GUIDANCE)}")
        self.tone = tone

    def inject_system_prompt(self, system_prompt: str) -> str:
        guidance = TONE_GUIDANCE[self.tone]
        return f"{system_prompt}\n\nTone guidance: {guidance}"
