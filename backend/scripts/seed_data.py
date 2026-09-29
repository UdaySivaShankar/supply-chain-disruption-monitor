import asyncio
import sys
import os

# Ensure backend dir is in path when running directly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import AsyncSessionLocal, engine
from models import Base, Supplier, InventoryItem, PurchaseOrder
from models.supplier import SupplierStatus
from models.purchase_order import POStatus
from datetime import datetime, timezone, timedelta
import uuid


async def seed():
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        # Check if already seeded
        from sqlalchemy.future import select
        existing = await db.execute(select(Supplier).limit(1))
        if existing.scalars().first():
            print("Database already seeded. Skipping.")
            return

        # ── Suppliers ──────────────────────────────────────────────
        suppliers = [
            Supplier(
                name="India Metals Ltd",
                country="India",
                city="Mumbai",
                contact_email="ops@indiametals.com",
                lead_time_days=12,
                reliability_score=0.88,
                capabilities=["steel", "iron ore", "aluminum"],
                status=SupplierStatus.active,
            ),
            Supplier(
                name="China Electronics Co",
                country="China",
                city="Shenzhen",
                contact_email="supply@chinaelec.cn",
                lead_time_days=18,
                reliability_score=0.75,
                capabilities=["microchips", "circuit boards", "sensors"],
                status=SupplierStatus.active,
            ),
            Supplier(
                name="German Plastics GmbH",
                country="Germany",
                city="Stuttgart",
                contact_email="orders@germanplastics.de",
                lead_time_days=8,
                reliability_score=0.95,
                capabilities=["plastics", "polymers", "composites"],
                status=SupplierStatus.active,
            ),
            Supplier(
                name="USA Chemical Corp",
                country="USA",
                city="Houston",
                contact_email="sales@usachem.com",
                lead_time_days=6,
                reliability_score=0.91,
                capabilities=["industrial chemicals", "solvents", "adhesives"],
                status=SupplierStatus.active,
            ),
            Supplier(
                name="Japan Tech Industries",
                country="Japan",
                city="Osaka",
                contact_email="export@japantech.jp",
                lead_time_days=14,
                reliability_score=0.97,
                capabilities=["precision components", "electronics", "optics"],
                status=SupplierStatus.active,
            ),
            Supplier(
                name="Brazil Pack Solutions",
                country="Brazil",
                city="Sao Paulo",
                contact_email="contact@brazilpack.br",
                lead_time_days=20,
                reliability_score=0.72,
                capabilities=["cardboard packaging", "plastic containers", "labels"],
                status=SupplierStatus.active,
            ),
            Supplier(
                name="Mexico Auto Parts",
                country="Mexico",
                city="Monterrey",
                contact_email="info@mexauto.mx",
                lead_time_days=7,
                reliability_score=0.83,
                capabilities=["steel stampings", "fasteners", "brackets"],
                status=SupplierStatus.active,
            ),
            Supplier(
                name="UK Specialty Supplies",
                country="United Kingdom",
                city="Birmingham",
                contact_email="procurement@ukspecialty.co.uk",
                lead_time_days=10,
                reliability_score=0.89,
                capabilities=["specialty chemicals", "lab materials", "technical plastics"],
                status=SupplierStatus.active,
            ),
        ]
        db.add_all(suppliers)
        await db.flush()  # Get IDs assigned

        # ── Inventory Items ────────────────────────────────────────
        items = [
            InventoryItem(
                name="Cold-Rolled Steel Sheet Grade A",
                sku="STL-CR-A001",
                category="Raw Metal",
                current_quantity=1200.0,
                unit="tonnes",
                daily_demand_rate=48.0,
                safety_stock=96.0,
                reorder_point=192.0,
                primary_supplier_id=suppliers[0].id,
                unit_cost=850.0,
            ),
            InventoryItem(
                name="Microcontroller Unit MCU-32",
                sku="ELC-MCU-032",
                category="Electronics",
                current_quantity=25000.0,
                unit="units",
                daily_demand_rate=800.0,
                safety_stock=2400.0,
                reorder_point=5600.0,
                primary_supplier_id=suppliers[1].id,
                unit_cost=4.5,
            ),
            InventoryItem(
                name="ABS Plastic Granules",
                sku="PLS-ABS-001",
                category="Plastics",
                current_quantity=350.0,
                unit="kg",
                daily_demand_rate=40.0,
                safety_stock=120.0,
                reorder_point=240.0,
                primary_supplier_id=suppliers[2].id,
                unit_cost=2.2,
            ),
            InventoryItem(
                name="Industrial Solvent IPA",
                sku="CHM-IPA-500",
                category="Chemicals",
                current_quantity=800.0,
                unit="liters",
                daily_demand_rate=30.0,
                safety_stock=90.0,
                reorder_point=150.0,
                primary_supplier_id=suppliers[3].id,
                unit_cost=3.8,
            ),
            InventoryItem(
                name="Precision Bearing PB-608",
                sku="MEC-PB-608",
                category="Mechanical",
                current_quantity=5000.0,
                unit="units",
                daily_demand_rate=120.0,
                safety_stock=360.0,
                reorder_point=720.0,
                primary_supplier_id=suppliers[4].id,
                unit_cost=1.2,
            ),
            InventoryItem(
                name="Corrugated Cardboard Box L",
                sku="PKG-BOX-L01",
                category="Packaging",
                current_quantity=10000.0,
                unit="units",
                daily_demand_rate=500.0,
                safety_stock=1500.0,
                reorder_point=3000.0,
                primary_supplier_id=suppliers[5].id,
                unit_cost=0.45,
            ),
            InventoryItem(
                name="Steel Fastener M8 Bolt",
                sku="STL-FAS-M8B",
                category="Fasteners",
                current_quantity=80000.0,
                unit="units",
                daily_demand_rate=2000.0,
                safety_stock=6000.0,
                reorder_point=12000.0,
                primary_supplier_id=suppliers[6].id,
                unit_cost=0.08,
            ),
            InventoryItem(
                name="Epoxy Resin Adhesive",
                sku="CHM-EPX-001",
                category="Chemicals",
                current_quantity=120.0,
                unit="kg",
                daily_demand_rate=8.0,
                safety_stock=24.0,
                reorder_point=40.0,
                primary_supplier_id=suppliers[7].id,
                unit_cost=22.0,
            ),
            InventoryItem(
                name="Aluminum Alloy Sheet 6061",
                sku="ALM-6061-002",
                category="Raw Metal",
                current_quantity=600.0,
                unit="tonnes",
                daily_demand_rate=25.0,
                safety_stock=75.0,
                reorder_point=150.0,
                primary_supplier_id=suppliers[0].id,
                unit_cost=2100.0,
            ),
            InventoryItem(
                name="LCD Display Module 7in",
                sku="ELC-LCD-7IN",
                category="Electronics",
                current_quantity=1500.0,
                unit="units",
                daily_demand_rate=60.0,
                safety_stock=180.0,
                reorder_point=360.0,
                primary_supplier_id=suppliers[1].id,
                unit_cost=28.0,
            ),
            InventoryItem(
                name="Polypropylene Film",
                sku="PLS-PPF-100",
                category="Plastics",
                current_quantity=2000.0,
                unit="kg",
                daily_demand_rate=90.0,
                safety_stock=270.0,
                reorder_point=500.0,
                primary_supplier_id=suppliers[2].id,
                unit_cost=1.9,
            ),
            InventoryItem(
                name="Stainless Steel Tube SS304",
                sku="STL-TUB-SS3",
                category="Raw Metal",
                current_quantity=400.0,
                unit="metres",
                daily_demand_rate=15.0,
                safety_stock=45.0,
                reorder_point=90.0,
                primary_supplier_id=suppliers[6].id,
                unit_cost=12.5,
            ),
        ]
        db.add_all(items)
        await db.flush()

        # ── Purchase Orders ────────────────────────────────────────
        now = datetime.now(timezone.utc)
        po_statuses = [
            POStatus.pending, POStatus.confirmed, POStatus.in_transit,
            POStatus.delayed, POStatus.delivered, POStatus.confirmed,
            POStatus.in_transit, POStatus.pending, POStatus.confirmed,
            POStatus.in_transit, POStatus.delayed, POStatus.delivered,
            POStatus.pending, POStatus.confirmed, POStatus.in_transit,
        ]
        purchase_orders = []
        for idx in range(15):
            sup = suppliers[idx % len(suppliers)]
            item = items[idx % len(items)]
            qty = 500.0 + idx * 100
            ucost = item.unit_cost
            status = po_statuses[idx]
            delay = (idx * 2) if status == POStatus.delayed else None
            po = PurchaseOrder(
                order_number=f"PO-2026-{1000 + idx}",
                supplier_id=sup.id,
                inventory_item_id=item.id,
                quantity=qty,
                unit_cost=ucost,
                total_cost=qty * ucost,
                status=status,
                order_date=now - timedelta(days=10 + idx),
                expected_delivery_date=now + timedelta(days=5 + idx),
                actual_delivery_date=now - timedelta(days=1) if status == POStatus.delivered else None,
                delay_days=delay,
                notes=f"Standard reorder for {item.name}" if not delay else f"Delayed by {delay} days due to supplier capacity issue",
            )
            purchase_orders.append(po)

        db.add_all(purchase_orders)
        await db.commit()

        print(f"Seeded: {len(suppliers)} suppliers, {len(items)} inventory items, {len(purchase_orders)} purchase orders.")
        print("Supplier IDs for simulator:")
        for s in suppliers:
            print(f"  {s.name}: {s.id}")


if __name__ == "__main__":
    asyncio.run(seed())
