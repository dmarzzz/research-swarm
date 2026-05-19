"""Tool registry shared by research backends.

DSPy consumes Python callables directly. Codex consumes a structured list
of tool specs, then this registry validates and executes the selected
Python callable. Retrieval, caching, indexing, and archive writes stay in
this process either way.
"""

from __future__ import annotations

import inspect
import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, get_args, get_origin

from research_agent.types import ToolCallRecord


ToolFn = Callable[..., Any]


@dataclass(frozen=True, slots=True)
class ToolSpec:
    name: str
    description: str
    parameters: dict[str, Any]


class ToolValidationError(ValueError):
    """Raised when a model asks for an invalid tool call."""


class ToolRegistry:
    """Validated dispatch table for agent-facing research tools."""

    def __init__(self, tools: list[ToolFn]) -> None:
        self._tools = {tool.__name__: tool for tool in tools}
        if len(self._tools) != len(tools):
            raise ValueError("Tool names must be unique.")

    @property
    def names(self) -> list[str]:
        return list(self._tools)

    def get(self, name: str) -> ToolFn:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise ToolValidationError(f"Unknown tool: {name}") from exc

    def specs(self) -> list[ToolSpec]:
        return [
            ToolSpec(
                name=name,
                description=inspect.getdoc(fn) or "",
                parameters=_signature_schema(fn),
            )
            for name, fn in self._tools.items()
        ]

    def render_for_prompt(self) -> str:
        blocks = []
        for spec in self.specs():
            params = json.dumps(spec.parameters, sort_keys=True)
            blocks.append(f"- {spec.name}\n  args schema: {params}\n  {spec.description}")
        return "\n\n".join(blocks)

    def validate_args(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        fn = self.get(name)
        if not isinstance(args, dict):
            raise ToolValidationError(f"Args for {name} must be a JSON object.")

        sig = inspect.signature(fn)
        params = sig.parameters
        accepts_kwargs = any(
            p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values()
        )
        if not accepts_kwargs:
            unknown = sorted(set(args) - set(params))
            if unknown:
                raise ToolValidationError(f"Unknown args for {name}: {', '.join(unknown)}")

        validated: dict[str, Any] = {}
        for param_name, param in params.items():
            if param.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
                continue
            if param_name not in args:
                if param.default is inspect.Parameter.empty:
                    raise ToolValidationError(f"Missing required arg for {name}: {param_name}")
                continue
            value = args[param_name]
            _validate_type(name, param_name, value, param.annotation)
            validated[param_name] = value
        return validated

    async def acall(self, name: str, args: dict[str, Any]) -> tuple[str, ToolCallRecord]:
        fn = self.get(name)
        validated = self.validate_args(name, args)
        start = time.perf_counter()
        try:
            result = fn(**validated)
            if inspect.isawaitable(result):
                result = await result
            text = "" if result is None else str(result)
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            return text, ToolCallRecord(
                tool=name,
                args=validated,
                ok=True,
                result_preview=_preview(text),
                elapsed_ms=elapsed_ms,
            )
        except Exception as exc:
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            return "", ToolCallRecord(
                tool=name,
                args=validated,
                ok=False,
                error=f"{type(exc).__name__}: {exc}",
                elapsed_ms=elapsed_ms,
            )


def build_default_registry(*, expanded_search_fn: ToolFn | None = None) -> ToolRegistry:
    """Return the canonical research tool registry."""

    from research_agent.tools import (
        arxiv_fetch_paper,
        arxiv_search,
        expanded_search,
        extract_links,
        fetch_url,
        fetch_urls_parallel,
        github_search,
        local_search,
        nitter_search,
        semantic_scholar_search,
        verify_arxiv_citations,
        web_search,
    )

    expanded = expanded_search_fn or expanded_search
    return ToolRegistry(
        [
            local_search,
            web_search,
            expanded,
            nitter_search,
            arxiv_search,
            semantic_scholar_search,
            github_search,
            fetch_url,
            fetch_urls_parallel,
            arxiv_fetch_paper,
            extract_links,
            verify_arxiv_citations,
        ]
    )


def _signature_schema(fn: ToolFn) -> dict[str, Any]:
    properties: dict[str, Any] = {}
    required: list[str] = []
    for name, param in inspect.signature(fn).parameters.items():
        if param.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
            continue
        properties[name] = _annotation_schema(param.annotation)
        if param.default is not inspect.Parameter.empty:
            properties[name]["default"] = param.default
        else:
            required.append(name)
    return {
        "type": "object",
        "properties": properties,
        "required": required,
        "additionalProperties": False,
    }


def _annotation_schema(annotation: Any) -> dict[str, Any]:
    if annotation is inspect.Parameter.empty:
        return {"type": "string"}
    if isinstance(annotation, str):
        return _string_annotation_schema(annotation)
    origin = get_origin(annotation)
    if origin is not None:
        args = get_args(annotation)
        if origin in (list, tuple, set):
            item_annotation = args[0] if args else str
            return {"type": "array", "items": _annotation_schema(item_annotation)}
        if origin is dict:
            return {"type": "object"}
    if annotation is str:
        return {"type": "string"}
    if annotation is int:
        return {"type": "integer"}
    if annotation is float:
        return {"type": "number"}
    if annotation is bool:
        return {"type": "boolean"}
    return {"type": "string"}


def _string_annotation_schema(annotation: str) -> dict[str, Any]:
    normalized = annotation.strip().lower()
    if normalized == "str":
        return {"type": "string"}
    if normalized == "int":
        return {"type": "integer"}
    if normalized == "float":
        return {"type": "number"}
    if normalized == "bool":
        return {"type": "boolean"}
    if normalized.startswith("list") or normalized.endswith("[]"):
        return {"type": "array", "items": {"type": "string"}}
    return {"type": "string"}


def _validate_type(tool: str, arg: str, value: Any, annotation: Any) -> None:
    schema = _annotation_schema(annotation)
    expected = schema.get("type")
    if expected == "string" and not isinstance(value, str):
        raise ToolValidationError(f"{tool}.{arg} must be a string.")
    if expected == "integer" and (not isinstance(value, int) or isinstance(value, bool)):
        raise ToolValidationError(f"{tool}.{arg} must be an integer.")
    if expected == "number" and (
        not isinstance(value, (int, float)) or isinstance(value, bool)
    ):
        raise ToolValidationError(f"{tool}.{arg} must be a number.")
    if expected == "boolean" and not isinstance(value, bool):
        raise ToolValidationError(f"{tool}.{arg} must be a boolean.")
    if expected == "array" and not isinstance(value, list):
        raise ToolValidationError(f"{tool}.{arg} must be an array.")
    if expected == "object" and not isinstance(value, dict):
        raise ToolValidationError(f"{tool}.{arg} must be an object.")


def _preview(text: str, limit: int = 240) -> str:
    compact = text.replace("\n", " ").strip()
    return compact if len(compact) <= limit else compact[: limit - 1] + "…"
