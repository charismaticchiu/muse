"""Data models for Muse sessions and images."""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class GeneratedImage:
    """Result of an image generation or edit call."""

    path: Path
    prompt: str
    provider: str
    metadata: dict = field(default_factory=dict)


@dataclass
class StepData:
    """A single step in a session's iteration chain."""

    step: int
    prompt: str
    parent_step: int | None
    provider: str
    model: str
    timestamp: datetime
    image: str  # filename, e.g. "step-001.png"
    metadata: dict = field(default_factory=dict)

    @property
    def json_filename(self) -> str:
        return f"step-{self.step:03d}.json"

    def to_dict(self) -> dict:
        d = asdict(self)
        d["timestamp"] = self.timestamp.isoformat()
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "StepData":
        d = d.copy()
        d["timestamp"] = datetime.fromisoformat(d["timestamp"])
        return cls(**d)


@dataclass
class SessionData:
    """Metadata for a session."""

    name: str
    created: datetime
    current_step: int
    provider: str
    total_steps: int

    def to_dict(self) -> dict:
        d = asdict(self)
        d["created"] = self.created.isoformat()
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "SessionData":
        d = d.copy()
        d["created"] = datetime.fromisoformat(d["created"])
        return cls(**d)
