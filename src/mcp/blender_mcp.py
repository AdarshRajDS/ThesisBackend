import subprocess
import time
from pathlib import Path
from typing import Dict, Optional
import shutil

from src.config.settings import settings


class BlenderMCP:

    def __init__(self):
        self.project_root = Path(__file__).resolve().parents[2]
        self.output_dir = Path(settings.base_data_dir) / "outputs" / "blender"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.generator_script = self.project_root / "src" / "mcp" / "blender_generator.py"

    def _is_blender_available(self) -> bool:
        return shutil.which("blender") is not None

    def _validate_prompt(self, prompt: str) -> Optional[str]:
        if not prompt or len(prompt.strip()) < 10:
            return "Prompt must be at least 10 characters long."

        normalized = prompt.strip().lower()
        anatomy_terms = ["brain", "anatomy", "hand", "limb", "organ", "bone", "muscle", "heart", "lung", "liver", "kidney"]
        if not any(term in normalized for term in anatomy_terms):
            return "Prompt must reference anatomy (e.g., brain, hand, organ)."

        return None

    def _sanitize_task_id(self, prompt: str) -> str:
        base = "brain"
        safe = "".join(c if c.isalnum() else "_" for c in prompt.lower())
        safe = safe[:40].strip("_")
        if not safe:
            safe = base
        timestamp = int(time.time())
        return f"{base}_{safe}_{timestamp}"

    def _map_quality(self, quality: str) -> int:
        mapping = {"draft": 1, "standard": 2, "high": 4}
        return mapping.get(quality, 2)

    def generate_3d_brain(
        self,
        prompt: str,
        quality: str = "standard",
        file_format: str = "glb",
        include_preview: bool = True,
    ) -> Dict[str, Optional[str]]:
        if not self._is_blender_available():
            return {"status": "error", "error": "Blender is not installed locally. Please install Blender or use the Docker container."}

        validation_error = self._validate_prompt(prompt)
        if validation_error:
            return {"status": "error", "error": validation_error}

        task_id = self._sanitize_task_id(prompt)
        model_filename = f"{task_id}.{file_format}"
        preview_filename = f"{task_id}.png"

        model_path = self.output_dir / model_filename
        preview_path = self.output_dir / preview_filename if include_preview else None

        blender_command = [
            "blender",
            "--background",
            "--python",
            str(self.generator_script),  # FIX 1: use absolute path instead of relative "src/mcp/blender_generator.py"
            "--",
            "--prompt",
            prompt,
            "--output-model",
            str(model_path),
            "--quality",
            str(self._map_quality(quality)),
        ]

        if preview_path is not None:
            blender_command.extend(["--output-preview", str(preview_path)])

        print(f"Running command: {blender_command}", flush=True)
        print(f"Generator script path: {self.generator_script}", flush=True)
        print(f"Generator script exists: {self.generator_script.exists()}", flush=True)
        print(f"CWD: {self.project_root}", flush=True)

        try:
            completed = subprocess.run(
                blender_command,
                capture_output=True,
                text=True,
                timeout=3000,  # FIX 2: was 30s — Blender startup alone takes 60-120s in Docker
                cwd=str(self.project_root),
            )
        except subprocess.TimeoutExpired as exc:
            print(f"Blender timeout error: {exc}", flush=True)
            return {"status": "error", "error": "Blender generation timed out after 5 minutes.", "detail": str(exc)}

        if completed.returncode != 0:
            print(f"Blender command failed: {blender_command}", flush=True)
            print(f"Return code: {completed.returncode}", flush=True)
            print(f"Stdout: {completed.stdout}", flush=True)
            print(f"Stderr: {completed.stderr}", flush=True)
            return {
                "status": "error",
                "error": "Blender generation failed.",
                "detail": completed.stderr or completed.stdout,
            }

        if not model_path.exists():
            return {"status": "error", "error": "Blender did not write the model file."}

        # FIX 3: only check for preview file if we actually requested one
        if preview_path is not None and not preview_path.exists():
            return {
                "status": "error",
                "error": "Blender did not write the preview image.",
            }

        return {
            "status": "generated",
            "task_id": task_id,
            "model_path": str(model_path),
            "preview_path": str(preview_path) if preview_path else None,
        }