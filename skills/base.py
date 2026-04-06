"""
BaseSkill — three-hook pipeline every skill must implement.

Hooks are called in order during generation:
  1. inject_system_prompt  — augments the platform system prompt before the API call
  2. inject_user_prompt    — augments the user prompt before the API call
  3. postprocess           — transforms the raw model output after the API call

A skill only needs to override the hook(s) it cares about.
"""


class BaseSkill:
    name: str = "base"

    def inject_system_prompt(self, system_prompt: str) -> str:
        """Append skill-specific instructions to the system prompt."""
        return system_prompt

    def inject_user_prompt(self, user_prompt: str) -> str:
        """Append skill-specific context or constraints to the user prompt."""
        return user_prompt

    def postprocess(self, output: str) -> str:
        """Transform the raw generated text (e.g. formatting, appending, filtering)."""
        return output
