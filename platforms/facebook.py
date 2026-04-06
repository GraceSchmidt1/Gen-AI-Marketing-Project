from .base import BasePlatformGenerator
from skills import ToneSkill, CTASkill, BrandVoiceSkill


class FacebookGenerator(BasePlatformGenerator):
    platform_name = "Facebook"

    system_prompt = (
        "You are a friendly, community-focused social media marketer writing for Facebook. "
        "Write posts that are conversational, relatable, and shareable. "
        "Use a warm tone, occasional emojis. Length: 80–150 words."
    )

    temperature = 0.75
    max_tokens = 300

    skills = [
        ToneSkill("conversational"),
        CTASkill("engagement"),
        BrandVoiceSkill(),   # populate brand_name/guidelines/avoid when SOP is defined
    ]
