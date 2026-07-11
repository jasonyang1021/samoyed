from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.core.config import settings


class AIUnavailableError(RuntimeError):
    pass


def _parse_json_text(value: str) -> dict[str, Any]:
    cleaned = value.strip()
    if "```" in cleaned:
        cleaned = cleaned.replace("```json", "").replace("```JSON", "").replace("```", "").strip()
    if "</think>" in cleaned:
        cleaned = cleaned.split("</think>", 1)[1].strip()
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start < 0 or end <= start:
            raise
        parsed = json.loads(cleaned[start:end + 1])
    if not isinstance(parsed, dict):
        raise AIUnavailableError("Dify workflow JSON output must be an object")
    return parsed


def active_provider(*, web_search: bool = False) -> str:
    requested = settings.ai_provider.strip().lower()
    dify_key = settings.dify_search_api_key if web_search else settings.dify_api_key
    if requested == "dify" and dify_key:
        return "dify"
    if requested == "openai" and settings.openai_api_key:
        return "openai"
    if requested == "auto":
        if dify_key:
            return "dify"
        if settings.openai_api_key:
            return "openai"
    return "rule_based"


def _output_text(payload: dict[str, Any]) -> str:
    if isinstance(payload.get("output_text"), str):
        return payload["output_text"]
    for item in payload.get("output", []):
        for content in item.get("content", []) if isinstance(item, dict) else []:
            if content.get("type") in {"output_text", "text"} and content.get("text"):
                return str(content["text"])
    raise AIUnavailableError("OpenAI response did not contain output text")


def _dify_result(payload: dict[str, Any]) -> dict[str, Any]:
    data = payload.get("data", payload)
    outputs = data.get("outputs", {}) if isinstance(data, dict) else {}
    if isinstance(outputs, dict):
        for key in ("result", "output", "text", "answer"):
            value = outputs.get(key)
            if isinstance(value, dict):
                return value
            if isinstance(value, str):
                try:
                    return _parse_json_text(value)
                except json.JSONDecodeError as error:
                    raise AIUnavailableError("Dify workflow output is not valid JSON") from error
        return outputs
    if isinstance(outputs, str):
        try:
            return _parse_json_text(outputs)
        except json.JSONDecodeError as error:
            raise AIUnavailableError("Dify workflow output is not valid JSON") from error
    raise AIUnavailableError("Dify workflow did not return outputs")


def _call_dify(prompt: str, schema_name: str, schema: dict[str, Any], *, web_search: bool = False) -> dict[str, Any]:
    api_key = settings.dify_search_api_key if web_search else settings.dify_api_key
    if not api_key:
        raise AIUnavailableError("Dify API key is not configured")
    schema_text = json.dumps(schema, ensure_ascii=False)
    workflow_prompt = f"{prompt}\n\nReturn ONLY valid JSON for schema {schema_name}. Do not use Markdown fences. Schema:\n{schema_text}"
    prompt_variable = _dify_prompt_variable(api_key)
    body = {"inputs": {prompt_variable: workflow_prompt, "schema_name": schema_name, "schema": schema_text}, "user": settings.dify_user, "response_mode": "blocking"}
    request = Request(
        f"{settings.dify_base_url.rstrip('/')}/workflows/run",
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json", "User-Agent": "AI-Research-Radar/0.1"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=90) as response:
            return _dify_result(json.loads(response.read().decode("utf-8")))
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="ignore")[:200]
        raise AIUnavailableError(f"Dify workflow request failed ({error.code}): {detail}") from error
    except (URLError, TimeoutError, json.JSONDecodeError) as error:
        raise AIUnavailableError(f"Dify workflow request failed: {error}") from error


def _dify_prompt_variable(api_key: str) -> str:
    request = Request(
        f"{settings.dify_base_url.rstrip('/')}/parameters",
        headers={"Authorization": f"Bearer {api_key}", "User-Agent": "AI-Research-Radar/0.1"},
        method="GET",
    )
    try:
        with urlopen(request, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))
        variables = []
        for item in payload.get("user_input_form", []) if isinstance(payload, dict) else []:
            if not isinstance(item, dict):
                continue
            for config in item.values():
                if isinstance(config, dict) and config.get("variable"):
                    variables.append(str(config["variable"]))
        if "prompt" in variables:
            return "prompt"
        if "promt" in variables:
            return "promt"
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
        pass
    return "prompt"


def check_dify_connection() -> dict[str, Any]:
    if not settings.dify_api_key:
        return {"configured": False, "reachable": False, "error": "DIFY_API_KEY is not configured"}
    request = Request(
        f"{settings.dify_base_url.rstrip('/')}/parameters",
        headers={"Authorization": f"Bearer {settings.dify_api_key}", "User-Agent": "AI-Research-Radar/0.1"},
        method="GET",
    )
    try:
        with urlopen(request, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))
        inputs = []
        for item in payload.get("user_input_form", []) if isinstance(payload, dict) else []:
            if not isinstance(item, dict):
                continue
            for config in item.values():
                if isinstance(config, dict) and config.get("variable"):
                    inputs.append(str(config["variable"]))
        return {"configured": True, "reachable": True, "workflow_inputs": inputs}
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="ignore")[:200]
        return {"configured": True, "reachable": False, "error": f"HTTP {error.code}: {detail}"}
    except (URLError, TimeoutError, json.JSONDecodeError) as error:
        return {"configured": True, "reachable": False, "error": str(error)}


def call_ai_json(prompt: str, schema_name: str, schema: dict[str, Any], *, web_search: bool = False) -> dict[str, Any]:
    provider = active_provider(web_search=web_search)
    if provider == "dify":
        return _call_dify(prompt, schema_name, schema, web_search=web_search)
    if provider != "openai" or not settings.openai_api_key:
        raise AIUnavailableError("No AI provider is configured")
    body: dict[str, Any] = {
        "model": settings.openai_model,
        "store": False,
        "input": prompt,
        "text": {"format": {"type": "json_schema", "name": schema_name, "schema": schema, "strict": True}},
    }
    if web_search:
        body["tools"] = [{"type": "web_search", "search_context_size": "medium"}]
    request = Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": f"Bearer {settings.openai_api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=90) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
        raise AIUnavailableError(f"OpenAI request failed: {error}") from error
    try:
        return json.loads(_output_text(payload))
    except (json.JSONDecodeError, TypeError) as error:
        raise AIUnavailableError("OpenAI returned invalid JSON") from error
