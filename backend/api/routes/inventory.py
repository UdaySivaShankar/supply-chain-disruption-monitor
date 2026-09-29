from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from database.connection import get_db
from services.supply_chain_service import get_all_inventory, get_inventory_by_id
from uuid import UUID

router = APIRouter(prefix="/inventory", tags=["Inventory"])

@router.get("")
async def list_inventory(db: AsyncSession = Depends(get_db)):
    return await get_all_inventory(db)

@router.get("/{id}")
async def get_inventory(id: UUID, db: AsyncSession = Depends(get_db)):
    item = await get_inventory_by_id(db, id)
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    return item
