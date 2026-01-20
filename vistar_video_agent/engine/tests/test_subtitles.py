from vistar_engine.planner import plan_shots
from vistar_engine.render import build_srt
from vistar_engine.spec import FilmSpec


def test_build_srt_contains_dialogue():
    spec = FilmSpec(
        version="1.0",
        title="Test",
        format=["shorts"],
        targets={"shorts": {"duration_sec": 15, "aspect": "9:16", "resolution": "1080x1920"}},
        scenes=[
            {
                "id": "S1",
                "summary": "Scene",
                "beats": ["Wide"],
                "dialogue": [{"character": "hero", "line": "Hello", "emotion": "calm"}],
            }
        ],
    )
    shots = plan_shots(spec, spec.targets, "shorts")
    srt = build_srt(shots)
    assert "Hello" in srt
