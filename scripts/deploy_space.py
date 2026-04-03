#!/usr/bin/env python3
"""
Upload this project to Hugging Face Spaces without sending .venv or other local junk.

`gradio deploy` calls `upload_folder` on the whole directory; huggingface_hub does not
apply .gitignore, so your virtualenv (hundreds of MB of torch, macOS .dylibs, etc.)
gets uploaded and the run looks "stuck" or fails.

Usage (from repo root, with HF token logged in):

    uv run python scripts/deploy_space.py

Optional: set hardware for *new* spaces or updates that apply it:

    export SPACE_HARDWARE=t4-small   # or cpu-basic, zero-a10g, ...
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Repo root = parent of scripts/
REPO_ROOT = Path(__file__).resolve().parent.parent
README = REPO_ROOT / "README.md"

# Paths are relative to REPO_ROOT (glob / filter_repo_objects style).
UPLOAD_IGNORE = [
    # Virtual environments (main issue with `gradio deploy`)
    ".venv/**",
    "venv/**",
    # Secrets and local env
    ".env",
    ".env.*",
    # Python / tooling
    "**/__pycache__/**",
    "**/*.pyc",
    ".pytest_cache/**",
    "**/*.egg-info/**",
    # OS / editor
    "**/.DS_Store",
    ".ipynb_checkpoints/**",
    # Generated artifacts (not needed on Space)
    "*.jsonl",
    "*.csv",
    # Git (defaults also skip .git, but explicit is fine)
    ".git/**",
]


def main() -> int:
    os.chdir(REPO_ROOT)
    if not README.is_file():
        print("README.md not found at repo root.", file=sys.stderr)
        return 1

    import huggingface_hub as hh

    try:
        configuration = hh.metadata_load(str(README))
    except ValueError as e:
        print(f"Invalid or missing README frontmatter: {e}", file=sys.stderr)
        return 1

    title = configuration.get("title")
    if not title:
        print("README frontmatter must include `title:` (Space repo slug).", file=sys.stderr)
        return 1

    hf_api = hh.HfApi()
    try:
        whoami = hf_api.whoami()
        if whoami.get("auth", {}).get("accessToken", {}).get("role") != "write":
            print("Need a write token. Run: huggingface-cli login", file=sys.stderr)
            return 1
    except Exception:
        print("Not logged in. Run: huggingface-cli login", file=sys.stderr)
        return 1

    hardware = os.environ.get("SPACE_HARDWARE") or configuration.get("hardware")
    create_kw = dict(
        repo_id=title,
        space_sdk="gradio",
        repo_type="space",
        exist_ok=True,
    )
    if hardware:
        create_kw["space_hardware"] = hardware

    space_id = hf_api.create_repo(**create_kw).repo_id

    print(f"Uploading {REPO_ROOT} to spaces/{space_id} (excluding venv & caches)…")
    hf_api.upload_folder(
        repo_id=space_id,
        repo_type="space",
        folder_path=str(REPO_ROOT),
        ignore_patterns=UPLOAD_IGNORE,
    )
    print(f"Done: https://huggingface.co/spaces/{space_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
