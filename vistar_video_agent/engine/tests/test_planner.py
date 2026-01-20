from vistar_engine.planner import plan_shots
from vistar_engine.spec import FilmSpec


def test_plan_shots_duration_fit():
    spec = FilmSpec(
        version="1.0",
        title="Test",
        format=["shorts"],
        targets={"shorts": {"duration_sec": 20, "aspect": "9:16", "resolution": "1080x1920"}},
        scenes=[{"id": "S1", "summary": "Scene", "beats": ["A", "B"], "dialogue": []}],
    )
    shots = plan_shots(spec, spec.targets, "shorts")
    total = sum(shot.duration_sec for shot in shots)
    assert total <= spec.targets.shorts.duration_sec
