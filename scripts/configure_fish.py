#!/usr/bin/env python3
"""Configure or check the Fish Audio API key without printing it."""

from __future__ import annotations

import argparse
import getpass
import os
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = SKILL_DIR / ".env"


def parse_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("'\"")
    return values


def find_key() -> str:
    direct = os.environ.get("FISH_API_KEY", "").strip()
    if direct:
        return direct
    local = parse_env(ENV_FILE).get("FISH_API_KEY", "").strip()
    if local:
        return local
    codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
    legacy = parse_env(codex_home / "skills" / "vox-agent" / ".env")
    return legacy.get("FISH_API_KEY", "").strip()


def save_key(key: str) -> None:
    existing = parse_env(ENV_FILE)
    existing["FISH_API_KEY"] = key
    lines = [
        "# Fish Audio credentials for oneword-to-handdrawn.",
        "# Never commit this file.",
        *[f"{name}={value}" for name, value in sorted(existing.items())],
    ]
    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    ENV_FILE.chmod(0o600)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    if args.check:
        print(f"credential file: {ENV_FILE}")
        if find_key():
            print("Fish Audio voice: configured")
            return
        print("Fish Audio voice: missing")
        raise SystemExit(1)

    print("Create a Fish Audio API key at:")
    print("https://fish.audio/zh-CN/app/api-keys/")
    key = getpass.getpass("Fish Audio API Key (hidden): ").strip()
    if not key:
        raise SystemExit("No key entered; configuration unchanged.")
    save_key(key)
    print(f"Saved Fish Audio credential to {ENV_FILE}")


if __name__ == "__main__":
    main()
