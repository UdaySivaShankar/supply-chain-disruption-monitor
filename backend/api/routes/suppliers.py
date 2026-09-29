from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from database.connection import get_db
from services.supply_chain_service import get_all_suppliers, get_supplier_by_id
from uuid import UUID

router = APIRouter(prefix="/suppliers", tags=["Suppliers"])

@router.get("")
async def list_suppliers(db: AsyncSession = Depends(get_db)):
    return await get_all_suppliers(db)

@router.get("/{id}")
async def get_supplier(id: UUID, db: AsyncSession = Depends(get_db)):
    supplier = await get_supplier_by_id(db, id)
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return supplier
