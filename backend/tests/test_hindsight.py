import pytest

import hindsight.client as hindsight_client_module
from hindsight.client import retain, recall, aretain, arecall
from agents.mitigation import mitigation_node
from workflows.state import AgentState
from utils.config import settings


class StubHindsightApi:
    """Records calls made by the wrapper to the Hindsight SDK client."""

    def __init__(self, fail=False):
        self.fail = fail
        self.retain_calls = []
        self.recall_calls = []
        self.recall_results = []

    def retain(self, bank_id, content):
        if self.fail:
            raise ConnectionError("hindsight unreachable")
        self.retain_calls.append({"bank_id": bank_id, "content": content})
        return {"id": "mem-1"}

    def recall(self, bank_id, query):
        if self.fail:
            raise ConnectionError("hindsight unreachable")
        self.recall_calls.append({"bank_id": bank_id, "query": query})
        return self.recall_results


class StubSdkScores:
    """Mirrors the SDK's RecallScores model."""

    def __init__(self, final):
        self.final = final
        self.reranker = final
        self.semantic = None
        self.keyword = None


class StubSdkResult:
    """Mirrors the SDK's RecallResult model (text + scores, no 'content' key)."""

    def __init__(self, text, final_score):
        self.id = f"res-{abs(hash(text)) % 10000}"
        self.text = text
        self.type = "world"
        self.scores = StubSdkScores(final_score)


class StubSdkRecallResponse:
    """Mirrors the SDK's RecallResponse model."""

    def __init__(self, results):
        self.results = results


class StubSdkRetainResponse:
    """Mirrors the SDK's RetainResponse model (Pydantic, dumped via to_dict)."""

    def __init__(self):
        self.items_count = 1
        self.operation_ids = []

    def to_dict(self):
        return {"items_count": self.items_count, "operation_ids": self.operation_ids}


class AsyncStubHindsightApi:
    """Stub exposing only the SDK's async methods (aretain/arecall)."""

    def __init__(self):
        self.retain_calls = []
        self.recall_calls = []

    async def aretain(self, bank_id, content):
        self.retain_calls.append({"bank_id": bank_id, "content": content})
        return StubSdkRetainResponse()

    async def arecall(self, bank_id, query):
        self.recall_calls.append({"bank_id": bank_id, "query": query})
        return StubSdkRecallResponse([StubSdkResult("memory from the server", 0.87)])


def base_state(**overrides):
    state: AgentState = {
        "case_id": "case-hindsight-1",
        "disruption_type": "supplier_delay",
        "severity": "high",
        "affected_supplier": {"name": "Test Metals Corp"},
        "affected_inventory": {"unit_cost": 800.0},
        "affected_order": {},
        "delay_days": 10,
        "inventory_coverage_days": 5.0,
        "daily_demand_rate": 25.0,
        "stockout_risk": 0.0,
        "business_impact": {"estimated_financial_loss": 100000.0},
        "hindsight_memories": [],
        "alternative_suppliers": [],
        "mitigation_strategies": [],
        "recommendation": {},
        "alerts": [],
        "agent_trace": [],
        "status": "recommending",
    }
    state.update(overrides)
    return state


@pytest.mark.asyncio
async def test_hindsight_retain_sends_bank_and_content(monkeypatch):
    api = StubHindsightApi()
    monkeypatch.setattr(hindsight_client_module, "client", api)

    result = retain(bank_id="supply-chain-memory", content="Supplier ABC delay resolved")

    assert result == {"id": "mem-1"}
    assert api.retain_calls == [
        {"bank_id": "supply-chain-memory", "content": "Supplier ABC delay resolved"}
    ]


@pytest.mark.asyncio
async def test_hindsight_retain_fails_softly_when_service_unavailable(monkeypatch):
    api = StubHindsightApi(fail=True)
    monkeypatch.setattr(hindsight_client_module, "client", api)

    # A memory write failure must never break the disruption workflow.
    assert retain(bank_id="supply-chain-memory", content="anything") == {}


@pytest.mark.asyncio
async def test_hindsight_recall_respects_limit(monkeypatch):
    api = StubHindsightApi()
    api.recall_results = [
        {"content": "memory one"},
        {"content": "memory two"},
        {"content": "memory three"},
    ]
    monkeypatch.setattr(hindsight_client_module, "client", api)

    results = recall(bank_id="supply-chain-memory", query="supplier delay", limit=2)

    assert len(results) == 2
    assert api.recall_calls[0]["query"] == "supplier delay"
    assert api.recall_calls[0]["bank_id"] == "supply-chain-memory"


@pytest.mark.asyncio
async def test_hindsight_recall_fails_softly_when_service_unavailable(monkeypatch):
    api = StubHindsightApi(fail=True)
    monkeypatch.setattr(hindsight_client_module, "client", api)

    assert recall(bank_id="supply-chain-memory", query="supplier delay") == []


@pytest.mark.asyncio
async def test_mitigation_node_recalls_empty_history_on_first_event(
    hindsight_store, sample_supplier, sample_alt_supplier
):
    """First disruption: no prior experience exists in Hindsight."""
    state = await mitigation_node(base_state())

    assert state["hindsight_memories"] == []
    assert hindsight_store.recall_calls, "mitigation agent must query Hindsight recall"
    assert hindsight_store.recall_calls[0]["bank_id"] == settings.hindsight_bank_id
    assert "Test Metals Corp" in hindsight_store.recall_calls[0]["query"]

    rec = state["recommendation"]
    assert rec["confidence_score"] == 0.76
    assert "No previous disruption memory found in Hindsight" in rec["rationale"]


@pytest.mark.asyncio
async def test_mitigation_node_uses_recalled_experience_on_repeat_event(
    hindsight_store, sample_supplier, sample_alt_supplier
):
    """Second, similar disruption: recalled experience changes the recommendation."""
    hindsight_store.retain(
        bank_id=settings.hindsight_bank_id,
        content=(
            "Disruption event involving supplier Test Metals Corp (Type: supplier_delay, "
            "Delay: 10 days). Mitigation recommended: emergency secondary purchase order. "
            "Operator decision: Approved. Actual outcome: Rerouted 45 percent of volume, "
            "no line stoppage."
        ),
    )

    state = await mitigation_node(base_state())

    assert len(state["hindsight_memories"]) == 1
    assert "no line stoppage" in state["hindsight_memories"][0]["content"]

    rec = state["recommendation"]
    assert rec["confidence_score"] == 0.94
    assert rec["risk_level"] == "Low"
    assert "Hindsight long-term memory retrieved" in rec["rationale"]

    # Explainability must expose the Hindsight contribution to the UI.
    trace = state["agent_trace"][0]
    assert "Hindsight recall queried memory bank" in trace["analysis"]
    assert "Hindsight Memories Recalled: 1" in trace["data_used"]


@pytest.mark.asyncio
async def test_hindsight_recall_normalises_sdk_response_shape(monkeypatch):
    """The SDK returns RecallResponse(results=[RecallResult]); callers get dicts."""
    api = StubHindsightApi()
    api.recall_results = StubSdkRecallResponse(
        [
            StubSdkResult("first memory", 0.91),
            StubSdkResult("second memory", 0.42),
            StubSdkResult("third memory", 0.11),
        ]
    )
    monkeypatch.setattr(hindsight_client_module, "client", api)

    results = recall(bank_id="supply-chain-memory", query="supplier delay", limit=2)

    assert [r["content"] for r in results] == ["first memory", "second memory"]
    assert results[0]["relevance_score"] == 0.91
    assert results[1]["relevance_score"] == 0.42


@pytest.mark.asyncio
async def test_hindsight_retain_normalises_sdk_response_shape(monkeypatch):
    """RetainResponse objects are dumped to a plain dict for callers."""
    api = StubHindsightApi()

    class RetainOnlyStub:
        def retain(self, bank_id, content):
            api.retain_calls.append({"bank_id": bank_id, "content": content})
            return StubSdkRetainResponse()

    monkeypatch.setattr(hindsight_client_module, "client", RetainOnlyStub())

    result = retain(bank_id="supply-chain-memory", content="Supplier ABC delay resolved")

    assert result == {"items_count": 1, "operation_ids": []}
    assert api.retain_calls == [
        {"bank_id": "supply-chain-memory", "content": "Supplier ABC delay resolved"}
    ]


@pytest.mark.asyncio
async def test_hindsight_calls_succeed_inside_a_running_event_loop(monkeypatch):
    """Regression: the SDK's sync helpers raise RuntimeError under uvicorn/LangGraph.

    The wrapper must therefore drive the async SDK methods on its own loop, or
    every real memory call would be silently swallowed.
    """
    api = AsyncStubHindsightApi()
    monkeypatch.setattr(hindsight_client_module, "client", api)

    stored = retain(bank_id="supply-chain-memory", content="Supplier ABC delay resolved")
    recalled = recall(bank_id="supply-chain-memory", query="supplier delay")

    assert api.retain_calls == [
        {"bank_id": "supply-chain-memory", "content": "Supplier ABC delay resolved"}
    ]
    assert api.recall_calls[0]["query"] == "supplier delay"
    assert stored == {"items_count": 1, "operation_ids": []}
    assert recalled[0]["content"] == "memory from the server"
    assert recalled[0]["relevance_score"] == 0.87


@pytest.mark.asyncio
async def test_hindsight_recall_fails_softly_when_async_client_raises(monkeypatch):
    class ExplodingStub:
        async def arecall(self, bank_id, query):
            raise TimeoutError("server never answered")

    monkeypatch.setattr(hindsight_client_module, "client", ExplodingStub())

    assert recall(bank_id="supply-chain-memory", query="supplier delay") == []


@pytest.mark.asyncio
async def test_async_variants_wrap_the_sync_calls_for_request_handlers(monkeypatch):
    """`aretain`/`arecall` are what the API routes and agent nodes await."""
    api = StubHindsightApi()
    api.recall_results = [{"content": "past outcome", "relevance_score": 0.8}]
    monkeypatch.setattr(hindsight_client_module, "client", api)

    stored = await aretain(bank_id="supply-chain-memory", content="Supplier ABC delay resolved")
    recalled = await arecall(bank_id="supply-chain-memory", query="supplier delay", limit=3)

    assert stored == {"id": "mem-1"}
    assert recalled == [{"content": "past outcome", "relevance_score": 0.8}]
    assert api.retain_calls == [
        {"bank_id": "supply-chain-memory", "content": "Supplier ABC delay resolved"}
    ]
    assert api.recall_calls == [
        {"bank_id": "supply-chain-memory", "query": "supplier delay"}
    ]


@pytest.mark.asyncio
async def test_async_variants_fail_softly(monkeypatch):
    api = StubHindsightApi(fail=True)
    monkeypatch.setattr(hindsight_client_module, "client", api)

    assert await aretain(bank_id="supply-chain-memory", content="anything") == {}
    assert await arecall(bank_id="supply-chain-memory", query="supplier delay") == []

