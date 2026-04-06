# Gen-AI-Marketing-Project

Local LLM-powered marketing post generator using [LM Studio](https://lmstudio.ai/) + Gemma 4 E4B.

## Setup

1. Open LM Studio, load `gemma-4-E4B-it-Q4_K_M.gguf`, and start the local server (default port 1234).
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

**Test model connection + generate one sample post per platform:**
```bash
python test_capabilities.py
```

**Generate posts for all platforms:**
```bash
python marketing_generator.py --topic "our spring product launch"
```

**Generate a post for a single platform:**
```bash
python marketing_generator.py --topic "new feature announcement" --platform linkedin
```

## Project Structure

```
config.py                  # Model endpoint, platform list, generation defaults
marketing_generator.py     # CLI entry point
test_capabilities.py       # Connection test + capability demo
platforms/
  base.py                  # BasePlatformGenerator (shared logic, SOP injection point)
  linkedin.py
  facebook.py
  instagram.py
```

## Roadmap

- [ ] Add platform-specific SOPs (inject into system prompts in `platforms/base.py`)
- [ ] Integrate skills (tone library, brand voice, hashtag strategy)
- [ ] Batch generation from a content brief CSV
