import pytest

from agents.mitigation import mitigation_node
from workflows.state import AgentState
from models.supplier import Supplier, SupplierStatus


def base_state(supplier_name="Test Metals Corp", **overrides):
    state: AgentState = {
        "case_id": "case-supplier-1",
        "disruption_type": "supplier_delay",
        "severity": "high",
        "affected_supplier": {"name": supplier_name},
        "affected_inventory": {"unit_cost": 800.0},
        "affected_order": {},
        "delay_days": 10,
        "inventory_coverage_days": 5.0,
        "daily_demand_rate": 25.0,
        "stockout_risk": 0.75,
        "business_impact": {"estimated_financial_loss": 150000.0},
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


async def add_supplier(db_session, **overrides):
    payload = dict(
        name="Alternative Co",
        country="Germany",
        city="Berlin",
        contact_email="ops@alternative.co",
        lead_time_days=9,
        reliability_score=0.8,
        capabilities=["steel"],
        status=SupplierStatus.active,
    )
    payload.update(overrides)
    supplier = Supplier(**payload)
    db_session.add(supplier)
    await db_session.commit()
    await db_session.refresh(supplier)
    return supplier


@pytest.mark.asyncio
async def test_alternative_suppliers_sorted_by_reliability(
    db_session, sample_supplier, sample_alt_supplier
):
    await add_supplier(
        db_session, name="Mid Reliable Ltd", reliability_score=0.8, lead_time_days=14
    )

    state = await mitigation_node(base_state())

    names = [s["name"] for s in state["alternative_suppliers"]]
    scores = [s["reliability_score"] for s in state["alternative_suppliers"]]
    assert scores == sorted(scores, reverse=True)
    assert names[0] == "Global Steel GmbH"  # 0.96 beats 0.92 and 0.80
    assert state["recommendation"]["alternative_supplier"] == "Global Steel GmbH"
    assert state["recommendation"]["steps"][0].startswith("Request immediate spot quote")


@pytest.mark.asyncio
async def test_affected_supplier_is_never_offered_as_its_own_alternative(
    db_session, sample_supplier, sample_alt_supplier
):
    state = await mitigation_node(base_state(supplier_name=sample_supplier.name))

    names = [s["name"] for s in state["alternative_suppliers"]]
    assert sample_supplier.name not in names
    assert names


@pytest.mark.asyncio
async def test_only_active_suppliers_are_considered(db_session, sample_supplier):
    await add_supplier(
        db_session,
        name="Inactive Superior Ltd",
        reliability_score=0.99,
        status=SupplierStatus.suspended,
    )
    await add_supplier(
        db_session, name="Active Backup Ltd", reliability_score=0.85, lead_time_days=6
    )

    state = await mitigation_node(base_state())

    names = [s["name"] for s in state["alternative_suppliers"]]
    assert "Inactive Superior Ltd" not in names
    assert "Active Backup Ltd" in names
    assert state["recommendation"]["alternative_supplier"] == "Active Backup Ltd"


@pytest.mark.asyncio
async def test_lead_time_of_selected_alternative_is_used_in_plan(
    db_session, sample_supplier, sample_alt_supplier
):
    state = await mitigation_node(base_state())

    plan = state["recommendation"]["steps"]
    assert any("7 days" in step for step in plan)  # Global Steel GmbH lead time
    assert state["alternative_suppliers"][0]["lead_time_days"] == 7


@pytest.mark.asyncio
async def test_supplier_comparison_reports_evidence_in_trace(
    db_session, sample_supplier, sample_alt_supplier
):
    state = await mitigation_node(base_state())

    trace = state["agent_trace"][0]
    assert trace["agent"] == "Alternative Supplier and Mitigation"
    assert "alternative suppliers from PostgreSQL operational state" in trace["analysis"]
    assert "Selected Global Steel GmbH as optimal candidate" in trace["analysis"]
    assert state["alternative_suppliers"][0]["id"] == str(sample_alt_supplier.id)


@pytest.mark.asyncio
async def test_no_alternative_available_falls_back_to_documented_default(
    db_session, sample_supplier
):
    """Only the disrupted supplier exists, so the agent must still respond."""
    state = await mitigation_node(base_state(supplier_name=sample_supplier.name))

    assert state["alternative_suppliers"] == []
    assert state["recommendation"]["alternative_supplier"] == "German Plastics GmbH"
    assert state["recommendation"]["confidence_score"] == 0.76
