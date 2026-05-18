import json
import time
import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any
import anthropic
from config import settings

logger = logging.getLogger("copago.agents")
_client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)


@dataclass
class AgentResult:
    success: bool
    data: dict = field(default_factory=dict)
    raw_text: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0
    error: str = ""


class CircuitBreaker:
    def __init__(self, threshold: int = 5, recovery_timeout: int = 60):
        self._failures = 0
        self._threshold = threshold
        self._recovery_timeout = recovery_timeout
        self._opened_at: float | None = None

    @property
    def is_open(self) -> bool:
        if self._opened_at is None:
            return False
        if time.time() - self._opened_at >= self._recovery_timeout:
            self._failures = 0
            self._opened_at = None
            return False
        return True

    def record_failure(self):
        self._failures += 1
        if self._failures >= self._threshold:
            self._opened_at = time.time()
            logger.warning("CircuitBreaker OPEN — too many failures")

    def record_success(self):
        self._failures = 0
        self._opened_at = None


def parse_json_safe(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1]) if len(lines) > 2 else text
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass
    return {}


class BaseAgent:
    name: str = "base"
    temperature: float = 0.1
    max_tokens: int = 1024
    _circuit_breaker = CircuitBreaker(
        threshold=settings.circuit_breaker_failure_threshold,
        recovery_timeout=settings.circuit_breaker_recovery_timeout,
    )

    def _load_prompt(self, version: str = None) -> str:
        v = version or settings.prompt_version
        import pathlib
        prompt_path = pathlib.Path(__file__).parent / "prompts" / f"{self.name}_{v}.txt"
        return prompt_path.read_text(encoding="utf-8")

    async def _call(self, system: str, user: str) -> AgentResult:
        if self._circuit_breaker.is_open:
            return AgentResult(success=False, error="Servicio temporalmente no disponible")
        t0 = time.perf_counter()
        try:
            response = await _client.messages.create(
                model=settings.claude_model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            elapsed = int((time.perf_counter() - t0) * 1000)
            raw = response.content[0].text
            data = parse_json_safe(raw)
            self._circuit_breaker.record_success()
            return AgentResult(
                success=True,
                data=data,
                raw_text=raw,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                latency_ms=elapsed,
            )
        except Exception as exc:
            self._circuit_breaker.record_failure()
            logger.error("Agent %s error: %s", self.name, exc)
            return AgentResult(success=False, error=str(exc), latency_ms=int((time.perf_counter() - t0) * 1000))
