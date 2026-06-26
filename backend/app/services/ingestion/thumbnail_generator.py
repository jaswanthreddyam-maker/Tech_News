import io
import os
import time
import logging
from typing import Dict, Any, Optional

from PIL import Image

from app.core.config import settings

logger = logging.getLogger(__name__)

class GeneratedThumbnail:
    def __init__(self, image_bytes: bytes, provider_name: str, model_version: str, duration_ms: int):
        self.image_bytes = image_bytes
        self.provider_name = provider_name
        self.model_version = model_version
        self.duration_ms = duration_ms

class ThumbnailImageGenerator:
    async def generate_image(self, spec: Dict[str, Any]) -> Optional[GeneratedThumbnail]:
        raise NotImplementedError()

class ImagenGenerator(ThumbnailImageGenerator):
    def __init__(self):
        try:
            from google import genai
            from app.core.config import settings
            if getattr(settings, "GEMINI_API_KEY", None) == "mock-happy-path":
                self.client = None
                self.model_name = "imagen-3.0-generate-001"
            else:
                self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
                self.model_name = "imagen-3.0-generate-001"
        except ImportError:
            self.client = None
            logger.warning("google-genai not installed. Imagen generator unavailable.")

    async def generate_image(self, spec: Dict[str, Any]) -> Optional[GeneratedThumbnail]:
        from app.core.config import settings
        if getattr(settings, "GEMINI_API_KEY", None) == "mock-happy-path":
            logger.info("ImagenGenerator: Executing Mock Happy Path")
            t0 = time.time()
            import asyncio
            await asyncio.sleep(1)
            
            # Create a solid color dummy image using PIL
            img = Image.new("RGB", (1200, 630), color=(147, 112, 219)) # Medium Purple
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format="JPEG")
            image_bytes = img_byte_arr.getvalue()
            
            return GeneratedThumbnail(
                image_bytes=image_bytes,
                provider_name="Imagen (Mock)",
                model_version=self.model_name,
                duration_ms=int((time.time() - t0) * 1000)
            )

        if not self.client:
            return None
            
        prompt = self._build_prompt(spec)
        logger.info(f"ImagenGenerator: Requesting image with prompt: {prompt}")
        
        t0 = time.time()
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            
            def _call_imagen():
                from google.genai import types
                return self.client.models.generate_images(
                    model=self.model_name,
                    prompt=prompt,
                    config=types.GenerateImagesConfig(
                        number_of_images=1,
                        output_mime_type="image/jpeg",
                        aspect_ratio="16:9"
                    )
                )

            result = await loop.run_in_executor(None, _call_imagen)
            duration_ms = int((time.time() - t0) * 1000)
            
            if not result.generated_images:
                logger.warning("ImagenGenerator: No images returned.")
                return None
                
            image_bytes = result.generated_images[0].image.image_bytes
            return GeneratedThumbnail(
                image_bytes=image_bytes,
                provider_name="Imagen",
                model_version=self.model_name,
                duration_ms=duration_ms
            )
        except Exception as e:
            logger.error(f"ImagenGenerator failed: {e}", exc_info=True)
            return None

    def _build_prompt(self, spec: Dict[str, Any]) -> str:
        base_style = spec.get("style", "professional editorial illustration, modern, clean, trustworthy")
        visuals = ", ".join(spec.get("visual_elements", []))
        topic = spec.get("topic", "")
        
        prompt = f"A high-quality {base_style} about {topic}. Visual elements: {visuals}."
        avoid = spec.get("avoid", [])
        if avoid:
            prompt += f" Do not include: {', '.join(avoid)}."
            
        return prompt

class OpenAIGenerator(ThumbnailImageGenerator):
    def __init__(self):
        try:
            from openai import AsyncOpenAI
            if hasattr(settings, "OPENAI_API_KEY") and settings.OPENAI_API_KEY:
                self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            else:
                self.client = None
        except ImportError:
            self.client = None

    async def generate_image(self, spec: Dict[str, Any]) -> Optional[GeneratedThumbnail]:
        if not self.client:
            return None
            
        prompt = self._build_prompt(spec)
        logger.info(f"OpenAIGenerator: Requesting image with prompt: {prompt}")
        
        t0 = time.time()
        try:
            response = await self.client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size="1024x1024",
                quality="standard",
                n=1,
            )
            duration_ms = int((time.time() - t0) * 1000)
            
            image_url = response.data[0].url
            
            # Download the image bytes
            import httpx
            async with httpx.AsyncClient() as http_client:
                img_res = await http_client.get(image_url)
                img_res.raise_for_status()
                image_bytes = img_res.content
                
            return GeneratedThumbnail(
                image_bytes=image_bytes,
                provider_name="OpenAI DALL-E",
                model_version="dall-e-3",
                duration_ms=duration_ms
            )
        except Exception as e:
            logger.error(f"OpenAIGenerator failed: {e}", exc_info=True)
            return None

    def _build_prompt(self, spec: Dict[str, Any]) -> str:
        base_style = spec.get("style", "professional editorial illustration, modern, clean, trustworthy")
        visuals = ", ".join(spec.get("visual_elements", []))
        topic = spec.get("topic", "")
        
        prompt = f"A high-quality {base_style} about {topic}. Visual elements: {visuals}. Do not include any text or words."
        return prompt

class MockGenerator(ThumbnailImageGenerator):
    async def generate_image(self, spec: Dict[str, Any]) -> Optional[GeneratedThumbnail]:
        logger.info(f"MockGenerator: Generating mock image for spec: {spec.get('headline')}")
        t0 = time.time()
        import asyncio
        await asyncio.sleep(1.5)  # Simulate network latency
        
        # Create a solid color dummy image using PIL
        img = Image.new("RGB", (1200, 630), color=(73, 109, 137))
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format="JPEG")
        image_bytes = img_byte_arr.getvalue()
        
        duration_ms = int((time.time() - t0) * 1000)
        
        return GeneratedThumbnail(
            image_bytes=image_bytes,
            provider_name="Mock Generator",
            model_version="v1.0-mock",
            duration_ms=duration_ms
        )

class ThumbnailImageService:
    def __init__(self):
        self.generators = [
            ImagenGenerator(),
            OpenAIGenerator()
        ]
        
    async def generate(self, spec: Dict[str, Any]) -> Optional[GeneratedThumbnail]:
        for gen in self.generators:
            result = await gen.generate_image(spec)
            if result:
                return result
        return None
