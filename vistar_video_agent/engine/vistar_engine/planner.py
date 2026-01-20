from __future__ import annotations

import random
from dataclasses import dataclass

from vistar_engine.spec import FilmSpec, SceneSpec, TargetsSpec


@dataclass
class PlannedShot:
    shot_id: str
    scene_id: str
    type: str
    duration_sec: float
    prompt: str
    negative_prompt: str
    camera: str
    seed: int
    aspect: str
    resolution: str
    audio: dict


SHOT_TYPES = ["establishing", "closeup", "action", "dialogue"]
CAMERA_DEFAULTS = ["slow dolly in", "wide pan", "handheld", "rack focus"]


def _build_prompt(spec: FilmSpec, scene: SceneSpec, beat: str, camera: str, characters: str) -> str:
    return (
        f"{spec.style.look}. {spec.style.palette} palette. "
        f"Scene: {scene.summary}. Beat: {beat}. Camera: {camera}. "
        f"Characters: {characters}"
    )


def _character_descriptor(spec: FilmSpec) -> str:
    if not spec.characters:
        return "narration only"
    return ", ".join(f"{c.id}: {c.description}" for c in spec.characters)


def plan_shots(spec: FilmSpec, targets: TargetsSpec, variant: str) -> list[PlannedShot]:
    target = getattr(targets, variant)
    if target is None:
        return []

    beats: list[tuple[SceneSpec, str, bool]] = []
    for scene in spec.scenes:
        for beat in scene.beats:
            beats.append((scene, beat, False))
        for dialogue in scene.dialogue:
            beats.append((scene, dialogue.line, True))

    if not beats:
        return []

    per_shot = max(1, len(beats))
    duration = target.duration_sec / per_shot
    duration = max(1.0, round(duration, 2))

    planned: list[PlannedShot] = []
    camera_idx = 0
    character_desc = _character_descriptor(spec)
    for idx, (scene, beat, is_dialogue) in enumerate(beats, start=1):
        shot_type = SHOT_TYPES[idx % len(SHOT_TYPES)]
        camera = scene.camera[idx % len(scene.camera)] if scene.camera else CAMERA_DEFAULTS[camera_idx % len(CAMERA_DEFAULTS)]
        camera_idx += 1
        seed = random.randint(1000, 99999)
        prompt = _build_prompt(spec, scene, beat, camera, character_desc)
        planned.append(
            PlannedShot(
                shot_id=f"{scene.id}_{idx:04d}",
                scene_id=scene.id,
                type=shot_type,
                duration_sec=duration,
                prompt=prompt,
                negative_prompt=spec.style.negatives,
                camera=camera,
                seed=seed,
                aspect=target.aspect,
                resolution=target.resolution,
                audio={
                    "dialogue_line": beat if is_dialogue else "",
                    "voice_id": None,
                    "sfx_tags": ["wind", "dust"],
                },
            )
        )
    return planned


def shots_to_dict(shots: list[PlannedShot]) -> list[dict]:
    return [shot.__dict__ for shot in shots]
