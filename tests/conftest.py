import json
from pathlib import Path

import pytest


@pytest.fixture
def muse_home(tmp_path):
    """Create a temporary ~/.muse directory structure."""
    home = tmp_path / ".muse"
    home.mkdir()
    (home / "sessions").mkdir()
    (home / "personas").mkdir()
    return home


@pytest.fixture
def sample_persona(muse_home):
    """Create a sample persona file."""
    persona = muse_home / "personas" / "collaborative.md"
    persona.write_text(
        "You are a collaborative art partner. "
        "Describe what works, suggest 1-2 improvements, "
        "and propose concrete next moves as muse tweak commands."
    )
    return persona


@pytest.fixture
def mock_provider():
    """A mock provider that returns predictable results."""
    from unittest.mock import MagicMock
    from muse.providers.base import ImageProvider
    from muse.models import GeneratedImage

    provider = MagicMock(spec=ImageProvider)
    provider.name = "mock"
    provider.supports_vision = True

    def fake_generate(prompt, **kwargs):
        # Create a 1x1 white PNG
        img_path = kwargs.get("output_path", Path("/tmp/mock.png"))
        img_path.parent.mkdir(parents=True, exist_ok=True)
        from PIL import Image
        img = Image.new("RGB", (64, 64), color="white")
        img.save(img_path)
        return GeneratedImage(
            path=img_path,
            prompt=prompt,
            provider="mock",
            metadata={"model": "mock-v1"},
        )

    provider.generate.side_effect = fake_generate
    provider.edit.side_effect = fake_generate
    provider.describe.return_value = "A white square image."
    return provider
