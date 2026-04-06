"""
Base class for platform-specific post generators.

Skill pipeline (executed in list order):
  1. inject_system_prompt — each skill augments the platform system prompt
  2. inject_user_prompt   — each skill augments the user prompt
  3. [model call]
  4. postprocess          — each skill transforms the raw output
"""

from openai import OpenAI
import config
from skills.base import BaseSkill


class BasePlatformGenerator:
    platform_name: str = "generic"

    system_prompt: str = "You are a helpful marketing assistant."
    max_tokens: int = config.DEFAULT_MAX_TOKENS
    temperature: float = config.DEFAULT_TEMPERATURE

    # Declare platform-default skills as a class attribute.
    # Subclasses override this list; callers can also pass skills= at instantiation.
    skills: list[BaseSkill] = []

    def __init__(self, skills: list[BaseSkill] | None = None):
        self.client = OpenAI(
            base_url=config.LM_STUDIO_BASE_URL,
            api_key=config.LM_STUDIO_API_KEY,
        )
        # Per-instance skills override the class-level default when provided
        if skills is not None:
            self._skills = skills
        else:
            self._skills = list(self.skills)

    # ------------------------------------------------------------------
    # Prompt construction
    # ------------------------------------------------------------------

    def build_user_prompt(self, topic: str, context: dict | None = None) -> str:
        parts = [f"Create a {self.platform_name} marketing post about: {topic}"]
        if context:
            for key, value in context.items():
                parts.append(f"{key}: {value}")
        return "\n".join(parts)

    def _apply_system_prompt_skills(self) -> str:
        prompt = self.system_prompt
        for skill in self._skills:
            prompt = skill.inject_system_prompt(prompt)
        return prompt

    def _apply_user_prompt_skills(self, user_prompt: str) -> str:
        for skill in self._skills:
            user_prompt = skill.inject_user_prompt(user_prompt)
        return user_prompt

    def _apply_postprocess_skills(self, output: str) -> str:
        for skill in self._skills:
            output = skill.postprocess(output)
        return output

    # ------------------------------------------------------------------
    # Generation
    # ------------------------------------------------------------------

    def generate(self, topic: str, context: dict | None = None) -> str:
        system_prompt = self._apply_system_prompt_skills()
        user_prompt = self._apply_user_prompt_skills(
            self.build_user_prompt(topic, context)
        )

        response = self.client.chat.completions.create(
            model=config.MODEL_ID,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )

        output = response.choices[0].message.content.strip()
        return self._apply_postprocess_skills(output)
