"""
AI Router Engine - Automatically selects the best AI model
"""
import asyncio
import time
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass
import httpx


class ModelType(Enum):
    GPT4 = "gpt-4"
    CLAUDE = "claude-3-opus"
    GEMINI = "gemini-pro"
    LLAMA = "llama-3-70b"
    OFFLINE = "offline-llama"


@dataclass
class ModelPerformance:
    model: ModelType
    latency_ms: float
    success_rate: float
    cost_per_1k_tokens: float
    capabilities: List[str]
    is_available: bool


class AIRouter:
    def __init__(self):
        self.models: Dict[ModelType, ModelPerformance] = {}
        self.query_history: List[Dict] = []
        self._init_models()

    def _init_models(self):
        from app.config import settings
        self.models = {
            ModelType.GPT4: ModelPerformance(
                model=ModelType.GPT4, latency_ms=800, success_rate=0.99,
                cost_per_1k_tokens=0.03,
                capabilities=["reasoning", "coding", "creative", "analysis"],
                is_available=bool(settings.OPENAI_API_KEY)
            ),
            ModelType.CLAUDE: ModelPerformance(
                model=ModelType.CLAUDE, latency_ms=900, success_rate=0.98,
                cost_per_1k_tokens=0.015,
                capabilities=["reasoning", "coding", "analysis", "long_context"],
                is_available=bool(settings.ANTHROPIC_API_KEY)
            ),
            ModelType.GEMINI: ModelPerformance(
                model=ModelType.GEMINI, latency_ms=600, success_rate=0.97,
                cost_per_1k_tokens=0.01,
                capabilities=["reasoning", "multimodal", "coding"],
                is_available=bool(settings.GOOGLE_API_KEY)
            ),
            ModelType.LLAMA: ModelPerformance(
                model=ModelType.LLAMA, latency_ms=1200, success_rate=0.95,
                cost_per_1k_tokens=0.005,
                capabilities=["reasoning", "coding"], is_available=True
            ),
            ModelType.OFFLINE: ModelPerformance(
                model=ModelType.OFFLINE, latency_ms=500, success_rate=0.90,
                cost_per_1k_tokens=0.0,
                capabilities=["basic_chat", "summarization"],
                is_available=settings.ENABLE_OFFLINE
            )
        }

    def analyze_query(self, query: str) -> Dict[str, Any]:
        complexity_score = 0
        required_capabilities = []

        if any(kw in query.lower() for kw in ["code", "programming", "function", "bug"]):
            complexity_score += 3
            required_capabilities.append("coding")

        if any(kw in query.lower() for kw in ["write", "story", "creative", "imagine"]):
            complexity_score += 2
            required_capabilities.append("creative")

        if any(kw in query.lower() for kw in ["analyze", "compare", "evaluate", "research"]):
            complexity_score += 3
            required_capabilities.append("analysis")

        if any(kw in query.lower() for kw in ["math", "calculate", "solve", "logic"]):
            complexity_score += 4
            required_capabilities.append("reasoning")

        if len(query) > 500:
            complexity_score += 2

        return {
            "complexity": min(complexity_score, 10),
            "required_capabilities": required_capabilities,
            "estimated_tokens": len(query) // 4 + 100
        }

    def select_model(self, query: str, prefer_offline: bool = False) -> ModelType:
        analysis = self.analyze_query(query)

        if prefer_offline and self.models[ModelType.OFFLINE].is_available:
            if analysis["complexity"] <= 3:
                return ModelType.OFFLINE

        model_scores = {}
        for model_type, performance in self.models.items():
            if not performance.is_available:
                continue

            score = 0
            for cap in analysis["required_capabilities"]:
                if cap in performance.capabilities:
                    score += 3

            score += (2000 - performance.latency_ms) / 200
            score += performance.success_rate * 2

            model_scores[model_type] = score

        if not model_scores:
            return ModelType.LLAMA

        best_model = max(model_scores, key=model_scores.get)

        self.query_history.append({
            "query": query[:100],
            "selected_model": best_model.value,
            "complexity": analysis["complexity"],
            "timestamp": time.time()
        })

        return best_model

    async def route_query(self, query: str, context: Optional[str] = None,
                         prefer_offline: bool = False) -> Dict[str, Any]:
        from app.config import settings
        model = self.select_model(query, prefer_offline)
        start_time = time.time()

        try:
            if model == ModelType.GPT4:
                response = await self._call_openai(query, context)
            elif model == ModelType.CLAUDE:
                response = await self._call_anthropic(query, context)
            elif model == ModelType.GEMINI:
                response = await self._call_gemini(query, context)
            elif model == ModelType.LLAMA:
                response = await self._call_llama(query, context)
            else:
                response = await self._call_offline(query, context)

            latency = (time.time() - start_time) * 1000

            return {
                "success": True, "model_used": model.value,
                "response": response, "latency_ms": latency, "cached": False
            }

        except Exception as e:
            for fallback in settings.FALLBACK_MODELS:
                try:
                    if fallback == "gpt-4":
                        response = await self._call_openai(query, context)
                    elif fallback == "claude-3":
                        response = await self._call_anthropic(query, context)
                    elif fallback == "gemini-pro":
                        response = await self._call_gemini(query, context)
                    else:
                        response = await self._call_llama(query, context)

                    return {
                        "success": True, "model_used": fallback,
                        "response": response,
                        "latency_ms": (time.time() - start_time) * 1000,
                        "fallback": True
                    }
                except Exception:
                    continue

            return {"success": False, "error": str(e), "model_used": model.value}

    async def _call_openai(self, query: str, context: Optional[str]) -> str:
        from app.config import settings
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"},
                json={
                    "model": "gpt-4",
                    "messages": [
                        {"role": "system", "content": context or "You are a helpful assistant"},
                        {"role": "user", "content": query}
                    ]
                }
            )
            return response.json()["choices"][0]["message"]["content"]

    async def _call_anthropic(self, query: str, context: Optional[str]) -> str:
        from app.config import settings
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": settings.ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01"},
                json={"model": "claude-3-opus-20240229", "max_tokens": 1024,
                      "messages": [{"role": "user", "content": query}]}
            )
            return response.json()["content"][0]["text"]

    async def _call_gemini(self, query: str, context: Optional[str]) -> str:
        from app.config import settings
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={settings.GOOGLE_API_KEY}",
                json={"contents": [{"parts": [{"text": query}]}]}
            )
            return response.json()["candidates"][0]["content"]["parts"][0]["text"]

    async def _call_llama(self, query: str, context: Optional[str]) -> str:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:11434/api/generate",
                json={"model": "llama3", "prompt": query, "stream": False}
            )
            return response.json()["response"]

    async def _call_offline(self, query: str, context: Optional[str]) -> str:
        return "Offline response: " + query[:100]


router = AIRouter()
