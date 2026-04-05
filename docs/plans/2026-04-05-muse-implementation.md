# Muse Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a CLI-first art creation tool that lets engineers generate, iterate, and critique AI images through a multi-modal closed loop with a web gallery.

**Architecture:** Layered monolith — single Python package with clean internal layers. Provider abstraction via ABC, session-based history with immutable steps, local web gallery served by Python.

**Tech Stack:** Python 3.11+, click, openai SDK, google-genai SDK, term-image, tomli/tomli-w, uv

---

## File Structure

```
muse/
  pyproject.toml
  src/
    muse/
      __init__.py
      cli.py                    # Click group + all subcommands
      config.py                 # Config loading, defaults, MUSE_HOME resolution
      models.py                 # GeneratedImage, StepData, SessionData dataclasses
      session.py                # Session create/resume/back/history logic
      providers/
        __init__.py             # Provider registry + auto-detection
        base.py                 # ImageProvider ABC
        openai_provider.py      # OpenAI (DALL-E 3 + GPT-4o)
        gemini_provider.py      # Gemini (generate + vision)
      review.py                 # Review engine: persona loading, describe dispatch
      preview.py                # Terminal inline image display
      gallery/
        __init__.py
        server.py               # HTTP server with /api/ endpoints + static serving
        static/
          index.html            # SPA: grid view + timeline view
          style.css             # Dark theme
          app.js                # Vanilla JS: routing, fetch, render
  data/
    personas/
      collaborative.md
      critic.md
      technical.md
  tests/
    __init__.py
    conftest.py                 # Shared fixtures (tmp muse home, mock providers)
    test_models.py
    test_config.py
    test_session.py
    test_providers.py
    test_review.py
    test_gallery_api.py
    test_cli.py
```

---

### Task 1: Project Scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `src/muse/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Create pyproject.toml**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "muse-art"
version = "0.1.0"
description = "CLI art creation tool for engineers"
requires-python = ">=3.11"
dependencies = [
    "click>=8.1",
    "openai>=1.0",
    "google-genai>=1.0",
    "term-image>=0.7",
    "tomli>=2.0;python_version<'3.12'",
    "tomli-w>=1.0",
    "Pillow>=10.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-tmp-files>=0.0.2",
]

[project.scripts]
muse = "muse.cli:main"

[tool.hatch.build.targets.wheel]
packages = ["src/muse"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 2: Create src/muse/__init__.py**

```python
"""Muse — CLI art creation tool for engineers."""
```

- [ ] **Step 3: Create tests/__init__.py**

Empty file.

- [ ] **Step 4: Create tests/conftest.py with shared fixtures**

```python
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
```

- [ ] **Step 5: Initialize uv project and install dev dependencies**

Run: `cd /Users/ericchiu/vibe_coded/muse && uv venv && uv pip install -e ".[dev]"`

Expected: Packages install successfully, `muse` entry point is registered.

- [ ] **Step 6: Verify pytest runs (no tests yet, just clean exit)**

Run: `cd /Users/ericchiu/vibe_coded/muse && uv run pytest --co`

Expected: "no tests ran" or empty collection, exit code 0 or 5 (no tests collected).

- [ ] **Step 7: Commit**

```bash
cd /Users/ericchiu/vibe_coded/muse
git add pyproject.toml src/ tests/
git commit -m "feat: scaffold muse project with pyproject.toml and test fixtures"
```

---

### Task 2: Data Models

**Files:**
- Create: `src/muse/models.py`
- Create: `tests/test_models.py`

- [ ] **Step 1: Write failing tests for models**

```python
# tests/test_models.py
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/ericchiu/vibe_coded/muse && uv run pytest tests/test_models.py -v`

Expected: ImportError — `muse.models` does not exist yet.

- [ ] **Step 3: Implement models.py**

```python
# src/muse/models.py
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/ericchiu/vibe_coded/muse && uv run pytest tests/test_models.py -v`

Expected: All 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
cd /Users/ericchiu/vibe_coded/muse
git add src/muse/models.py tests/test_models.py
git commit -m "feat: add data models (GeneratedImage, StepData, SessionData)"
```

---

### Task 3: Configuration

**Files:**
- Create: `src/muse/config.py`
- Create: `tests/test_config.py`
- Create: `data/personas/collaborative.md`
- Create: `data/personas/critic.md`
- Create: `data/personas/technical.md`

- [ ] **Step 1: Write failing tests for config**

```python
# tests/test_config.py
import os
from pathlib import Path

from muse.config import MuseConfig, load_config, get_muse_home, detect_providers


class TestGetMuseHome:
    def test_default_home(self, monkeypatch, tmp_path):
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.delenv("MUSE_HOME", raising=False)
        home = get_muse_home()
        assert home == tmp_path / ".muse"

    def test_custom_home(self, monkeypatch, tmp_path):
        custom = tmp_path / "custom_muse"
        monkeypatch.setenv("MUSE_HOME", str(custom))
        home = get_muse_home()
        assert home == custom


class TestLoadConfig:
    def test_default_config_when_no_file(self, muse_home, monkeypatch):
        monkeypatch.setenv("MUSE_HOME", str(muse_home))
        config = load_config(muse_home)
        assert config.provider == "auto"
        assert config.persona == "collaborative"
        assert config.size == "1024x1024"
        assert config.gallery_port == 3333
        assert config.preview == "terminal"

    def test_load_from_toml(self, muse_home, monkeypatch):
        monkeypatch.setenv("MUSE_HOME", str(muse_home))
        config_file = muse_home / "config.toml"
        config_file.write_text(
            '[defaults]\nprovider = "gemini"\nsize = "512x512"\n'
        )
        config = load_config(muse_home)
        assert config.provider == "gemini"
        assert config.size == "512x512"
        # Unset values keep defaults
        assert config.persona == "collaborative"


class TestDetectProviders:
    def test_detects_openai(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test123")
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        providers = detect_providers()
        assert "openai" in providers
        assert "gemini" not in providers

    def test_detects_gemini(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.setenv("GEMINI_API_KEY", "AI-test123")
        providers = detect_providers()
        assert "gemini" in providers
        assert "openai" not in providers

    def test_detects_both(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.setenv("GEMINI_API_KEY", "AI-test")
        providers = detect_providers()
        assert "openai" in providers
        assert "gemini" in providers

    def test_detects_none(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        providers = detect_providers()
        assert len(providers) == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/ericchiu/vibe_coded/muse && uv run pytest tests/test_config.py -v`

Expected: ImportError — `muse.config` does not exist.

- [ ] **Step 3: Implement config.py**

```python
# src/muse/config.py
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
    preview: str = "terminal"  # "terminal", "gallery", "none"
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/ericchiu/vibe_coded/muse && uv run pytest tests/test_config.py -v`

Expected: All 7 tests PASS.

- [ ] **Step 5: Create bundled persona files**

`data/personas/collaborative.md`:
```markdown
You are a collaborative art partner helping an engineer iterate on generated images.
Be conversational and specific.

- Describe what's working well in the image
- Identify 1-2 things that could improve
- Suggest concrete next moves phrased as `muse tweak "..."` commands
- Reference composition, color, mood, and style
- Keep it concise: 3-5 sentences
```

`data/personas/critic.md`:
```markdown
You are a formal art critic analyzing a generated image.

- Evaluate composition, color theory, and visual hierarchy
- Assess emotional impact and mood
- Comment on technique and style execution
- Provide structured analysis: strengths, weaknesses, overall assessment
- Use art terminology precisely
```

`data/personas/technical.md`:
```markdown
You are a technical image analyst providing a factual description.

- Describe exactly what appears in the image: subjects, colors, layout
- Note what's present vs what was requested in the prompt
- Identify any artifacts, inconsistencies, or quality issues
- Do not make aesthetic judgments — stick to factual observations
- This helps debug the gap between prompt intent and model output
```

- [ ] **Step 6: Commit**

```bash
cd /Users/ericchiu/vibe_coded/muse
git add src/muse/config.py tests/test_config.py data/
git commit -m "feat: add config loading, key detection, and bundled personas"
```

---

### Task 4: Session Manager

**Files:**
- Create: `src/muse/session.py`
- Create: `tests/test_session.py`

- [ ] **Step 1: Write failing tests for session manager**

```python
# tests/test_session.py
import json
from datetime import datetime, timezone
from pathlib import Path

from muse.session import SessionManager
from muse.models import StepData, GeneratedImage


class TestSessionCreate:
    def test_create_session(self, muse_home):
        mgr = SessionManager(muse_home)
        session = mgr.create("a sunset over mountains", provider="openai")
        assert session.name == "a-sunset-over-mountains"
        assert session.current_step == 0
        assert session.total_steps == 0
        assert (muse_home / "sessions" / "a-sunset-over-mountains").is_dir()
        assert (muse_home / "sessions" / "a-sunset-over-mountains" / "steps").is_dir()

    def test_create_session_slugifies(self, muse_home):
        mgr = SessionManager(muse_home)
        session = mgr.create("A Cozy Cabin!!  In a Forest?", provider="openai")
        assert session.name == "a-cozy-cabin-in-a-forest"

    def test_create_session_collision(self, muse_home):
        mgr = SessionManager(muse_home)
        s1 = mgr.create("sunset", provider="openai")
        s2 = mgr.create("sunset", provider="openai")
        assert s1.name == "sunset"
        assert s2.name == "sunset-2"

    def test_create_session_truncates_long_names(self, muse_home):
        mgr = SessionManager(muse_home)
        long_prompt = "a " * 100 + "sunset"
        session = mgr.create(long_prompt, provider="openai")
        assert len(session.name) <= 60


class TestSessionAddStep:
    def test_add_step(self, muse_home):
        mgr = SessionManager(muse_home)
        session = mgr.create("sunset", provider="openai")

        img = GeneratedImage(
            path=Path("/tmp/test.png"),
            prompt="sunset",
            provider="openai",
            metadata={"model": "dall-e-3"},
        )
        step = mgr.add_step(session.name, img, parent_step=None)
        assert step.step == 1
        assert step.parent_step is None

        # Session updated
        session = mgr.load(session.name)
        assert session.current_step == 1
        assert session.total_steps == 1

    def test_add_multiple_steps(self, muse_home):
        mgr = SessionManager(muse_home)
        session = mgr.create("sunset", provider="openai")

        for i in range(3):
            img = GeneratedImage(
                path=Path(f"/tmp/test{i}.png"),
                prompt=f"step {i}",
                provider="openai",
                metadata={},
            )
            mgr.add_step(session.name, img, parent_step=i if i > 0 else None)

        session = mgr.load(session.name)
        assert session.current_step == 3
        assert session.total_steps == 3


class TestSessionBack:
    def test_back_one(self, muse_home):
        mgr = SessionManager(muse_home)
        session = mgr.create("sunset", provider="openai")

        for i in range(3):
            img = GeneratedImage(
                path=Path(f"/tmp/test{i}.png"),
                prompt=f"step {i}",
                provider="openai",
                metadata={},
            )
            mgr.add_step(session.name, img, parent_step=i if i > 0 else None)

        mgr.back(session.name, n=1)
        session = mgr.load(session.name)
        assert session.current_step == 2
        # total_steps unchanged — steps are immutable
        assert session.total_steps == 3

    def test_back_multiple(self, muse_home):
        mgr = SessionManager(muse_home)
        session = mgr.create("sunset", provider="openai")

        for i in range(3):
            img = GeneratedImage(
                path=Path(f"/tmp/test{i}.png"),
                prompt=f"step {i}",
                provider="openai",
                metadata={},
            )
            mgr.add_step(session.name, img, parent_step=i if i > 0 else None)

        mgr.back(session.name, n=2)
        session = mgr.load(session.name)
        assert session.current_step == 1

    def test_back_clamps_at_one(self, muse_home):
        mgr = SessionManager(muse_home)
        session = mgr.create("sunset", provider="openai")

        img = GeneratedImage(
            path=Path("/tmp/test.png"),
            prompt="sunset",
            provider="openai",
            metadata={},
        )
        mgr.add_step(session.name, img, parent_step=None)

        mgr.back(session.name, n=100)
        session = mgr.load(session.name)
        assert session.current_step == 1


class TestSessionList:
    def test_list_sessions(self, muse_home):
        mgr = SessionManager(muse_home)
        mgr.create("alpha", provider="openai")
        mgr.create("beta", provider="gemini")

        sessions = mgr.list_sessions()
        names = [s.name for s in sessions]
        assert "alpha" in names
        assert "beta" in names

    def test_list_empty(self, muse_home):
        mgr = SessionManager(muse_home)
        sessions = mgr.list_sessions()
        assert sessions == []


class TestSessionHistory:
    def test_get_history(self, muse_home):
        mgr = SessionManager(muse_home)
        session = mgr.create("sunset", provider="openai")

        for i in range(3):
            img = GeneratedImage(
                path=Path(f"/tmp/test{i}.png"),
                prompt=f"prompt {i}",
                provider="openai",
                metadata={},
            )
            mgr.add_step(session.name, img, parent_step=i if i > 0 else None)

        steps = mgr.get_history(session.name)
        assert len(steps) == 3
        assert steps[0].step == 1
        assert steps[2].step == 3
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/ericchiu/vibe_coded/muse && uv run pytest tests/test_session.py -v`

Expected: ImportError — `muse.session` does not exist.

- [ ] **Step 3: Implement session.py**

```python
# src/muse/session.py
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

        # Copy image into session
        dest = steps_dir / image_filename
        if image.path.exists():
            shutil.copy2(image.path, dest)

        # Update session
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
            self.sessions_dir
            / session_name
            / "steps"
            / f"step-{session.current_step:03d}.json"
        )
        if not step_file.exists():
            return None
        return StepData.from_dict(json.loads(step_file.read_text()))

    def save_review(self, session_name: str, step_num: int, review_text: str) -> Path:
        """Save review output for a step."""
        review_path = (
            self.sessions_dir
            / session_name
            / "steps"
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/ericchiu/vibe_coded/muse && uv run pytest tests/test_session.py -v`

Expected: All 10 tests PASS.

- [ ] **Step 5: Commit**

```bash
cd /Users/ericchiu/vibe_coded/muse
git add src/muse/session.py tests/test_session.py
git commit -m "feat: add session manager with create, back, history, resume"
```

---

### Task 5: Provider Base + Registry

**Files:**
- Create: `src/muse/providers/__init__.py`
- Create: `src/muse/providers/base.py`
- Create: `tests/test_providers.py`

- [ ] **Step 1: Write failing tests for provider base and registry**

```python
# tests/test_providers.py
from pathlib import Path
from unittest.mock import MagicMock

from muse.providers.base import ImageProvider
from muse.providers import ProviderRegistry
from muse.models import GeneratedImage


class TestImageProviderABC:
    def test_cannot_instantiate_directly(self):
        """ABC should not be instantiable."""
        import pytest

        with pytest.raises(TypeError):
            ImageProvider()


class TestProviderRegistry:
    def test_register_and_get(self):
        registry = ProviderRegistry()
        mock_cls = MagicMock()
        mock_cls.name = "mock"
        mock_cls.is_available.return_value = True
        mock_instance = MagicMock(spec=ImageProvider)
        mock_instance.name = "mock"
        mock_instance.supports_vision = True
        mock_cls.return_value = mock_instance

        registry.register("mock", mock_cls)
        provider = registry.get("mock")
        assert provider.name == "mock"

    def test_get_unknown_provider(self):
        import pytest

        registry = ProviderRegistry()
        with pytest.raises(KeyError):
            registry.get("nonexistent")

    def test_available_providers(self):
        registry = ProviderRegistry()

        avail_cls = MagicMock()
        avail_cls.is_available.return_value = True
        avail_cls.return_value = MagicMock(name="avail")

        unavail_cls = MagicMock()
        unavail_cls.is_available.return_value = False

        registry.register("avail", avail_cls)
        registry.register("unavail", unavail_cls)

        available = registry.available()
        assert "avail" in available
        assert "unavail" not in available

    def test_get_auto_returns_first_available(self):
        registry = ProviderRegistry()

        mock_cls = MagicMock()
        mock_cls.is_available.return_value = True
        mock_instance = MagicMock(spec=ImageProvider)
        mock_instance.name = "first"
        mock_cls.return_value = mock_instance

        registry.register("first", mock_cls)
        provider = registry.get_auto()
        assert provider is not None

    def test_get_auto_returns_none_when_empty(self):
        registry = ProviderRegistry()
        provider = registry.get_auto()
        assert provider is None

    def test_get_vision_provider(self):
        registry = ProviderRegistry()

        no_vision_cls = MagicMock()
        no_vision_cls.is_available.return_value = True
        no_vision_inst = MagicMock(spec=ImageProvider)
        no_vision_inst.supports_vision = False
        no_vision_cls.return_value = no_vision_inst

        vision_cls = MagicMock()
        vision_cls.is_available.return_value = True
        vision_inst = MagicMock(spec=ImageProvider)
        vision_inst.supports_vision = True
        vision_cls.return_value = vision_inst

        registry.register("nope", no_vision_cls)
        registry.register("yes", vision_cls)

        provider = registry.get_vision_provider()
        assert provider.supports_vision is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/ericchiu/vibe_coded/muse && uv run pytest tests/test_providers.py -v`

Expected: ImportError — `muse.providers.base` does not exist.

- [ ] **Step 3: Implement base.py**

```python
# src/muse/providers/base.py
"""Abstract base class for image providers."""

from abc import ABC, abstractmethod
from pathlib import Path

from muse.models import GeneratedImage


class ImageProvider(ABC):
    """Interface that all image providers must implement."""

    name: str
    supports_vision: bool = True

    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> GeneratedImage:
        """Generate an image from a text prompt."""
        ...

    @abstractmethod
    def edit(self, image: Path, prompt: str, **kwargs) -> GeneratedImage:
        """Edit an existing image with a text prompt."""
        ...

    @abstractmethod
    def describe(self, image: Path, system_prompt: str) -> str:
        """Describe/critique an image (vision). Returns text."""
        ...

    @classmethod
    @abstractmethod
    def is_available(cls) -> bool:
        """Check if this provider's API key is configured."""
        ...
```

- [ ] **Step 4: Implement providers/__init__.py with registry**

```python
# src/muse/providers/__init__.py
"""Provider registry and auto-detection."""

from muse.providers.base import ImageProvider


class ProviderRegistry:
    """Registry of available image providers."""

    def __init__(self):
        self._providers: dict[str, type[ImageProvider]] = {}
        self._instances: dict[str, ImageProvider] = {}

    def register(self, name: str, provider_cls: type[ImageProvider]) -> None:
        self._providers[name] = provider_cls

    def get(self, name: str) -> ImageProvider:
        if name not in self._providers:
            raise KeyError(f"Unknown provider: {name}")
        if name not in self._instances:
            self._instances[name] = self._providers[name]()
        return self._instances[name]

    def available(self) -> list[str]:
        return [
            name
            for name, cls in self._providers.items()
            if cls.is_available()
        ]

    def get_auto(self) -> ImageProvider | None:
        for name in self.available():
            return self.get(name)
        return None

    def get_vision_provider(self) -> ImageProvider | None:
        for name in self.available():
            provider = self.get(name)
            if provider.supports_vision:
                return provider
        return None


def build_registry() -> ProviderRegistry:
    """Build the default registry with all known providers."""
    registry = ProviderRegistry()

    # Import lazily to avoid requiring all SDKs
    try:
        from muse.providers.openai_provider import OpenAIProvider
        registry.register("openai", OpenAIProvider)
    except ImportError:
        pass

    try:
        from muse.providers.gemini_provider import GeminiProvider
        registry.register("gemini", GeminiProvider)
    except ImportError:
        pass

    return registry
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /Users/ericchiu/vibe_coded/muse && uv run pytest tests/test_providers.py -v`

Expected: All 7 tests PASS.

- [ ] **Step 6: Commit**

```bash
cd /Users/ericchiu/vibe_coded/muse
git add src/muse/providers/ tests/test_providers.py
git commit -m "feat: add provider ABC and registry with auto-detection"
```

---

### Task 6: OpenAI Provider

**Files:**
- Create: `src/muse/providers/openai_provider.py`

- [ ] **Step 1: Write failing test for OpenAI provider**

Add to `tests/test_providers.py`:

```python
class TestOpenAIProviderAvailability:
    def test_not_available_without_key(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        from muse.providers.openai_provider import OpenAIProvider
        assert OpenAIProvider.is_available() is False

    def test_available_with_key(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        from muse.providers.openai_provider import OpenAIProvider
        assert OpenAIProvider.is_available() is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/ericchiu/vibe_coded/muse && uv run pytest tests/test_providers.py::TestOpenAIProviderAvailability -v`

Expected: ImportError — `muse.providers.openai_provider` does not exist.

- [ ] **Step 3: Implement openai_provider.py**

```python
# src/muse/providers/openai_provider.py
"""OpenAI provider: DALL-E 3 for generation, GPT-4o for vision."""

import base64
import os
from pathlib import Path

from openai import OpenAI

from muse.models import GeneratedImage
from muse.providers.base import ImageProvider


class OpenAIProvider(ImageProvider):
    name = "openai"
    supports_vision = True

    def __init__(self):
        self._client = OpenAI()

    def generate(self, prompt: str, **kwargs) -> GeneratedImage:
        size = kwargs.get("size", "1024x1024")
        model = kwargs.get("model", "dall-e-3")
        output_path = kwargs["output_path"]

        response = self._client.images.generate(
            model=model,
            prompt=prompt,
            size=size,
            n=1,
            response_format="b64_json",
        )

        image_data = base64.b64decode(response.data[0].b64_json)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(image_data)

        return GeneratedImage(
            path=output_path,
            prompt=prompt,
            provider=self.name,
            metadata={
                "model": model,
                "size": size,
                "revised_prompt": getattr(response.data[0], "revised_prompt", None),
            },
        )

    def edit(self, image: Path, prompt: str, **kwargs) -> GeneratedImage:
        """Edit using DALL-E 3 — re-generates with context from the original prompt."""
        # DALL-E 3 doesn't have a true edit API, so we re-generate
        return self.generate(prompt, **kwargs)

    def describe(self, image: Path, system_prompt: str) -> str:
        image_data = base64.b64encode(image.read_bytes()).decode("utf-8")
        model = "gpt-4o"

        response = self._client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Please review this image:"},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_data}"
                            },
                        },
                    ],
                },
            ],
            max_tokens=500,
        )
        return response.choices[0].message.content

    @classmethod
    def is_available(cls) -> bool:
        return bool(os.environ.get("OPENAI_API_KEY"))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/ericchiu/vibe_coded/muse && uv run pytest tests/test_providers.py::TestOpenAIProviderAvailability -v`

Expected: 2 tests PASS.

- [ ] **Step 5: Commit**

```bash
cd /Users/ericchiu/vibe_coded/muse
git add src/muse/providers/openai_provider.py tests/test_providers.py
git commit -m "feat: add OpenAI provider (DALL-E 3 + GPT-4o vision)"
```

---

### Task 7: Gemini Provider

**Files:**
- Create: `src/muse/providers/gemini_provider.py`

- [ ] **Step 1: Write failing test for Gemini provider**

Add to `tests/test_providers.py`:

```python
class TestGeminiProviderAvailability:
    def test_not_available_without_key(self, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        from muse.providers.gemini_provider import GeminiProvider
        assert GeminiProvider.is_available() is False

    def test_available_with_key(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "AI-test")
        from muse.providers.gemini_provider import GeminiProvider
        assert GeminiProvider.is_available() is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/ericchiu/vibe_coded/muse && uv run pytest tests/test_providers.py::TestGeminiProviderAvailability -v`

Expected: ImportError — `muse.providers.gemini_provider` does not exist.

- [ ] **Step 3: Implement gemini_provider.py**

```python
# src/muse/providers/gemini_provider.py
"""Gemini provider: image generation + vision via Google GenAI."""

import os
from pathlib import Path

from google import genai
from google.genai import types

from muse.models import GeneratedImage
from muse.providers.base import ImageProvider


class GeminiProvider(ImageProvider):
    name = "gemini"
    supports_vision = True

    def __init__(self):
        self._client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

    def generate(self, prompt: str, **kwargs) -> GeneratedImage:
        model = kwargs.get("model", "gemini-2.0-flash-exp")
        output_path = kwargs["output_path"]

        response = self._client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"],
            ),
        )

        # Extract the image part from the response
        image_data = None
        for part in response.candidates[0].content.parts:
            if part.inline_data and part.inline_data.mime_type.startswith("image/"):
                image_data = part.inline_data.data
                break

        if image_data is None:
            raise RuntimeError("Gemini did not return an image")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(image_data)

        return GeneratedImage(
            path=output_path,
            prompt=prompt,
            provider=self.name,
            metadata={"model": model},
        )

    def edit(self, image: Path, prompt: str, **kwargs) -> GeneratedImage:
        """Edit by sending the image + new prompt to Gemini."""
        model = kwargs.get("model", "gemini-2.0-flash-exp")
        output_path = kwargs["output_path"]

        image_bytes = image.read_bytes()
        response = self._client.models.generate_content(
            model=model,
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
                prompt,
            ],
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"],
            ),
        )

        new_image_data = None
        for part in response.candidates[0].content.parts:
            if part.inline_data and part.inline_data.mime_type.startswith("image/"):
                new_image_data = part.inline_data.data
                break

        if new_image_data is None:
            raise RuntimeError("Gemini did not return an edited image")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(new_image_data)

        return GeneratedImage(
            path=output_path,
            prompt=prompt,
            provider=self.name,
            metadata={"model": model},
        )

    def describe(self, image: Path, system_prompt: str) -> str:
        model = "gemini-2.0-flash"
        image_bytes = image.read_bytes()

        response = self._client.models.generate_content(
            model=model,
            contents=[
                system_prompt,
                types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
                "Please review this image.",
            ],
        )
        return response.text

    @classmethod
    def is_available(cls) -> bool:
        return bool(os.environ.get("GEMINI_API_KEY"))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/ericchiu/vibe_coded/muse && uv run pytest tests/test_providers.py::TestGeminiProviderAvailability -v`

Expected: 2 tests PASS.

- [ ] **Step 5: Commit**

```bash
cd /Users/ericchiu/vibe_coded/muse
git add src/muse/providers/gemini_provider.py tests/test_providers.py
git commit -m "feat: add Gemini provider (generate + vision)"
```

---

### Task 8: Review Engine

**Files:**
- Create: `src/muse/review.py`
- Create: `tests/test_review.py`

- [ ] **Step 1: Write failing tests for review engine**

```python
# tests/test_review.py
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
                step=1,
                prompt="sunset over mountains",
                parent_step=None,
                provider="openai",
                model="dall-e-3",
                timestamp=datetime(2026, 4, 5, tzinfo=timezone.utc),
                image="step-001.png",
                metadata={},
            ),
            StepData(
                step=2,
                prompt="make sky more purple",
                parent_step=1,
                provider="openai",
                model="dall-e-3",
                timestamp=datetime(2026, 4, 5, tzinfo=timezone.utc),
                image="step-002.png",
                metadata={},
            ),
        ]
        prompt = engine.build_review_prompt("collaborative", steps)
        assert "collaborative art partner" in prompt
        assert "sunset over mountains" in prompt
        assert "make sky more purple" in prompt

    def test_review_calls_describe(self, muse_home, sample_persona, mock_provider):
        engine = ReviewEngine(muse_home)
        image_path = Path("/tmp/test.png")
        image_path.parent.mkdir(parents=True, exist_ok=True)

        # Create a tiny test image
        from PIL import Image
        img = Image.new("RGB", (64, 64), color="blue")
        img.save(image_path)

        steps = [
            StepData(
                step=1,
                prompt="blue square",
                parent_step=None,
                provider="mock",
                model="mock-v1",
                timestamp=datetime(2026, 4, 5, tzinfo=timezone.utc),
                image="step-001.png",
                metadata={},
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/ericchiu/vibe_coded/muse && uv run pytest tests/test_review.py -v`

Expected: ImportError — `muse.review` does not exist.

- [ ] **Step 3: Implement review.py**

```python
# src/muse/review.py
"""Review engine: load personas, build prompts, call describe."""

from pathlib import Path

from muse.models import StepData
from muse.providers.base import ImageProvider


class ReviewEngine:
    """Handles image review using personas and provider vision."""

    def __init__(self, muse_home: Path):
        self.personas_dir = muse_home / "personas"

    def load_persona(self, name: str) -> str:
        """Load a persona template by name."""
        persona_file = self.personas_dir / f"{name}.md"
        if not persona_file.exists():
            raise FileNotFoundError(f"Persona not found: {name}")
        return persona_file.read_text()

    def build_review_prompt(self, persona_name: str, history: list[StepData]) -> str:
        """Build the full system prompt: persona + session history context."""
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
        """Run a review: load persona, build prompt, call describe."""
        system_prompt = self.build_review_prompt(persona_name, history)
        return provider.describe(image_path, system_prompt)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/ericchiu/vibe_coded/muse && uv run pytest tests/test_review.py -v`

Expected: All 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
cd /Users/ericchiu/vibe_coded/muse
git add src/muse/review.py tests/test_review.py
git commit -m "feat: add review engine with persona loading and history context"
```

---

### Task 9: Terminal Image Preview

**Files:**
- Create: `src/muse/preview.py`

- [ ] **Step 1: Implement preview.py**

```python
# src/muse/preview.py
"""Terminal inline image display with protocol auto-detection."""

import os
import sys
from pathlib import Path


def detect_protocol() -> str:
    """Detect the best image display protocol for the current terminal."""
    term_program = os.environ.get("TERM_PROGRAM", "")
    term = os.environ.get("TERM", "")

    if term_program == "iTerm.app":
        return "iterm"
    if term == "xterm-kitty":
        return "kitty"
    if term_program == "WezTerm":
        return "iterm"  # WezTerm supports iTerm protocol
    return "fallback"


def show_image(image_path: Path, preview_mode: str = "terminal") -> None:
    """Display an image in the terminal or suggest alternatives."""
    if preview_mode == "none":
        return

    if preview_mode == "gallery":
        print(f"  Image saved: {image_path}")
        print("  Run `muse gallery` to view in browser")
        return

    protocol = detect_protocol()

    if protocol == "fallback":
        # Try term-image as a last resort
        try:
            from term_image.image import from_file

            img = from_file(str(image_path))
            img.draw()
            return
        except Exception:
            print(f"  Image saved: {image_path}")
            print("  Run `muse gallery` to view in browser")
            return

    if protocol == "iterm":
        _show_iterm(image_path)
    elif protocol == "kitty":
        _show_kitty(image_path)


def _show_iterm(image_path: Path) -> None:
    """Display image using iTerm2 inline image protocol."""
    import base64

    image_data = base64.b64encode(image_path.read_bytes()).decode("ascii")
    # iTerm2 proprietary escape sequence
    sys.stdout.write(f"\033]1337;File=inline=1;width=auto;height=auto:{image_data}\a")
    sys.stdout.write("\n")
    sys.stdout.flush()


def _show_kitty(image_path: Path) -> None:
    """Display image using Kitty graphics protocol."""
    import base64

    image_data = base64.b64encode(image_path.read_bytes()).decode("ascii")
    # Kitty graphics protocol — send in chunks of 4096
    while image_data:
        chunk = image_data[:4096]
        image_data = image_data[4096:]
        m = 1 if image_data else 0
        sys.stdout.write(f"\033_Ga=T,f=100,m={m};{chunk}\033\\")
    sys.stdout.write("\n")
    sys.stdout.flush()
```

- [ ] **Step 2: Commit**

```bash
cd /Users/ericchiu/vibe_coded/muse
git add src/muse/preview.py
git commit -m "feat: add terminal image preview with protocol auto-detection"
```

Note: Terminal preview is protocol-dependent and best tested manually. The core display logic is thin wrappers around standard escape sequences.

---

### Task 10: CLI Commands

**Files:**
- Create: `src/muse/cli.py`
- Create: `tests/test_cli.py`

- [ ] **Step 1: Write failing tests for CLI**

```python
# tests/test_cli.py
from click.testing import CliRunner

from muse.cli import main


class TestCLIBasics:
    def test_help(self):
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "muse" in result.output.lower() or "art" in result.output.lower()

    def test_providers_no_keys(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        runner = CliRunner()
        result = runner.invoke(main, ["providers"])
        assert result.exit_code == 0
        assert "no key" in result.output.lower() or "not found" in result.output.lower() or "none" in result.output.lower()

    def test_resume_empty(self, muse_home, monkeypatch):
        monkeypatch.setenv("MUSE_HOME", str(muse_home))
        runner = CliRunner()
        result = runner.invoke(main, ["resume"])
        assert result.exit_code == 0
        assert "no sessions" in result.output.lower()

    def test_history_no_active_session(self, muse_home, monkeypatch):
        monkeypatch.setenv("MUSE_HOME", str(muse_home))
        runner = CliRunner()
        result = runner.invoke(main, ["history"])
        assert result.exit_code != 0 or "no active session" in result.output.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/ericchiu/vibe_coded/muse && uv run pytest tests/test_cli.py -v`

Expected: ImportError — `muse.cli` does not exist.

- [ ] **Step 3: Implement cli.py**

```python
# src/muse/cli.py
"""Muse CLI — art creation tool for engineers."""

import json
import sys
from pathlib import Path

import click

from muse.config import (
    MuseConfig,
    detect_providers,
    ensure_muse_home,
    get_muse_home,
    load_config,
)
from muse.models import GeneratedImage
from muse.preview import show_image
from muse.providers import build_registry
from muse.review import ReviewEngine
from muse.session import SessionManager


def _get_context():
    """Load config, session manager, and provider registry."""
    muse_home = get_muse_home()
    ensure_muse_home(muse_home)
    config = load_config(muse_home)
    session_mgr = SessionManager(muse_home)
    registry = build_registry()
    return muse_home, config, session_mgr, registry


# Track active session in a state file
def _get_active_session(muse_home: Path) -> str | None:
    state_file = muse_home / ".active_session"
    if state_file.exists():
        return state_file.read_text().strip()
    return None


def _set_active_session(muse_home: Path, name: str) -> None:
    state_file = muse_home / ".active_session"
    state_file.write_text(name)


@click.group()
def main():
    """Muse — CLI art creation tool for engineers."""
    pass


@main.command()
@click.argument("prompt")
@click.option("--provider", default=None, help="Force a specific provider")
@click.option("--size", default=None, help="Image size (e.g. 1024x1024)")
def new(prompt, provider, size):
    """Start a new session and generate the first image."""
    muse_home, config, session_mgr, registry = _get_context()

    # Resolve provider
    if provider:
        prov = registry.get(provider)
    elif config.provider != "auto":
        prov = registry.get(config.provider)
    else:
        prov = registry.get_auto()

    if prov is None:
        click.echo("\n  No API keys detected.\n")
        click.echo("  Set up a provider:")
        click.echo('    export OPENAI_API_KEY="sk-..."')
        click.echo('    export GEMINI_API_KEY="AI..."')
        click.echo("\n  Run: muse providers")
        sys.exit(1)

    session = session_mgr.create(prompt, provider=prov.name)
    click.echo(f"  Session: {session.name}")
    click.echo(f"  Provider: {prov.name}")

    # Generate
    step_num = 1
    output_path = (
        muse_home
        / "sessions"
        / session.name
        / "steps"
        / f"step-{step_num:03d}.png"
    )
    kwargs = {"output_path": output_path}
    if size or config.size:
        kwargs["size"] = size or config.size

    try:
        result = prov.generate(prompt, **kwargs)
    except Exception as e:
        click.echo(f"  Error: {e}", err=True)
        sys.exit(1)

    session_mgr.add_step(session.name, result, parent_step=None)
    _set_active_session(muse_home, session.name)

    click.echo(f"  Step 1 saved")
    show_image(result.path, config.preview)
    click.echo()
    click.echo("  Run `muse review` for AI feedback")
    click.echo('  Run `muse tweak "..."` to iterate')
    click.echo("  Run `muse gallery` for full browser view")


@main.command()
@click.argument("prompt")
@click.option("--provider", default=None, help="Force a specific provider")
@click.option("--size", default=None, help="Image size")
@click.option("--from", "from_step", default=None, type=int, help="Branch from step N")
def tweak(prompt, provider, size, from_step):
    """Iterate on the current image with a new prompt."""
    muse_home, config, session_mgr, registry = _get_context()

    session_name = _get_active_session(muse_home)
    if not session_name:
        click.echo("  No active session. Run `muse new` or `muse resume` first.")
        sys.exit(1)

    session = session_mgr.load(session_name)
    parent = from_step or session.current_step

    # Get current image path
    current_image = (
        muse_home
        / "sessions"
        / session_name
        / "steps"
        / f"step-{parent:03d}.png"
    )

    # Resolve provider
    if provider:
        prov = registry.get(provider)
    elif config.provider != "auto":
        prov = registry.get(config.provider)
    else:
        prov = registry.get_auto()

    if prov is None:
        click.echo("  No providers available. Run `muse providers`.")
        sys.exit(1)

    step_num = session.total_steps + 1
    output_path = (
        muse_home
        / "sessions"
        / session_name
        / "steps"
        / f"step-{step_num:03d}.png"
    )
    kwargs = {"output_path": output_path}
    if size or config.size:
        kwargs["size"] = size or config.size

    try:
        result = prov.edit(current_image, prompt, **kwargs)
    except Exception as e:
        click.echo(f"  Error: {e}", err=True)
        sys.exit(1)

    session_mgr.add_step(session_name, result, parent_step=parent)
    click.echo(f"  Step {step_num} generated from step {parent}")
    show_image(result.path, config.preview)


@main.command()
@click.option("--persona", default=None, help="Review persona to use")
def review(persona):
    """Get AI critique of the current image."""
    muse_home, config, session_mgr, registry = _get_context()

    session_name = _get_active_session(muse_home)
    if not session_name:
        click.echo("  No active session. Run `muse new` or `muse resume` first.")
        sys.exit(1)

    persona_name = persona or config.persona

    # Copy bundled personas if user has none
    _ensure_personas(muse_home)

    engine = ReviewEngine(muse_home)
    history = session_mgr.get_history(session_name)
    session = session_mgr.load(session_name)

    current_image = (
        muse_home
        / "sessions"
        / session_name
        / "steps"
        / f"step-{session.current_step:03d}.png"
    )

    if not current_image.exists():
        click.echo("  No image at current step.")
        sys.exit(1)

    # Get a vision-capable provider
    vision_prov = registry.get_vision_provider()
    if vision_prov is None:
        click.echo("  No vision-capable provider available. Run `muse providers`.")
        sys.exit(1)

    try:
        result = engine.review(vision_prov, current_image, persona_name, history)
    except FileNotFoundError as e:
        click.echo(f"  {e}")
        sys.exit(1)
    except Exception as e:
        click.echo(f"  Error: {e}", err=True)
        sys.exit(1)

    click.echo()
    click.echo(result)

    session_mgr.save_review(session_name, session.current_step, result)


@main.command()
def history():
    """Show iteration history for the current session."""
    muse_home, config, session_mgr, registry = _get_context()

    session_name = _get_active_session(muse_home)
    if not session_name:
        click.echo("  No active session. Run `muse new` or `muse resume` first.")
        sys.exit(1)

    session = session_mgr.load(session_name)
    steps = session_mgr.get_history(session_name)

    click.echo(f"  {session.name}")
    for step in steps:
        marker = " <- current" if step.step == session.current_step else ""
        parent_info = ""
        if step.parent_step is not None:
            parent_info = f" (from {step.parent_step})"
        click.echo(f'  {step.step}. "{step.prompt}"{parent_info}{marker}')


@main.command()
@click.argument("n", default=1, type=int)
def back(n):
    """Roll back N steps (default 1)."""
    muse_home, config, session_mgr, registry = _get_context()

    session_name = _get_active_session(muse_home)
    if not session_name:
        click.echo("  No active session.")
        sys.exit(1)

    session = session_mgr.back(session_name, n)
    click.echo(f"  Rolled back to step {session.current_step}")

    current_image = (
        muse_home
        / "sessions"
        / session_name
        / "steps"
        / f"step-{session.current_step:03d}.png"
    )
    if current_image.exists():
        show_image(current_image, config.preview)


@main.command()
@click.argument("name", required=False)
def resume(name):
    """List sessions or resume a specific one."""
    muse_home, config, session_mgr, registry = _get_context()

    if name:
        try:
            session = session_mgr.load(name)
        except (FileNotFoundError, json.JSONDecodeError):
            click.echo(f"  Session not found: {name}")
            sys.exit(1)

        _set_active_session(muse_home, name)
        click.echo(f"  Resumed: {session.name} (step {session.current_step}/{session.total_steps})")
        return

    sessions = session_mgr.list_sessions()
    if not sessions:
        click.echo("  No sessions found. Run `muse new` to start one.")
        return

    click.echo("  Sessions:")
    active = _get_active_session(muse_home)
    for s in sessions:
        marker = " *" if s.name == active else ""
        click.echo(f"    {s.name} ({s.total_steps} steps){marker}")


@main.command()
def providers():
    """List detected providers and their status."""
    muse_home, config, session_mgr, registry = _get_context()
    available = detect_providers()

    click.echo()
    click.echo("  Provider    Status")
    click.echo("  " + "-" * 30)

    provider_names = ["openai", "gemini"]
    for name in provider_names:
        status = "ready" if name in available else "no key"
        symbol = "+" if name in available else "-"
        click.echo(f"  {symbol} {name:<12} {status}")

    click.echo()
    if available:
        click.echo(f"  Active: {available[0]} (auto-detected)")
    else:
        click.echo("  No providers found. Set an API key:")
        click.echo('    export OPENAI_API_KEY="sk-..."')
        click.echo('    export GEMINI_API_KEY="AI..."')


@main.command()
@click.argument("args", nargs=-1)
def config(args):
    """Show or set configuration."""
    muse_home, cfg, session_mgr, registry = _get_context()

    if not args:
        # Show current config
        click.echo(f"  provider: {cfg.provider}")
        click.echo(f"  persona:  {cfg.persona}")
        click.echo(f"  size:     {cfg.size}")
        click.echo(f"  preview:  {cfg.preview}")
        click.echo(f"  gallery:  port {cfg.gallery_port}")
        click.echo(f"\n  Config file: {muse_home / 'config.toml'}")
        return

    if len(args) >= 3 and args[0] == "set":
        key, value = args[1], args[2]
        _set_config_value(muse_home, key, value)
        click.echo(f"  Set {key} = {value}")
    else:
        click.echo("  Usage: muse config set <key> <value>")


@main.command()
@click.option("--port", default=None, type=int, help="Gallery port")
def gallery(port):
    """Launch the web gallery in your browser."""
    muse_home, config, session_mgr, registry = _get_context()
    gallery_port = port or config.gallery_port

    from muse.gallery.server import start_gallery
    start_gallery(muse_home, port=gallery_port)


def _set_config_value(muse_home: Path, key: str, value: str) -> None:
    """Update a single config value in config.toml."""
    import tomli_w

    try:
        import tomllib
    except ModuleNotFoundError:
        import tomli as tomllib

    config_path = muse_home / "config.toml"
    if config_path.exists():
        with open(config_path, "rb") as f:
            data = tomllib.load(f)
    else:
        data = {}

    defaults = data.setdefault("defaults", {})
    # Convert numeric values
    try:
        value = int(value)
    except ValueError:
        pass
    defaults[key] = value

    with open(config_path, "wb") as f:
        tomli_w.dump(data, f)


def _ensure_personas(muse_home: Path) -> None:
    """Copy bundled personas to ~/.muse/personas/ if missing."""
    personas_dir = muse_home / "personas"
    bundled_dir = Path(__file__).parent.parent.parent / "data" / "personas"

    if not bundled_dir.exists():
        return

    for persona_file in bundled_dir.glob("*.md"):
        dest = personas_dir / persona_file.name
        if not dest.exists():
            dest.write_text(persona_file.read_text())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/ericchiu/vibe_coded/muse && uv run pytest tests/test_cli.py -v`

Expected: All 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
cd /Users/ericchiu/vibe_coded/muse
git add src/muse/cli.py tests/test_cli.py
git commit -m "feat: add CLI commands (new, tweak, review, history, back, resume, gallery, providers, config)"
```

---

### Task 11: Web Gallery Server

**Files:**
- Create: `src/muse/gallery/__init__.py`
- Create: `src/muse/gallery/server.py`
- Create: `tests/test_gallery_api.py`

- [ ] **Step 1: Write failing tests for gallery API**

```python
# tests/test_gallery_api.py
import json
from pathlib import Path
from unittest.mock import patch

from muse.gallery.server import GalleryApp
from muse.models import GeneratedImage
from muse.session import SessionManager


class TestGalleryAPI:
    def test_sessions_endpoint_empty(self, muse_home):
        app = GalleryApp(muse_home)
        response = app.handle_api("/api/sessions")
        data = json.loads(response)
        assert data == []

    def test_sessions_endpoint_with_data(self, muse_home):
        mgr = SessionManager(muse_home)
        session = mgr.create("test session", provider="openai")
        img = GeneratedImage(
            path=Path("/tmp/test.png"),
            prompt="test",
            provider="openai",
            metadata={"model": "dall-e-3"},
        )
        mgr.add_step(session.name, img, parent_step=None)

        app = GalleryApp(muse_home)
        response = app.handle_api("/api/sessions")
        data = json.loads(response)
        assert len(data) == 1
        assert data[0]["name"] == "test-session"
        assert data[0]["total_steps"] == 1

    def test_session_detail_endpoint(self, muse_home):
        mgr = SessionManager(muse_home)
        session = mgr.create("sunset", provider="openai")
        img = GeneratedImage(
            path=Path("/tmp/test.png"),
            prompt="sunset",
            provider="openai",
            metadata={"model": "dall-e-3"},
        )
        mgr.add_step(session.name, img, parent_step=None)

        app = GalleryApp(muse_home)
        response = app.handle_api("/api/sessions/sunset")
        data = json.loads(response)
        assert data["session"]["name"] == "sunset"
        assert len(data["steps"]) == 1

    def test_session_detail_not_found(self, muse_home):
        app = GalleryApp(muse_home)
        response = app.handle_api("/api/sessions/nonexistent")
        data = json.loads(response)
        assert "error" in data
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/ericchiu/vibe_coded/muse && uv run pytest tests/test_gallery_api.py -v`

Expected: ImportError — `muse.gallery.server` does not exist.

- [ ] **Step 3: Create gallery/__init__.py**

```python
# src/muse/gallery/__init__.py
"""Web gallery for browsing muse sessions."""
```

- [ ] **Step 4: Implement gallery/server.py**

```python
# src/muse/gallery/server.py
"""HTTP server for the muse web gallery."""

import json
import mimetypes
import webbrowser
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

from muse.session import SessionManager


class GalleryApp:
    """Handles API logic for the gallery."""

    def __init__(self, muse_home: Path):
        self.muse_home = muse_home
        self.session_mgr = SessionManager(muse_home)

    def handle_api(self, path: str) -> str:
        """Route API requests and return JSON strings."""
        if path == "/api/sessions":
            return self._list_sessions()
        if path.startswith("/api/sessions/"):
            name = path[len("/api/sessions/"):]
            return self._session_detail(name)
        return json.dumps({"error": "not found"})

    def _list_sessions(self) -> str:
        sessions = self.session_mgr.list_sessions()
        return json.dumps([s.to_dict() for s in sessions], default=str)

    def _session_detail(self, name: str) -> str:
        try:
            session = self.session_mgr.load(name)
        except (FileNotFoundError, json.JSONDecodeError):
            return json.dumps({"error": f"Session not found: {name}"})

        steps = self.session_mgr.get_history(name)
        return json.dumps(
            {
                "session": session.to_dict(),
                "steps": [s.to_dict() for s in steps],
            },
            default=str,
        )


class GalleryHandler(SimpleHTTPRequestHandler):
    """HTTP handler that serves API + static files."""

    def __init__(self, *args, gallery_app: GalleryApp, static_dir: Path, **kwargs):
        self.gallery_app = gallery_app
        self.static_dir = static_dir
        super().__init__(*args, directory=str(static_dir), **kwargs)

    def do_GET(self):
        if self.path.startswith("/api/"):
            self._handle_api()
        elif self.path.startswith("/images/"):
            self._handle_image()
        else:
            super().do_GET()

    def _handle_api(self):
        response = self.gallery_app.handle_api(self.path)
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(response.encode())

    def _handle_image(self):
        """Serve images from session directories."""
        # Path format: /images/<session>/<filename>
        parts = self.path[len("/images/"):].split("/", 1)
        if len(parts) != 2:
            self.send_error(404)
            return

        session_name, filename = parts
        image_path = (
            self.gallery_app.muse_home
            / "sessions"
            / session_name
            / "steps"
            / filename
        )

        if not image_path.exists():
            self.send_error(404)
            return

        mime_type = mimetypes.guess_type(str(image_path))[0] or "image/png"
        self.send_response(200)
        self.send_header("Content-Type", mime_type)
        self.end_headers()
        self.wfile.write(image_path.read_bytes())

    def log_message(self, format, *args):
        pass  # Suppress request logs


def start_gallery(muse_home: Path, port: int = 3333, open_browser: bool = True):
    """Start the gallery HTTP server."""
    static_dir = Path(__file__).parent / "static"
    app = GalleryApp(muse_home)

    handler = partial(GalleryHandler, gallery_app=app, static_dir=static_dir)
    server = HTTPServer(("127.0.0.1", port), handler)

    url = f"http://localhost:{port}"
    print(f"  Gallery running at {url}")

    if open_browser:
        webbrowser.open(url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Gallery stopped.")
        server.server_close()
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /Users/ericchiu/vibe_coded/muse && uv run pytest tests/test_gallery_api.py -v`

Expected: All 4 tests PASS.

- [ ] **Step 6: Commit**

```bash
cd /Users/ericchiu/vibe_coded/muse
git add src/muse/gallery/ tests/test_gallery_api.py
git commit -m "feat: add gallery server with session API and image serving"
```

---

### Task 12: Web Gallery Frontend

**Files:**
- Create: `src/muse/gallery/static/index.html`
- Create: `src/muse/gallery/static/style.css`
- Create: `src/muse/gallery/static/app.js`

- [ ] **Step 1: Create index.html**

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>muse gallery</title>
    <link rel="stylesheet" href="/style.css">
</head>
<body>
    <header>
        <h1>muse</h1>
        <nav id="breadcrumb"></nav>
    </header>
    <main id="app"></main>
    <script src="/app.js"></script>
</body>
</html>
```

- [ ] **Step 2: Create style.css**

```css
/* style.css — muse gallery dark theme */
* { margin: 0; padding: 0; box-sizing: border-box; }

body {
    background: #0f0f1a;
    color: #e0e0e0;
    font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
    min-height: 100vh;
}

header {
    padding: 20px 32px;
    border-bottom: 1px solid #1e1e3a;
    display: flex;
    align-items: center;
    gap: 24px;
}

header h1 { font-size: 20px; color: #fff; font-weight: 600; }

#breadcrumb { color: #666; font-size: 14px; }
#breadcrumb a { color: #7c3aed; text-decoration: none; }

main { padding: 32px; }

/* Grid view */
.sessions-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
    gap: 20px;
}

.session-card {
    background: #1a1a2e;
    border: 1px solid #2a2a4a;
    border-radius: 12px;
    overflow: hidden;
    cursor: pointer;
    transition: border-color 0.2s, transform 0.2s;
}

.session-card:hover { border-color: #7c3aed; transform: translateY(-2px); }
.session-card img { width: 100%; height: 180px; object-fit: cover; background: #111; }
.session-card .info { padding: 12px 16px; }
.session-card .name { color: #fff; font-size: 14px; font-weight: 500; margin-bottom: 4px; }
.session-card .meta { color: #666; font-size: 12px; }

/* Timeline view */
.timeline-strip {
    display: flex; gap: 8px; overflow-x: auto;
    padding: 16px 0; margin-bottom: 24px;
}

.timeline-thumb { min-width: 80px; text-align: center; cursor: pointer; opacity: 0.6; transition: opacity 0.2s; }
.timeline-thumb.active { opacity: 1; }
.timeline-thumb img { width: 80px; height: 80px; object-fit: cover; border-radius: 8px; border: 2px solid transparent; }
.timeline-thumb.active img { border-color: #7c3aed; }
.timeline-thumb .label { font-size: 10px; color: #888; margin-top: 4px; }
.timeline-thumb.active .label { color: #7c3aed; }
.timeline-arrow { display: flex; align-items: center; color: #333; font-size: 18px; }

.step-detail { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
.step-image img { width: 100%; border-radius: 12px; background: #111; }
.step-info { background: #1a1a2e; border-radius: 12px; padding: 24px; }
.step-info .step-label { color: #7c3aed; font-size: 12px; text-transform: uppercase; margin-bottom: 8px; }
.step-info .prompt { color: #ccc; font-size: 14px; line-height: 1.5; margin-bottom: 16px; }
.step-info .metadata { color: #666; font-size: 12px; line-height: 1.8; }
.step-info .review-text { margin-top: 16px; padding-top: 16px; border-top: 1px solid #2a2a4a; color: #aaa; font-size: 13px; line-height: 1.6; }

.empty { text-align: center; color: #666; padding: 80px 0; font-size: 16px; }

@media (max-width: 768px) { .step-detail { grid-template-columns: 1fr; } }
```

- [ ] **Step 3: Create app.js**

Note: This gallery is a local-only tool serving the user's own session data. All dynamic content comes from the local `/api/` endpoints. We use `textContent` for user-generated text (prompts) and DOM construction for structure to avoid XSS concerns.

```javascript
// app.js — muse gallery SPA (local-only, serves user's own data)
const appEl = document.getElementById('app');
const breadcrumbEl = document.getElementById('breadcrumb');

let currentView = 'grid';
let currentSession = null;
let currentStep = null;
let pollTimer = null;

async function fetchJSON(url) {
    const res = await fetch(url);
    return res.json();
}

function escapeAttr(str) {
    return String(str).replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function navigate(view, session, step) {
    currentView = view;
    currentSession = session;
    currentStep = step;
    render();
}

async function render() {
    clearInterval(pollTimer);

    if (currentView === 'grid') {
        await renderGrid();
        breadcrumbEl.textContent = '';
        pollTimer = setInterval(renderGrid, 2000);
    } else if (currentView === 'timeline') {
        await renderTimeline();
        // Build breadcrumb with safe DOM methods
        breadcrumbEl.textContent = '';
        const link = document.createElement('a');
        link.href = '#';
        link.textContent = 'sessions';
        link.addEventListener('click', function(e) { e.preventDefault(); navigate('grid'); });
        breadcrumbEl.appendChild(link);
        breadcrumbEl.appendChild(document.createTextNode(' / ' + currentSession));
        pollTimer = setInterval(function() { renderTimeline(true); }, 2000);
    }
}

async function renderGrid() {
    const sessions = await fetchJSON('/api/sessions');

    if (sessions.length === 0) {
        appEl.textContent = '';
        const emptyDiv = document.createElement('div');
        emptyDiv.className = 'empty';
        emptyDiv.textContent = 'No sessions yet. Run muse new "..." to start.';
        appEl.appendChild(emptyDiv);
        return;
    }

    const grid = document.createElement('div');
    grid.className = 'sessions-grid';

    sessions.forEach(function(s) {
        const card = document.createElement('div');
        card.className = 'session-card';
        card.addEventListener('click', function() { navigate('timeline', s.name, s.current_step); });

        const img = document.createElement('img');
        img.src = '/images/' + encodeURIComponent(s.name) + '/step-' + String(s.current_step).padStart(3, '0') + '.png';
        img.alt = s.name;
        img.addEventListener('error', function() { this.style.background = '#1a1a2e'; });

        const info = document.createElement('div');
        info.className = 'info';

        const nameDiv = document.createElement('div');
        nameDiv.className = 'name';
        nameDiv.textContent = s.name;

        const metaDiv = document.createElement('div');
        metaDiv.className = 'meta';
        metaDiv.textContent = s.total_steps + ' step' + (s.total_steps !== 1 ? 's' : '') + ' \u00b7 ' + s.provider;

        info.appendChild(nameDiv);
        info.appendChild(metaDiv);
        card.appendChild(img);
        card.appendChild(info);
        grid.appendChild(card);
    });

    appEl.textContent = '';
    appEl.appendChild(grid);
}

async function renderTimeline(isPolling) {
    const data = await fetchJSON('/api/sessions/' + encodeURIComponent(currentSession));

    if (data.error) {
        appEl.textContent = '';
        const errDiv = document.createElement('div');
        errDiv.className = 'empty';
        errDiv.textContent = data.error;
        appEl.appendChild(errDiv);
        return;
    }

    const session = data.session;
    const steps = data.steps;
    if (!currentStep) currentStep = session.current_step;

    // Don't re-render if nothing changed during polling
    if (isPolling && steps.length === parseInt(appEl.dataset.stepCount || '0', 10)) return;
    appEl.dataset.stepCount = steps.length;

    const activeStep = steps.find(function(s) { return s.step === currentStep; }) || steps[steps.length - 1];

    // Build timeline strip
    const strip = document.createElement('div');
    strip.className = 'timeline-strip';

    steps.forEach(function(s, i) {
        var thumb = document.createElement('div');
        thumb.className = 'timeline-thumb' + (s.step === currentStep ? ' active' : '');
        thumb.addEventListener('click', function() { currentStep = s.step; renderTimeline(); });

        var thumbImg = document.createElement('img');
        thumbImg.src = '/images/' + encodeURIComponent(session.name) + '/step-' + String(s.step).padStart(3, '0') + '.png';
        thumbImg.alt = 'Step ' + s.step;
        thumbImg.addEventListener('error', function() { this.style.background = '#1a1a2e'; });

        var label = document.createElement('div');
        label.className = 'label';
        label.textContent = 'Step ' + s.step + (s.step === session.current_step ? ' \u2605' : '');

        thumb.appendChild(thumbImg);
        thumb.appendChild(label);
        strip.appendChild(thumb);

        if (i < steps.length - 1) {
            var arrow = document.createElement('div');
            arrow.className = 'timeline-arrow';
            arrow.textContent = '\u2192';
            strip.appendChild(arrow);
        }
    });

    // Build step detail
    var detail = document.createElement('div');
    detail.className = 'step-detail';

    var imageDiv = document.createElement('div');
    imageDiv.className = 'step-image';
    var mainImg = document.createElement('img');
    mainImg.src = '/images/' + encodeURIComponent(session.name) + '/' + activeStep.image;
    mainImg.alt = 'Step ' + activeStep.step;
    imageDiv.appendChild(mainImg);

    var infoDiv = document.createElement('div');
    infoDiv.className = 'step-info';

    var stepLabel = document.createElement('div');
    stepLabel.className = 'step-label';
    stepLabel.textContent = 'Step ' + activeStep.step + (activeStep.step === session.current_step ? ' \u2014 current' : '');

    var prompt = document.createElement('div');
    prompt.className = 'prompt';
    prompt.textContent = '"' + activeStep.prompt + '"';

    var metadata = document.createElement('div');
    metadata.className = 'metadata';
    var metaLines = ['Provider: ' + activeStep.provider, 'Model: ' + activeStep.model];
    if (activeStep.parent_step) metaLines.push('From step: ' + activeStep.parent_step);
    metaLines.push(activeStep.timestamp);
    metadata.textContent = metaLines.join(' | ');

    infoDiv.appendChild(stepLabel);
    infoDiv.appendChild(prompt);
    infoDiv.appendChild(metadata);

    detail.appendChild(imageDiv);
    detail.appendChild(infoDiv);

    appEl.textContent = '';
    appEl.appendChild(strip);
    appEl.appendChild(detail);
}

// Initial render
navigate('grid');
```

- [ ] **Step 4: Commit**

```bash
cd /Users/ericchiu/vibe_coded/muse
git add src/muse/gallery/static/
git commit -m "feat: add web gallery frontend (grid + timeline views, dark theme)"
```

---

### Task 13: Integration Test

**Files:**
- Create: `tests/test_integration.py`

- [ ] **Step 1: Write integration test for the full loop**

```python
# tests/test_integration.py
"""Integration test: new -> tweak -> review -> back -> history."""
from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from muse.cli import main


def _make_mock_registry(mock_provider):
    """Create a mock registry that returns our mock provider."""
    from muse.providers import ProviderRegistry

    registry = ProviderRegistry()
    mock_cls = MagicMock()
    mock_cls.is_available.return_value = True
    mock_cls.return_value = mock_provider
    registry.register("mock", mock_cls)
    return registry


class TestFullLoop:
    def test_new_tweak_review_back_history(self, muse_home, mock_provider, monkeypatch):
        monkeypatch.setenv("MUSE_HOME", str(muse_home))
        runner = CliRunner()

        mock_reg = _make_mock_registry(mock_provider)

        with patch("muse.cli.build_registry", return_value=mock_reg):
            # Step 1: muse new
            result = runner.invoke(main, ["new", "sunset over mountains"])
            assert result.exit_code == 0, result.output
            assert "session" in result.output.lower()
            assert "step 1" in result.output.lower()

            # Step 2: muse tweak
            result = runner.invoke(main, ["tweak", "make sky more purple"])
            assert result.exit_code == 0, result.output
            assert "step 2" in result.output.lower()

            # Step 3: muse review
            result = runner.invoke(main, ["review"])
            assert result.exit_code == 0, result.output
            assert "white square" in result.output.lower()

            # Step 4: muse history
            result = runner.invoke(main, ["history"])
            assert result.exit_code == 0, result.output
            assert "sunset over mountains" in result.output
            assert "make sky more purple" in result.output
            assert "current" in result.output.lower()

            # Step 5: muse back
            result = runner.invoke(main, ["back"])
            assert result.exit_code == 0, result.output
            assert "step 1" in result.output.lower()

            # Step 6: verify history shows step 1 as current
            result = runner.invoke(main, ["history"])
            assert result.exit_code == 0, result.output
            # Step 1 should be current now
            lines = result.output.strip().split("\n")
            for line in lines:
                if "1." in line:
                    assert "current" in line.lower()
```

- [ ] **Step 2: Run integration test**

Run: `cd /Users/ericchiu/vibe_coded/muse && uv run pytest tests/test_integration.py -v`

Expected: PASS — full loop works end to end with mocked provider.

- [ ] **Step 3: Run all tests**

Run: `cd /Users/ericchiu/vibe_coded/muse && uv run pytest -v`

Expected: All tests PASS.

- [ ] **Step 4: Commit**

```bash
cd /Users/ericchiu/vibe_coded/muse
git add tests/test_integration.py
git commit -m "test: add integration test for full muse loop"
```

---

### Task 14: Package Data and Final Polish

**Files:**
- Modify: `pyproject.toml` (include data files)
- Create: `.gitignore`

- [ ] **Step 1: Update pyproject.toml to include data files and gallery static**

Add to `pyproject.toml`:

```toml
[tool.hatch.build.targets.wheel.force-include]
"data/personas" = "data/personas"
```

- [ ] **Step 2: Create .gitignore**

```
__pycache__/
*.pyc
.venv/
*.egg-info/
dist/
build/
.superpowers/
```

- [ ] **Step 3: Verify install and entry point**

Run: `cd /Users/ericchiu/vibe_coded/muse && uv pip install -e ".[dev]" && uv run muse --help`

Expected: Help text displays all commands: `new`, `tweak`, `review`, `history`, `back`, `resume`, `gallery`, `providers`, `config`.

- [ ] **Step 4: Run full test suite one final time**

Run: `cd /Users/ericchiu/vibe_coded/muse && uv run pytest -v`

Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
cd /Users/ericchiu/vibe_coded/muse
git add pyproject.toml .gitignore
git commit -m "chore: add .gitignore and configure package data inclusion"
```
