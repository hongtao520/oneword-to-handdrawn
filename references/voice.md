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

If the user voluntarily supplies a Fish Audio key in the conversation, accept it as authorization
to configure this Skill. Run `scripts/configure_fish.py --from-stdin`, send the value only through
stdin, do not repeat it anywhere, verify with `--check`, and continue. Do not reject the key merely
because it arrived in chat.

If all lookup locations are missing and the user has not supplied a key, do not generate a fake or
system voice. Tell the user they may paste the key directly in the conversation or use the hidden
prompt in `scripts/configure_fish.py`.

To replace the voice while preserving the picture, pass the already-built silent master through
the same project and rerun `build_video.py --mode voiced` with a different `reference_id`.
