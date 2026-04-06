"""
Capability test — verifies the model connection and runs a post for each platform.
Run this first to confirm LM Studio is up and the model is loaded.
"""

from openai import OpenAI
import config
from platforms import REGISTRY


def test_connection() -> bool:
    client = OpenAI(base_url=config.LM_STUDIO_BASE_URL, api_key=config.LM_STUDIO_API_KEY)
    try:
        models = client.models.list()
        names = [m.id for m in models.data]
        print(f"[OK] Connected to LM Studio. Available models: {names}")
        if not any(config.MODEL_ID in n or n in config.MODEL_ID for n in names):
            print(f"[WARN] Expected model '{config.MODEL_ID}' not found in list — make sure it is loaded in LM Studio.")
        return True
    except Exception as e:
        print(f"[FAIL] Cannot reach LM Studio at {config.LM_STUDIO_BASE_URL}: {e}")
        print("  -> Start LM Studio, load the model, and enable the local server (port 1234).")
        return False


def test_platform(platform: str, topic: str = "sustainable packaging for small businesses") -> None:
    print(f"\n[TEST] {platform.upper()}")
    try:
        generator = REGISTRY[platform]()
        post = generator.generate(topic)
        print(post)
        print(f"[OK] {platform} — {len(post)} chars generated")
    except Exception as e:
        print(f"[FAIL] {platform}: {e}")


if __name__ == "__main__":
    print("=== Marketing Generator — Capability Test ===\n")
    if not test_connection():
        raise SystemExit(1)

    for platform in config.PLATFORMS:
        test_platform(platform)

    print("\n=== All tests complete ===")
