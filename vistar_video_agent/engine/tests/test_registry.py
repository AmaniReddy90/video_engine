from vistar_engine.registry import ModelRegistry, validate_registry


def test_registry_validation_missing_paths():
    registry = ModelRegistry(
        mode="procedural",
        animatediff={"workflow_path": "C:/missing.json"},
        tts={"model_path": "C:/missing.onnx", "binary_path": "C:/missing.exe"},
        music={"track_path": "C:/missing.wav"},
    )
    errors = validate_registry(registry)
    assert any("animatediff.workflow_path" in error for error in errors)
    assert any("tts.model_path" in error for error in errors)
    assert any("tts.binary_path" in error for error in errors)
    assert any("music.track_path" in error for error in errors)
