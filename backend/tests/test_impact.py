import pytest
from agents.impact_assessment import impact_assessment_node
from workflows.state import AgentState


@pytest.mark.asyncio
async def test_impact_assessment_financial_loss():
    # 10 days delay with 5 days coverage -> 5 days shortage * 20 units/day * $500/unit + downtime
    state: AgentState = {
        "case_id": "case-imp-1",
        "disruption_type": "supplier_delay",
        "severity": "high",
        "affected_supplier": {"name": "Test Metals"},
        "affected_inventory": {"unit_cost": 500.0},
        "affected_order": {},
        "delay_days": 10,
        "inventory_coverage_days": 5.0,
        "daily_demand_rate": 20.0,
        "stockout_risk": 0.85,
        "business_impact": {},
        "hindsight_memories": [],
        "alternative_suppliers": [],
        "mitigation_strategies": [],
        "recommendation": {},
        "alerts": [],
        "agent_trace": [],
        "status": "analyzing",
    }

    result = await impact_assessment_node(state)
    impact = result["business_impact"]
    assert impact["estimated_financial_loss"] > 0
    assert impact["days_short"] == 5.0
    assert impact["direct_materials_at_risk"] == 5.0 * 20.0 * 500.0  # $50,000

    trace = result["agent_trace"][0]
    assert trace["agent"] == "Impact Assessment"
    assert "Direct Material Value" in trace["data_used"][2]
