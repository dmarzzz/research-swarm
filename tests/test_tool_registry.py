import asyncio

import pytest

from research_agent.tool_registry import ToolRegistry, ToolValidationError


def echo(query: str, limit: int = 3) -> str:
    """Echo a query."""
    return query[:limit]


async def async_echo(query: str) -> str:
    """Echo a query asynchronously."""
    return query


def test_tool_registry_generates_schema() -> None:
    registry = ToolRegistry([echo])
    spec = registry.specs()[0]

    assert spec.name == "echo"
    assert spec.parameters["required"] == ["query"]
    assert spec.parameters["properties"]["query"]["type"] == "string"
    assert spec.parameters["properties"]["limit"]["type"] == "integer"


def test_tool_registry_validates_unknown_args() -> None:
    registry = ToolRegistry([echo])

    with pytest.raises(ToolValidationError, match="Unknown args"):
        registry.validate_args("echo", {"query": "abc", "extra": True})


def test_tool_registry_validates_types() -> None:
    registry = ToolRegistry([echo])

    with pytest.raises(ToolValidationError, match="must be an integer"):
        registry.validate_args("echo", {"query": "abc", "limit": "bad"})


def test_tool_registry_calls_async_tools() -> None:
    registry = ToolRegistry([async_echo])

    result, record = asyncio.run(registry.acall("async_echo", {"query": "abc"}))

    assert result == "abc"
    assert record.ok is True
