#!/usr/bin/env python3
"""Create a minimal One Word to Hand-drawn project skeleton."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--scenes", type=int, default=7)
    args = parser.parse_args()

    if not 1 <= args.scenes <= 30:
        raise SystemExit("--scenes must be between 1 and 30")

    project = Path(args.project).expanduser().resolve()
    storyboard_path = project / "storyboard.json"
    if storyboard_path.exists():
        raise SystemExit(f"Refusing to overwrite existing storyboard: {storyboard_path}")

    (project / "images").mkdir(parents=True, exist_ok=True)
    (project / "out").mkdir(parents=True, exist_ok=True)
    (project / "work").mkdir(parents=True, exist_ok=True)
    scenes = []
    for index in range(1, args.scenes + 1):
        scene_id = f"{index:02d}"
        scenes.append(
            {
                "id": scene_id,
                "caption": f"第{index}幕文字",
                "narration": f"第{index}幕旁白。",
                "image": f"images/{scene_id}.png",
                "visual": f"第{index}幕的彩色手绘场景",
            }
        )
    storyboard = {
        "title": args.title,
        "language": "zh",
        "scenes": scenes,
    }
    storyboard_path.write_text(
        json.dumps(storyboard, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"PROJECT={project}")
    print(f"STORYBOARD={storyboard_path}")


if __name__ == "__main__":
    main()
