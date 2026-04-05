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
            name for name, cls in self._providers.items()
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
