from .base import BasePlatformGenerator
from skills import ToneSkill, CTASkill, BrandVoiceSkill


class LinkedInGenerator(BasePlatformGenerator):
    platform_name = "LinkedIn"

    system_prompt = (
        "You are a professional B2B marketing copywriter specializing in LinkedIn. "
        "Write posts that are authoritative, insight-driven, and encourage professional discussion. "
        "Use short paragraphs, a clear hook in the first line. Avoid excessive emojis. "
        "Length: 150–300 words."
    )

    temperature = 0.65
    max_tokens = 400

    skills = [
        ToneSkill("professional"),
        CTASkill("question"),
        BrandVoiceSkill(),   # populate brand_name/guidelines/avoid when SOP is defined
    ]
