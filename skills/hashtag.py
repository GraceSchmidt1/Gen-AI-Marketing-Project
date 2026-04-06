from .base import BaseSkill


class HashtagSkill(BaseSkill):
    """
    Instructs the model to include hashtags and optionally appends
    a fixed set of brand hashtags in postprocess.
    """

    name = "hashtag"

    def __init__(self, count: int = 8, brand_tags: list[str] | None = None):
        """
        Args:
            count:      How many hashtags the model should generate.
            brand_tags: Optional list of always-on brand hashtags to append
                        after generation (e.g. ["#BrandName", "#OurSlogan"]).
        """
        self.count = count
        self.brand_tags = brand_tags or []

    def inject_system_prompt(self, system_prompt: str) -> str:
        instruction = (
            f"After the caption body, add exactly {self.count} relevant hashtags on a new line. "
            "Choose hashtags that are specific, discoverable, and mix broad and niche terms."
        )
        return f"{system_prompt}\n\nHashtag instruction: {instruction}"

    def postprocess(self, output: str) -> str:
        if not self.brand_tags:
            return output
        brand_line = " ".join(self.brand_tags)
        return f"{output}\n{brand_line}"
