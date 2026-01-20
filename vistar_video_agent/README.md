# Vistar Video Agent

Offline-first Windows desktop video generator using a local FastAPI engine and Tauri UI.

## Quick Start (Engine)

```bash
cd vistar_video_agent/engine
python -m vistar_engine
```

Open the UI in a browser:

```
http://127.0.0.1:8765/ui
```

## API Highlights

- `GET /health`
- `GET /models`
- `POST /models`
- `POST /projects`
- `POST /generate/{project_id}`
- `GET /status/{job_id}`

## Vault Layout

Projects are stored under `vistar_video_agent/vault/<project_name>_<project_id>` with `spec.yaml`, `plan.json`, `shots.json`, `renders/`, `outputs/`, and `logs/`.

## Build Scripts

- `scripts/build_engine.ps1` - build the Python engine executable via PyInstaller.
- `scripts/build_tauri.ps1` - build the Tauri shell.
- `scripts/build_portable_exe.ps1` - build full portable bundle.
- `scripts/doctor.ps1` - check for Rust/Node/MSVC/Python prerequisites.

## Notes

- The engine defaults to procedural rendering if ComfyUI is unavailable.
- Model paths are validated and errors are shown in the UI.
- Generation currently supports dual outputs (shorts/full) with procedural subtitles, optional Piper-based TTS (when configured), a low-bed music tone or looping local audio track (auto-converted to WAV if needed), basic procedural SFX tones per shot tags, optional ComfyUI image rendering, and optional AnimateDiff video clips when a workflow path is provided.

## Film Spec Input Tips

- Provide `version`, `title`, `targets`, and at least one scene with beats or dialogue.
- Use `format` to select shorts/full outputs; durations will clamp to valid ranges.
- Audio toggles live under `audio.voice.enabled`, `audio.music.enabled`, and `audio.sfx.enabled`.

## Sample Spec Snippet

```yaml
version: "1.0"
title: "Discovery"
format: ["shorts", "full"]
targets:
  shorts:
    duration_sec: 30
    aspect: "9:16"
    resolution: "1080x1920"
  full:
    duration_sec: 120
    aspect: "16:9"
    resolution: "1920x1080"
scenes:
  - id: "S1"
    summary: "A quiet ruin at dusk."
    beats:
      - "Wide establishing: crumbling arches."
      - "Close-up: glowing artifact pulses."
```

## Model Format Notes

- Music tracks accept `wav`, `mp3`, `flac`, `ogg`, or `m4a` and are auto-converted to WAV.
- Music model paths can point at `gguf`, `pt`, or `safetensors` files for future backend use.
