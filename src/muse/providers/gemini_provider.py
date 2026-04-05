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
