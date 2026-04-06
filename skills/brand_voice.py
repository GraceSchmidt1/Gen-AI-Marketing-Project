from .base import BaseSkill


class BrandVoiceSkill(BaseSkill):
    """
    Enforces brand voice guidelines by injecting brand-specific rules
    into both the system and user prompts.

    Populate `guidelines` and `avoid` when your brand SOPs are defined.
    """

    name = "brand_voice"

    def __init__(
        self,
        brand_name: str = "",
        guidelines: list[str] | None = None,
        avoid: list[str] | None = None,
    ):
        """
        Args:
            brand_name:  The brand name to reference in prompts.
            guidelines:  Positive brand voice rules (e.g. "be empowering", "use 'we' not 'I'").
            avoid:       Words, phrases, or tones to exclude (e.g. "never say 'cheap'").
        """
        self.brand_name = brand_name
        self.guidelines = guidelines or []
        self.avoid = avoid or []

    def inject_system_prompt(self, system_prompt: str) -> str:
        if not self.guidelines and not self.avoid:
            return system_prompt

        lines = []
        if self.brand_name:
            lines.append(f"Brand: {self.brand_name}")
        if self.guidelines:
            lines.append("Brand voice rules:\n" + "\n".join(f"  - {g}" for g in self.guidelines))
        if self.avoid:
            lines.append("Avoid:\n" + "\n".join(f"  - {a}" for a in self.avoid))

        brand_block = "\n".join(lines)
        return f"{system_prompt}\n\nBrand voice guidelines:\n{brand_block}"

    def inject_user_prompt(self, user_prompt: str) -> str:
        if self.brand_name:
            return f"{user_prompt}\nBrand name to use: {self.brand_name}"
        return user_prompt
