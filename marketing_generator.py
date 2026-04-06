"""
Main entry point for generating marketing posts.
Usage:
    python marketing_generator.py
    python marketing_generator.py --topic "summer sale" --platform linkedin
"""

import argparse
from platforms import REGISTRY
import config


def generate_all(topic: str, context: dict | None = None) -> dict[str, str]:
    results = {}
    for platform in config.PLATFORMS:
        generator = REGISTRY[platform]()
        print(f"  Generating {platform} post...", flush=True)
        results[platform] = generator.generate(topic, context)
    return results


def print_results(topic: str, results: dict[str, str]) -> None:
    print(f"\n{'='*60}")
    print(f"  Topic: {topic}")
    print(f"{'='*60}\n")
    for platform, post in results.items():
        print(f"--- {platform.upper()} ---")
        print(post)
        print()


def main():
    parser = argparse.ArgumentParser(description="Generate platform-specific marketing posts.")
    parser.add_argument("--topic", default="our new product launch", help="Topic / brief for the post")
    parser.add_argument(
        "--platform",
        choices=list(REGISTRY.keys()) + ["all"],
        default="all",
        help="Target platform (default: all)",
    )
    args = parser.parse_args()

    print(f"Connecting to LM Studio at {config.LM_STUDIO_BASE_URL} ...")

    if args.platform == "all":
        results = generate_all(args.topic)
    else:
        generator = REGISTRY[args.platform]()
        print(f"  Generating {args.platform} post...", flush=True)
        results = {args.platform: generator.generate(args.topic)}

    print_results(args.topic, results)


if __name__ == "__main__":
    main()
