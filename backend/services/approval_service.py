from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models import ApprovalRequest, DisruptionCase
from models.approval_request import ApprovalStatus
from models.disruption_case import DisruptionStatus
from typing import Optional
from uuid import UUID
from datetime import datetime, timezone

async def get_approval_request_by_case(db: AsyncSession, case_id: UUID) -> Optional[ApprovalRequest]:
    result = await db.execute(select(ApprovalRequest).where(ApprovalRequest.disruption_case_id == case_id))
    return result.scalars().first()

async def update_approval_status(db: AsyncSession, case_id: UUID, status: ApprovalStatus, notes: str = None) -> Optional[ApprovalRequest]:
    req = await get_approval_request_by_case(db, case_id)
    if req:
        req.status = status
        req.reviewer_notes = notes
        req.decided_at = datetime.now(timezone.utc)
        
        # also update case status
        case_res = await db.execute(select(DisruptionCase).where(DisruptionCase.id == case_id))
        case = case_res.scalars().first()
        if case:
            case.status = DisruptionStatus.approved if status == ApprovalStatus.approved else DisruptionStatus.rejected
        
        await db.commit()
    return req
