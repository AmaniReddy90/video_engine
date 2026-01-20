from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field, field_validator, model_validator


class TargetSpec(BaseModel):
    duration_sec: int
    aspect: str
    resolution: str

    @field_validator("duration_sec")
    @classmethod
    def duration_positive(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("duration_sec must be positive")
        return value


class StyleSpec(BaseModel):
    look: str = "cinematic, filmic lighting, shallow depth of field"
    mode: str = "cinematic_3d"
    negatives: str = "blurry, jitter, watermark, lowres"
    palette: str = "teal-orange"
    pacing: Literal["fast", "medium", "slow"] = "medium"


class VoiceSpec(BaseModel):
    enabled: bool = True
    style: str = "warm narrator"
    language: str = "en"


class MusicSpec(BaseModel):
    enabled: bool = True
    genre: str = "epic orchestral"
    bpm: int = 120


class SfxSpec(BaseModel):
    enabled: bool = True


class AudioSpec(BaseModel):
    voice: VoiceSpec = Field(default_factory=VoiceSpec)
    music: MusicSpec = Field(default_factory=MusicSpec)
    sfx: SfxSpec = Field(default_factory=SfxSpec)


class CharacterSpec(BaseModel):
    id: str
    description: str
    voice_id: str | None = None


class DialogueLine(BaseModel):
    character: str
    line: str
    emotion: str | None = None


class SceneSpec(BaseModel):
    id: str
    summary: str
    beats: list[str] = Field(default_factory=list)
    dialogue: list[DialogueLine] = Field(default_factory=list)
    camera: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def ensure_content(self) -> "SceneSpec":
        if not self.beats and not self.dialogue:
            raise ValueError("Each scene must have beats or dialogue")
        return self


class TargetsSpec(BaseModel):
    shorts: TargetSpec | None = None
    full: TargetSpec | None = None


class FilmSpec(BaseModel):
    version: str
    title: str
    format: list[Literal["shorts", "full"]] = Field(default_factory=lambda: ["shorts", "full"])
    targets: TargetsSpec
    style: StyleSpec = Field(default_factory=StyleSpec)
    audio: AudioSpec = Field(default_factory=AudioSpec)
    characters: list[CharacterSpec] = Field(default_factory=list)
    scenes: list[SceneSpec]

    @field_validator("version")
    @classmethod
    def version_required(cls, value: str) -> str:
        if not value:
            raise ValueError("version required")
        return value

    @field_validator("title")
    @classmethod
    def title_required(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("title required")
        return value

    @model_validator(mode="after")
    def ensure_scenes(self) -> "FilmSpec":
        if not self.scenes:
            raise ValueError("scenes required")
        return self


def clamp_targets(targets: TargetsSpec) -> TargetsSpec:
    if targets.shorts:
        targets.shorts.duration_sec = max(15, min(60, targets.shorts.duration_sec))
    if targets.full:
        targets.full.duration_sec = max(60, min(3600, targets.full.duration_sec))
    return targets
