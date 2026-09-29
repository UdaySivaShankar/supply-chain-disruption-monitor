from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models import Supplier, InventoryItem, PurchaseOrder
from typing import List, Optional
from uuid import UUID

async def get_all_suppliers(db: AsyncSession) -> List[Supplier]:
    result = await db.execute(select(Supplier))
    return list(result.scalars().all())

async def get_supplier_by_id(db: AsyncSession, supplier_id: UUID) -> Optional[Supplier]:
    result = await db.execute(select(Supplier).where(Supplier.id == supplier_id))
    return result.scalars().first()

async def get_all_inventory(db: AsyncSession) -> List[InventoryItem]:
    result = await db.execute(select(InventoryItem))
    return list(result.scalars().all())

async def get_inventory_by_id(db: AsyncSession, inventory_id: UUID) -> Optional[InventoryItem]:
    result = await db.execute(select(InventoryItem).where(InventoryItem.id == inventory_id))
    return result.scalars().first()

async def get_all_purchase_orders(db: AsyncSession) -> List[PurchaseOrder]:
    result = await db.execute(select(PurchaseOrder))
    return list(result.scalars().all())

async def get_purchase_order_by_id(db: AsyncSession, po_id: UUID) -> Optional[PurchaseOrder]:
    result = await db.execute(select(PurchaseOrder).where(PurchaseOrder.id == po_id))
    return result.scalars().first()
