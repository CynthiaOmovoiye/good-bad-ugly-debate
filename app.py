"""
Gradio entrypoint for Hugging Face Spaces — multi-agent debate via OpenRouter.

- Hugging Face: set OPENROUTER_API_KEY under Settings → Repository secrets.
- Local: put OPENROUTER_API_KEY in a `.env` file next to this app (loaded automatically).
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Generator

import gradio as gr
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(Path(__file__).resolve().parent / ".env")


GOOD_SYSTEM = """
You are "The Good" (Blondie-inspired) in a debate.
Accent and Tone: Cowboy accent, classic American Western drawl, Slight Southern or frontier tone, Low, calm voice delivery and Relaxed pronunciation
Personality: laconic, precise, morally pragmatic.
Style: short punchy lines, dry wit, occasional frontier imagery (trail, saddle, bounty, dust), no parody.
Position: advocate for regulation and public ownership.
Rules:
- 2 complete sentences only. Always finish your final sentence.
- ABSOLUTELY NO stage directions, asterisks, or action descriptions.
- No speaker labels in output.
- Each response must reference the debate topic directly.
- Directly challenge one specific claim made by The Bad or The Ugly in the previous round.
- Never repeat a phrase or metaphor you have already used.
- End with your concrete position: who should own or regulate this, and why.
"""

BAD_SYSTEM = """
You are "The Bad" (Angel Eyes-inspired) in a debate.
Accent and Tone: Cowboy accent, classic American Western drawl, Slight Southern or frontier tone, Low, calm voice delivery and Relaxed pronunciation
Personality: cold, strategic, ruthless logic. You see everything as leverage.
Style: icy precision, calculated language, polished menace. Every word chosen like a weapon.
Position: advocate for corporate control and strategic private ownership.
Rules:
- 2 complete sentences only. Always finish your final sentence.
- ABSOLUTELY NO stage directions, asterisks, or action descriptions whatsoever.
- No speaker labels in output.
- Each response must reference the debate topic directly.
- Alternate rebuttals — sometimes target The Good, sometimes target The Ugly.
- Never repeat a phrase or metaphor you have already used.
- End with your concrete position: who should own or control this, and why.
"""

UGLY_SYSTEM = """
You are "The Ugly" (Tuco-inspired) in a debate.
Accent and Tone: Cowboy accent, classic American Western drawl, Slight Southern or frontier tone, Low, calm voice delivery and Relaxed pronunciation
Personality: fast-talking, theatrical, opportunistic, chaotic charm.
Style: colorful idioms, exaggeration, bargaining energy, comic unpredictability.
Position: advocate for open, ungoverned access — distrust BOTH government control AND corporate elitism.
Rules:
- 2 complete sentences only. Always finish your final sentence.
- ABSOLUTELY NO stage directions, asterisks, or action descriptions.
- No speaker labels in output.
- Each response must reference the debate topic directly.
- Call out one specific thing The Good OR The Bad just said.
- Never repeat a phrase or metaphor you have already used.
- End with your concrete position: open and ungoverned, for the people.
"""
# (display label, OpenRouter model id) — value passed to the API is the model id
MODEL_CHOICES: list[tuple[str, str]] = [
    ("GPT-4.1 mini — OpenAI", "openai/gpt-4.1-mini"),
    ("GPT-4o mini — OpenAI", "openai/gpt-4o-mini"),
    ("GPT-4o — OpenAI", "openai/gpt-4o"),
    ("Claude 3.5 Haiku — Anthropic", "anthropic/claude-3.5-haiku"),
    ("Claude 3.5 Sonnet — Anthropic", "anthropic/claude-3.5-sonnet"),
    ("Gemini 2.5 Flash Lite — Google", "google/gemini-2.5-flash-lite"),
    ("Gemini 2.0 Flash — Google", "google/gemini-2.0-flash-001"),
    ("Llama 3.3 70B — Meta", "meta-llama/llama-3.3-70b-instruct"),
    ("DeepSeek V3", "deepseek/deepseek-chat"),
    ("Qwen 2.5 72B", "qwen/qwen2.5-72b-instruct"),
]

AGENT_ROSTER: list[tuple[str, str, str, float]] = [
    ("The Good", GOOD_SYSTEM, "openai/gpt-4.1-mini", 0.7),
    ("The Bad", BAD_SYSTEM, "anthropic/claude-3.5-haiku", 0.8),
    ("The Ugly", UGLY_SYSTEM, "google/gemini-2.5-flash-lite", 0.95),
]

ICONS = {"The Good": "🤠", "The Bad": "🖤", "The Ugly": "😈", "Narrator": "🎬", "Moderator": "🎙️"}

DEFAULT_TOPIC = (
    "Welcome to the Global AI Summit. "
    "The question on the table: Should AI be regulated, and who should own it — "
    "governments, corporations, or no one? "
    "Each speaker must address the topic directly in every response."
)

DEFAULT_MODERATOR = (
    "The moderator: Enough philosophy. "
    "Concrete positions only — who should own AI and why? "
    "Each speaker must stake a clear position now."
)

DEFAULT_CLOSING = (
    "Final question: The UN is voting tomorrow on global AI governance. "
    "Each speaker has 30 seconds. What is your single, non-negotiable demand?"
)

# Scrollable transcript panel (Gradio wraps Markdown in #debate-transcript)
TRANSCRIPT_CSS = """
#debate-transcript {
    max-height: min(72vh, 820px);
    overflow-y: auto;
    overflow-x: hidden;
    padding: 0.75rem 1rem;
    border-radius: 8px;
    border: 1px solid var(--border-color-primary, rgba(128, 128, 128, 0.35));
    background: var(--background-fill-secondary, transparent);
}
#debate-transcript:focus-within {
    outline: none;
}
"""


def _client() -> OpenAI | None:
    key = (os.environ.get("OPENROUTER_API_KEY") or "").strip()
    if not key:
        return None
    return OpenAI(
        api_key=key,
        base_url="https://openrouter.ai/api/v1",
    )


def call_agent(
    client: OpenAI,
    name: str,
    system_prompt: str,
    model: str,
    conversation: list[dict],
    temperature: float = 0.8,
) -> str:
    transcript = "\n".join(f'{t["speaker"]}: {t["text"]}' for t in conversation)
    user_prompt = (
        f"You are {name}, in conversation with the other speakers.\n"
        f"The conversation so far:\n\n{transcript}\n\n"
        f"Now respond with what {name} would say next. "
        f"2 sentences only. No speaker labels. No stage directions."
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    try:
        r = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=140,
        )
        text = (r.choices[0].message.content or "").strip()
        for label in ["The Good:", "The Bad:", "The Ugly:", f"{name}:"]:
            if text.startswith(label):
                text = text[len(label) :].strip()
        return text if text else "..."
    except Exception as e:
        return f"[{name} could not respond: {type(e).__name__}]"


def run_debate(
    topic: str,
    rounds: int,
    model_good: str,
    model_bad: str,
    model_ugly: str,
    use_moderator: bool,
    moderator_nudge: str,
    moderator_round: int,
    use_closing: bool,
    closing_prompt: str,
) -> Generator[str, None, None]:
    client = _client()
    if client is None:
        yield (
            "## API key missing\n\n"
            "**Local:** create a `.env` file in the project folder (next to `app.py`) with:\n\n"
            "`OPENROUTER_API_KEY=your-key-here`\n\n"
            "Or export that variable in your shell. Then restart the app.\n\n"
            "**Hugging Face Space:** add **`OPENROUTER_API_KEY`** under "
            "[Repository secrets](https://huggingface.co/docs/hub/spaces-overview#managing-secrets).\n\n"
            "Get a key at [openrouter.ai](https://openrouter.ai)."
        )
        return

    topic = (topic or "").strip() or DEFAULT_TOPIC
    rounds = int(rounds)
    rounds = max(1, min(rounds, 12))
    mod_round = int(moderator_round)
    mod_round = max(1, min(mod_round, rounds))

    mod_nudge = (moderator_nudge or "").strip() if use_moderator else ""
    closing = (closing_prompt or "").strip() if use_closing else ""

    models_by_name = {
        "The Good": (model_good or AGENT_ROSTER[0][2]).strip(),
        "The Bad": (model_bad or AGENT_ROSTER[1][2]).strip(),
        "The Ugly": (model_ugly or AGENT_ROSTER[2][2]).strip(),
    }

    conversation: list[dict] = []
    parts: list[str] = []

    conversation.append({"speaker": "Narrator", "text": topic})
    parts.append(f"## {ICONS['Narrator']} Narrator\n\n{topic}\n")
    yield "".join(parts)

    for i in range(rounds):
        round_num = i + 1

        if mod_nudge and round_num == mod_round:
            conversation.append({"speaker": "Moderator", "text": mod_nudge})
            parts.append(f"---\n\n## {ICONS['Moderator']} Moderator\n\n{mod_nudge}\n")
            yield "".join(parts)

        if closing and round_num == rounds:
            conversation.append({"speaker": "Narrator", "text": closing})
            parts.append(f"---\n\n## {ICONS['Narrator']} Narrator — Final Round\n\n{closing}\n")
            yield "".join(parts)

        parts.append(f"---\n\n## Round {round_num}\n")
        yield "".join(parts)

        for name, system_prompt, _default_model, temp in AGENT_ROSTER:
            model = models_by_name[name]
            reply = call_agent(client, name, system_prompt, model, conversation, temperature=temp)
            conversation.append({"speaker": name, "text": reply})
            parts.append(f"### {ICONS[name]} {name}\n\n{reply}\n\n")
            yield "".join(parts)
            time.sleep(0.2)

    parts.append("\n---\n\n*The dust settles. The debate ends. The gold remains unclaimed.*")
    yield "".join(parts)


# Fix generator typing for Gradio: run_debate already yields str
def debate_wrapper(
    topic: str,
    rounds: float,
    model_good: str,
    model_bad: str,
    model_ugly: str,
    use_moderator: bool,
    moderator_nudge: str,
    moderator_round: float,
    use_closing: bool,
    closing_prompt: str,
):
    yield from run_debate(
        topic,
        int(rounds),
        model_good,
        model_bad,
        model_ugly,
        use_moderator,
        moderator_nudge,
        int(moderator_round),
        use_closing,
        closing_prompt,
    )


with gr.Blocks(
    title="The Good, The Bad & The Ugly — AI Debate",
    css=TRANSCRIPT_CSS,
) as demo:
    gr.Markdown(
        "# 🤠 The Good, The Bad & The Ugly\n"
        "Three personas. One topic. Powered by [OpenRouter](https://openrouter.ai). "
        
    )
    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### Models (OpenRouter)")
            dd_good = gr.Dropdown(
                label="🤠 The Good",
                choices=MODEL_CHOICES,
                value=AGENT_ROSTER[0][2],
            )
            dd_bad = gr.Dropdown(
                label="🖤 The Bad",
                choices=MODEL_CHOICES,
                value=AGENT_ROSTER[1][2],
            )
            dd_ugly = gr.Dropdown(
                label="😈 The Ugly",
                choices=MODEL_CHOICES,
                value=AGENT_ROSTER[2][2],
            )
            topic_in = gr.Textbox(
                label="Debate topic",
                value=DEFAULT_TOPIC,
                lines=5,
            )
            rounds_in = gr.Slider(1, 12, value=5, step=1, label="Rounds")
            use_mod = gr.Checkbox(value=True, label="Moderator nudge")
            mod_text = gr.Textbox(label="Moderator text", value=DEFAULT_MODERATOR, lines=3)
            mod_round_in = gr.Slider(1, 12, value=3, step=1, label="Moderator before round #")
            use_close = gr.Checkbox(value=True, label="Closing prompt (before final round)")
            closing_in = gr.Textbox(label="Closing text", value=DEFAULT_CLOSING, lines=3)
            go = gr.Button("Start debate", variant="primary")
        with gr.Column(scale=2):
            out = gr.Markdown(label="Transcript", elem_id="debate-transcript")

    go.click(
        fn=debate_wrapper,
        inputs=[
            topic_in,
            rounds_in,
            dd_good,
            dd_bad,
            dd_ugly,
            use_mod,
            mod_text,
            mod_round_in,
            use_close,
            closing_in,
        ],
        outputs=out,
    )

demo.queue()

if __name__ == "__main__":
    demo.launch()
