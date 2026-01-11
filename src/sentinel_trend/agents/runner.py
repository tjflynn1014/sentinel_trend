from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable

from openai import APIStatusError, OpenAI, RateLimitError

from sentinel_trend.agents.tools import tool_compare_variants, tool_real_backtest


_SYSTEM_PROMPT = """You are a Research Agent for sentinel_trend.
You must call compare_variants for windows [180, 200, 220] and summarize results.
Produce a markdown report that includes:
- A table with window, final_value, cagr, max_drawdown, volatility, turnover_initial, turnover_avg_equity, trade_count.
- A robustness statement using the provided heuristic.
- Any qa_warnings from each run.
Write the report content only; do not fabricate numbers.
"""


def _tool_definitions() -> list[dict[str, Any]]:
    """
    Responses API tool schema requires tool 'name' at the top level for type=function.
    (This differs from the nested 'function': {...} schema used in some other APIs.)
    """
    return [
        {
            "type": "function",
            "name": "real_backtest",
            "description": "Run a real backtest for a single SMA window.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sma_window": {"type": "integer", "minimum": 1},
                    "cost_bps": {"type": "number", "minimum": 0},
                    "refresh": {"type": "boolean"},
                },
                "required": ["sma_window", "cost_bps", "refresh"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "compare_variants",
            "description": "Compare multiple SMA windows and return robustness verdict.",
            "parameters": {
                "type": "object",
                "properties": {
                    "windows": {
                        "type": "array",
                        "items": {"type": "integer", "minimum": 1},
                        "minItems": 1,
                    },
                    "cost_bps": {"type": "number", "minimum": 0},
                    "refresh": {"type": "boolean"},
                },
                "required": ["windows", "cost_bps", "refresh"],
                "additionalProperties": False,
            },
        },
    ]


def _as_dict(obj: Any) -> dict[str, Any]:
    if isinstance(obj, dict):
        return obj
    # OpenAI SDK objects are pydantic-ish; try model_dump if present
    dump = getattr(obj, "model_dump", None)
    if callable(dump):
        return dump()
    # Fallback: try __dict__ (may include extra internal fields; acceptable for robust parsing)
    d = getattr(obj, "__dict__", None)
    if isinstance(d, dict):
        return d
    return {}


def _extract_function_calls(response: Any) -> list[dict[str, Any]]:
    """
    Responses API returns tool calls in response.output as items with type == 'function_call'.
    """
    output = getattr(response, "output", None)
    if not output:
        return []
    calls: list[dict[str, Any]] = []
    for item in output:
        item_d = _as_dict(item)
        item_type = item_d.get("type") or getattr(item, "type", None)
        if item_type == "function_call":
            calls.append(item_d)
    return calls


def _parse_call(call: dict[str, Any]) -> tuple[str, dict[str, Any], str]:
    """
    Extract (name, args, call_id) from a function_call item.
    """
    name = call.get("name")
    arguments = call.get("arguments", "{}")
    call_id = call.get("call_id") or call.get("id")  # be defensive across SDK versions

    if not name:
        raise ValueError(f"Malformed function_call: missing name: {call}")
    if not call_id:
        raise ValueError(f"Malformed function_call: missing call_id: {call}")

    if isinstance(arguments, str):
        try:
            args = json.loads(arguments) if arguments.strip() else {}
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON arguments for tool {name}: {arguments}") from e
    elif isinstance(arguments, dict):
        args = arguments
    else:
        args = {}

    return name, args, call_id


def _extract_text(response: Any) -> str:
    """
    Prefer response.output_text if available; otherwise stitch 'output_text' parts from messages.
    """
    output_text = getattr(response, "output_text", None)
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()

    output = getattr(response, "output", None) or []
    parts: list[str] = []

    for item in output:
        item_d = _as_dict(item)
        if item_d.get("type") != "message":
            continue
        content = item_d.get("content", [])
        for part in content:
            if isinstance(part, dict) and part.get("type") == "output_text":
                parts.append(part.get("text", ""))

    text = "".join(parts).strip()
    if not text:
        raise RuntimeError("No report text in response")
    return text


def _handle_openai_error(exc: Exception) -> RuntimeError:
    message = str(exc)
    if "insufficient_quota" in message:
        return RuntimeError(
            "OpenAI API quota exceeded or billing not enabled. "
            "Visit platform.openai.com -> Billing to enable API usage. "
            f"Original error: {message}"
        )
    return RuntimeError(f"OpenAI API error: {message}")


def _create_response(client: OpenAI, **kwargs: object) -> Any:
    try:
        return client.responses.create(**kwargs)
    except (RateLimitError, APIStatusError, Exception) as exc:
        raise _handle_openai_error(exc) from exc


def run_agent_research(refresh: bool) -> str:
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not set; source your .env (e.g. `source .env`).")

    client = OpenAI()
    tools = _tool_definitions()

    # Tool implementations
    tool_map: dict[str, Callable[..., dict[str, Any]]] = {
        "real_backtest": tool_real_backtest,
        "compare_variants": tool_compare_variants,
    }

    response = _create_response(
        client,
        model="gpt-4.1-mini",
        input=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": "Run the research workflow now."},
        ],
        tools=tools,
    )

    # Tool loop
    for _ in range(8):
        calls = _extract_function_calls(response)

        if not calls:
            report_text = _extract_text(response)
            runs_dir = Path("runs")
            runs_dir.mkdir(parents=True, exist_ok=True)
            report_path = runs_dir / "agent_research_report.md"
            report_path.write_text(report_text, encoding="utf-8")
            return str(report_path)

        tool_outputs: list[dict[str, Any]] = []
        for call in calls:
            name, args, call_id = _parse_call(call)
            if name not in tool_map:
                raise ValueError(f"Unknown tool requested by model: {name}")

            # Enforce refresh default from CLI if not provided by model
            if "refresh" not in args:
                args["refresh"] = bool(refresh)
            else:
                args["refresh"] = bool(args["refresh"])

            result = tool_map[name](**args)

            tool_outputs.append(
                {
                    "type": "function_call_output",
                    "call_id": call_id,
                    "output": json.dumps(result),
                }
            )

        response = _create_response(
            client,
            model="gpt-4.1-mini",
            input=tool_outputs,
            tools=tools,
            previous_response_id=response.id,
        )

    raise RuntimeError("Tool loop did not complete (too many iterations without a final report).")
