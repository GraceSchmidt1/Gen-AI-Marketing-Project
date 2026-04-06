"""
Project configuration — model endpoint and platform defaults.
"""

LM_STUDIO_BASE_URL = "http://localhost:1234/v1"
LM_STUDIO_API_KEY = "lm-studio"   # LM Studio ignores the key but openai client requires one

# Model identifier as LM Studio reports it (matches the loaded model name in the UI)
MODEL_ID = "lmstudio-community/gemma-4-E4B-it-GGUF/gemma-4-E4B-it-Q4_K_M.gguf"

# Generation defaults (tune per-platform later)
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 512

# Supported platforms — order here controls test output order
PLATFORMS = ["linkedin", "facebook", "instagram"]
