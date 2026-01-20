from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from pathlib import Path

import yaml

from vistar_engine.settings import get_engine_paths
from vistar_engine.spec import FilmSpec, clamp_targets


@dataclass
class ProjectPaths:
    root: Path
    spec_path: Path
    plan_path: Path
    shots_path: Path
    renders_dir: Path
    outputs_dir: Path
    logs_dir: Path


def create_project(spec: FilmSpec) -> ProjectPaths:
    paths = get_engine_paths()
    project_id = uuid.uuid4().hex[:8]
    project_name = f"{spec.title.replace(' ', '_')}_{project_id}"
    project_root = paths.vault_dir / project_name
    renders_dir = project_root / "renders"
    (renders_dir / "images").mkdir(parents=True, exist_ok=True)
    (renders_dir / "video").mkdir(parents=True, exist_ok=True)
    (renders_dir / "audio").mkdir(parents=True, exist_ok=True)
    outputs_dir = project_root / "outputs"
    logs_dir = project_root / "logs"
    project_root.mkdir(parents=True, exist_ok=True)
    renders_dir.mkdir(parents=True, exist_ok=True)
    outputs_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    clamp_targets(spec.targets)
    spec_path = project_root / "spec.yaml"
    spec_path.write_text(yaml.safe_dump(spec.model_dump(), sort_keys=False), encoding="utf-8")
    plan_path = project_root / "plan.json"
    shots_path = project_root / "shots.json"
    return ProjectPaths(
        root=project_root,
        spec_path=spec_path,
        plan_path=plan_path,
        shots_path=shots_path,
        renders_dir=renders_dir,
        outputs_dir=outputs_dir,
        logs_dir=logs_dir,
    )


def write_plan(paths: ProjectPaths, plan: dict) -> None:
    paths.plan_path.write_text(json.dumps(plan, indent=2), encoding="utf-8")


def write_shots(paths: ProjectPaths, shots: list[dict]) -> None:
    paths.shots_path.write_text(json.dumps(shots, indent=2), encoding="utf-8")
