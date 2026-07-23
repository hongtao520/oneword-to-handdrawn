# Fish Audio voice handling

The default is the public Fish Audio voice `儿童故事女声`:

```json
{
  "provider": "fish",
  "model": "s2.1-pro-free",
  "name": "儿童故事女声",
  "reference_id": "7b248932fa704935ae2cd0fc1ed374fe",
  "speed": 1.3,
  "temperature": 0.55,
  "top_p": 0.7
}
```

The build generates voice first, trims only file-edge silence, then derives exact scene lengths.
Do not post-compress narration merely to fit a fixed visual slot.

Credential lookup order:

1. `FISH_API_KEY` environment variable;
2. `<skill-dir>/.env`;
3. an installed `vox-agent/.env` under `${CODEX_HOME:-~/.codex}/skills/vox-agent`.

If all are missing, do not generate a fake or system voice. Tell the user where to create a Fish
API key and run `scripts/configure_fish.py`.

To replace the voice while preserving the picture, pass the already-built silent master through
the same project and rerun `build_video.py --mode voiced` with a different `reference_id`.
