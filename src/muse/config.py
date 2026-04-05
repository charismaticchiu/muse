"""Configuration loading and provider detection."""

import os
from dataclasses import dataclass, field
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib


@dataclass
class MuseConfig:
    """Muse configuration with defaults."""

    provider: str = "auto"
    persona: str = "collaborative"
    size: str = "1024x1024"
    gallery_port: int = 3333
    preview: str = "terminal"
    providers: dict = field(default_factory=dict)


def get_muse_home() -> Path:
    """Resolve the muse home directory."""
    env = os.environ.get("MUSE_HOME")
    if env:
        return Path(env)
    return Path.home() / ".muse"


def load_config(muse_home: Path) -> MuseConfig:
    """Load config from TOML file, falling back to defaults."""
    config = MuseConfig()
    config_path = muse_home / "config.toml"

    if config_path.exists():
        with open(config_path, "rb") as f:
            data = tomllib.load(f)

        defaults = data.get("defaults", {})
        if "provider" in defaults:
            config.provider = defaults["provider"]
        if "persona" in defaults:
            config.persona = defaults["persona"]
        if "size" in defaults:
            config.size = defaults["size"]
        if "gallery_port" in defaults:
            config.gallery_port = defaults["gallery_port"]
        if "preview" in defaults:
            config.preview = defaults["preview"]

        config.providers = {
            k: v for k, v in data.items() if k.startswith("providers")
        }

    return config


def detect_providers() -> list[str]:
    """Detect which providers have API keys available."""
    available = []
    if os.environ.get("OPENAI_API_KEY"):
        available.append("openai")
    if os.environ.get("GEMINI_API_KEY"):
        available.append("gemini")
    return available


def ensure_muse_home(muse_home: Path) -> None:
    """Create ~/.muse directory structure if it doesn't exist."""
    muse_home.mkdir(exist_ok=True)
    (muse_home / "sessions").mkdir(exist_ok=True)
    (muse_home / "personas").mkdir(exist_ok=True)
