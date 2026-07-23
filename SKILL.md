---
name: oneword-to-handdrawn
description: Turn one Chinese word, idiom, topic, short prompt, or supplied story into a finished 3:4 colorful hand-drawn whiteboard story video with the original handwritten text-wipe effect, the YangAgent two-stage sketch-to-color drawing animation applied only to the illustration area, tight narration-driven cuts, and optional Fish Audio narration. Use whenever the user asks to make a hand-drawn story, fairy-tale, idiom, children’s, whiteboard, or “one word to video” animation, including requests such as “帮我做一个视频”, “把这个成语做成手绘视频”, voiced videos, silent videos, or voice replacement.
---

# One Word to Hand-drawn

Turn a title or short story into the approved 1080×1440 hand-drawn video style.

## Non-negotiable visual contract

- Generate each illustration directly in color on a clean light background.
- Apply the YangAgent original two-stage algorithm only to the lower illustration: black-line drawing first, then color reveal, with the real hand and pen visible.
- Keep captions separate above the illustration. Reveal them with the original left-to-right `TextWipe`; never feed caption text into the whiteboard animation.
- Use 3:4 portrait output at 1080×1440, 30 fps, H.264.
- Keep all illustration content contained. Never crop characters or important marks.
- Retain only about 0.1 seconds of the completed illustration before cutting.
- For voiced work, let narration duration drive every scene. Start narration at 0.12 seconds and cut about 0.08 seconds after it ends.

## Choose the mode

- Default to `voiced` unless the user explicitly requests silent/no narration.
- Use `silent` when the user says “不要配音”, “静音”, or equivalent.
- When replacing a voice, reuse the existing silent master; do not rerender images or animation.

## Workflow

1. Choose the mode, then run preflight before writing the story or generating images:

   ```bash
   # Default voiced version: checks Fish first, then privately installs missing runtimes
   python3 <skill-dir>/scripts/preflight.py --mode voiced

   # Silent version: no Fish key required
   python3 <skill-dir>/scripts/preflight.py --mode silent
   ```

   Preflight uses an existing Node.js 20+ and FFmpeg when available. Otherwise it downloads
   private copies under `~/.cache/oneword-to-handdrawn/`; do not make the user install global
   packages manually. The build also runs this dependency bootstrap as a safety net. The first
   build downloads the pinned YangAgent source and installs its Python packages in an isolated
   environment.

2. For voiced work, if preflight reports missing Fish credentials, stop before making any assets.
   Tell the user to create an API key at `https://fish.audio/zh-CN/app/api-keys/`, then run:

   ```bash
   python3 <skill-dir>/scripts/configure_fish.py
   ```

   Never request or display the key in chat. Resume only after
   `python3 <skill-dir>/scripts/configure_fish.py --check` succeeds.

3. Create a project folder outside this skill and initialize it:

   ```bash
   python3 <skill-dir>/scripts/init_project.py \
     --project /absolute/path/to/project \
     --title "狐假虎威" \
     --scenes 7
   ```

4. Write `<project>/storyboard.json` using [storyboard.md](references/storyboard.md).
   Preserve supplied wording. For a topic or idiom, write a concise 6–8 scene story with one
   narration sentence and one short handwritten caption per scene.

5. Generate one square color illustration for every scene. Read
   [image-prompts.md](references/image-prompts.md) before generating. Save exact files under
   `<project>/images/` as listed in the storyboard. Do not put text inside images.

6. Validate inputs:

   ```bash
   python3 <skill-dir>/scripts/validate_project.py /absolute/path/to/project
   ```

7. Build:

   ```bash
   # Default voiced version
   python3 <skill-dir>/scripts/build_video.py /absolute/path/to/project --mode voiced

   # Silent version
   python3 <skill-dir>/scripts/build_video.py /absolute/path/to/project --mode silent
   ```

   Do not edit or replace the pinned upstream drawing algorithm. Read
   [voice.md](references/voice.md) when changing voices.

8. Inspect at least one early drawing frame, one completed frame, and every scene cut. Confirm:

   - captions use `TextWipe` and contain no hand overlay;
   - the hand stays inside the illustration region;
   - narration is not clipped;
   - there is no long completed-frame hold;
   - the final MP4 decodes without warnings.

## Voice defaults

- Provider: Fish Audio
- Model: `s2.1-pro-free`
- Voice: `儿童故事女声`
- Reference ID: `7b248932fa704935ae2cd0fc1ed374fe`

Use one voice for the entire story. Honor an explicitly selected Fish library or authorized
cloned voice with:

```bash
python3 <skill-dir>/scripts/build_video.py /absolute/path/to/project \
  --mode voiced \
  --voice-name "用户选择的音色" \
  --voice-reference-id FISH_REFERENCE_ID
```

## Output contract

- Silent master: `<project>/out/picture_silent.mp4`
- Voiced final: `<project>/out/picture_voiced.mp4`
- Timing report: `<project>/out/timing.json`
- Scene clips: `<project>/work/clips/`

Always preserve and report the silent master, even for voiced requests. Report scene count,
duration, resolution, mode, voice name, and both relevant output paths. After delivering a
voiced result, tell the user: “如果你想换音色，可以告诉我音色名称或 Fish Audio
reference ID，我会保持画面不变重新配音。”
