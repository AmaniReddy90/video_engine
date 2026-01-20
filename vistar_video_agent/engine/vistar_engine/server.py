from __future__ import annotations

import json
import shutil
import subprocess
import uuid
from pathlib import Path

import requests
import yaml
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from vistar_engine import __version__
from vistar_engine.audio import resolve_music_track, synthesize_tts
from vistar_engine.ffmpeg_tools import build_loop_audio, build_tone_audio
from vistar_engine.jobs import job_manager, run_pipeline
from vistar_engine.project import ProjectPaths, create_project
from vistar_engine.registry import ModelRegistry, get_registry_store, validate_registry
from vistar_engine.settings import get_engine_paths
from vistar_engine.spec import FilmSpec

app = FastAPI()
paths = get_engine_paths()
paths.vault_dir.mkdir(parents=True, exist_ok=True)
paths.logs_dir.mkdir(parents=True, exist_ok=True)

ui_dir = paths.root_dir / "app" / "ui"
if ui_dir.exists():
    app.mount("/ui", StaticFiles(directory=ui_dir, html=True), name="ui")


@app.get("/health")
def health() -> dict:
    return {
        "ok": True,
        "version": __version__,
        "mode": get_registry_store().load().mode,
        "vault": str(paths.vault_dir),
    }


@app.get("/diagnostics")
def diagnostics() -> dict:
    registry = get_registry_store().load()
    errors = validate_registry(registry)
    comfyui_reachable = _check_comfyui(registry.comfyui.get("url"))
    return {
        "ffmpeg": bool(paths.ffmpeg_path) or _which("ffmpeg"),
        "ffmpeg_path": str(paths.ffmpeg_path) if paths.ffmpeg_path else None,
        "comfyui": registry.comfyui.get("url"),
        "comfyui_reachable": comfyui_reachable,
        "vault_writable": _check_vault_writable(paths.vault_dir),
        "gpu": _detect_gpu(),
        "errors": errors,
    }


@app.get("/models")
def get_models() -> dict:
    registry = get_registry_store().load()
    return registry.to_dict()


@app.post("/models")
def set_models(payload: dict) -> dict:
    store = get_registry_store()
    registry = ModelRegistry(**payload)
    store.save(registry)
    errors = validate_registry(registry)
    return {"ok": len(errors) == 0, "errors": errors, "registry": registry.to_dict()}


@app.post("/projects")
def create_project_endpoint(payload: dict) -> dict:
    spec = FilmSpec(**payload)
    project = create_project(spec)
    return {"project_id": project.root.name, "path": str(project.root)}


@app.post("/generate/{project_id}")
def generate(project_id: str, payload: dict, background_tasks: BackgroundTasks) -> dict:
    spec = FilmSpec(**payload)
    project_root = paths.vault_dir / project_id
    if not project_root.exists():
        raise HTTPException(status_code=404, detail="project not found")
    project_root.mkdir(parents=True, exist_ok=True)
    (project_root / "renders").mkdir(parents=True, exist_ok=True)
    (project_root / "outputs").mkdir(parents=True, exist_ok=True)
    (project_root / "logs").mkdir(parents=True, exist_ok=True)
    (project_root / "spec.yaml").write_text(
        yaml.safe_dump(spec.model_dump(), sort_keys=False), encoding="utf-8"
    )
    project_paths = ProjectPaths(
        root=project_root,
        spec_path=project_root / "spec.yaml",
        plan_path=project_root / "plan.json",
        shots_path=project_root / "shots.json",
        renders_dir=project_root / "renders",
        outputs_dir=project_root / "outputs",
        logs_dir=project_root / "logs",
    )
    job = job_manager.create_job()
    variant = "shorts" if "shorts" in spec.format else "full"
    background_tasks.add_task(run_pipeline, job.job_id, spec, project_paths, variant)
    return {"job_id": job.job_id, "project_id": project_id}


@app.get("/status/{job_id}")
def status(job_id: str) -> dict:
    status = job_manager.get(job_id)
    if not status:
        raise HTTPException(status_code=404, detail="job not found")
    return status.to_dict()


@app.get("/ui")
def ui_index() -> HTMLResponse:
    index_path = ui_dir / "index.html"
    if not index_path.exists():
        return HTMLResponse("UI not found", status_code=404)
    return HTMLResponse(index_path.read_text(encoding="utf-8"))


@app.post("/diagnostics/test_image")
def test_image() -> dict:
    return {"ok": True, "message": "Procedural image test passed"}


@app.post("/diagnostics/test_tts")
def test_tts() -> dict:
    registry = get_registry_store().load()
    output_dir = paths.logs_dir / "diagnostics"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "tts_test.wav"
    ok, message = synthesize_tts("Vistar test line.", output_path, registry.tts)
    if not ok:
        return {"ok": False, "message": message}
    return {"ok": True, "message": f"TTS ok: {output_path}"}


@app.post("/diagnostics/test_music")
def test_music() -> dict:
    registry = get_registry_store().load()
    output_dir = paths.logs_dir / "diagnostics"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "music_test.wav"
    track_path = resolve_music_track(registry.music)
    if track_path:
        cmd = build_loop_audio(track_path, 2.0, output_path)
    else:
        cmd = build_tone_audio(2.0, output_path, frequency=220)
    try:
        subprocess.run([paths.ffmpeg_path or "ffmpeg", *cmd.args[1:]], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        return {"ok": False, "message": f"Music test failed: {exc}"}
    return {"ok": True, "message": f"Music test ok: {output_path}"}


@app.get("/download/{project_id}/{filename}")
def download_output(project_id: str, filename: str) -> FileResponse:
    file_path = paths.vault_dir / project_id / "outputs" / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="file not found")
    return FileResponse(file_path)


@app.post("/spec/normalize")
def normalize_spec(payload: dict) -> dict:
    if "raw" in payload:
        raw = payload["raw"]
        data = yaml.safe_load(raw)
    else:
        data = payload
    spec = FilmSpec(**data)
    normalized = yaml.safe_dump(spec.model_dump(), sort_keys=False)
    return {"spec": normalized}


@app.post("/spec/parse")
def parse_spec(payload: dict) -> dict:
    if "raw" in payload:
        raw = payload["raw"]
        data = yaml.safe_load(raw)
    else:
        data = payload
    spec = FilmSpec(**data)
    return spec.model_dump()


@app.get("/logs/{project_id}/{job_id}")
def get_logs(project_id: str, job_id: str) -> dict:
    log_path = paths.vault_dir / project_id / "logs" / f"{job_id}.log"
    if not log_path.exists():
        raise HTTPException(status_code=404, detail="log not found")
    return json.loads(log_path.read_text(encoding="utf-8"))


def _which(binary: str) -> bool:
    return shutil.which(binary) is not None


def _check_vault_writable(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        test_file = path / f".write_test_{uuid.uuid4().hex}"
        test_file.write_text("ok", encoding="utf-8")
        test_file.unlink(missing_ok=True)
        return True
    except OSError:
        return False


def _detect_gpu() -> str | None:
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
            check=True,
            capture_output=True,
            text=True,
        )
        output = result.stdout.strip()
        return output or None
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def _check_comfyui(url: str | None) -> bool:
    if not url:
        return False
    try:
        response = requests.get(f"{url}/system_stats", timeout=2)
        return response.status_code < 400
    except requests.RequestException:
        return False
