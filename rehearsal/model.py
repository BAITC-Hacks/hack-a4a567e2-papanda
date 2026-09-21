"""Explicit model configuration; Agents SDK orchestration; no synthetic fallback."""
import asyncio
import json
import os
import time
from dataclasses import asdict, is_dataclass

from agents import Agent, Runner, RunConfig, OpenAIChatCompletionsModel, OpenAIResponsesModel
from openai import AsyncOpenAI, APIConnectionError, APIStatusError
from pydantic import BaseModel


class ModelGatewayError(RuntimeError):
    """A technical generation failure, never evidence of a contradiction."""


class ModelGateway:
    def __init__(self, model: str, log, *, base_url=None, api_key=None,
                 api_mode=None, structured_mode=None, timeout=60.0, retries=1):
        if not model or not model.strip():
            raise ValueError("Укажите OPENAI_MODEL явно")
        if timeout <= 0 or retries not in (0, 1, 2):
            raise ValueError("timeout должен быть положительным; retries: 0, 1 или 2")
        base_url = base_url or os.getenv("OPENAI_BASE_URL")
        api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("Нужен OPENAI_API_KEY выбранного провайдера; для локального сервера укажите его тестовое значение явно")
        self.api_mode = api_mode or os.getenv("OPENAI_API_MODE") or ("chat_completions" if base_url else "responses")
        self.structured_mode = structured_mode or os.getenv("OPENAI_STRUCTURED_MODE", "native")
        if self.api_mode not in ("responses", "chat_completions"):
            raise ValueError("OPENAI_API_MODE: responses или chat_completions")
        if self.structured_mode not in ("native", "json_prompt"):
            raise ValueError("OPENAI_STRUCTURED_MODE: native или json_prompt")
        self.model, self.log, self.timeout, self.retries = model, log, timeout, retries
        # Disable SDK client retries: this gateway owns the bounded retry budget.
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=timeout, max_retries=0)
        adapter = OpenAIResponsesModel if self.api_mode == "responses" else OpenAIChatCompletionsModel
        self.sdk_model = adapter(model=model, openai_client=self.client)

    async def close(self):
        await self.client.close()

    async def generate(self, instructions: str, payload: dict,
                       output_type: type[BaseModel], stage: str) -> BaseModel:
        output = await self._run(instructions, payload, stage, output_type)
        return output

    async def text(self, instructions: str, payload: dict, stage: str) -> str:
        return await self._run(instructions, payload, stage, None)

    async def _run(self, instructions, payload, stage, output_type):
        native = output_type is not None and self.structured_mode == "native"
        if output_type is not None and not native:
            instructions += "\nВерни только JSON без Markdown по этой схеме:\n" + json.dumps(output_type.model_json_schema(), ensure_ascii=False)
        agent = Agent(name=stage, instructions=instructions, model=self.sdk_model,
                      output_type=output_type if native else None)
        for attempt in range(1, self.retries + 2):
            started = time.perf_counter()
            self.log.emit("model_request", stage=stage, attempt=attempt, model=self.model,
                          api_mode=self.api_mode, structured_mode=self.structured_mode,
                          instructions=instructions, payload=payload,
                          output_schema=output_type.model_json_schema() if output_type else None)
            try:
                result = await asyncio.wait_for(
                    Runner.run(agent, input=json.dumps(payload, ensure_ascii=False), max_turns=1,
                               run_config=RunConfig(tracing_disabled=True)), timeout=self.timeout)
                raw = result.final_output
                # Preserve explicit output, never raw model reasoning items or headers.
                self.log.emit("model_output", stage=stage, attempt=attempt,
                              output=raw.model_dump(mode="json") if isinstance(raw, BaseModel) else raw)
                usage = result.context_wrapper.usage
                usage_data = asdict(usage) if is_dataclass(usage) else {
                    key: getattr(usage, key, None) for key in ("requests", "input_tokens", "output_tokens", "total_tokens")}
                self.log.emit("model_usage", stage=stage, attempt=attempt, usage=usage_data)
                if output_type:
                    output = (output_type.model_validate_json(raw) if isinstance(raw, str)
                              else output_type.model_validate(raw))
                else:
                    if not isinstance(raw, str) or not raw.strip():
                        raise ValueError("Модель вернула пустой или нетекстовый ответ")
                    output = raw
                self.log.emit("model_success", stage=stage, attempt=attempt,
                              elapsed_seconds=time.perf_counter() - started, usage=usage_data)
                return output
            except Exception as exc:
                retryable = isinstance(exc, (TimeoutError, APIConnectionError)) or (
                    isinstance(exc, APIStatusError) and (exc.status_code == 429 or exc.status_code >= 500))
                retry = retryable and attempt <= self.retries
                # Do not copy provider exception text: it can contain URLs, headers or keys.
                self.log.emit("model_error", stage=stage, attempt=attempt,
                              error_type=type(exc).__name__, retry=retry,
                              status_code=exc.status_code if isinstance(exc, APIStatusError) else None,
                              elapsed_seconds=time.perf_counter() - started)
                if not retry:
                    raise ModelGatewayError(f"{stage}: {type(exc).__name__}; результат не получен или не прошёл проверку схемы") from None
                await asyncio.sleep(min(attempt, 2))
