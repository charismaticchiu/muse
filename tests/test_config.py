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
