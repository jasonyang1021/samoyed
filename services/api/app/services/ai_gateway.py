from __future__ import annotations

import json
import ast
import re
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.core.config import settings


class AIUnavailableError(RuntimeError):
    pass


def _parse_json_text(value: str) -> dict[str, Any]:
    return parse_json_object(value)


def parse_json_object(value: str) -> dict[str, Any]:
    """Parse JSON returned by providers that may wrap it in markdown or thinking text."""
    cleaned = value.strip()
    if "</think>" in cleaned:
        cleaned = cleaned.rsplit("</think>", 1)[1].strip()
    if "```" in cleaned:
        cleaned = cleaned.replace("```json", "").replace("```JSON", "").replace("```", "").strip()
    candidates = [cleaned]
    # Providers sometimes append a sentence after the JSON object. Decode from
    # every opening brace instead of requiring the final character to be `}`.
    candidates.extend(cleaned[index:] for index, char in enumerate(cleaned) if char == "{")
    last_error: Exception | None = None
    for candidate in candidates:
        repaired = re.sub(r",\s*([}\]])", r"\1", candidate)
        for version in (candidate, repaired):
            for loader in (lambda text: json.loads(text), lambda text: json.loads(text, strict=False), ast.literal_eval):
                try:
                    parsed = loader(version)
                    if isinstance(parsed, dict):
                        return parsed
                except (ValueError, SyntaxError, json.JSONDecodeError) as error:
                    last_error = error
            # raw_decode accepts a valid object followed by model chatter and
            # also makes this path tolerant of a harmless trailing comma.
            try:
                parsed, _ = json.JSONDecoder(strict=False).raw_decode(version.lstrip())
                if isinstance(parsed, dict):
                    return parsed
            except (ValueError, json.JSONDecodeError) as error:
                last_error = error
    raise AIUnavailableError(f"Provider JSON output could not be parsed: {last_error}")


def salvage_json_object(value: str) -> dict[str, Any]:
    """Recover the useful assistant fields when a model's JSON is malformed."""
    recovered: dict[str, Any] = {}
    for key in ("answer", "learning_summary"):
        match = re.search(rf'"{key}"\s*:\s*"((?:\\.|[^"\\])*)"', value, flags=re.S)
        if match:
            try:
                recovered[key] = json.loads(f'"{match.group(1)}"', strict=False)
            except (TypeError, ValueError, json.JSONDecodeError):
                recovered[key] = match.group(1).replace('\\"', '"').replace("\\n", "\n")
    for key in ("conclusions", "studied_articles", "uncertainties", "suggested_questions", "source_indexes"):
        match = re.search(rf'"{key}"\s*:\s*(\[[\s\S]*?\])', value)
        if not match:
            continue
        try:
            parsed = json.loads(match.group(1), strict=False)
            if isinstance(parsed, list):
                recovered[key] = parsed
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
    if recovered:
        return recovered
    raise AIUnavailableError("Provider JSON output did not contain recoverable assistant fields")


def active_provider(*, web_search: bool = False, purpose: str = "default") -> str:
    requested = (settings.assistant_provider if purpose == "assistant" else settings.ai_provider).strip().lower()
    dify_key = settings.dify_search_api_key if web_search else settings.dify_api_key
    if requested == "deepseek" and settings.deepseek_api_key:
        return "deepseek"
    if requested == "dify" and dify_key:
        return "dify"
    if requested == "openai" and settings.openai_api_key:
        return "openai"
    if requested == "auto":
        if settings.deepseek_api_key:
            return "deepseek"
        if dify_key:
            return "dify"
        if settings.openai_api_key:
            return "openai"
    return "rule_based"


def active_model(provider: str | None = None) -> str:
    selected = provider or active_provider()
    if selected == "deepseek":
        return settings.deepseek_model
    return settings.openai_model


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
    if provider == "deepseek":
        return _call_deepseek_json(prompt, schema_name, schema)
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


def _deepseek_request(body: dict[str, Any]) -> dict[str, Any]:
    if not settings.deepseek_api_key:
        raise AIUnavailableError("DEEPSEEK_API_KEY is not configured")
    request = Request(
        f"{settings.deepseek_base_url.rstrip('/')}/chat/completions",
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": f"Bearer {settings.deepseek_api_key}", "Content-Type": "application/json", "User-Agent": "AI-Research-Radar/0.1"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=90) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if not isinstance(payload, dict):
            raise AIUnavailableError("DeepSeek response was not an object")
        return payload
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="ignore")[:300]
        raise AIUnavailableError(f"DeepSeek request failed ({error.code}): {detail}") from error
    except (URLError, TimeoutError, json.JSONDecodeError) as error:
        raise AIUnavailableError(f"DeepSeek request failed: {error}") from error


def _deepseek_message(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        message = payload["choices"][0]["message"]
    except (KeyError, IndexError, TypeError) as error:
        raise AIUnavailableError("DeepSeek response did not contain a message") from error
    if not isinstance(message, dict):
        raise AIUnavailableError("DeepSeek response message was invalid")
    return message


def _openai_chat_request(body: dict[str, Any]) -> dict[str, Any]:
    if not settings.openai_api_key:
        raise AIUnavailableError("OPENAI_API_KEY is not configured")
    request = Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": f"Bearer {settings.openai_api_key}", "Content-Type": "application/json", "User-Agent": "AI-Research-Radar/0.1"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=90) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if not isinstance(payload, dict):
            raise AIUnavailableError("OpenAI response was not an object")
        return payload
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="ignore")[:300]
        raise AIUnavailableError(f"OpenAI chat request failed ({error.code}): {detail}") from error
    except (URLError, TimeoutError, json.JSONDecodeError) as error:
        raise AIUnavailableError(f"OpenAI chat request failed: {error}") from error


def _agent_request(provider: str, body: dict[str, Any]) -> dict[str, Any]:
    if provider == "deepseek":
        return _deepseek_request(body)
    if provider == "openai":
        return _openai_chat_request(body)
    raise AIUnavailableError(f"Provider {provider} does not support the Snowy agent loop")


def _call_deepseek_json(prompt: str, schema_name: str, schema: dict[str, Any]) -> dict[str, Any]:
    body = {
        "model": settings.deepseek_model,
        "messages": [
            {"role": "system", "content": f"Return ONLY valid JSON for schema {schema_name}. Do not use Markdown fences."},
            {"role": "user", "content": f"{prompt}\nSchema:\n{json.dumps(schema, ensure_ascii=False)}"},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.2,
        "stream": False,
    }
    message = _deepseek_message(_deepseek_request(body))
    content = message.get("content")
    if not isinstance(content, str):
        raise AIUnavailableError("DeepSeek JSON response did not contain text")
    try:
        result = _parse_json_text(content)
    except (json.JSONDecodeError, TypeError) as error:
        raise AIUnavailableError("DeepSeek returned invalid JSON") from error
    return result


def call_chat_agent(
    system_prompt: str,
    user_prompt: str,
    tools: list[dict[str, Any]],
    execute_tool: Callable[[str, dict[str, Any]], Any],
    *,
    max_turns: int | None = None,
) -> tuple[str, str]:
    """Run a provider-neutral tool loop. The model provider is configured in one place."""
    provider = active_provider(purpose="assistant")
    if provider not in {"deepseek", "openai"}:
        raise AIUnavailableError("The configured provider does not support the Snowy agent loop")
    messages: list[dict[str, Any]] = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
    for _ in range(max_turns or settings.deepseek_max_tool_turns):
        model = settings.deepseek_model if provider == "deepseek" else settings.openai_model
        payload = _agent_request(provider, {"model": model, "messages": messages, "tools": tools, "tool_choice": "auto", "temperature": 0.2, "stream": False})
        message = _deepseek_message(payload)
        tool_calls = message.get("tool_calls") or []
        if not tool_calls:
            content = message.get("content")
            if not isinstance(content, str):
                raise AIUnavailableError("DeepSeek agent did not return text")
            return content, provider
        assistant_message = {"role": "assistant", "content": message.get("content") or "", "tool_calls": tool_calls}
        if message.get("reasoning_content") is not None:
            assistant_message["reasoning_content"] = message["reasoning_content"]
        messages.append(assistant_message)
        for tool_call in tool_calls:
            try:
                function = tool_call["function"]
                name = str(function["name"])
                arguments = json.loads(function.get("arguments") or "{}")
                try:
                    result = execute_tool(name, arguments if isinstance(arguments, dict) else {})
                except Exception:
                    result = {"error": f"Tool {name} failed; continue with the other available evidence."}
            except (KeyError, TypeError, json.JSONDecodeError, ValueError) as error:
                result = {"error": f"Invalid tool call: {error}"}
            messages.append({"role": "tool", "tool_call_id": tool_call.get("id", ""), "content": json.dumps(result, ensure_ascii=False, default=str)})
    # A model can keep requesting more searches even after enough evidence is
    # available. Give it one final no-tools turn so the answer still comes
    # from the configured model instead of silently falling back to rules.
    messages.append({
        "role": "user",
        "content": "停止调用工具。请只根据已经获得的研究证据完成最终回答，并严格返回之前要求的 JSON。不要再请求任何工具。",
    })
    final_model = settings.deepseek_model if provider == "deepseek" else settings.openai_model
    final_payload = _agent_request(provider, {"model": final_model, "messages": messages, "temperature": 0.2, "stream": False})
    final_message = _deepseek_message(final_payload)
    final_content = final_message.get("content")
    if not isinstance(final_content, str):
        raise AIUnavailableError("Agent final response did not contain text")
    return final_content, provider
