from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from database.connection import get_db
from models.disruption_case import DisruptionCase
from sqlalchemy.future import select
from uuid import UUID

router = APIRouter(prefix="/agents", tags=["Agents"])

@router.get("/{case_id}/trace")
async def get_agent_trace(case_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DisruptionCase).where(DisruptionCase.id == case_id))
    case = result.scalars().first()
    if not case:
        raise HTTPException(status_code=404, detail="Disruption case not found")
    
    return {"trace": case.agent_trace}
