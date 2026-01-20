from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from vistar_engine.audio import resolve_music_track, synthesize_tts
from vistar_engine.comfyui import download_view, load_workflow, submit_prompt, wait_for_completion
from vistar_engine.ffmpeg_tools import (
    build_burn_subtitles,
    build_concat_audio,
    build_concat_file,
    build_concat_video,
    build_convert_audio,
    build_fit_audio,
    build_image_clip,
    build_loop_audio,
    build_mix_audio,
    build_mux_audio,
    build_silence_audio,
    build_tone_audio,
)
from vistar_engine.planner import PlannedShot


@dataclass
class RenderResult:
    output_path: Path
    warnings: list[str]


def _ensure_font() -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        return ImageFont.truetype("arial.ttf", 24)
    except OSError:
        return ImageFont.load_default()


def render_shot_image(shot: PlannedShot, output_dir: Path) -> Path:
    width, height = map(int, shot.resolution.split("x"))
    image = Image.new("RGB", (width, height), color=(20, 20, 30))
    draw = ImageDraw.Draw(image)
    font = _ensure_font()
    text = f"{shot.shot_id}\n{shot.type}\n{shot.camera}"
    draw.multiline_text((20, 20), text, fill=(240, 240, 240), font=font)
    output_path = output_dir / f"{shot.shot_id}.png"
    image.save(output_path)
    return output_path


def render_procedural_video(
    shots: list[PlannedShot],
    output_dir: Path,
    ffmpeg_path: str | None = None,
    image_overrides: dict[str, Path] | None = None,
    clip_overrides: dict[str, Path] | None = None,
    tts_config: dict | None = None,
    music_config: dict | None = None,
    voice_enabled: bool = True,
    music_enabled: bool = True,
    sfx_enabled: bool = True,
) -> RenderResult:
    output_dir.mkdir(parents=True, exist_ok=True)
    image_dir = output_dir / "images"
    clip_dir = output_dir / "video"
    image_dir.mkdir(parents=True, exist_ok=True)
    clip_dir.mkdir(parents=True, exist_ok=True)

    warnings: list[str] = []
    clips: list[Path] = []
    for shot in shots:
        if clip_overrides and shot.shot_id in clip_overrides:
            clips.append(clip_overrides[shot.shot_id])
            continue
        if image_overrides and shot.shot_id in image_overrides:
            image_path = image_overrides[shot.shot_id]
        else:
            image_path = render_shot_image(shot, image_dir)
        clip_path = clip_dir / f"{shot.shot_id}.mp4"
        cmd = build_image_clip(image_path, shot.duration_sec, 30, clip_path)
        try:
            subprocess.run([ffmpeg_path or "ffmpeg", *cmd.args[1:]], check=True, capture_output=True)
            clips.append(clip_path)
        except (subprocess.CalledProcessError, FileNotFoundError) as exc:
            warnings.append(f"ffmpeg failed for {shot.shot_id}: {exc}")
            clip_path.write_text("ffmpeg missing; placeholder", encoding="utf-8")
            clips.append(clip_path)

    concat_path = output_dir / "concat.txt"
    build_concat_file(clips, concat_path)
    output_path = output_dir / "assembled.mp4"
    concat_cmd = build_concat_video(concat_path, output_path)
    try:
        subprocess.run([ffmpeg_path or "ffmpeg", *concat_cmd.args[1:]], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        warnings.append(f"ffmpeg concat failed: {exc}")
        output_path.write_text("ffmpeg missing; placeholder", encoding="utf-8")

    subtitles_path = output_dir / "captions.srt"
    if shots:
        subtitles_path.write_text(build_srt(shots), encoding="utf-8")
        if output_path.exists():
            subtitled_path = output_dir / "assembled_subtitled.mp4"
            burn_cmd = build_burn_subtitles(output_path, subtitles_path, subtitled_path)
            try:
                subprocess.run(
                    [ffmpeg_path or "ffmpeg", *burn_cmd.args[1:]], check=True, capture_output=True
                )
                output_path = subtitled_path
            except (subprocess.CalledProcessError, FileNotFoundError) as exc:
                warnings.append(f"ffmpeg subtitles failed: {exc}")

    audio_dir = output_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    audio_track = _build_audio_track(
        shots,
        audio_dir,
        ffmpeg_path,
        warnings,
        tts_config=tts_config,
        music_config=music_config,
        voice_enabled=voice_enabled,
        music_enabled=music_enabled,
        sfx_enabled=sfx_enabled,
    )
    if audio_track and output_path.exists():
        muxed_path = output_dir / "assembled_with_audio.mp4"
        mux_cmd = build_mux_audio(output_path, audio_track, muxed_path)
        try:
            subprocess.run([ffmpeg_path or "ffmpeg", *mux_cmd.args[1:]], check=True, capture_output=True)
            output_path = muxed_path
        except (subprocess.CalledProcessError, FileNotFoundError) as exc:
            warnings.append(f"ffmpeg audio mux failed: {exc}")

    (output_dir / "render_meta.json").write_text(
        json.dumps({"clips": [str(c) for c in clips]}, indent=2), encoding="utf-8"
    )
    return RenderResult(output_path=output_path, warnings=warnings)


def render_comfyui_images(
    shots: list[PlannedShot],
    output_dir: Path,
    templates_dir: Path,
    comfyui_url: str,
    checkpoint: str,
) -> tuple[dict[str, Path], list[str]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    warnings: list[str] = []
    images: dict[str, Path] = {}
    template_path = templates_dir / "workflows" / "sd_image.json"
    for shot in shots:
        width, height = map(int, shot.resolution.split("x"))
        substitutions = {
            "prompt": shot.prompt,
            "negative_prompt": shot.negative_prompt,
            "seed": shot.seed,
            "width": width,
            "height": height,
            "checkpoint": checkpoint,
        }
        try:
            workflow = load_workflow(template_path, substitutions)
            prompt_id = submit_prompt(comfyui_url, workflow)
            history = wait_for_completion(comfyui_url, prompt_id)
            filename = _extract_image_filename(history)
            if not filename:
                warnings.append(f"No image output for {shot.shot_id}")
                continue
            output_path = output_dir / f"{shot.shot_id}.png"
            download_view(comfyui_url, filename, output_path)
            images[shot.shot_id] = output_path
        except Exception as exc:
            warnings.append(f"ComfyUI render failed for {shot.shot_id}: {exc}")
    return images, warnings


def render_comfyui_videos(
    shots: list[PlannedShot],
    output_dir: Path,
    workflow_path: Path,
    comfyui_url: str,
    checkpoint: str,
) -> tuple[dict[str, Path], list[str]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    warnings: list[str] = []
    videos: dict[str, Path] = {}
    for shot in shots:
        width, height = map(int, shot.resolution.split("x"))
        substitutions = {
            "prompt": shot.prompt,
            "negative_prompt": shot.negative_prompt,
            "seed": shot.seed,
            "width": width,
            "height": height,
            "checkpoint": checkpoint,
        }
        try:
            workflow = load_workflow(workflow_path, substitutions)
            prompt_id = submit_prompt(comfyui_url, workflow)
            history = wait_for_completion(comfyui_url, prompt_id)
            filename = _extract_video_filename(history)
            if not filename:
                warnings.append(f"No video output for {shot.shot_id}")
                continue
            output_path = output_dir / f"{shot.shot_id}.mp4"
            download_view(comfyui_url, filename, output_path)
            videos[shot.shot_id] = output_path
        except Exception as exc:
            warnings.append(f"ComfyUI video failed for {shot.shot_id}: {exc}")
    return videos, warnings


def build_srt(shots: list[PlannedShot]) -> str:
    entries: list[str] = []
    current = 0.0
    index = 1
    for shot in shots:
        start = current
        end = current + shot.duration_sec
        current = end
        line = shot.audio.get("dialogue_line", "")
        if not line:
            continue
        entries.append(str(index))
        entries.append(f"{format_srt_time(start)} --> {format_srt_time(end)}")
        entries.append(line)
        entries.append("")
        index += 1
    return "\n".join(entries)


def format_srt_time(seconds: float) -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def _build_audio_track(
    shots: list[PlannedShot],
    audio_dir: Path,
    ffmpeg_path: str | None,
    warnings: list[str],
    tts_config: dict | None,
    music_config: dict | None,
    voice_enabled: bool,
    music_enabled: bool,
    sfx_enabled: bool,
) -> Path | None:
    if not shots:
        return None
    segments: list[Path] = []
    total_duration = sum(shot.duration_sec for shot in shots)
    dialogue_path: Path | None = None
    if voice_enabled:
        for index, shot in enumerate(shots, start=1):
            segment_path = audio_dir / f"segment_{index:04d}.wav"
            if shot.audio.get("dialogue_line") and tts_config:
                raw_path = audio_dir / f"segment_{index:04d}_raw.wav"
                ok, message = synthesize_tts(shot.audio["dialogue_line"], raw_path, tts_config)
                if ok:
                    fit_cmd = build_fit_audio(raw_path, shot.duration_sec, segment_path)
                    try:
                        subprocess.run(
                            [ffmpeg_path or "ffmpeg", *fit_cmd.args[1:]], check=True, capture_output=True
                        )
                        segments.append(segment_path)
                        continue
                    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
                        warnings.append(f"ffmpeg TTS fit failed: {exc}")
                else:
                    warnings.append(message)

            if shot.audio.get("dialogue_line"):
                cmd = build_tone_audio(shot.duration_sec, segment_path)
            else:
                cmd = build_silence_audio(shot.duration_sec, segment_path)
            try:
                subprocess.run([ffmpeg_path or "ffmpeg", *cmd.args[1:]], check=True, capture_output=True)
                segments.append(segment_path)
            except (subprocess.CalledProcessError, FileNotFoundError) as exc:
                warnings.append(f"ffmpeg audio segment failed: {exc}")
                return None

        concat_path = audio_dir / "audio_concat.txt"
        build_concat_file(segments, concat_path)
        dialogue_path = audio_dir / "dialogue_track.wav"
        concat_cmd = build_concat_audio(concat_path, dialogue_path)
        try:
            subprocess.run([ffmpeg_path or "ffmpeg", *concat_cmd.args[1:]], check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError) as exc:
            warnings.append(f"ffmpeg audio concat failed: {exc}")
            return None

    music_path: Path | None = None
    if music_enabled and total_duration > 0:
        music_path = audio_dir / "music_track.wav"
        music_track = resolve_music_track(music_config)
        if music_track:
            source_track = music_track
            if music_track.suffix.lower() != ".wav":
                converted_track = audio_dir / f"music_converted_{music_track.stem}.wav"
                convert_cmd = build_convert_audio(music_track, converted_track)
                try:
                    subprocess.run(
                        [ffmpeg_path or "ffmpeg", *convert_cmd.args[1:]], check=True, capture_output=True
                    )
                    source_track = converted_track
                except (subprocess.CalledProcessError, FileNotFoundError) as exc:
                    warnings.append(f"ffmpeg music convert failed: {exc}")
                    source_track = music_track
            music_cmd = build_loop_audio(source_track, total_duration, music_path)
        else:
            music_cmd = build_tone_audio(total_duration, music_path, frequency=220)
        try:
            subprocess.run([ffmpeg_path or "ffmpeg", *music_cmd.args[1:]], check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError) as exc:
            warnings.append(f"ffmpeg music track failed: {exc}")
            music_path = None

    base_track = None
    if dialogue_path and music_path:
        mixed_path = audio_dir / "mix_track.wav"
        mix_cmd = build_mix_audio(dialogue_path, music_path, mixed_path)
        try:
            subprocess.run([ffmpeg_path or "ffmpeg", *mix_cmd.args[1:]], check=True, capture_output=True)
            base_track = mixed_path
        except (subprocess.CalledProcessError, FileNotFoundError) as exc:
            warnings.append(f"ffmpeg audio mix failed: {exc}")
            base_track = dialogue_path
    elif dialogue_path:
        base_track = dialogue_path
    else:
        base_track = music_path

    sfx_path: Path | None = None
    if sfx_enabled and total_duration > 0:
        sfx_segments: list[Path] = []
        for index, shot in enumerate(shots, start=1):
            segment_path = audio_dir / f"sfx_segment_{index:04d}.wav"
            if shot.audio.get("sfx_tags"):
                cmd = build_tone_audio(shot.duration_sec, segment_path, frequency=880)
            else:
                cmd = build_silence_audio(shot.duration_sec, segment_path)
            try:
                subprocess.run([ffmpeg_path or "ffmpeg", *cmd.args[1:]], check=True, capture_output=True)
                sfx_segments.append(segment_path)
            except (subprocess.CalledProcessError, FileNotFoundError) as exc:
                warnings.append(f"ffmpeg sfx segment failed: {exc}")
                sfx_segments = []
                break
        if sfx_segments:
            concat_path = audio_dir / "sfx_concat.txt"
            build_concat_file(sfx_segments, concat_path)
            sfx_path = audio_dir / "sfx_track.wav"
            concat_cmd = build_concat_audio(concat_path, sfx_path)
            try:
                subprocess.run([ffmpeg_path or "ffmpeg", *concat_cmd.args[1:]], check=True, capture_output=True)
            except (subprocess.CalledProcessError, FileNotFoundError) as exc:
                warnings.append(f"ffmpeg sfx concat failed: {exc}")
                sfx_path = None

    if base_track and sfx_path:
        mixed_path = audio_dir / "mix_track_sfx.wav"
        mix_cmd = build_mix_audio(base_track, sfx_path, mixed_path)
        try:
            subprocess.run([ffmpeg_path or "ffmpeg", *mix_cmd.args[1:]], check=True, capture_output=True)
            return mixed_path
        except (subprocess.CalledProcessError, FileNotFoundError) as exc:
            warnings.append(f"ffmpeg sfx mix failed: {exc}")
            return base_track

    if base_track:
        return base_track
    return sfx_path


def _extract_image_filename(history: dict) -> str | None:
    outputs = history.get("outputs", {})
    for output in outputs.values():
        for image in output.get("images", []):
            filename = image.get("filename")
            if filename:
                return filename
    return None


def _extract_video_filename(history: dict) -> str | None:
    outputs = history.get("outputs", {})
    for output in outputs.values():
        for video in output.get("videos", []):
            filename = video.get("filename")
            if filename:
                return filename
    return None
