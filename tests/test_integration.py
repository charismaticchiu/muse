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
            lines = result.output.strip().split("\n")
            for line in lines:
                if "1." in line:
                    assert "current" in line.lower()
