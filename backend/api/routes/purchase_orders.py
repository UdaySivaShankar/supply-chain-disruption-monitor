from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from database.connection import get_db
from services.supply_chain_service import get_all_purchase_orders, get_purchase_order_by_id
from uuid import UUID

router = APIRouter(prefix="/purchase-orders", tags=["Purchase Orders"])

@router.get("")
async def list_purchase_orders(db: AsyncSession = Depends(get_db)):
    return await get_all_purchase_orders(db)

@router.get("/{id}")
async def get_purchase_order(id: UUID, db: AsyncSession = Depends(get_db)):
    po = await get_purchase_order_by_id(db, id)
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    return po
