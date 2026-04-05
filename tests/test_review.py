from pathlib import Path
from unittest.mock import MagicMock

from muse.review import ReviewEngine
from muse.models import StepData
from datetime import datetime, timezone


class TestReviewEngine:
    def test_load_persona(self, muse_home, sample_persona):
        engine = ReviewEngine(muse_home)
        text = engine.load_persona("collaborative")
        assert "collaborative art partner" in text

    def test_load_persona_missing(self, muse_home):
        import pytest
        engine = ReviewEngine(muse_home)
        with pytest.raises(FileNotFoundError):
            engine.load_persona("nonexistent")

    def test_build_prompt_with_history(self, muse_home, sample_persona):
        engine = ReviewEngine(muse_home)
        steps = [
            StepData(
                step=1, prompt="sunset over mountains", parent_step=None,
                provider="openai", model="dall-e-3",
                timestamp=datetime(2026, 4, 5, tzinfo=timezone.utc),
                image="step-001.png", metadata={},
            ),
            StepData(
                step=2, prompt="make sky more purple", parent_step=1,
                provider="openai", model="dall-e-3",
                timestamp=datetime(2026, 4, 5, tzinfo=timezone.utc),
                image="step-002.png", metadata={},
            ),
        ]
        prompt = engine.build_review_prompt("collaborative", steps)
        assert "collaborative art partner" in prompt
        assert "sunset over mountains" in prompt
        assert "make sky more purple" in prompt

    def test_review_calls_describe(self, muse_home, sample_persona, mock_provider):
        engine = ReviewEngine(muse_home)
        image_path = Path("/tmp/test_review.png")
        image_path.parent.mkdir(parents=True, exist_ok=True)

        # Write a minimal valid 1x1 red PNG (no PIL dependency)
        import struct, zlib
        def _png_chunk(tag, data):
            c = struct.pack(">I", len(data)) + tag + data
            return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        raw = (
            b"\x89PNG\r\n\x1a\n"
            + _png_chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
            + _png_chunk(b"IDAT", zlib.compress(b"\x00\xff\x00\x00"))
            + _png_chunk(b"IEND", b"")
        )
        image_path.write_bytes(raw)

        steps = [
            StepData(
                step=1, prompt="blue square", parent_step=None,
                provider="mock", model="mock-v1",
                timestamp=datetime(2026, 4, 5, tzinfo=timezone.utc),
                image="step-001.png", metadata={},
            ),
        ]
        result = engine.review(
            provider=mock_provider,
            image_path=image_path,
            persona_name="collaborative",
            history=steps,
        )
        assert result == "A white square image."
        mock_provider.describe.assert_called_once()
