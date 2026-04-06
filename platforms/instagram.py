from .base import BasePlatformGenerator
from skills import ToneSkill, CTASkill, HashtagSkill, BrandVoiceSkill


class InstagramGenerator(BasePlatformGenerator):
    platform_name = "Instagram"

    system_prompt = (
        "You are a creative social media marketer writing Instagram captions. "
        "Write visually evocative, punchy captions with a strong opening line. "
        "Use emojis strategically. Caption body: 50–100 words."
    )

    temperature = 0.8
    max_tokens = 250

    skills = [
        ToneSkill("visual"),
        CTASkill("follow"),
        HashtagSkill(count=8),   # brand_tags=["#YourBrand"] once brand is defined
        BrandVoiceSkill(),
    ]
