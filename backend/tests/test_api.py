import pytest
from uuid import uuid4

from models import DisruptionCase, Alert
from models.disruption_case import DisruptionType, Severity, DisruptionStatus


async def make_case(db_session, supplier_id, **overrides):
    payload = dict(
        title="Supplier delivery slipped",
        disruption_type=DisruptionType.supplier_delay,
        severity=Severity.high,
        status=DisruptionStatus.detecting,
        affected_supplier_id=supplier_id,
        description="Shipment held at port",
        delay_days=6,
    )
    payload.update(overrides)
    case = DisruptionCase(**payload)
    db_session.add(case)
    await db_session.commit()
    await db_session.refresh(case)
    return case


@pytest.mark.asyncio
async def test_health_endpoint(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["service"] == "supply-chain-monitoring-api"


@pytest.mark.asyncio
async def test_list_suppliers_returns_actual_records(client, sample_supplier, sample_alt_supplier):
    resp = await client.get("/suppliers")
    assert resp.status_code == 200
    body = resp.json()
    names = {s["name"] for s in body}
    assert {"Test Metals Corp", "Global Steel GmbH"} <= names

    supplier = next(s for s in body if s["name"] == "Test Metals Corp")
    assert supplier["lead_time_days"] == 10
    assert supplier["reliability_score"] == 0.92
    assert supplier["status"] == "active"


@pytest.mark.asyncio
async def test_get_supplier_by_id_and_missing_id(client, sample_supplier):
    resp = await client.get(f"/suppliers/{sample_supplier.id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == str(sample_supplier.id)

    missing = await client.get(f"/suppliers/{uuid4()}")
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_list_inventory_and_detail(client, sample_inventory_item):
    resp = await client.get("/inventory")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["current_quantity"] == 500.0
    assert body[0]["daily_demand_rate"] == 25.0

    detail = await client.get(f"/inventory/{sample_inventory_item.id}")
    assert detail.status_code == 200
    assert detail.json()["sku"] == "SKU-STEEL-001"

    missing = await client.get(f"/inventory/{uuid4()}")
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_list_purchase_orders(client, sample_purchase_order):
    resp = await client.get("/purchase-orders")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["order_number"] == "PO-TEST-001"
    assert body[0]["status"] == "in_transit"


@pytest.mark.asyncio
async def test_list_and_get_disruptions(client, db_session, sample_supplier):
    case = await make_case(db_session, sample_supplier.id)

    resp = await client.get("/disruptions")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["id"] == str(case.id)
    assert body[0]["delay_days"] == 6

    detail = await client.get(f"/disruptions/{case.id}")
    assert detail.status_code == 200
    assert detail.json()["title"] == "Supplier delivery slipped"

    missing = await client.get(f"/disruptions/{uuid4()}")
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_agent_trace_endpoint(client, db_session, sample_supplier):
    trace = [{"agent": "Reviewer Agent", "analysis": "checked", "conclusions": "ok"}]
    case = await make_case(db_session, sample_supplier.id, agent_trace=trace)

    resp = await client.get(f"/agents/{case.id}/trace")
    assert resp.status_code == 200
    assert resp.json()["trace"][0]["agent"] == "Reviewer Agent"

    missing = await client.get(f"/agents/{uuid4()}/trace")
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_dashboard_stats_match_actual_data(client, db_session, sample_supplier, sample_inventory_item):
    # Sample item: 500 units / 25 per day = 20 days coverage, so not at risk.
    resp = await client.get("/dashboard/stats")
    assert resp.status_code == 200
    body = resp.json()
    assert body["active_disruptions"] == 0
    assert body["pending_approvals"] == 0
    assert body["inventory_at_risk"] == 0

    await make_case(db_session, sample_supplier.id, status=DisruptionStatus.pending_approval)
    sample_inventory_item.current_quantity = 50.0  # 2 days coverage
    await db_session.commit()

    resp = await client.get("/dashboard/stats")
    body = resp.json()
    assert body["active_disruptions"] == 1
    assert body["pending_approvals"] == 1
    assert body["affected_suppliers"] == 1
    assert body["inventory_at_risk"] == 1
    assert len(body["active_disruption_list"]) == 1


@pytest.mark.asyncio
async def test_alerts_endpoint_and_mark_read(client, db_session, sample_supplier):
    case = await make_case(db_session, sample_supplier.id)
    db_session.add(
        Alert(
            disruption_case_id=case.id,
            alert_type="supplier_delay_alert",
            severity=Severity.high,
            title="Delay warning",
            message="6 day delay reported",
        )
    )
    await db_session.commit()

    resp = await client.get("/alerts")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["is_read"] is False

    read_resp = await client.post(f"/alerts/{body[0]['id']}/read")
    assert read_resp.status_code == 200

    resp = await client.get("/alerts")
    assert resp.json()[0]["is_read"] is True

    missing = await client.post(f"/alerts/{uuid4()}/read")
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_disruption_memory_endpoint(client, db_session, sample_supplier):
    memories = [{"content": "Past steel delay resolved by rerouting", "relevance_score": 0.9}]
    case = await make_case(db_session, sample_supplier.id, hindsight_memories=memories)

    resp = await client.get(f"/disruptions/{case.id}/memory")
    assert resp.status_code == 200
    assert resp.json()["hindsight_memories"] == memories

    missing = await client.get(f"/disruptions/{uuid4()}/memory")
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_memory_endpoint_lists_resolved_cases(client, db_session, sample_supplier):
    case = await make_case(
        db_session,
        sample_supplier.id,
        status=DisruptionStatus.resolved,
        outcome="Rerouted 45 percent of volume, no line stoppage",
    )

    resp = await client.get("/memory")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert str(case.id) == body[0]["id"]
    assert "no line stoppage" in body[0]["content"]


@pytest.mark.asyncio
async def test_simulate_rejects_invalid_payload(client, sample_supplier):
    # Missing required fields
    resp = await client.post("/disruptions/simulate", json={"type": "supplier_delay"})
    assert resp.status_code == 422

    # Unknown enum value
    resp = await client.post(
        "/disruptions/simulate",
        json={
            "type": "meteor_strike",
            "supplier_id": str(sample_supplier.id),
            "description": "unexpected event",
            "delay_days": 5,
            "severity": "high",
        },
    )
    assert resp.status_code == 422

    # Negative delay is not a valid operational input
    resp = await client.post(
        "/disruptions/simulate",
        json={
            "type": "supplier_delay",
            "supplier_id": str(sample_supplier.id),
            "description": "negative delay attempt",
            "delay_days": -3,
            "severity": "high",
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_simulate_rejects_unknown_supplier(client):
    resp = await client.post(
        "/disruptions/simulate",
        json={
            "type": "supplier_delay",
            "supplier_id": str(uuid4()),
            "description": "supplier does not exist in catalog",
            "delay_days": 7,
            "severity": "high",
        },
    )
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Supplier not found"


@pytest.mark.asyncio
async def test_write_endpoints_open_when_no_api_key_configured(
    client, db_session, sample_supplier
):
    """Default deployment: no API key set, so no header is required."""
    case = await make_case(db_session, sample_supplier.id)

    resp = await client.post(f"/disruptions/{case.id}/approve", json={"notes": "ok"})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_write_endpoints_require_api_key_when_configured(
    client, db_session, sample_supplier, monkeypatch
):
    from utils.config import settings

    monkeypatch.setattr(settings, "api_key", "test-secret-key")
    case = await make_case(db_session, sample_supplier.id)

    denied = await client.post(f"/disruptions/{case.id}/approve", json={"notes": "ok"})
    assert denied.status_code == 401

    wrong_key = await client.post(
        f"/disruptions/{case.id}/approve",
        json={"notes": "ok"},
        headers={"X-API-Key": "not-the-key"},
    )
    assert wrong_key.status_code == 401

    allowed = await client.post(
        f"/disruptions/{case.id}/approve",
        json={"notes": "ok"},
        headers={"X-API-Key": "test-secret-key"},
    )
    assert allowed.status_code == 200
