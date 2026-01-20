from __future__ import annotations

import subprocess
from pathlib import Path


SUPPORTED_AUDIO_EXTS = {".wav", ".mp3", ".flac", ".ogg", ".m4a"}


def resolve_tts_engine(tts_config: dict | None) -> str:
    if not tts_config:
        return "piper"
    return tts_config.get("engine") or "piper"


def synthesize_tts(text: str, output_path: Path, tts_config: dict | None) -> tuple[bool, str]:
    if not tts_config:
        return False, "TTS not configured"
    model_path = tts_config.get("model_path")
    if not model_path:
        return False, "TTS model_path not set"
    engine = resolve_tts_engine(tts_config)
    if engine != "piper":
        return False, f"Unsupported TTS engine: {engine}"
    binary = tts_config.get("binary_path") or "piper"
    cmd = [binary, "--model", model_path, "--output_file", str(output_path), "--text", text]
    speaker = tts_config.get("speaker")
    if speaker is not None:
        cmd.extend(["--speaker", str(speaker)])
    try:
        subprocess.run(cmd, check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        return False, f"TTS failed: {exc}"
    return True, "TTS ok"


def resolve_music_track(music_config: dict | None) -> Path | None:
    if not music_config:
        return None
    track_path = music_config.get("track_path") or music_config.get("model_path")
    if not track_path:
        return None
    candidate = Path(track_path)
    if candidate.exists() and candidate.suffix.lower() in SUPPORTED_AUDIO_EXTS:
        return candidate
    return None
