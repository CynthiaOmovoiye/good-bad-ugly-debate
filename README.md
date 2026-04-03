---
# HF / `gradio deploy` use `title` as the Space repo name — alphanumeric, hyphens, underscores only.
title: good-bad-ugly-debate
emoji: 🤠
colorFrom: yellow
colorTo: gray
sdk: gradio
app_file: app.py
pinned: false
license: mit
---

# 🤠 The Good, The Bad & The Ugly — Multi-Agent AI Debate

Three LLMs. Three personas. One debate topic — decided by you.

Inspired by Sergio Leone's 1966 Spaghetti Western, this project pits three AI agents with distinct personalities against each other in a structured, multi-round debate — each speaking only in character, challenging each other directly.

| Agent | Model | Personality | Position |
|-------|-------|-------------|----------|
| 🤠 The Good | GPT-4.1-mini | Laconic, principled, morally pragmatic | Regulation & public ownership |
| 🖤 The Bad | Claude 3.5 Haiku | Cold, strategic, ruthless logic | Corporate control |
| 😈 The Ugly | Gemini 2.5 Flash | Theatrical, opportunistic, chaotic charm | Open & ungoverned access |

All three models run through **[OpenRouter](https://openrouter.ai)** — one API key, any model.

---

## Two Versions, Two Architectures

This repo contains two notebooks that implement the same debate system using different context management strategies. The comparison is intentional.

### `good_bad_ugly_debate.ipynb` — Role-mapped history
Each agent maintains its **own separate message history**. Its own replies appear as `assistant` turns; other agents' replies arrive as `user` messages. This mirrors how you'd structure a real production system where agent identity needs to be strictly preserved across turns.

```
Agent A history:       Agent B history:
  system: A's persona    system: B's persona
  assistant: A reply 1   user: A reply 1
  user: B reply 1        assistant: B reply 1
  user: C reply 1        user: C reply 1
  assistant: A reply 2   user: A reply 2
  ...                    assistant: B reply 2
```

### `good_bad_ugly_simple.ipynb` — Shared transcript
One **shared conversation list** is maintained. Every agent call receives the full transcript as a plain-text `user` prompt and is told which character to play next. Simpler, more coherent, and easier to extend.

```python
# The entire system per agent call:
system: who this agent IS
user:   full transcript so far + "respond as The Good"
```

**When to use which:**
- Role-mapped: when strict turn-by-turn identity fidelity matters (e.g., a memory-augmented agent that needs to recall only its own prior outputs)
- Shared transcript: for most multi-agent use cases — cleaner, easier to debug, easier to extend

---

## Features

- **Multi-provider** — GPT-4.1-mini, Claude 3.5 Haiku, and Gemini 2.5 Flash Lite all in one system
- **Configurable** — swap the debate topic, number of rounds, add a moderator nudge, inject a closing prompt
- **Moderator interrupts** — inject a redirect mid-debate to force concrete positions
- **Fallback lines** — graceful handling if any API call fails, debate continues uninterrupted
- **Rendered output** — responses display as formatted Markdown in notebook

---

## Hugging Face Space

This repo is ready to run as a [Gradio Space](https://huggingface.co/docs/hub/spaces-sdks-gradio).

1. Push the repo to Hugging Face (e.g. **Create new Space** → Gradio, then `git push` this project).
2. In the Space **Settings → Repository secrets**, add `OPENROUTER_API_KEY` with your [OpenRouter](https://openrouter.ai) key.
3. The Space builds from `requirements.txt` and serves `app.py`.

Local preview:

```bash
pip install -r requirements.txt
export OPENROUTER_API_KEY="your-key"
python app.py
```

---

## Quick Start (notebooks / Colab)

```bash
# 1. Get a free API key at https://openrouter.ai
# 2. Open either notebook in Google Colab
# 3. Add your key as a Colab secret named OPENROUTER_API_KEY
# 4. Edit Cell 3 to set your topic and rounds
# 5. Runtime → Run all
```

No local setup needed. Colab handles everything.

---

## Customisation

Edit **Cell 3** in either notebook:

```python
DEBATE_TOPIC = "Your question here"
ROUNDS = 5                    # 3–6 recommended
MODERATOR_NUDGE = "..."       # set to None to skip
MODERATOR_ROUND = 3           # fires before this round
CLOSING_PROMPT = "..."        # set to None to skip
```

To swap models, edit Cell 5:
```python
good_model = "openai/gpt-4o"          # any OpenRouter model
bad_model  = "anthropic/claude-opus-4"
ugly_model = "google/gemini-2.0-flash"
```

---

## Architecture Notes

**Why OpenRouter?** A single API client (`openai.OpenAI` with a custom `base_url`) routes to any supported provider. This means you can swap `good_model`, `bad_model`, and `ugly_model` to any of 200+ models without changing the rest of the code.

**Why different temperatures?** The Good uses `0.7` (controlled, precise), The Bad `0.8` (calculated but varied), The Ugly `0.95` (chaotic, unpredictable). Temperature shapes character as much as the system prompt does.

**Why 140 max tokens?** Forcing brevity makes the debate snappier and prevents any one agent from dominating. The 2-sentence rule in the system prompt + the token cap creates a natural rhythm.

---

## Requirements

**Space / local app:** see `requirements.txt` (`gradio`, `openai`).

**Notebooks:**

```
openai>=1.0.0
ipython
```

Or just run in Colab — nothing to install locally.

---

## Author

Built by **Cynthia Omovoiye** — AI Engineer specialising in production LLM systems, multi-agent workflows, and RAG pipelines.

- [LinkedIn](https://www.linkedin.com/in/cynthia-omovoiye-469568184)
- [Portfolio](https://cynthia-omovoiye-portfolio.netlify.app)

## License

MIT
