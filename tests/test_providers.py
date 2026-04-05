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
