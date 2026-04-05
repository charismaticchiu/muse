import json
import struct
import zlib
from pathlib import Path

import pytest


def _make_minimal_png(path: Path, width: int = 64, height: int = 64) -> None:
    """Create a minimal valid white PNG without PIL (broken on Python 3.14)."""

    def _chunk(chunk_type: bytes, data: bytes) -> bytes:
        c = chunk_type + data
        crc = struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
        return struct.pack(">I", len(data)) + c + crc

    header = b"\x89PNG\r\n\x1a\n"
    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    ihdr = _chunk(b"IHDR", ihdr_data)

    # White pixel rows: filter byte (0) + RGB(255,255,255) * width
    raw_row = b"\x00" + b"\xff\xff\xff" * width
    raw_data = raw_row * height
    idat = _chunk(b"IDAT", zlib.compress(raw_data))
    iend = _chunk(b"IEND", b"")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(header + ihdr + idat + iend)


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
        img_path = kwargs.get("output_path", Path("/tmp/mock.png"))
        _make_minimal_png(img_path)
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
