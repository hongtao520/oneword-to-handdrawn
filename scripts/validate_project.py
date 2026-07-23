#!/usr/bin/env python3
"""Validate storyboard structure and referenced illustration files."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


SUPPORTED_IMAGES = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}


def load_project(project: Path) -> tuple[dict, list[dict]]:
    storyboard_path = project / "storyboard.json"
    if not storyboard_path.is_file():
        raise SystemExit(f"Missing storyboard: {storyboard_path}")
    try:
        storyboard = json.loads(storyboard_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON in {storyboard_path}: {exc}") from exc

    scenes = storyboard.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        raise SystemExit("storyboard.scenes must be a non-empty array")
    return storyboard, scenes


def validate(project: Path) -> dict:
    storyboard, scenes = load_project(project)
    ids: set[str] = set()
    errors: list[str] = []
    for index, scene in enumerate(scenes, 1):
        if not isinstance(scene, dict):
            errors.append(f"scene {index}: must be an object")
            continue
        scene_id = str(scene.get("id") or "").strip()
        caption = str(scene.get("caption") or scene.get("text") or "").strip()
        narration = str(scene.get("narration") or "").strip()
        image_value = str(scene.get("image") or "").strip()
        if not scene_id:
            errors.append(f"scene {index}: missing id")
        elif scene_id in ids:
            errors.append(f"scene {index}: duplicate id {scene_id}")
        ids.add(scene_id)
        if not caption:
            errors.append(f"scene {scene_id or index}: missing caption")
        if not narration:
            errors.append(f"scene {scene_id or index}: missing narration")
        if not image_value:
            errors.append(f"scene {scene_id or index}: missing image")
            continue
        image_path = (project / image_value).resolve()
        try:
            image_path.relative_to(project)
        except ValueError:
            errors.append(f"scene {scene_id or index}: image escapes project: {image_value}")
            continue
        if image_path.suffix.lower() not in SUPPORTED_IMAGES:
            errors.append(f"scene {scene_id or index}: unsupported image: {image_value}")
        elif not image_path.is_file():
            errors.append(f"scene {scene_id or index}: image not found: {image_value}")

    if errors:
        raise SystemExit("Project validation failed:\n- " + "\n- ".join(errors))
    return {
        "title": str(storyboard.get("title") or project.name),
        "scene_count": len(scenes),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("project")
    args = parser.parse_args()
    project = Path(args.project).expanduser().resolve()
    result = validate(project)
    print(f"VALID: {result['title']} ({result['scene_count']} scenes)")


if __name__ == "__main__":
    main()
