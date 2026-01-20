from vistar_engine.comfyui import load_workflow
from vistar_engine.settings import get_engine_paths


def test_load_workflow_substitution():
    paths = get_engine_paths()
    template_path = paths.templates_dir / "workflows" / "sd_image.json"
    workflow = load_workflow(
        template_path,
        {
            "prompt": "test prompt",
            "negative_prompt": "no blur",
            "seed": 42,
            "width": 512,
            "height": 512,
            "checkpoint": "model.safetensors",
        },
    )
    prompt = workflow["prompt"]
    assert prompt["prompt"] == "test prompt"
    assert prompt["negative_prompt"] == "no blur"
    assert prompt["seed"] == "42"
    assert prompt["width"] == "512"
    assert prompt["height"] == "512"
    assert prompt["checkpoint"] == "model.safetensors"
