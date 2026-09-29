"""Fail-soft wrapper around the Hindsight long-term memory SDK.

Why this module exists:

* **One stable event loop.** The SDK's synchronous helpers call
  ``loop.run_until_complete`` internally, which raises ``RuntimeError`` when the
  caller is already inside a running event loop (FastAPI handlers, LangGraph
  nodes), so every real retain/recall would fail and be swallowed by the
  ``except`` blocks below. We therefore prefer the SDK's ``aretain``/``arecall``
  methods and execute them on a private background loop, which also gives the
  SDK's shared HTTP client exactly one loop to bind its connections to.
* **Stable return shapes.** The SDK returns Pydantic response objects
  (``RetainResponse``, ``RecallResponse`` with ``RecallResult.text`` and
  ``scores.final``), while the agents and API routes expect plain ``dict`` /
  ``list[dict]`` with ``content`` and ``relevance_score`` keys. Everything is
  normalised here so callers never depend on SDK internals.
* **Non-blocking callers.** Request handlers and agent nodes await
  :func:`aretain`/:func:`arecall`, which run the blocking wrapper on a worker
  thread so the application's event loop keeps serving other requests.
* **Never break the workflow.** Hindsight is an enrichment source: if the
  server is down, misconfigured or slow, the disruption workflow must continue
  with an empty memory list rather than fail the request.
"""

from __future__ import annotations

import asyncio
import threading
from concurrent.futures import Future
from typing import Any, Dict, List, Optional

from hindsight_client import Hindsight

from utils.config import settings
from utils.logger import logger

# Matches the SDK's own default request timeout so a slow memory operation
# never hangs a request longer than the SDK itself would allow.
CALL_TIMEOUT_SECONDS = 300.0

# Score used when Hindsight does not report one for a recalled memory.
DEFAULT_RELEVANCE = 0.92

client = Hindsight(base_url=settings.hindsight_base_url)


class _BackgroundLoop:
    """A single daemon thread owning one event loop for all SDK calls.

    ``run_coroutine_threadsafe`` lets synchronous callers (and callers that
    already run on the uvicorn loop) hand work to that loop and block for the
    result, exactly like a normal outbound HTTP call would.
    """

    def __init__(self) -> None:
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._started = threading.Event()
        self._thread = threading.Thread(
            target=self._run, name="hindsight-memory-loop", daemon=True
        )
        self._thread.start()
        self._started.wait(timeout=5)

    def _run(self) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self._loop = loop
        self._started.set()
        loop.run_forever()

    def run(self, coro: Any) -> Any:
        loop = self._loop
        if loop is None or loop.is_closed():  # pragma: no cover - defensive
            raise RuntimeError("Hindsight memory loop is not running")
        future: Future = asyncio.run_coroutine_threadsafe(coro, loop)
        try:
            return future.result(timeout=CALL_TIMEOUT_SECONDS)
        except Exception:
            future.cancel()
            raise


_loop_runner: Optional[_BackgroundLoop] = None
_loop_lock = threading.Lock()


def _runner() -> _BackgroundLoop:
    """Lazily start the background loop so importing this module stays cheap."""
    global _loop_runner
    if _loop_runner is None:
        with _loop_lock:
            if _loop_runner is None:
                _loop_runner = _BackgroundLoop()
    return _loop_runner


def _invoke(async_name: str, sync_name: str, **kwargs: Any) -> Any:
    """Call the SDK's async method when available, else its sync method.

    Stubs and fakes used in tests only expose the synchronous method, so both
    paths are supported.
    """
    async_method = getattr(client, async_name, None)
    if async_method is not None:
        return _runner().run(async_method(**kwargs))
    return getattr(client, sync_name)(**kwargs)


def _as_dict(item: Any) -> Dict[str, Any]:
    """Convert an SDK response object (or plain str/dict) into a dict."""
    if isinstance(item, dict):
        return dict(item)
    if isinstance(item, str):
        return {"content": item}
    for attr in ("to_dict", "model_dump"):
        dump = getattr(item, attr, None)
        if callable(dump):
            try:
                data = dump()
            except Exception:  # pragma: no cover - defensive
                continue
            if isinstance(data, dict):
                return data
    try:
        data = dict(vars(item))
    except TypeError:
        data = {}
    if data:
        return data
    for key in ("content", "text"):
        value = getattr(item, key, None)
        if isinstance(value, str) and value:
            return {key: value}
    return {"content": str(item)}


def _score_of(data: Dict[str, Any]) -> float:
    """Pull the ranking score out of a recall result, if the SDK reports one."""
    scores = data.get("scores")
    keys = ("final", "reranker", "semantic", "keyword")
    if isinstance(scores, dict):
        for key in keys:
            value = scores.get(key)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                return float(value)
    elif scores is not None:
        for key in keys:
            value = getattr(scores, key, None)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                return float(value)
    for key in keys:
        value = data.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return float(value)
    return DEFAULT_RELEVANCE


def _normalise_memory(item: Any) -> Dict[str, Any]:
    """Normalise one recalled memory into ``{content, relevance_score, ...}``."""
    data = _as_dict(item)
    content = data.get("content")
    if not content:
        content = data.get("text") or data.get("message") or ""
    if not content:
        return {}
    data["content"] = content
    data.setdefault("relevance_score", _score_of(data))
    return data


def _normalise_memories(response: Any) -> List[Dict[str, Any]]:
    """Accept a ``RecallResponse``, a list, or ``None`` and return a list."""
    if response is None:
        items: List[Any] = []
    elif hasattr(response, "results"):
        items = list(getattr(response, "results") or [])
    elif isinstance(response, dict) and "results" in response:
        items = list(response.get("results") or [])
    elif isinstance(response, (list, tuple)):
        items = list(response)
    else:
        items = [response]

    memories: List[Dict[str, Any]] = []
    for item in items:
        if item is None:
            continue
        memory = _normalise_memory(item)
        if memory:
            memories.append(memory)
    return memories


def retain(bank_id: str, content: str) -> dict:
    """Store one experience in Hindsight. Returns ``{}`` on any failure."""
    try:
        response = _invoke("aretain", "retain", bank_id=bank_id, content=content)
    except Exception as exc:
        logger.warning(f"Failed to retain memory in Hindsight: {exc}")
        return {}
    if response is None:
        return {}
    if isinstance(response, dict):
        return response
    return _as_dict(response)


def recall(bank_id: str, query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Retrieve up to ``limit`` memories. Returns ``[]`` on any failure."""
    try:
        response = _invoke("arecall", "recall", bank_id=bank_id, query=query)
    except Exception as exc:
        logger.warning(f"Failed to recall memory from Hindsight: {exc}")
        return []
    return _normalise_memories(response)[: max(0, limit)]


async def aretain(bank_id: str, content: str) -> dict:
    """Async variant of :func:`retain`.

    Used by request handlers and agent nodes so the blocking SDK call runs on a
    worker thread and the caller's event loop stays free for other requests.
    """
    return await asyncio.to_thread(retain, bank_id=bank_id, content=content)


async def arecall(
    bank_id: str, query: str, limit: int = 5
) -> List[Dict[str, Any]]:
    """Async variant of :func:`recall` (same guarantees, non-blocking loop)."""
    return await asyncio.to_thread(recall, bank_id=bank_id, query=query, limit=limit)


__all__ = ["retain", "recall", "aretain", "arecall", "client"]
