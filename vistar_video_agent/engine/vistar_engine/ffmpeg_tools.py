from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class FfmpegCommand:
    args: list[str]

    def as_shell(self) -> str:
        return " ".join(self.args)


def build_image_clip(image_path: Path, duration: float, fps: int, output_path: Path) -> FfmpegCommand:
    return FfmpegCommand(
        [
            "ffmpeg",
            "-y",
            "-loop",
            "1",
            "-i",
            str(image_path),
            "-t",
            str(duration),
            "-r",
            str(fps),
            "-vf",
            "format=yuv420p",
            str(output_path),
        ]
    )


def build_concat_file(clip_paths: list[Path], concat_path: Path) -> None:
    content = "\n".join(f"file '{path.as_posix()}'" for path in clip_paths)
    concat_path.write_text(content, encoding="utf-8")


def build_concat_video(concat_path: Path, output_path: Path) -> FfmpegCommand:
    return FfmpegCommand(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_path),
            "-c",
            "copy",
            str(output_path),
        ]
    )


def build_burn_subtitles(video_path: Path, srt_path: Path, output_path: Path) -> FfmpegCommand:
    subtitle_path = srt_path.as_posix().replace(":", "\\:")
    return FfmpegCommand(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(video_path),
            "-vf",
            f"subtitles='{subtitle_path}'",
            "-c:a",
            "copy",
            str(output_path),
        ]
    )


def build_silence_audio(duration: float, output_path: Path) -> FfmpegCommand:
    return FfmpegCommand(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=channel_layout=stereo:sample_rate=44100",
            "-t",
            str(duration),
            str(output_path),
        ]
    )


def build_tone_audio(duration: float, output_path: Path, frequency: int = 440) -> FfmpegCommand:
    return FfmpegCommand(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency={frequency}:sample_rate=44100",
            "-t",
            str(duration),
            str(output_path),
        ]
    )


def build_concat_audio(concat_path: Path, output_path: Path) -> FfmpegCommand:
    return FfmpegCommand(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_path),
            "-c",
            "copy",
            str(output_path),
        ]
    )


def build_mix_audio(primary_path: Path, secondary_path: Path, output_path: Path) -> FfmpegCommand:
    return FfmpegCommand(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(primary_path),
            "-i",
            str(secondary_path),
            "-filter_complex",
            "amix=inputs=2:weights=1 0.3:normalize=0",
            "-c:a",
            "pcm_s16le",
            str(output_path),
        ]
    )


def build_fit_audio(input_path: Path, duration: float, output_path: Path) -> FfmpegCommand:
    return FfmpegCommand(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(input_path),
            "-af",
            "apad",
            "-t",
            str(duration),
            "-c:a",
            "pcm_s16le",
            str(output_path),
        ]
    )


def build_loop_audio(input_path: Path, duration: float, output_path: Path) -> FfmpegCommand:
    return FfmpegCommand(
        [
            "ffmpeg",
            "-y",
            "-stream_loop",
            "-1",
            "-i",
            str(input_path),
            "-t",
            str(duration),
            "-c:a",
            "pcm_s16le",
            str(output_path),
        ]
    )


def build_convert_audio(input_path: Path, output_path: Path) -> FfmpegCommand:
    return FfmpegCommand(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(input_path),
            "-ar",
            "44100",
            "-ac",
            "2",
            str(output_path),
        ]
    )


def build_mux_audio(video_path: Path, audio_path: Path, output_path: Path) -> FfmpegCommand:
    return FfmpegCommand(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(video_path),
            "-i",
            str(audio_path),
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-shortest",
            str(output_path),
        ]
    )
