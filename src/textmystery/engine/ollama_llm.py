from __future__ import annotations

import time

try:
    import ollama as _ollama
except ImportError:
    _ollama = None  # type: ignore[assignment]

try:
    from orket_extension_sdk.llm import GenerateRequest, GenerateResponse
except ImportError:
    GenerateRequest = None  # type: ignore[assignment,misc]
    GenerateResponse = None  # type: ignore[assignment,misc]


class OllamaLLMProvider:
    """Sync LLMProvider backed by local Ollama."""

    def __init__(self, model: str = "llama3.1:8b", timeout: int = 5) -> None:
        self.model = model
        self.timeout = timeout
        self._available: bool | None = None

    def is_available(self) -> bool:
        if _ollama is None:
            return False
        if self._available is not None:
            return self._available
        try:
            client = _ollama.Client()
            response = client.list()
            models = response.get("models", [])
            if not models and hasattr(response, "models"):
                models = response.models or []
            model_names: list[str] = []
            for m in models:
                name = m.get("name", "") if isinstance(m, dict) else getattr(m, "model", "")
                model_names.append(str(name))
            self._available = any(self.model in n for n in model_names)
        except Exception:
            self._available = False
        return self._available

    def generate(self, request: GenerateRequest) -> GenerateResponse:
        if not self.is_available():
            return GenerateResponse(text="", model=self.model, latency_ms=0)

        messages = [
            {"role": "system", "content": request.system_prompt},
            {"role": "user", "content": request.user_message},
        ]
        options: dict = {"temperature": request.temperature, "num_predict": request.max_tokens}
        if request.stop_sequences:
            options["stop"] = list(request.stop_sequences)

        started = time.perf_counter()
        try:
            client = _ollama.Client()
            response = client.chat(model=self.model, messages=messages, options=options)
            content = response.get("message", {}).get("content", "")
            if not content and hasattr(response, "message"):
                content = getattr(response.message, "content", "")
            latency_ms = int((time.perf_counter() - started) * 1000)
            return GenerateResponse(
                text=str(content),
                model=self.model,
                latency_ms=latency_ms,
                input_tokens=response.get("prompt_eval_count"),
                output_tokens=response.get("eval_count"),
            )
        except Exception:
            latency_ms = int((time.perf_counter() - started) * 1000)
            return GenerateResponse(text="", model=self.model, latency_ms=latency_ms)
