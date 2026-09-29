import pytest
from sqlalchemy.future import select
from uuid import uuid4

from models import DisruptionCase, ApprovalRequest
from models.approval_request import ApprovalStatus
from models.disruption_case import DisruptionType, Severity, DisruptionStatus
from services.approval_service import get_approval_request_by_case, update_approval_status


async def seed_case(db_session, sample_supplier, status=DisruptionStatus.pending_approval):
    case = DisruptionCase(
        title="Approval case",
        disruption_type=DisruptionType.supplier_delay,
        severity=Severity.medium,
        status=status,
        affected_supplier_id=sample_supplier.id,
        description="Awaiting operator decision",
        delay_days=4,
        recommendation={
            "recommended_action": "Reroute 45 percent of volume",
            "confidence_score": 0.94,
            "risk_level": "Low",
        },
    )
    db_session.add(case)
    await db_session.commit()
    await db_session.refresh(case)
    return case


async def seed_pending_approval(db_session, case):
    request = ApprovalRequest(
        disruption_case_id=case.id,
        recommendation_summary="Reroute 45 percent of volume to Global Steel GmbH",
        recommended_action="Reroute 45 percent of volume",
        confidence_score=0.94,
        risk_level="Low",
        status=ApprovalStatus.pending,
    )
    db_session.add(request)
    await db_session.commit()
    await db_session.refresh(request)
    return request


@pytest.mark.asyncio
async def test_get_approval_request_returns_none_when_absent(db_session, sample_supplier):
    case = await seed_case(db_session, sample_supplier)
    assert await get_approval_request_by_case(db_session, case.id) is None


@pytest.mark.asyncio
async def test_service_approval_marks_case_approved(db_session, sample_supplier):
    case = await seed_case(db_session, sample_supplier)
    await seed_pending_approval(db_session, case)

    updated = await update_approval_status(
        db_session, case.id, ApprovalStatus.approved, notes="Checked evidence"
    )

    assert updated is not None
    assert updated.status == ApprovalStatus.approved
    assert updated.reviewer_notes == "Checked evidence"
    assert updated.decided_at is not None

    await db_session.refresh(case)
    assert case.status == DisruptionStatus.approved


@pytest.mark.asyncio
async def test_service_rejection_marks_case_rejected(db_session, sample_supplier):
    case = await seed_case(db_session, sample_supplier)
    await seed_pending_approval(db_session, case)

    updated = await update_approval_status(db_session, case.id, ApprovalStatus.rejected)

    assert updated.status == ApprovalStatus.rejected
    await db_session.refresh(case)
    assert case.status == DisruptionStatus.rejected


@pytest.mark.asyncio
async def test_api_approve_creates_approval_record_and_trace(client, db_session, sample_supplier):
    case = await seed_case(db_session, sample_supplier)

    resp = await client.post(
        f"/disruptions/{case.id}/approve", json={"notes": "Approved by shift lead"}
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"

    await db_session.refresh(case)
    assert case.status == DisruptionStatus.approved
    assert case.agent_trace[-1]["agent"] == "Human Operations Manager"
    assert "Approved by shift lead" in case.agent_trace[-1]["analysis"]

    approval = (
        await db_session.execute(
            select(ApprovalRequest).where(ApprovalRequest.disruption_case_id == case.id)
        )
    ).scalars().one()
    assert approval.status == ApprovalStatus.approved
    assert approval.decided_at is not None
    assert approval.reviewer_notes == "Approved by shift lead"


@pytest.mark.asyncio
async def test_api_approve_updates_existing_pending_request(client, db_session, sample_supplier):
    case = await seed_case(db_session, sample_supplier)
    await seed_pending_approval(db_session, case)

    resp = await client.post(f"/disruptions/{case.id}/approve", json={"notes": "go ahead"})
    assert resp.status_code == 200

    rows = (
        await db_session.execute(
            select(ApprovalRequest).where(ApprovalRequest.disruption_case_id == case.id)
        )
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].status == ApprovalStatus.approved


@pytest.mark.asyncio
async def test_api_reject_marks_case_rejected(client, db_session, sample_supplier):
    case = await seed_case(db_session, sample_supplier)
    await seed_pending_approval(db_session, case)

    resp = await client.post(
        f"/disruptions/{case.id}/reject", json={"notes": "Too expensive"}
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"

    await db_session.refresh(case)
    assert case.status == DisruptionStatus.rejected

    approval = (
        await db_session.execute(
            select(ApprovalRequest).where(ApprovalRequest.disruption_case_id == case.id)
        )
    ).scalars().one()
    assert approval.status == ApprovalStatus.rejected
    assert approval.reviewer_notes == "Too expensive"


@pytest.mark.asyncio
async def test_api_approve_rejects_unknown_case(client):
    resp = await client.post(f"/disruptions/{uuid4()}/approve", json={"notes": "x"})
    assert resp.status_code == 404

    resp = await client.post(f"/disruptions/{uuid4()}/reject", json={"notes": "x"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_approve_validates_payload(client, db_session, sample_supplier):
    case = await seed_case(db_session, sample_supplier)

    # Notes longer than the accepted limit are rejected
    resp = await client.post(
        f"/disruptions/{case.id}/approve", json={"notes": "x" * 2001}
    )
    assert resp.status_code == 422
