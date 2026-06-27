"""
Image Generation - Multiple AI providers
"""
import asyncio
import base64
from typing import Dict, Optional, Any
import httpx


class ImageGenerator:
    def __init__(self):
        from app.config import settings
        self.providers = {
            "openai": bool(settings.OPENAI_API_KEY),
            "stability": bool(settings.STABILITY_API_KEY),
            "replicate": bool(settings.REPLICATE_API_TOKEN),
            "local": settings.ENABLE_OFFLINE
        }

    async def generate(self, prompt: str, size: str = "1024x1024",
                      style: Optional[str] = None,
                      provider: Optional[str] = None) -> Dict[str, Any]:
        enhanced_prompt = self._enhance_prompt(prompt, style)

        if provider and self.providers.get(provider):
            selected_provider = provider
        else:
            selected_provider = self._select_provider()

        start_time = asyncio.get_event_loop().time()

        try:
            if selected_provider == "openai":
                result = await self._generate_openai(enhanced_prompt, size)
            elif selected_provider == "stability":
                result = await self._generate_stability(enhanced_prompt, size)
            elif selected_provider == "replicate":
                result = await self._generate_replicate(enhanced_prompt, size)
            else:
                result = await self._generate_local(enhanced_prompt, size)

            generation_time = asyncio.get_event_loop().time() - start_time

            return {
                "success": True, "provider": selected_provider,
                "prompt": enhanced_prompt, "image_data": result["image_data"],
                "format": result.get("format", "png"),
                "generation_time": generation_time, "size": size
            }
        except Exception as e:
            for fallback in ["stability", "replicate", "local"]:
                if fallback != selected_provider and self.providers.get(fallback):
                    try:
                        if fallback == "stability":
                            result = await self._generate_stability(enhanced_prompt, size)
                        elif fallback == "replicate":
                            result = await self._generate_replicate(enhanced_prompt, size)
                        else:
                            result = await self._generate_local(enhanced_prompt, size)
                        return {
                            "success": True, "provider": fallback,
                            "prompt": enhanced_prompt, "image_data": result["image_data"],
                            "format": result.get("format", "png"), "fallback": True
                        }
                    except Exception:
                        continue

            return {"success": False, "error": str(e), "provider": selected_provider}

    def _enhance_prompt(self, prompt: str, style: Optional[str]) -> str:
        style_modifiers = {
            "photorealistic": "highly detailed, photorealistic, 8k, professional photography",
            "anime": "anime style, manga, vibrant colors, detailed",
            "oil_painting": "oil painting style, artistic, textured, museum quality",
            "digital_art": "digital art, concept art, trending on artstation",
            "cinematic": "cinematic, dramatic lighting, movie still, film grain",
            "3d": "3D render, octane render, blender, unreal engine 5"
        }
        if style and style in style_modifiers:
            return f"{prompt}, {style_modifiers[style]}"
        return prompt

    def _select_provider(self) -> str:
        if self.providers["openai"]:
            return "openai"
        elif self.providers["stability"]:
            return "stability"
        elif self.providers["replicate"]:
            return "replicate"
        return "local"

    async def _generate_openai(self, prompt: str, size: str) -> Dict:
        from app.config import settings
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/images/generations",
                headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"},
                json={"model": "dall-e-3", "prompt": prompt, "size": size,
                      "quality": "standard", "n": 1}, timeout=60.0
            )
            data = response.json()
            image_url = data["data"][0]["url"]
            image_response = await client.get(image_url)
            return {"image_data": base64.b64encode(image_response.content).decode()}

    async def _generate_stability(self, prompt: str, size: str) -> Dict:
        from app.config import settings
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image",
                headers={"Authorization": f"Bearer {settings.STABILITY_API_KEY}",
                         "Content-Type": "application/json"},
                json={"text_prompts": [{"text": prompt}], "cfg_scale": 7,
                      "samples": 1, "steps": 30}, timeout=60.0
            )
            data = response.json()
            return {"image_data": data["artifacts"][0]["base64"]}

    async def _generate_replicate(self, prompt: str, size: str) -> Dict:
        from app.config import settings
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.replicate.com/v1/predictions",
                headers={"Authorization": f"Token {settings.REPLICATE_API_TOKEN}"},
                json={"version": "stability-ai/stable-diffusion-xl-base-1.0",
                      "input": {"prompt": prompt}}
            )
            prediction = response.json()
            prediction_id = prediction["id"]
            while True:
                status_response = await client.get(
                    f"https://api.replicate.com/v1/predictions/{prediction_id}",
                    headers={"Authorization": f"Token {settings.REPLICATE_API_TOKEN}"}
                )
                status_data = status_response.json()
                if status_data["status"] == "succeeded":
                    image_url = status_data["output"][0]
                    image_response = await client.get(image_url)
                    return {"image_data": base64.b64encode(image_response.content).decode()}
                elif status_data["status"] == "failed":
                    raise Exception("Generation failed")
                await asyncio.sleep(1)

    async def _generate_local(self, prompt: str, size: str) -> Dict:
        return {"image_data": "placeholder_local_generation"}


image_generator = ImageGenerator()
