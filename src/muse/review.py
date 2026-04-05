"""Review engine: load personas, build prompts, call describe."""

from pathlib import Path

from muse.models import StepData
from muse.providers.base import ImageProvider


class ReviewEngine:
    """Handles image review using personas and provider vision."""

    def __init__(self, muse_home: Path):
        self.personas_dir = muse_home / "personas"

    def load_persona(self, name: str) -> str:
        persona_file = self.personas_dir / f"{name}.md"
        if not persona_file.exists():
            raise FileNotFoundError(f"Persona not found: {name}")
        return persona_file.read_text()

    def build_review_prompt(self, persona_name: str, history: list[StepData]) -> str:
        persona_text = self.load_persona(persona_name)

        if not history:
            return persona_text

        history_lines = ["\n\n---\nSession history (for context):"]
        for step in history:
            prefix = f"Step {step.step}"
            if step.parent_step is not None:
                prefix += f" (from step {step.parent_step})"
            history_lines.append(f"- {prefix}: \"{step.prompt}\"")

        return persona_text + "\n".join(history_lines)

    def review(
        self,
        provider: ImageProvider,
        image_path: Path,
        persona_name: str,
        history: list[StepData],
    ) -> str:
        system_prompt = self.build_review_prompt(persona_name, history)
        return provider.describe(image_path, system_prompt)
