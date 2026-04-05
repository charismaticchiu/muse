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
