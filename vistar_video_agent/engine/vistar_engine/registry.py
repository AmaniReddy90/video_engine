from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import requests

from vistar_engine.settings import get_engine_paths


@dataclass
class ModelRegistry:
    mode: str = "procedural"
    vault_dir: str | None = None
    comfyui: dict[str, Any] = field(default_factory=lambda: {"url": "http://127.0.0.1:8188"})
    sd: dict[str, Any] = field(default_factory=dict)
    animatediff: dict[str, Any] = field(default_factory=dict)
    tts: dict[str, Any] = field(default_factory=dict)
    music: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "vault_dir": self.vault_dir,
            "comfyui": self.comfyui,
            "sd": self.sd,
            "animatediff": self.animatediff,
            "tts": self.tts,
            "music": self.music,
        }


class RegistryStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> ModelRegistry:
        if not self.path.exists():
            registry = ModelRegistry()
            self.save(registry)
            return registry
        data = json.loads(self.path.read_text(encoding="utf-8"))
        return ModelRegistry(**data)

    def save(self, registry: ModelRegistry) -> None:
        self.path.write_text(json.dumps(registry.to_dict(), indent=2), encoding="utf-8")


def validate_registry(registry: ModelRegistry) -> list[str]:
    errors: list[str] = []
    for key in ("animatediff", "tts", "music"):
        model_path = registry.to_dict().get(key, {}).get("model_path")
        if model_path and not Path(model_path).exists():
            errors.append(f"{key}.model_path not found: {model_path}")
    tts_binary = registry.to_dict().get("tts", {}).get("binary_path")
    if tts_binary and not Path(tts_binary).exists():
        errors.append(f"tts.binary_path not found: {tts_binary}")
    music_track = registry.to_dict().get("music", {}).get("track_path")
    if music_track and not Path(music_track).exists():
        errors.append(f"music.track_path not found: {music_track}")
    workflow_path = registry.to_dict().get("animatediff", {}).get("workflow_path")
    if workflow_path and not Path(workflow_path).exists():
        errors.append(f"animatediff.workflow_path not found: {workflow_path}")
    if registry.mode == "comfyui":
        url = registry.comfyui.get("url")
        if url:
            try:
                response = requests.get(f"{url}/system_stats", timeout=2)
                if response.status_code >= 400:
                    errors.append("ComfyUI reachable but returned error")
            except requests.RequestException:
                errors.append("ComfyUI not reachable")
    return errors


def get_registry_store() -> RegistryStore:
    paths = get_engine_paths()
    return RegistryStore(paths.registry_path)
