import pytest
from sqlalchemy.future import select

from models import DisruptionCase, ApprovalRequest, Alert
from models.approval_request import ApprovalStatus
from models.disruption_case import DisruptionType, Severity, DisruptionStatus
from workflows.disruption_workflow import app as workflow_app
from workflows.state import AgentState


EXPECTED_AGENT_SEQUENCE = [
    "Supply Chain Monitoring",
    "Disruption Detection",
    "Inventory and Demand Analysis",
    "Impact Assessment",
    "Alternative Supplier and Mitigation",
    "Alert and Response Planning",
    "Reviewer Agent",
    "Human Approval Gatekeeper",
]


async def seed_case(db_session, sample_supplier, sample_inventory_item):
    case = DisruptionCase(
        title="Steel shipment delayed",
        disruption_type=DisruptionType.supplier_delay,
        severity=Severity.high,
        status=DisruptionStatus.detecting,
        affected_supplier_id=sample_supplier.id,
        description="Vessel rerouted, delivery slips past stockout date",
        delay_days=10,
    )
    db_session.add(case)
    await db_session.commit()
    await db_session.refresh(case)
    return case


def build_state(case, item) -> AgentState:
    coverage = round(item.current_quantity / item.daily_demand_rate, 1)
    return {
        "case_id": str(case.id),
        "disruption_type": case.disruption_type.value,
        "severity": case.severity.value,
        "affected_supplier": {"name": "Test Metals Corp"},
        "affected_inventory": {
            "name": item.name,
            "sku": item.sku,
            "unit_cost": float(item.unit_cost),
            "current_quantity": float(item.current_quantity),
            "daily_demand_rate": float(item.daily_demand_rate),
        },
        "affected_order": {},
        "delay_days": case.delay_days,
        "inventory_coverage_days": coverage,
        "daily_demand_rate": float(item.daily_demand_rate),
        "stockout_risk": 0.0,
        "business_impact": {},
        "hindsight_memories": [],
        "alternative_suppliers": [],
        "mitigation_strategies": [],
        "recommendation": {},
        "alerts": [],
        "agent_trace": [],
        "status": case.status.value,
    }


@pytest.mark.asyncio
async def test_workflow_runs_all_seven_agents_in_order(
    db_session, sample_supplier, sample_inventory_item, hindsight_store
):
    case = await seed_case(db_session, sample_supplier, sample_inventory_item)

    result = await workflow_app.ainvoke(build_state(case, sample_inventory_item))

    agents = [entry["agent"] for entry in result["agent_trace"]]
    assert agents == EXPECTED_AGENT_SEQUENCE

    # Every step must carry explainability content for the UI.
    for entry in result["agent_trace"]:
        assert entry["analysis"]
        assert entry["conclusions"]
        assert entry["data_used"]

    assert result["status"] == "pending_approval"


@pytest.mark.asyncio
async def test_workflow_calculates_inventory_and_impact_from_operational_data(
    db_session, sample_supplier, sample_inventory_item
):
    case = await seed_case(db_session, sample_supplier, sample_inventory_item)

    result = await workflow_app.ainvoke(build_state(case, sample_inventory_item))

    # 500 units / 25 per day = 20 days coverage against a 10 day delay.
    assert result["inventory_coverage_days"] == 20.0
    # Coverage exceeds delay, so the risk is moderate rather than critical.
    assert 0 < result["stockout_risk"] <= 0.4
    assert result["business_impact"]["estimated_financial_loss"] >= 0
    assert result["recommendation"]["recommended_action"]
    assert result["recommendation"]["confidence_score"] in (0.76, 0.94)


@pytest.mark.asyncio
async def test_workflow_never_executes_actions_without_human_approval(
    db_session, sample_supplier, sample_inventory_item, hindsight_store
):
    case = await seed_case(db_session, sample_supplier, sample_inventory_item)

    result = await workflow_app.ainvoke(build_state(case, sample_inventory_item))

    await db_session.refresh(case)
    assert case.status == DisruptionStatus.pending_approval
    # The disrupted supplier must not be switched automatically.
    assert case.affected_supplier_id == sample_supplier.id
    assert case.outcome is None

    approval_res = await db_session.execute(
        select(ApprovalRequest).where(ApprovalRequest.disruption_case_id == case.id)
    )
    approval = approval_res.scalars().one()
    assert approval.status == ApprovalStatus.pending
    assert approval.decided_at is None
    assert approval.recommended_action

    gatekeeper = result["agent_trace"][-1]
    assert gatekeeper["agent"] == "Human Approval Gatekeeper"
    assert "requires human approval" in gatekeeper["conclusions"]

    # No experience may be retained before the case is actually resolved.
    assert hindsight_store.memories == []


@pytest.mark.asyncio
async def test_workflow_generates_alerts_and_persists_analysis(
    db_session, sample_supplier, sample_inventory_item
):
    case = await seed_case(db_session, sample_supplier, sample_inventory_item)

    result = await workflow_app.ainvoke(build_state(case, sample_inventory_item))

    await db_session.refresh(case)
    assert case.recommendation["recommended_action"]
    assert case.agent_trace[-1]["agent"] == "Human Approval Gatekeeper"
    assert case.hindsight_memories == []

    alerts_res = await db_session.execute(select(Alert).where(Alert.disruption_case_id == case.id))
    alerts = list(alerts_res.scalars().all())
    assert len(alerts) == 1
    assert "Awaiting mandatory human operator authorization" in alerts[0].message


@pytest.mark.asyncio
async def test_workflow_trace_marks_hindsight_contribution(
    db_session, sample_supplier, sample_inventory_item, hindsight_store
):
    case = await seed_case(db_session, sample_supplier, sample_inventory_item)

    result = await workflow_app.ainvoke(build_state(case, sample_inventory_item))

    mitigation = next(
        entry
        for entry in result["agent_trace"]
        if entry["agent"] == "Alternative Supplier and Mitigation"
    )
    assert hindsight_store.recall_calls
    assert "Hindsight recall queried memory bank" in mitigation["analysis"]
    assert "Hindsight Memories Recalled: 0" in mitigation["data_used"]

    reviewer = next(
        entry for entry in result["agent_trace"] if entry["agent"] == "Reviewer Agent"
    )
    assert "Historical Hindsight context incorporated" in reviewer["analysis"]
