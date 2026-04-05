import json
from pathlib import Path

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
