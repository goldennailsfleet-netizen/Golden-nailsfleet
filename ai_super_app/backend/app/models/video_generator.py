"""
Video Generation - Text to Video
"""
import asyncio
from typing import Dict, Optional, Any
import httpx


class VideoGenerator:
    def __init__(self):
        from app.config import settings
        self.providers = {
            "runway": bool(settings.REPLICATE_API_TOKEN),
            "pika": False,
            "replicate": bool(settings.REPLICATE_API_TOKEN),
            "local": settings.ENABLE_OFFLINE
        }

    async def generate(self, prompt: str, duration: int = 4,
                      resolution: str = "720p",
                      style: Optional[str] = None,
                      provider: Optional[str] = None) -> Dict[str, Any]:
        enhanced_prompt = self._enhance_prompt(prompt, style)

        if provider and self.providers.get(provider):
            selected_provider = provider
        else:
            selected_provider = self._select_provider()

        start_time = asyncio.get_event_loop().time()

        try:
            if selected_provider == "runway":
                result = await self._generate_runway(enhanced_prompt, duration, resolution)
            elif selected_provider == "replicate":
                result = await self._generate_replicate(enhanced_prompt, duration, resolution)
            else:
                result = await self._generate_local(enhanced_prompt, duration, resolution)

            generation_time = asyncio.get_event_loop().time() - start_time

            return {
                "success": True, "provider": selected_provider,
                "prompt": enhanced_prompt, "video_url": result.get("video_url"),
                "video_data": result.get("video_data"),
                "duration": duration, "resolution": resolution,
                "generation_time": generation_time
            }
        except Exception as e:
            return {"success": False, "error": str(e), "provider": selected_provider}

    def _enhance_prompt(self, prompt: str, style: Optional[str]) -> str:
        style_modifiers = {
            "cinematic": "cinematic shot, professional filmmaking, dramatic lighting",
            "anime": "anime style animation, smooth motion, vibrant colors",
            "realistic": "photorealistic, smooth camera movement, high quality",
            "3d": "3D animation, blender render, smooth motion"
        }
        if style and style in style_modifiers:
            return f"{prompt}, {style_modifiers[style]}"
        return prompt

    def _select_provider(self) -> str:
        if self.providers["runway"]:
            return "runway"
        elif self.providers["replicate"]:
            return "replicate"
        return "local"

    async def _generate_runway(self, prompt: str, duration: int, resolution: str) -> Dict:
        from app.config import settings
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.replicate.com/v1/predictions",
                headers={"Authorization": f"Token {settings.REPLICATE_API_TOKEN}"},
                json={"version": "runwayml/gen-2",
                      "input": {"prompt": prompt,
                                "num_frames": duration * 24,
                                "width": 1280 if resolution == "720p" else 1920,
                                "height": 720 if resolution == "720p" else 1080}}
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
                    return {"video_url": status_data["output"]}
                elif status_data["status"] == "failed":
                    raise Exception("Video generation failed")
                await asyncio.sleep(2)

    async def _generate_replicate(self, prompt: str, duration: int, resolution: str) -> Dict:
        from app.config import settings
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.replicate.com/v1/predictions",
                headers={"Authorization": f"Token {settings.REPLICATE_API_TOKEN}"},
                json={"version": "stability-ai/stable-video-diffusion",
                      "input": {"prompt": prompt, "num_frames": duration * 24}}
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
                    return {"video_url": status_data["output"]}
                elif status_data["status"] == "failed":
                    raise Exception("Video generation failed")
                await asyncio.sleep(2)

    async def _generate_local(self, prompt: str, duration: int, resolution: str) -> Dict:
        return {"video_url": "placeholder_local_video_generation"}


video_generator = VideoGenerator()
