from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from vistar_engine.planner import plan_shots, shots_to_dict
from vistar_engine.project import ProjectPaths, write_plan, write_shots
from vistar_engine.registry import get_registry_store
from vistar_engine.render import render_comfyui_images, render_comfyui_videos, render_procedural_video
from vistar_engine.settings import get_engine_paths
from vistar_engine.spec import FilmSpec


@dataclass
class JobStatus:
    job_id: str
    state: str
    progress: float
    message: str
    warnings: list[str] = field(default_factory=list)
    logs: list[str] = field(default_factory=list)
    outputs: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "job_id": self.job_id,
            "state": self.state,
            "progress": self.progress,
            "message": self.message,
            "warnings": self.warnings,
            "logs": self.logs,
            "outputs": self.outputs,
        }


class JobManager:
    def __init__(self) -> None:
        self._jobs: dict[str, JobStatus] = {}
        self._lock = threading.Lock()

    def create_job(self) -> JobStatus:
        job_id = f"job_{int(time.time())}_{len(self._jobs) + 1}"
        status = JobStatus(job_id=job_id, state="queued", progress=0.0, message="Queued")
        with self._lock:
            self._jobs[job_id] = status
        return status

    def update(self, job_id: str, **kwargs) -> None:
        with self._lock:
            status = self._jobs[job_id]
            for key, value in kwargs.items():
                setattr(status, key, value)

    def log(self, job_id: str, message: str) -> None:
        with self._lock:
            self._jobs[job_id].logs.append(message)

    def get(self, job_id: str) -> JobStatus | None:
        with self._lock:
            return self._jobs.get(job_id)

    def run_async(self, job_id: str, func: Callable[[], None]) -> None:
        thread = threading.Thread(target=func, daemon=True)
        thread.start()


job_manager = JobManager()


def run_pipeline(job_id: str, spec: FilmSpec, project: ProjectPaths, variant: str) -> None:
    job_manager.update(job_id, state="running", progress=0.05, message="Planning shots")
    plan_data: dict[str, dict] = {"variants": {}}
    paths = get_engine_paths()
    ffmpeg_path = paths.ffmpeg_path
    registry = get_registry_store().load()
    warnings: list[str] = []
    outputs: dict[str, str] = {}

    variants = [variant]
    if len(spec.format) > 1:
        variants = spec.format

    shots_payload: dict[str, list[dict]] = {}
    for idx, target_variant in enumerate(variants, start=1):
        shots = plan_shots(spec, spec.targets, target_variant)
        plan_data["variants"][target_variant] = {"shots": len(shots)}
        shots_payload[target_variant] = shots_to_dict(shots)
        job_manager.log(job_id, f"Planned {len(shots)} shots for {target_variant}.")

        progress = 0.2 + (idx - 1) * (0.7 / max(1, len(variants)))
        job_manager.update(job_id, progress=progress, message=f"Rendering {target_variant} shots")
        image_overrides = None
        clip_overrides = None
        if registry.mode == "comfyui":
            comfyui_url = registry.comfyui.get("url", "")
            checkpoint = registry.sd.get("checkpoint", "")
            if comfyui_url:
                workflow_path = registry.animatediff.get("workflow_path")
                if not workflow_path:
                    workflow_path = str(paths.templates_dir / "workflows" / "animatediff_video.json")
                if workflow_path and Path(workflow_path).exists():
                    videos, comfyui_warnings = render_comfyui_videos(
                        shots,
                        project.renders_dir / target_variant / "video",
                        Path(workflow_path),
                        comfyui_url,
                        checkpoint,
                    )
                    warnings.extend(comfyui_warnings)
                    for warning in comfyui_warnings:
                        job_manager.log(job_id, warning)
                    if videos:
                        clip_overrides = videos
                elif workflow_path:
                    warning = f"AnimateDiff workflow not found: {workflow_path}"
                    warnings.append(warning)
                    job_manager.log(job_id, warning)
                if not clip_overrides:
                    images, comfyui_warnings = render_comfyui_images(
                        shots,
                        project.renders_dir / target_variant / "images",
                        paths.templates_dir,
                        comfyui_url,
                        checkpoint,
                    )
                    warnings.extend(comfyui_warnings)
                    for warning in comfyui_warnings:
                        job_manager.log(job_id, warning)
                    if images:
                        image_overrides = images
        render_result = render_procedural_video(
            shots,
            project.renders_dir / target_variant,
            ffmpeg_path=str(ffmpeg_path) if ffmpeg_path else None,
            image_overrides=image_overrides,
            clip_overrides=clip_overrides,
            tts_config=registry.tts,
            music_config=registry.music,
            voice_enabled=spec.audio.voice.enabled,
            music_enabled=spec.audio.music.enabled,
            sfx_enabled=spec.audio.sfx.enabled,
        )
        warnings.extend(render_result.warnings)
        for warning in render_result.warnings:
            job_manager.log(job_id, warning)

        job_manager.update(job_id, message=f"Stitching {target_variant} output")
        output_path = project.outputs_dir / f"{target_variant}.mp4"
        if render_result.output_path.exists():
            output_path.write_bytes(render_result.output_path.read_bytes())
        else:
            output_path.write_text("render failed", encoding="utf-8")
        outputs[target_variant] = f"/download/{project.root.name}/{target_variant}.mp4"
        job_manager.log(job_id, f"Output ready at {output_path}")
        job_manager.update(job_id, message=f"Exported {target_variant} output")

    write_plan(project, plan_data)
    write_shots(project, shots_payload)

    job_manager.update(
        job_id, progress=1.0, state="completed", message="Completed", warnings=warnings, outputs=outputs
    )

    log_path = project.logs_dir / f"{job_id}.log"
    log_path.write_text(json.dumps(job_manager.get(job_id).to_dict(), indent=2), encoding="utf-8")
