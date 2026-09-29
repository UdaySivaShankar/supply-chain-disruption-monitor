import pytest
from agents.inventory_analysis import inventory_analysis_node
from workflows.state import AgentState


@pytest.mark.asyncio
async def test_inventory_coverage_deficit_calculation():
    # Scenario: delay (10 days) > coverage (5 days) -> stockout projected
    state: AgentState = {
        "case_id": "test-case-1",
        "disruption_type": "supplier_delay",
        "severity": "high",
        "affected_supplier": {"name": "Test Supplier"},
        "affected_inventory": {"unit_cost": 800.0},
        "affected_order": {},
        "delay_days": 10,
        "inventory_coverage_days": 5.0,
        "daily_demand_rate": 20.0,
        "stockout_risk": 0.0,
        "business_impact": {},
        "hindsight_memories": [],
        "alternative_suppliers": [],
        "mitigation_strategies": [],
        "recommendation": {},
        "alerts": [],
        "agent_trace": [],
        "status": "analyzing",
    }

    result = await inventory_analysis_node(state)

    assert result["stockout_risk"] >= 0.70
    assert result["inventory_coverage_days"] == 5.0
    assert len(result["agent_trace"]) == 1
    trace_entry = result["agent_trace"][0]
    assert trace_entry["agent"] == "Inventory and Demand Analysis"
    assert "stockout deficit" in trace_entry["analysis"]


@pytest.mark.asyncio
async def test_inventory_coverage_sufficient_buffer():
    # Scenario: delay (3 days) < coverage (15 days) -> low risk
    state: AgentState = {
        "case_id": "test-case-2",
        "disruption_type": "supplier_delay",
        "severity": "low",
        "affected_supplier": {"name": "Test Supplier"},
        "affected_inventory": {"unit_cost": 50.0},
        "affected_order": {},
        "delay_days": 3,
        "inventory_coverage_days": 15.0,
        "daily_demand_rate": 10.0,
        "stockout_risk": 0.0,
        "business_impact": {},
        "hindsight_memories": [],
        "alternative_suppliers": [],
        "mitigation_strategies": [],
        "recommendation": {},
        "alerts": [],
        "agent_trace": [],
        "status": "analyzing",
    }

    result = await inventory_analysis_node(state)

    assert result["stockout_risk"] < 0.40
    assert result["inventory_coverage_days"] == 15.0
    assert "cushion" in result["agent_trace"][0]["analysis"]
