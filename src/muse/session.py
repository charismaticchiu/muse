"""Session management: create, load, resume, history, back."""

import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

from muse.models import GeneratedImage, SessionData, StepData


class SessionManager:
    """Manages muse sessions on disk."""

    def __init__(self, muse_home: Path):
        self.sessions_dir = muse_home / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    def create(self, prompt: str, provider: str) -> SessionData:
        """Create a new session from a prompt."""
        name = self._slugify(prompt)
        name = self._unique_name(name)

        session_dir = self.sessions_dir / name
        session_dir.mkdir()
        (session_dir / "steps").mkdir()

        session = SessionData(
            name=name,
            created=datetime.now(timezone.utc),
            current_step=0,
            provider=provider,
            total_steps=0,
        )
        self._save_session(session)
        return session

    def load(self, name: str) -> SessionData:
        """Load a session by name."""
        session_file = self.sessions_dir / name / "session.json"
        data = json.loads(session_file.read_text())
        return SessionData.from_dict(data)

    def add_step(
        self, session_name: str, image: GeneratedImage, parent_step: int | None
    ) -> StepData:
        """Add a new step to a session. Copies the image into the session dir."""
        session = self.load(session_name)
        step_num = session.total_steps + 1
        image_filename = f"step-{step_num:03d}.png"

        step = StepData(
            step=step_num,
            prompt=image.prompt,
            parent_step=parent_step,
            provider=image.provider,
            model=image.metadata.get("model", "unknown"),
            timestamp=datetime.now(timezone.utc),
            image=image_filename,
            metadata=image.metadata,
        )

        steps_dir = self.sessions_dir / session_name / "steps"
        step_json = steps_dir / step.json_filename
        step_json.write_text(json.dumps(step.to_dict(), indent=2))

        dest = steps_dir / image_filename
        if image.path.exists() and image.path.resolve() != dest.resolve():
            shutil.copy2(image.path, dest)

        session.current_step = step_num
        session.total_steps = step_num
        self._save_session(session)

        return step

    def back(self, session_name: str, n: int = 1) -> SessionData:
        """Move current_step back by n. Clamps at 1."""
        session = self.load(session_name)
        session.current_step = max(1, session.current_step - n)
        self._save_session(session)
        return session

    def list_sessions(self) -> list[SessionData]:
        """List all sessions, sorted by most recently modified."""
        sessions = []
        for d in sorted(self.sessions_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
            session_file = d / "session.json"
            if session_file.exists():
                data = json.loads(session_file.read_text())
                sessions.append(SessionData.from_dict(data))
        return sessions

    def get_history(self, session_name: str) -> list[StepData]:
        """Get all steps for a session, ordered by step number."""
        steps_dir = self.sessions_dir / session_name / "steps"
        steps = []
        for f in sorted(steps_dir.glob("step-*.json")):
            data = json.loads(f.read_text())
            steps.append(StepData.from_dict(data))
        return steps

    def get_current_step(self, session_name: str) -> StepData | None:
        """Get the current step data."""
        session = self.load(session_name)
        if session.current_step == 0:
            return None
        step_file = (
            self.sessions_dir / session_name / "steps"
            / f"step-{session.current_step:03d}.json"
        )
        if not step_file.exists():
            return None
        return StepData.from_dict(json.loads(step_file.read_text()))

    def save_review(self, session_name: str, step_num: int, review_text: str) -> Path:
        """Save review output for a step."""
        review_path = (
            self.sessions_dir / session_name / "steps"
            / f"step-{step_num:03d}-review.md"
        )
        review_path.write_text(review_text)
        return review_path

    def _save_session(self, session: SessionData) -> None:
        session_file = self.sessions_dir / session.name / "session.json"
        session_file.write_text(json.dumps(session.to_dict(), indent=2))

    def _slugify(self, text: str) -> str:
        slug = text.lower().strip()
        slug = re.sub(r"[^a-z0-9\s-]", "", slug)
        slug = re.sub(r"[\s-]+", "-", slug)
        slug = slug.strip("-")
        if len(slug) > 60:
            slug = slug[:60].rstrip("-")
        return slug or "untitled"

    def _unique_name(self, name: str) -> str:
        if not (self.sessions_dir / name).exists():
            return name
        counter = 2
        while (self.sessions_dir / f"{name}-{counter}").exists():
            counter += 1
        return f"{name}-{counter}"
