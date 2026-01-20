from __future__ import annotations

import json
import time
from pathlib import Path

import requests


def load_workflow(template_path: Path, substitutions: dict[str, str]) -> dict:
    workflow = template_path.read_text(encoding="utf-8")
    for key, value in substitutions.items():
        workflow = workflow.replace(f"${{{key}}}", str(value))
    return json.loads(workflow)


def submit_prompt(url: str, workflow: dict) -> str:
    response = requests.post(f"{url}/prompt", json={"prompt": workflow}, timeout=10)
    response.raise_for_status()
    return response.json().get("prompt_id", "")


def wait_for_completion(url: str, prompt_id: str, timeout_sec: int = 120) -> dict:
    start = time.time()
    while time.time() - start < timeout_sec:
        response = requests.get(f"{url}/history/{prompt_id}", timeout=10)
        response.raise_for_status()
        data = response.json()
        if prompt_id in data:
            return data[prompt_id]
        time.sleep(1)
    raise TimeoutError("ComfyUI job timed out")


def download_view(url: str, filename: str, output_path: Path) -> Path:
    response = requests.get(f"{url}/view?filename={filename}", timeout=10)
    response.raise_for_status()
    output_path.write_bytes(response.content)
    return output_path
