import pytest
from agents.detection import detection_node
from agents.monitoring import monitoring_node
from workflows.state import AgentState


@pytest.mark.asyncio
async def test_monitoring_node_trace_generation():
    state: AgentState = {
        "case_id": "case-mon-1",
        "disruption_type": "logistics",
        "severity": "medium",
        "affected_supplier": {"name": "China Electronics Co"},
        "affected_inventory": {},
        "affected_order": {},
        "delay_days": 7,
        "inventory_coverage_days": 10.0,
        "daily_demand_rate": 50.0,
        "stockout_risk": 0.0,
        "business_impact": {},
        "hindsight_memories": [],
        "alternative_suppliers": [],
        "mitigation_strategies": [],
        "recommendation": {},
        "alerts": [],
        "agent_trace": [],
        "status": "detecting",
    }

    result = await monitoring_node(state)
    assert len(result["agent_trace"]) == 1
    assert result["agent_trace"][0]["agent"] == "Supply Chain Monitoring"
    assert "China Electronics Co" in result["agent_trace"][0]["analysis"]


@pytest.mark.asyncio
async def test_detection_node_critical_classification():
    state: AgentState = {
        "case_id": "case-det-1",
        "disruption_type": "supplier_delay",
        "severity": "critical",
        "affected_supplier": {"name": "India Metals Ltd"},
        "affected_inventory": {},
        "affected_order": {},
        "delay_days": 14,
        "inventory_coverage_days": 3.0,
        "daily_demand_rate": 40.0,
        "stockout_risk": 0.0,
        "business_impact": {},
        "hindsight_memories": [],
        "alternative_suppliers": [],
        "mitigation_strategies": [],
        "recommendation": {},
        "alerts": [],
        "agent_trace": [],
        "status": "detecting",
    }

    result = await detection_node(state)
    assert len(result["agent_trace"]) == 1
    trace = result["agent_trace"][0]
    assert trace["agent"] == "Disruption Detection"
    assert "CRITICAL DISRUPTION" in trace["conclusions"]
