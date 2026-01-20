from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class EnginePaths:
    root_dir: Path
    vault_dir: Path
    templates_dir: Path
    registry_path: Path
    logs_dir: Path
    resources_dir: Path
    ffmpeg_path: Path | None


def get_engine_paths() -> EnginePaths:
    root_dir = Path(__file__).resolve().parents[2]
    vault_dir = root_dir / "vault"
    templates_dir = root_dir / "engine" / "templates"
    registry_path = root_dir / "engine" / "registry.json"
    logs_dir = root_dir / "engine" / "logs"
    resources_dir = root_dir / "resources"
    ffmpeg_path = None
    candidate = resources_dir / "ffmpeg" / "ffmpeg.exe"
    if candidate.exists():
        ffmpeg_path = candidate
    return EnginePaths(
        root_dir=root_dir,
        vault_dir=vault_dir,
        templates_dir=templates_dir,
        registry_path=registry_path,
        logs_dir=logs_dir,
        resources_dir=resources_dir,
        ffmpeg_path=ffmpeg_path,
    )
