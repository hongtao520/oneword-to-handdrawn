#!/usr/bin/env python3
"""Check or privately install the external runtime used by this skill."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
import zipfile
from pathlib import Path
from typing import Any


MIN_NODE_MAJOR = 20
IMAGEIO_FFMPEG_SPEC = "imageio-ffmpeg>=0.5,<0.7"
NODE_INDEX = "https://nodejs.org/dist/index.json"


def run(
    command: list[str],
    *,
    capture: bool = False,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        text=True,
        capture_output=capture,
        check=check,
    )


def default_cache_dir() -> Path:
    configured = os.environ.get("ONEWORD_HANDDRAWN_CACHE")
    if configured:
        return Path(configured).expanduser().resolve()
    return (Path.home() / ".cache" / "oneword-to-handdrawn").resolve()


def node_major(node: str) -> int | None:
    result = run([node, "--version"], capture=True, check=False)
    if result.returncode != 0:
        return None
    value = result.stdout.strip().lstrip("v").split(".", 1)[0]
    return int(value) if value.isdigit() else None


def system_node() -> tuple[str, str, str] | None:
    node = shutil.which("node")
    npm = shutil.which("npm")
    npx = shutil.which("npx")
    if node and npm and npx and (node_major(node) or 0) >= MIN_NODE_MAJOR:
        return node, npm, npx
    return None


def platform_node_target() -> tuple[str, str, str]:
    system = platform.system().lower()
    machine = platform.machine().lower()
    if system == "darwin":
        os_name = "darwin"
        archive = "tar.gz"
    elif system == "linux":
        os_name = "linux"
        archive = "tar.gz"
    elif system == "windows":
        os_name = "win"
        archive = "zip"
    else:
        raise SystemExit(f"Unsupported operating system for private Node install: {system}")

    if machine in {"arm64", "aarch64"}:
        arch = "arm64"
    elif machine in {"x86_64", "amd64"}:
        arch = "x64"
    else:
        raise SystemExit(f"Unsupported CPU for private Node install: {machine}")
    return os_name, arch, archive


def download(url: str, destination: Path) -> None:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "oneword-to-handdrawn dependency installer"},
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        with destination.open("wb") as stream:
            shutil.copyfileobj(response, stream)


def verify_node_archive(version: str, archive: Path, filename: str) -> None:
    checksums_url = f"https://nodejs.org/dist/{version}/SHASUMS256.txt"
    request = urllib.request.Request(
        checksums_url,
        headers={"User-Agent": "oneword-to-handdrawn dependency installer"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        checksums = response.read().decode("utf-8")
    expected = None
    for line in checksums.splitlines():
        digest, _, name = line.partition("  ")
        if name.strip() == filename:
            expected = digest.strip()
            break
    if not expected:
        raise SystemExit(f"Node.js checksum not found for {filename}.")
    actual = hashlib.sha256(archive.read_bytes()).hexdigest()
    if actual != expected:
        raise SystemExit(f"Node.js checksum verification failed for {filename}.")


def latest_lts_node() -> str:
    request = urllib.request.Request(
        NODE_INDEX,
        headers={"User-Agent": "oneword-to-handdrawn dependency installer"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        releases: list[dict[str, Any]] = json.load(response)
    for release in releases:
        version = str(release.get("version", ""))
        major = version.lstrip("v").split(".", 1)[0]
        if release.get("lts") and major.isdigit() and int(major) >= MIN_NODE_MAJOR:
            return version
    raise SystemExit("Unable to find a supported Node.js LTS release.")


def safe_extract_tar(archive: Path, destination: Path) -> None:
    destination_root = destination.resolve()
    with tarfile.open(archive, "r:gz") as bundle:
        for member in bundle.getmembers():
            target = (destination / member.name).resolve()
            if destination_root not in target.parents and target != destination_root:
                raise SystemExit("Unsafe path found in Node.js archive.")
        bundle.extractall(destination)


def safe_extract_zip(archive: Path, destination: Path) -> None:
    destination_root = destination.resolve()
    with zipfile.ZipFile(archive) as bundle:
        for name in bundle.namelist():
            target = (destination / name).resolve()
            if destination_root not in target.parents and target != destination_root:
                raise SystemExit("Unsafe path found in Node.js archive.")
        bundle.extractall(destination)


def private_node(cache_dir: Path, install: bool) -> tuple[str, str, str] | None:
    runtime_dir = cache_dir / "runtime" / "node"
    manifest_path = runtime_dir / "runtime.json"
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            root = runtime_dir / str(manifest["directory"])
            bin_dir = root if platform.system() == "Windows" else root / "bin"
            node_name = "node.exe" if platform.system() == "Windows" else "node"
            npm_name = "npm.cmd" if platform.system() == "Windows" else "npm"
            npx_name = "npx.cmd" if platform.system() == "Windows" else "npx"
            paths = (bin_dir / node_name, bin_dir / npm_name, bin_dir / npx_name)
            if all(path.is_file() for path in paths):
                os.environ["PATH"] = str(bin_dir) + os.pathsep + os.environ.get("PATH", "")
                return tuple(str(path) for path in paths)  # type: ignore[return-value]
        except (KeyError, json.JSONDecodeError):
            pass
    if not install:
        return None

    version = latest_lts_node()
    os_name, arch, extension = platform_node_target()
    directory = f"node-{version}-{os_name}-{arch}"
    filename = f"{directory}.{extension}"
    url = f"https://nodejs.org/dist/{version}/{filename}"
    print(f"Installing private Node.js {version} from nodejs.org...")
    runtime_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=runtime_dir) as temporary:
        temp_dir = Path(temporary)
        archive = temp_dir / f"node.{extension}"
        download(url, archive)
        verify_node_archive(version, archive, filename)
        if extension == "zip":
            safe_extract_zip(archive, temp_dir)
        else:
            safe_extract_tar(archive, temp_dir)
        extracted = temp_dir / directory
        if not extracted.is_dir():
            raise SystemExit("Downloaded Node.js archive has an unexpected layout.")
        target = runtime_dir / directory
        if target.exists():
            shutil.rmtree(target)
        shutil.move(str(extracted), str(target))
    manifest_path.write_text(
        json.dumps({"version": version, "directory": directory}, indent=2) + "\n",
        encoding="utf-8",
    )
    return private_node(cache_dir, install=False)


def system_ffmpeg() -> str | None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return None
    result = run([ffmpeg, "-version"], capture=True, check=False)
    return ffmpeg if result.returncode == 0 else None


def private_ffmpeg(cache_dir: Path, install: bool) -> str | None:
    packages_dir = cache_dir / "runtime" / "python-packages"
    probe = (
        "import sys;"
        f"sys.path.insert(0,{str(packages_dir)!r});"
        "import imageio_ffmpeg;"
        "print(imageio_ffmpeg.get_ffmpeg_exe())"
    )
    result = run([sys.executable, "-c", probe], capture=True, check=False)
    if result.returncode == 0:
        executable = result.stdout.strip().splitlines()[-1]
        if executable and Path(executable).is_file():
            return executable
    if not install:
        return None

    print("Installing a private FFmpeg runtime...")
    packages_dir.mkdir(parents=True, exist_ok=True)
    run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--no-input",
            "--quiet",
            "--upgrade",
            "--target",
            str(packages_dir),
            IMAGEIO_FFMPEG_SPEC,
        ]
    )
    return private_ffmpeg(cache_dir, install=False)


def ensure_dependencies(cache_dir: Path, *, install: bool) -> dict[str, str]:
    if sys.version_info < (3, 9):
        raise SystemExit("Python 3.9 or newer is required.")
    cache_dir.mkdir(parents=True, exist_ok=True)

    node_tools = system_node() or private_node(cache_dir, install)
    ffmpeg = system_ffmpeg() or private_ffmpeg(cache_dir, install)
    missing = []
    if not node_tools:
        missing.append("Node.js 20+ with npm/npx")
    if not ffmpeg:
        missing.append("FFmpeg")
    if missing:
        raise SystemExit(
            "Missing dependencies: "
            + ", ".join(missing)
            + ". Run setup_dependencies.py --install."
        )

    node, npm, npx = node_tools
    return {
        "python": sys.executable,
        "node": node,
        "npm": npm,
        "npx": npx,
        "ffmpeg": ffmpeg,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--install", action="store_true")
    parser.add_argument("--cache-dir")
    args = parser.parse_args()
    cache_dir = (
        Path(args.cache_dir).expanduser().resolve()
        if args.cache_dir
        else default_cache_dir()
    )
    runtime = ensure_dependencies(cache_dir, install=args.install)
    print("Dependencies ready:")
    for name, path in runtime.items():
        print(f"  {name}: {path}")


if __name__ == "__main__":
    main()
