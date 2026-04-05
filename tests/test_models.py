import json
from datetime import datetime, timezone
from pathlib import Path

from muse.models import GeneratedImage, StepData, SessionData


class TestGeneratedImage:
    def test_creation(self):
        img = GeneratedImage(
            path=Path("/tmp/test.png"),
            prompt="a sunset",
            provider="openai",
            metadata={"model": "dall-e-3"},
        )
        assert img.path == Path("/tmp/test.png")
        assert img.prompt == "a sunset"
        assert img.provider == "openai"
        assert img.metadata["model"] == "dall-e-3"


class TestStepData:
    def test_creation(self):
        step = StepData(
            step=1,
            prompt="a sunset over mountains",
            parent_step=None,
            provider="openai",
            model="dall-e-3",
            timestamp=datetime(2026, 4, 5, 10, 30, 0, tzinfo=timezone.utc),
            image="step-001.png",
            metadata={"size": "1024x1024"},
        )
        assert step.step == 1
        assert step.parent_step is None

    def test_to_dict_and_from_dict(self):
        step = StepData(
            step=2,
            prompt="make sky purple",
            parent_step=1,
            provider="openai",
            model="dall-e-3",
            timestamp=datetime(2026, 4, 5, 10, 31, 0, tzinfo=timezone.utc),
            image="step-002.png",
            metadata={},
        )
        d = step.to_dict()
        assert d["step"] == 2
        assert d["parent_step"] == 1
        assert d["timestamp"] == "2026-04-05T10:31:00+00:00"

        restored = StepData.from_dict(d)
        assert restored.step == step.step
        assert restored.prompt == step.prompt
        assert restored.parent_step == step.parent_step

    def test_step_filename(self):
        step = StepData(
            step=3,
            prompt="test",
            parent_step=2,
            provider="openai",
            model="dall-e-3",
            timestamp=datetime(2026, 4, 5, tzinfo=timezone.utc),
            image="step-003.png",
            metadata={},
        )
        assert step.json_filename == "step-003.json"
        assert step.image == "step-003.png"


class TestSessionData:
    def test_creation(self):
        session = SessionData(
            name="sunset-mountains",
            created=datetime(2026, 4, 5, 10, 30, 0, tzinfo=timezone.utc),
            current_step=1,
            provider="openai",
            total_steps=1,
        )
        assert session.name == "sunset-mountains"
        assert session.current_step == 1

    def test_to_dict_and_from_dict(self):
        session = SessionData(
            name="sunset-mountains",
            created=datetime(2026, 4, 5, 10, 30, 0, tzinfo=timezone.utc),
            current_step=2,
            provider="openai",
            total_steps=3,
        )
        d = session.to_dict()
        assert d["name"] == "sunset-mountains"

        restored = SessionData.from_dict(d)
        assert restored.name == session.name
        assert restored.current_step == session.current_step
        assert restored.total_steps == session.total_steps
