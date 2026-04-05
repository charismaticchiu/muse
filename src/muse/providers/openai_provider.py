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
