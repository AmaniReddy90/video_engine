from pathlib import Path

from vistar_engine.ffmpeg_tools import (
    build_burn_subtitles,
    build_concat_audio,
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


def test_build_image_clip():
    cmd = build_image_clip(Path("a.png"), 2.5, 30, Path("out.mp4"))
    assert cmd.args[0] == "ffmpeg"
    assert "-loop" in cmd.args


def test_build_concat_video():
    cmd = build_concat_video(Path("concat.txt"), Path("final.mp4"))
    assert "concat" in cmd.args


def test_build_burn_subtitles():
    cmd = build_burn_subtitles(Path("video.mp4"), Path("captions.srt"), Path("out.mp4"))
    assert "subtitles" in " ".join(cmd.args)


def test_build_silence_audio():
    cmd = build_silence_audio(3.5, Path("silence.wav"))
    assert "anullsrc" in " ".join(cmd.args)


def test_build_mux_audio():
    cmd = build_mux_audio(Path("video.mp4"), Path("audio.wav"), Path("out.mp4"))
    assert "-shortest" in cmd.args


def test_build_tone_audio():
    cmd = build_tone_audio(2.0, Path("tone.wav"), frequency=330)
    assert "sine=" in " ".join(cmd.args)


def test_build_concat_audio():
    cmd = build_concat_audio(Path("audio.txt"), Path("out.wav"))
    assert "concat" in cmd.args


def test_build_mix_audio():
    cmd = build_mix_audio(Path("primary.wav"), Path("secondary.wav"), Path("out.wav"))
    assert "amix" in " ".join(cmd.args)


def test_build_fit_audio():
    cmd = build_fit_audio(Path("input.wav"), 4.0, Path("out.wav"))
    assert "apad" in " ".join(cmd.args)


def test_build_loop_audio():
    cmd = build_loop_audio(Path("input.wav"), 8.0, Path("out.wav"))
    assert "-stream_loop" in cmd.args


def test_build_convert_audio():
    cmd = build_convert_audio(Path("input.mp3"), Path("out.wav"))
    assert "-ar" in cmd.args
