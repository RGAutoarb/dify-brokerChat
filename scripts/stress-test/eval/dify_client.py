"""Dify advanced-chat streaming client for evaluation."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any

import httpx


@dataclass
class EvalResponse:
    """Structured response from a single Dify chat-messages call."""

    final_answer: str = ""
    events_trace: list[dict[str, Any]] = field(default_factory=list)
    nodes_fired: list[str] = field(default_factory=list)
    citations: list[dict[str, Any]] = field(default_factory=list)
    timing: dict[str, float] = field(default_factory=dict)
    error: str | None = None


def send_query(
    query: str,
    *,
    base_url: str,
    api_key: str,
    user: str = "eval-harness",
    connect_timeout: float = 10.0,
    read_timeout: float = 60.0,
) -> EvalResponse:
    """Send a single query to /v1/chat-messages with streaming and parse the response.

    Args:
        query: The user's question.
        base_url: Dify service API base (e.g. http://localhost/v1).
        api_key: App-level API key (app-xxx).
        user: Arbitrary user identifier for the conversation.
        connect_timeout: TCP connect timeout in seconds.
        read_timeout: Timeout for reading the full stream.

    Returns:
        EvalResponse with parsed answer, events, citations, and timing.
    """
    url = f"{base_url.rstrip('/')}/chat-messages"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
        "Cache-Control": "no-cache",
    }
    payload = {
        "inputs": {},
        "query": query,
        "response_mode": "streaming",
        "conversation_id": "",
        "user": user,
    }

    result = EvalResponse()
    answer_chunks: list[str] = []
    t_start = time.monotonic()

    try:
        with httpx.Client(timeout=httpx.Timeout(read_timeout, connect=connect_timeout)) as client:
            with client.stream("POST", url, headers=headers, json=payload) as resp:
                if resp.status_code != 200:
                    result.error = f"HTTP {resp.status_code}: {resp.read().decode()[:500]}"
                    return result

                data_buffer: list[str] = []

                for raw_line in resp.iter_lines():
                    line = raw_line.strip() if isinstance(raw_line, str) else raw_line.decode().strip()

                    if not line:
                        if data_buffer:
                            data_str = "\n".join(data_buffer)
                            data_buffer.clear()
                            _process_data(data_str, result, answer_chunks)
                        continue

                    if line.startswith(":"):
                        continue

                    if ":" in line:
                        field_name, value = line.split(":", 1)
                        value = value.lstrip()
                        if field_name == "data":
                            data_buffer.append(value)

                # Flush remaining buffer
                if data_buffer:
                    _process_data("\n".join(data_buffer), result, answer_chunks)

    except httpx.TimeoutException:
        result.error = f"Timeout after {read_timeout}s"
    except httpx.ConnectError as exc:
        result.error = f"Connection error: {exc}"
    except Exception as exc:
        result.error = f"Unexpected error: {exc}"

    t_end = time.monotonic()
    result.timing["total_seconds"] = round(t_end - t_start, 3)
    result.final_answer = "".join(answer_chunks).strip()
    return result


def _process_data(
    data_str: str,
    result: EvalResponse,
    answer_chunks: list[str],
) -> None:
    """Process a single SSE data payload."""
    if data_str == "[DONE]":
        return

    try:
        event = json.loads(data_str)
    except json.JSONDecodeError:
        return

    event_type = event.get("event", "")
    result.events_trace.append({"event": event_type, "data": event})

    if event_type == "node_started":
        node_id = event.get("data", {}).get("node_id", "")
        if node_id and node_id not in result.nodes_fired:
            result.nodes_fired.append(node_id)

    elif event_type == "node_finished":
        node_id = event.get("data", {}).get("node_id", "")
        if node_id and node_id not in result.nodes_fired:
            result.nodes_fired.append(node_id)

    elif event_type == "message":
        answer_chunks.append(event.get("answer", ""))

    elif event_type == "message_end":
        metadata = event.get("metadata", {})
        resources = metadata.get("retriever_resources", [])
        if resources:
            result.citations.extend(resources)

    elif event_type == "error":
        result.error = event.get("message", "Unknown streaming error")
