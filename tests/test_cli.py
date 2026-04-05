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
