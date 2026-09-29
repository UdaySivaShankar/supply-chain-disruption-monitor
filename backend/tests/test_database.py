import pytest
from sqlalchemy.future import select
from models import Supplier, InventoryItem, PurchaseOrder, DisruptionCase, Alert, ApprovalRequest
from models.supplier import SupplierStatus
from models.disruption_case import DisruptionType, Severity, DisruptionStatus
from models.approval_request import ApprovalStatus
import uuid


@pytest.mark.asyncio
async def test_database_crud_supplier(db_session):
    # Create
    sup = Supplier(
        name="Apex Industrial",
        country="Japan",
        city="Tokyo",
        lead_time_days=14,
        reliability_score=0.98,
        capabilities=["electronics", "semiconductors"],
        status=SupplierStatus.active,
    )
    db_session.add(sup)
    await db_session.commit()
    await db_session.refresh(sup)

    assert sup.id is not None
    assert sup.name == "Apex Industrial"

    # Read
    res = await db_session.execute(select(Supplier).where(Supplier.name == "Apex Industrial"))
    fetched = res.scalars().first()
    assert fetched is not None
    assert fetched.country == "Japan"
    assert "semiconductors" in fetched.capabilities

    # Update
    fetched.reliability_score = 0.99
    await db_session.commit()
    await db_session.refresh(fetched)
    assert fetched.reliability_score == 0.99


@pytest.mark.asyncio
async def test_database_inventory_supplier_relationship(db_session, sample_supplier, sample_inventory_item):
    res = await db_session.execute(
        select(InventoryItem).where(InventoryItem.id == sample_inventory_item.id)
    )
    item = res.scalars().first()
    assert item is not None
    assert item.primary_supplier_id == sample_supplier.id
    assert item.current_quantity == 500.0


@pytest.mark.asyncio
async def test_database_disruption_case_and_alerts(db_session, sample_supplier):
    case = DisruptionCase(
        title="Supplier Delay Event",
        disruption_type=DisruptionType.supplier_delay,
        severity=Severity.high,
        status=DisruptionStatus.detecting,
        affected_supplier_id=sample_supplier.id,
        description="Shipment held due to customs inspection",
        delay_days=8,
    )
    db_session.add(case)
    await db_session.commit()
    await db_session.refresh(case)

    assert case.id is not None
    assert case.status == DisruptionStatus.detecting

    # Add Alert
    alert = Alert(
        disruption_case_id=case.id,
        alert_type="supplier_delay_alert",
        severity=Severity.high,
        title="Delay Warning",
        message="8 day delay reported",
    )
    db_session.add(alert)
    await db_session.commit()

    alert_res = await db_session.execute(select(Alert).where(Alert.disruption_case_id == case.id))
    fetched_alert = alert_res.scalars().first()
    assert fetched_alert is not None
    assert fetched_alert.title == "Delay Warning"
    assert fetched_alert.is_read is False
