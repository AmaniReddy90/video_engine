from vistar_engine.spec import FilmSpec, TargetsSpec, TargetSpec, clamp_targets


def sample_spec():
    return {
        "version": "1.0",
        "title": "My Film",
        "format": ["shorts", "full"],
        "targets": {
            "shorts": {"duration_sec": 30, "aspect": "9:16", "resolution": "1080x1920"},
            "full": {"duration_sec": 180, "aspect": "16:9", "resolution": "1920x1080"},
        },
        "scenes": [
            {
                "id": "S1",
                "summary": "Discovery",
                "beats": ["Wide establishing"],
                "dialogue": [],
            }
        ],
    }


def test_spec_validation():
    spec = FilmSpec(**sample_spec())
    assert spec.title == "My Film"


def test_clamp_targets():
    targets = TargetsSpec(
        shorts=TargetSpec(duration_sec=10, aspect="9:16", resolution="1080x1920"),
        full=TargetSpec(duration_sec=5000, aspect="16:9", resolution="1920x1080"),
    )
    clamp_targets(targets)
    assert targets.shorts.duration_sec == 15
    assert targets.full.duration_sec == 3600
