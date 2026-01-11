from __future__ import annotations

import httpx
import pytest
from openai import RateLimitError

from sentinel_trend.agents import runner


def test_agent_runner_quota_error(monkeypatch) -> None:
    class DummyResponses:
        def create(self, **kwargs):  # type: ignore[no-untyped-def]
            request = httpx.Request("POST", "https://example.com")
            response = httpx.Response(429, request=request)
            raise RateLimitError(
                "insufficient_quota",
                response=response,
                body={"error": {"code": "insufficient_quota"}},
            )

    class DummyClient:
        def __init__(self):  # type: ignore[no-untyped-def]
            self.responses = DummyResponses()

    monkeypatch.setenv("OPENAI_API_KEY", "test")
    monkeypatch.setattr(runner, "OpenAI", DummyClient)

    with pytest.raises(RuntimeError) as excinfo:
        runner.run_agent_research(refresh=False)
    assert "OpenAI API quota exceeded or billing not enabled" in str(excinfo.value)
