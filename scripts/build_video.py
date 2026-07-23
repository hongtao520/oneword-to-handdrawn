#!/usr/bin/env python3
"""Build the approved caption + YangAgent hand-drawn story video."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import wave
import zipfile
from pathlib import Path
from typing import Any

from configure_fish import find_key
from setup_dependencies import default_cache_dir, ensure_dependencies
from validate_project import load_project, validate


SKILL_DIR = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = SKILL_DIR / "assets" / "remotion-template"
WHITEBOARD_REPO = "https://github.com/yangagent/whiteboard-animation-skill.git"
WHITEBOARD_COMMIT = "36798ab30c3a655b462b5818b66cb2d5cb3d4516"
DEFAULT_VOICE_NAME = "儿童故事女声"
DEFAULT_VOICE_REFERENCE_ID = "7b248932fa704935ae2cd0fc1ed374fe"
DEFAULT_VOICE_MODEL = "s2.1-pro-free"
FPS = 30
WIDTH = 1080
HEIGHT = 1440
LEAD_IN = 0.12
TAIL = 0.08
MIN_SCENE_FRAMES = 84
FINAL_HOLD_FRAMES = 3
RAW_DURATION_MS = 10000
EDGE_TRIM = (
    "silenceremove=start_periods=1:start_duration=0.05:start_threshold=-42dB:"
    "start_silence=0.03,areverse,"
    "silenceremove=start_periods=1:start_duration=0.05:start_threshold=-42dB:"
    "start_silence=0.03,areverse"
)


def run(
    command: list[str],
    *,
    cwd: Path | None = None,
    capture: bool = False,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=str(cwd) if cwd else None,
        text=True,
        capture_output=capture,
        check=check,
    )


def safe_scene_id(value: Any, index: int) -> str:
    scene_id = str(value or f"{index:02d}").strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]+", scene_id):
        raise SystemExit(
            f"Scene id may contain only letters, digits, '_' and '-': {scene_id}"
        )
    return scene_id


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def picture_fingerprint(project: Path, scenes: list[dict]) -> str:
    digest = hashlib.sha256((project / "storyboard.json").read_bytes())
    for scene in scenes:
        image = (project / str(scene["image"])).resolve()
        digest.update(str(scene.get("id", "")).encode("utf-8"))
        digest.update(file_sha256(image).encode("ascii"))
    return digest.hexdigest()


def wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as stream:
        return stream.getnframes() / float(stream.getframerate())


def ensure_whiteboard(cache_dir: Path) -> tuple[Path, str]:
    checkout = cache_dir / f"whiteboard-animation-skill-{WHITEBOARD_COMMIT[:8]}"
    marker = checkout / ".oneword-source.json"
    source_valid = False
    if marker.is_file():
        try:
            source_valid = (
                json.loads(marker.read_text(encoding="utf-8")).get("commit")
                == WHITEBOARD_COMMIT
            )
        except json.JSONDecodeError:
            source_valid = False
    if not source_valid:
        cache_dir.mkdir(parents=True, exist_ok=True)
        print(f"Downloading approved YangAgent revision -> {checkout}")
        archive_url = (
            "https://github.com/yangagent/whiteboard-animation-skill/"
            f"archive/{WHITEBOARD_COMMIT}.zip"
        )
        with tempfile.TemporaryDirectory(dir=cache_dir) as temporary:
            temp_dir = Path(temporary)
            archive = temp_dir / "source.zip"
            request = urllib.request.Request(
                archive_url,
                headers={"User-Agent": "oneword-to-handdrawn source installer"},
            )
            with urllib.request.urlopen(request, timeout=180) as response:
                archive.write_bytes(response.read())
            with zipfile.ZipFile(archive) as bundle:
                destination_root = temp_dir.resolve()
                for name in bundle.namelist():
                    target = (temp_dir / name).resolve()
                    if (
                        destination_root not in target.parents
                        and target != destination_root
                    ):
                        raise SystemExit("Unsafe path found in YangAgent archive.")
                bundle.extractall(temp_dir)
            extracted = temp_dir / (
                f"whiteboard-animation-skill-{WHITEBOARD_COMMIT}"
            )
            if not extracted.is_dir():
                raise SystemExit("YangAgent archive has an unexpected layout.")
            if checkout.exists():
                shutil.rmtree(checkout)
            shutil.move(str(extracted), str(checkout))
        marker.write_text(
            json.dumps(
                {"repository": WHITEBOARD_REPO, "commit": WHITEBOARD_COMMIT},
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    whiteboard_skill = checkout / "skills" / "whiteboard-animation"
    setup = whiteboard_skill / "scripts" / "setup_env.py"
    check = run([sys.executable, str(setup), "--check"], capture=True, check=False)
    if check.returncode != 0:
        print("Preparing isolated YangAgent Python environment...")
        prepared = run([sys.executable, str(setup)], capture=True)
        output = prepared.stdout
    else:
        output = check.stdout
    matches = re.findall(r"^PYTHON_PATH=(.+)$", output, flags=re.MULTILINE)
    if matches:
        python_path = matches[-1].strip()
    elif sys.platform == "win32":
        python_path = str(whiteboard_skill / ".venv" / "Scripts" / "python.exe")
    else:
        python_path = str(whiteboard_skill / ".venv" / "bin" / "python")
    if not Path(python_path).is_file():
        raise SystemExit("YangAgent environment did not provide a Python executable")
    return whiteboard_skill, python_path


def prepare_image(
    python_path: str, source: Path, destination: Path
) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    run(
        [
            python_path,
            str(SKILL_DIR / "scripts" / "prepare_image.py"),
            str(source),
            str(destination),
        ]
    )


def generate_raw_whiteboard(
    python_path: str,
    whiteboard_skill: Path,
    image: Path,
    output_dir: Path,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    before = set(output_dir.glob("*_h264.mp4"))
    run(
        [
            python_path,
            str(whiteboard_skill / "scripts" / "generate_whiteboard.py"),
            str(image),
            "--output-dir",
            str(output_dir),
            "--duration",
            str(RAW_DURATION_MS),
        ]
    )
    candidates = sorted(
        set(output_dir.glob("*_h264.mp4")) - before,
        key=lambda path: path.stat().st_mtime,
    )
    if not candidates:
        candidates = sorted(
            output_dir.glob("*_h264.mp4"), key=lambda path: path.stat().st_mtime
        )
    if not candidates:
        raise SystemExit(f"YangAgent did not create an H.264 video in {output_dir}")
    return candidates[-1]


def retime_whiteboard(
    ffmpeg: str,
    raw: Path,
    destination: Path,
    scene_frames: int,
) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    # The pinned upstream algorithm deterministically targets 420 active 60fps
    # frames and writes 418 drawable frames before its fixed 180-frame hold.
    source_active = 418 / 60
    active_frames = max(1, scene_frames - FINAL_HOLD_FRAMES)
    active_seconds = active_frames / FPS
    setpts_factor = active_seconds / source_active
    hold_seconds = FINAL_HOLD_FRAMES / FPS
    video_filter = (
        f"trim=start=0:end={source_active:.6f},"
        "setpts=PTS-STARTPTS,"
        f"setpts={setpts_factor:.9f}*PTS,"
        f"fps={FPS},"
        f"scale={WIDTH}:{WIDTH}:force_original_aspect_ratio=decrease:flags=lanczos,"
        f"pad={WIDTH}:{WIDTH}:(ow-iw)/2:(oh-ih)/2:color=0xF6F1E3,"
        f"trim=end_frame={active_frames},"
        "setpts=PTS-STARTPTS,"
        f"tpad=stop_mode=clone:stop_duration={hold_seconds:.6f},"
        f"trim=end_frame={scene_frames},"
        "setpts=PTS-STARTPTS,format=yuv420p"
    )
    run(
        [
            ffmpeg,
            "-y",
            "-loglevel",
            "error",
            "-i",
            str(raw),
            "-vf",
            video_filter,
            "-an",
            "-c:v",
            "libx264",
            "-crf",
            "18",
            "-preset",
            "medium",
            "-movflags",
            "+faststart",
            str(destination),
        ]
    )


def trim_voice(ffmpeg: str, source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    run(
        [
            ffmpeg,
            "-y",
            "-loglevel",
            "error",
            "-i",
            str(source),
            "-af",
            EDGE_TRIM,
            "-ar",
            "48000",
            "-ac",
            "1",
            str(destination),
        ]
    )


def fish_tts(
    key: str,
    text: str,
    destination: Path,
    *,
    model: str,
    reference_id: str,
    speed: float,
    temperature: float,
    top_p: float,
) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(
        {
            "text": text,
            "reference_id": reference_id,
            "format": "wav",
            "sample_rate": 44100,
            "normalize": True,
            "latency": "normal",
            "temperature": temperature,
            "top_p": top_p,
            "prosody": {"speed": speed, "volume": 0},
        },
        ensure_ascii=False,
    ).encode("utf-8")
    request = urllib.request.Request(
        "https://api.fish.audio/v1/tts",
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "model": model,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            audio = response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"Fish Audio TTS failed ({exc.code}): {detail}") from exc
    if not audio:
        raise SystemExit("Fish Audio returned an empty response")
    destination.write_bytes(audio)


def generate_voice_files(
    project: Path,
    scenes: list[dict],
    ffmpeg: str,
    args: argparse.Namespace,
) -> list[Path]:
    key = find_key()
    if not key:
        raise SystemExit(
            "Fish Audio API key is not configured.\n"
            "Create one at https://fish.audio/zh-CN/app/api-keys/ and run:\n"
            f"python3 {SKILL_DIR / 'scripts' / 'configure_fish.py'}"
        )
    audio_dir = project / "work" / "audio"
    trimmed_dir = audio_dir / "trimmed"
    voice_signature = hashlib.sha256(
        json.dumps(
            {
                "model": args.voice_model,
                "reference_id": args.voice_reference_id,
                "speed": args.voice_speed,
                "temperature": args.temperature,
                "top_p": args.top_p,
                "texts": [scene["narration"] for scene in scenes],
            },
            ensure_ascii=False,
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    manifest_path = audio_dir / "voice-manifest.json"
    manifest = {}
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            manifest = {}
    reusable = (
        not args.regenerate_voice
        and manifest.get("signature") == voice_signature
    )

    results: list[Path] = []
    for index, scene in enumerate(scenes, 1):
        scene_id = safe_scene_id(scene.get("id"), index)
        raw = audio_dir / f"{scene_id}.wav"
        trimmed = trimmed_dir / f"{scene_id}.wav"
        if reusable and trimmed.is_file():
            print(f"Reusing narration {scene_id}")
        else:
            print(f"Generating narration {scene_id} with {args.voice_name}")
            fish_tts(
                key,
                str(scene["narration"]),
                raw,
                model=args.voice_model,
                reference_id=args.voice_reference_id,
                speed=args.voice_speed,
                temperature=args.temperature,
                top_p=args.top_p,
            )
            trim_voice(ffmpeg, raw, trimmed)
        results.append(trimmed)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(
            {
                "signature": voice_signature,
                "voice_name": args.voice_name,
                "reference_id": args.voice_reference_id,
                "model": args.voice_model,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return results


def estimate_silent_frames(scene: dict) -> int:
    text = str(scene.get("narration") or scene.get("caption") or "")
    readable = re.sub(r"[\s，。！？；：、“”‘’（）()…—,.!?;:'\"-]", "", text)
    seconds = len(readable) / 6.3 + 0.35
    seconds = max(MIN_SCENE_FRAMES / FPS, min(7.0, seconds))
    return math.ceil(seconds * FPS)


def atempo_chain(factor: float) -> str:
    parts: list[str] = []
    while factor > 2.0:
        parts.append("atempo=2.0")
        factor /= 2.0
    if factor > 1.001:
        parts.append(f"atempo={factor:.6f}")
    return ",".join(parts)


def render_silent(
    project: Path,
    scenes: list[dict],
    scene_frames: list[int],
    clips: list[Path],
    output: Path,
    npm: str,
    npx: str,
) -> None:
    renderer = project / ".oneword-renderer"
    shutil.copytree(TEMPLATE_DIR, renderer, dirs_exist_ok=True)
    public_clips = renderer / "public" / "clips"
    public_clips.mkdir(parents=True, exist_ok=True)
    render_scenes = []
    for index, (scene, frames, clip) in enumerate(
        zip(scenes, scene_frames, clips), 1
    ):
        scene_id = safe_scene_id(scene.get("id"), index)
        target = public_clips / f"{scene_id}.mp4"
        shutil.copy2(clip, target)
        render_scenes.append(
            {
                "id": scene_id,
                "caption": scene.get("caption") or scene.get("text"),
                "duration_frames": frames,
                "video": f"clips/{scene_id}.mp4",
            }
        )
    (renderer / "storyboard.json").write_text(
        json.dumps(
            {
                "title": project.name,
                "fps": FPS,
                "width": WIDTH,
                "height": HEIGHT,
                "scenes": render_scenes,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    if not (renderer / "node_modules").is_dir():
        print("Installing isolated Remotion dependencies...")
        run([npm, "install", "--no-audit", "--no-fund"], cwd=renderer)
    output.parent.mkdir(parents=True, exist_ok=True)
    run(
        [
            npx,
            "remotion",
            "render",
            "src/index.ts",
            "HanddrawnStory",
            str(output),
            "--codec=h264",
            "--crf=18",
            "--pixel-format=yuv420p",
            "--muted",
            "--concurrency=1",
        ],
        cwd=renderer,
    )


def mux_voice(
    ffmpeg: str,
    silent: Path,
    audio_paths: list[Path],
    scene_frames: list[int],
    output: Path,
    voice_volume: float,
) -> list[dict]:
    inputs = ["-i", str(silent)]
    filters: list[str] = []
    labels: list[str] = []
    timings: list[dict] = []
    elapsed_frames = 0
    for index, (audio, frames) in enumerate(zip(audio_paths, scene_frames), 1):
        inputs += ["-i", str(audio)]
        duration = wav_duration(audio)
        scene_seconds = frames / FPS
        available = max(0.35, scene_seconds - LEAD_IN - TAIL)
        speedup = max(1.0, duration / available)
        start = elapsed_frames / FPS + LEAD_IN
        chain = ["aresample=48000"]
        tempo = atempo_chain(speedup)
        if tempo:
            chain.append(tempo)
        chain.extend(
            [
                f"volume={voice_volume}",
                f"adelay={int(round(start * 1000))}:all=1",
            ]
        )
        label = f"v{index}"
        filters.append(f"[{index}:a]{','.join(chain)}[{label}]")
        labels.append(f"[{label}]")
        timings.append(
            {
                "id": index,
                "start_s": round(start, 3),
                "source_s": round(duration, 3),
                "speedup": round(speedup, 4),
            }
        )
        if speedup > 1.15:
            print(
                f"Warning: scene {index} narration needs {speedup:.2f}x compression "
                "to preserve the locked picture."
            )
        elapsed_frames += frames
    total = elapsed_frames / FPS
    filters.append(
        f"{''.join(labels)}amix=inputs={len(labels)}:normalize=0:duration=longest,"
        f"apad,atrim=0:{total:.6f}[voice]"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    run(
        [
            ffmpeg,
            "-y",
            "-loglevel",
            "error",
            *inputs,
            "-filter_complex",
            ";".join(filters),
            "-map",
            "0:v:0",
            "-map",
            "[voice]",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            "-t",
            f"{total:.6f}",
            str(output),
        ]
    )
    return timings


def verify_video(ffmpeg: str, path: Path) -> None:
    result = run(
        [ffmpeg, "-v", "warning", "-i", str(path), "-f", "null", "-"],
        capture=True,
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit(f"Final video failed decode verification:\n{result.stderr}")
    if result.stderr.strip():
        print(f"Decode warnings for {path.name}:\n{result.stderr.strip()}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("project")
    parser.add_argument("--mode", choices=("voiced", "silent"), default="voiced")
    parser.add_argument("--voice-name", default=DEFAULT_VOICE_NAME)
    parser.add_argument(
        "--voice-reference-id", default=DEFAULT_VOICE_REFERENCE_ID
    )
    parser.add_argument("--voice-model", default=DEFAULT_VOICE_MODEL)
    parser.add_argument("--voice-speed", type=float, default=1.3)
    parser.add_argument("--temperature", type=float, default=0.55)
    parser.add_argument("--top-p", type=float, default=0.7)
    parser.add_argument("--voice-volume", type=float, default=1.1)
    parser.add_argument("--rebuild-picture", action="store_true")
    parser.add_argument("--regenerate-voice", action="store_true")
    parser.add_argument("--cache-dir")
    parser.add_argument("--no-install-deps", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    project = Path(args.project).expanduser().resolve()
    validate(project)
    storyboard, scenes = load_project(project)
    if args.mode == "voiced" and not find_key():
        raise SystemExit(
            "Fish Audio API key is not configured.\n"
            "Create one at https://fish.audio/zh-CN/app/api-keys/ and run:\n"
            f"python3 {SKILL_DIR / 'scripts' / 'configure_fish.py'}"
        )
    cache_dir = (
        Path(args.cache_dir).expanduser().resolve()
        if args.cache_dir
        else default_cache_dir()
    )
    runtime = ensure_dependencies(cache_dir, install=not args.no_install_deps)
    ffmpeg = runtime["ffmpeg"]

    fingerprint = picture_fingerprint(project, scenes)
    out_dir = project / "out"
    work_dir = project / "work"
    silent_output = out_dir / "picture_silent.mp4"
    voiced_output = out_dir / "picture_voiced.mp4"
    timing_path = out_dir / "timing.json"
    previous: dict[str, Any] = {}
    if timing_path.is_file():
        try:
            previous = json.loads(timing_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            previous = {}

    picture_locked = (
        silent_output.is_file()
        and not args.rebuild_picture
        and previous.get("picture_fingerprint") == fingerprint
        and len(previous.get("scenes") or []) == len(scenes)
    )
    if silent_output.is_file() and not args.rebuild_picture and not picture_locked:
        raise SystemExit(
            "An existing silent master does not match the current storyboard/images. "
            "Use a new project folder or pass --rebuild-picture."
        )

    audio_paths: list[Path] = []
    if args.mode == "voiced":
        audio_paths = generate_voice_files(project, scenes, ffmpeg, args)

    if picture_locked:
        scene_frames = [
            int(scene_timing["duration_frames"])
            for scene_timing in previous["scenes"]
        ]
        print(f"Reusing locked silent master: {silent_output}")
    elif args.mode == "voiced":
        scene_frames = [
            max(
                MIN_SCENE_FRAMES,
                math.ceil((LEAD_IN + wav_duration(path) + TAIL) * FPS),
            )
            for path in audio_paths
        ]
    else:
        scene_frames = [estimate_silent_frames(scene) for scene in scenes]

    if not picture_locked:
        whiteboard_skill, python_path = ensure_whiteboard(cache_dir)
        prepared_dir = work_dir / "prepared"
        raw_dir = work_dir / "raw"
        clips_dir = work_dir / "clips"
        clips: list[Path] = []
        for index, (scene, frames) in enumerate(zip(scenes, scene_frames), 1):
            scene_id = safe_scene_id(scene.get("id"), index)
            source_image = (project / str(scene["image"])).resolve()
            prepared_image = prepared_dir / f"{scene_id}.png"
            print(f"[{index}/{len(scenes)}] Preparing illustration {scene_id}")
            prepare_image(python_path, source_image, prepared_image)
            print(f"[{index}/{len(scenes)}] Running original YangAgent algorithm")
            raw = generate_raw_whiteboard(
                python_path,
                whiteboard_skill,
                prepared_image,
                raw_dir / scene_id,
            )
            clip = clips_dir / f"{scene_id}.mp4"
            retime_whiteboard(ffmpeg, raw, clip, frames)
            clips.append(clip)
        render_silent(
            project,
            scenes,
            scene_frames,
            clips,
            silent_output,
            runtime["npm"],
            runtime["npx"],
        )

    voice_timings: list[dict] = []
    final_output = silent_output
    if args.mode == "voiced":
        voice_timings = mux_voice(
            ffmpeg,
            silent_output,
            audio_paths,
            scene_frames,
            voiced_output,
            args.voice_volume,
        )
        final_output = voiced_output

    scene_report = []
    elapsed_frames = 0
    for index, (scene, frames) in enumerate(zip(scenes, scene_frames), 1):
        scene_report.append(
            {
                "id": safe_scene_id(scene.get("id"), index),
                "start_frame": elapsed_frames,
                "start_s": round(elapsed_frames / FPS, 3),
                "duration_frames": frames,
                "duration_s": round(frames / FPS, 3),
            }
        )
        elapsed_frames += frames
    report = {
        "title": storyboard.get("title") or project.name,
        "mode": args.mode,
        "picture_fingerprint": fingerprint,
        "fps": FPS,
        "width": WIDTH,
        "height": HEIGHT,
        "total_frames": elapsed_frames,
        "total_s": round(elapsed_frames / FPS, 3),
        "silent_master": str(silent_output),
        "voiced_output": str(voiced_output) if args.mode == "voiced" else None,
        "voice": (
            {
                "name": args.voice_name,
                "reference_id": args.voice_reference_id,
                "model": args.voice_model,
                "speed": args.voice_speed,
            }
            if args.mode == "voiced"
            else None
        ),
        "scenes": scene_report,
        "voice_timings": voice_timings,
        "yangagent": {
            "repository": WHITEBOARD_REPO,
            "commit": WHITEBOARD_COMMIT,
        },
    }
    timing_path.parent.mkdir(parents=True, exist_ok=True)
    timing_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    verify_video(ffmpeg, final_output)
    print(f"SILENT_MASTER={silent_output}")
    if args.mode == "voiced":
        print(f"VOICED_OUTPUT={voiced_output}")
        print(f"VOICE={args.voice_name}")
    print(f"DURATION={elapsed_frames / FPS:.3f}s")
    print(f"FINAL={final_output}")


if __name__ == "__main__":
    main()
