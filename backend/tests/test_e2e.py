"""End to end disruption lifecycle.

Covers the flow required by the specification: simulate a disruption, run the
agent workflow, generate a recommendation, approve it, record the outcome,
verify the experience is retained in Hindsight, then trigger a similar
disruption and prove the recalled experience changes the recommendation.
"""

import uuid

import pytest

from sqlalchemy.future import select

from models import DisruptionCase, ApprovalRequest
from models.approval_request import ApprovalStatus
from models.disruption_case import DisruptionStatus
from models.inventory_item import InventoryItem
from models.supplier import Supplier, SupplierStatus
from utils.config import settings


async def seed_abc_supplier(db_session):
    """Supplier ABC with 25 tonnes on hand and 5 tonnes per day demand."""
    supplier = Supplier(
        name="Supplier ABC Steel Co",
        country="India",
        city="Mumbai",
        contact_email="ops@supplierabc.example",
        lead_time_days=12,
        reliability_score=0.88,
        capabilities=["steel"],
        status=SupplierStatus.active,
    )
    db_session.add(supplier)
    await db_session.flush()

    item = InventoryItem(
        name="Grade A Steel Sheet",
        sku="SKU-ABC-STEEL",
        category="Raw Metal",
        current_quantity=25.0,
        unit="tonnes",
        daily_demand_rate=5.0,
        safety_stock=10.0,
        reorder_point=20.0,
        primary_supplier_id=supplier.id,
        unit_cost=800.0,
    )
    db_session.add(item)
    await db_session.commit()
    await db_session.refresh(supplier)
    return supplier, item


async def trigger_disruption(client, supplier, delay_days=10, severity="critical"):
    resp = await client.post(
        "/disruptions/simulate",
        json={
            "type": "supplier_delay",
            "supplier_id": str(supplier.id),
            "description": "Supplier ABC reports a delivery delay",
            "delay_days": delay_days,
            "severity": severity,
        },
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["case_id"]


async def fetch_case(client, case_id):
    resp = await client.get(f"/disruptions/{case_id}")
    assert resp.status_code == 200
    return resp.json()


@pytest.mark.asyncio
async def test_end_to_end_disruption_lifecycle_with_hindsight_learning(
    client, db_session, hindsight_store
):
    supplier, item = await seed_abc_supplier(db_session)

    # ---------------------------------------------------------------- 1. simulate
    first_case_id = await trigger_disruption(client, supplier)

    # ---------------------------------------------------------------- 2. agents ran
    first = await fetch_case(client, first_case_id)
    assert first["status"] == "pending_approval"
    agent_names = [entry["agent"] for entry in first["agent_trace"]]
    assert agent_names[0] == "Supply Chain Monitoring"
    assert agent_names[-1] == "Human Approval Gatekeeper"
    assert len(agent_names) == 8

    # ------------------------------------------------- 3. inventory and impact math
    assert first["inventory_coverage_days"] == 5.0  # 25 tonnes / 5 tonnes per day
    assert first["stockout_risk"] >= 0.7  # 10 day delay against 5 days of cover
    assert first["estimated_impact_value"] > 0

    # ------------------------------------------------------ 4. hindsight was searched
    assert hindsight_store.recall_calls, "mitigation agent must search Hindsight"
    assert first["hindsight_memories"] == []  # first event, no prior experience

    # ----------------------------------------------------- 5. recommendation drafted
    recommendation = first["recommendation"]
    assert recommendation["recommended_action"]
    assert recommendation["alternative_supplier"]
    first_confidence = recommendation["confidence_score"]
    assert first_confidence == 0.76
    assert "No previous disruption memory found in Hindsight" in recommendation["rationale"]

    # ---------------------------------------------------------- 6. explainability
    trace_resp = await client.get(f"/agents/{first_case_id}/trace")
    assert trace_resp.status_code == 200
    trace = trace_resp.json()["trace"]
    mitigation_entry = next(e for e in trace if e["agent"] == "Alternative Supplier and Mitigation")
    assert "Hindsight recall queried memory bank" in mitigation_entry["analysis"]
    assert "PostgreSQL operational state" in mitigation_entry["analysis"]

    memory_resp = await client.get(f"/disruptions/{first_case_id}/memory")
    assert memory_resp.status_code == 200
    assert memory_resp.json()["hindsight_memories"] == []

    # -------------------------------------------------- 7. human approval (mandatory)
    approval_resp = await client.post(
        f"/disruptions/{first_case_id}/approve",
        json={"notes": "Approved after reviewing evidence"},
    )
    assert approval_resp.status_code == 200
    first = await fetch_case(client, first_case_id)
    assert first["status"] == "approved"

    # ------------------------------------------------------- 8. resolve and retain
    outcome_text = (
        "Rerouted 45 percent of volume to the alternative supplier, "
        "delivery landed 2 days before stockout, no line stoppage"
    )
    resolve_resp = await client.post(
        f"/disruptions/{first_case_id}/resolve", json={"outcome": outcome_text}
    )
    assert resolve_resp.status_code == 200

    first = await fetch_case(client, first_case_id)
    assert first["status"] == "resolved"
    assert first["outcome"] == outcome_text

    assert len(hindsight_store.retain_calls) == 1
    retained = hindsight_store.retain_calls[0]
    assert retained["bank_id"] == settings.hindsight_bank_id
    assert "Supplier ABC Steel Co" in retained["content"]
    assert outcome_text in retained["content"]

    # ------------------------------------------------- 9. retained memory is visible
    memory_page = await client.get("/memory")
    assert memory_page.status_code == 200
    assert any("Supplier ABC" in entry["content"] for entry in memory_page.json())

    approval_rows = (
        await db_session.execute(
            select(ApprovalRequest).where(
                ApprovalRequest.disruption_case_id == uuid.UUID(first["id"])
            )
        )
    ).scalars().all()
    assert len(approval_rows) == 1
    assert approval_rows[0].status == ApprovalStatus.approved
    assert approval_rows[0].decided_at is not None

    # ------------------------------------------- 10. trigger a similar disruption
    second_case_id = await trigger_disruption(client, supplier)
    second = await fetch_case(client, second_case_id)
    assert second["id"] != first["id"]
    assert second["status"] == "pending_approval"

    # --------------------------------- 11. recalled experience changes the outcome
    assert len(second["hindsight_memories"]) == 1
    assert "no line stoppage" in second["hindsight_memories"][0]["content"]

    second_recommendation = second["recommendation"]
    assert second_recommendation["confidence_score"] > first_confidence
    assert second_recommendation["risk_level"] == "Low"
    assert "Hindsight long-term memory retrieved" in second_recommendation["rationale"]

    # --------------------------------------------- 12. dashboard reflects real state
    stats = (await client.get("/dashboard/stats")).json()
    assert stats["active_disruptions"] == 1  # first case resolved, second pending
    assert stats["pending_approvals"] == 1
    assert stats["affected_suppliers"] == 1


@pytest.mark.asyncio
async def test_end_to_end_rejected_recommendation_is_recorded(
    client, db_session, hindsight_store
):
    """A rejected recommendation is recorded and never executes the action."""
    supplier, item = await seed_abc_supplier(db_session)

    case_id = await trigger_disruption(client, supplier, delay_days=4, severity="medium")

    reject_resp = await client.post(
        f"/disruptions/{case_id}/reject", json={"notes": "Alternative supplier failed audit"}
    )
    assert reject_resp.status_code == 200

    case = await fetch_case(client, case_id)
    assert case["status"] == "rejected"
    assert case["outcome"] is None

    # Nothing may be retained until the case is actually resolved.
    assert hindsight_store.retain_calls == []

    approval_rows = (
        await db_session.execute(
            select(ApprovalRequest).where(ApprovalRequest.disruption_case_id == uuid.UUID(case["id"]))
        )
    ).scalars().all()
    assert len(approval_rows) == 1
    assert approval_rows[0].status == ApprovalStatus.rejected
