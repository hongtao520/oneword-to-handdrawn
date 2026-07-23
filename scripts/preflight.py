#!/usr/bin/env python3
"""Run the first-use checks before story or image work begins."""

from __future__ import annotations

import argparse
from pathlib import Path

from configure_fish import find_key
from setup_dependencies import default_cache_dir, ensure_dependencies


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("voiced", "silent"), default="voiced")
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--cache-dir")
    args = parser.parse_args()

    if args.mode == "voiced" and not find_key():
        skill_dir = Path(__file__).resolve().parent.parent
        raise SystemExit(
            "Fish Audio API key is required for the voiced version.\n"
            "Create one at https://fish.audio/zh-CN/app/api-keys/ and run:\n"
            f"python3 {skill_dir / 'scripts' / 'configure_fish.py'}\n"
            "Then rerun this preflight. Use --mode silent if narration is not needed."
        )

    cache_dir = (
        Path(args.cache_dir).expanduser().resolve()
        if args.cache_dir
        else default_cache_dir()
    )
    runtime = ensure_dependencies(cache_dir, install=not args.check_only)
    print(f"Preflight ready for {args.mode} mode.")
    print(f"Node.js: {runtime['node']}")
    print(f"FFmpeg: {runtime['ffmpeg']}")


if __name__ == "__main__":
    main()
