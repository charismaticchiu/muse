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
        ...

    @abstractmethod
    def edit(self, image: Path, prompt: str, **kwargs) -> GeneratedImage:
        ...

    @abstractmethod
    def describe(self, image: Path, system_prompt: str) -> str:
        ...

    @classmethod
    @abstractmethod
    def is_available(cls) -> bool:
        ...
