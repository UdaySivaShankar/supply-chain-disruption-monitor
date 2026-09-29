from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from database.connection import engine, get_db
from models import Base
from models.disruption_case import DisruptionCase, DisruptionStatus
from models.inventory_item import InventoryItem
from models.alert import Alert
from utils.config import settings
from utils.security import require_api_key
from api.routes import suppliers, inventory, purchase_orders, disruptions, agents
from hindsight.client import arecall


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all tables on startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(
    title="Supply Chain Disruption Monitoring API",
    version="1.0.0",
    description="Agentic AI system for detecting, analyzing, and mitigating supply chain disruptions.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(suppliers.router)
app.include_router(inventory.router)
app.include_router(purchase_orders.router)
app.include_router(disruptions.router)
app.include_router(agents.router)


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "supply-chain-monitoring-api"}


@app.get("/dashboard/stats")
async def dashboard_stats(db: AsyncSession = Depends(get_db)):
    # Active disruptions (not resolved)
    active_res = await db.execute(
        select(DisruptionCase).where(DisruptionCase.status != DisruptionStatus.resolved)
    )
    active_cases = list(active_res.scalars().all())
    active_count = len(active_cases)

    # Pending approvals
    pending_res = await db.execute(
        select(DisruptionCase).where(DisruptionCase.status == DisruptionStatus.pending_approval)
    )
    pending_count = len(list(pending_res.scalars().all()))

    # Affected suppliers (unique suppliers in active disruptions)
    affected_supplier_ids = set(
        c.affected_supplier_id for c in active_cases if c.affected_supplier_id
    )
    affected_suppliers_count = len(affected_supplier_ids)

    # Inventory items at risk: coverage_days < 7 (calculated inline)
    inv_res = await db.execute(select(InventoryItem))
    all_items = list(inv_res.scalars().all())
    at_risk_count = sum(
        1 for item in all_items
        if item.daily_demand_rate and item.daily_demand_rate > 0
        and (item.current_quantity / item.daily_demand_rate) < 7
    )

    # Recent alerts (last 10)
    alerts_res = await db.execute(
        select(Alert).order_by(Alert.created_at.desc()).limit(10)
    )
    recent_alerts_raw = list(alerts_res.scalars().all())
    recent_alerts = [
        {
            "id": str(a.id),
            "disruption_case_id": str(a.disruption_case_id),
            "alert_type": a.alert_type,
            "severity": a.severity.value if a.severity else None,
            "title": a.title,
            "message": a.message,
            "is_read": a.is_read,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in recent_alerts_raw
    ]

    # Active disruption list (serialized)
    active_list = [
        {
            "id": str(c.id),
            "title": c.title,
            "disruption_type": c.disruption_type.value if c.disruption_type else None,
            "severity": c.severity.value if c.severity else None,
            "status": c.status.value if c.status else None,
            "detected_at": c.detected_at.isoformat() if c.detected_at else None,
            "inventory_coverage_days": c.inventory_coverage_days,
            "stockout_risk": c.stockout_risk,
        }
        for c in active_cases[:10]
    ]

    return {
        "active_disruptions": active_count,
        "pending_approvals": pending_count,
        "affected_suppliers": affected_suppliers_count,
        "inventory_at_risk": at_risk_count,
        "recent_alerts": recent_alerts,
        "active_disruption_list": active_list,
    }


@app.get("/memory")
async def list_memories(db: AsyncSession = Depends(get_db)):
    """Returns all experiential memories from Hindsight and resolved disruptions."""
    # Query Hindsight memory bank
    raw_hindsight = await arecall(
        bank_id=settings.hindsight_bank_id,
        query="disruption mitigation outcome supplier delay logistics",
        limit=15,
    )

    # Also query resolved cases with stored outcomes
    resolved_res = await db.execute(
        select(DisruptionCase)
        .where(DisruptionCase.status == DisruptionStatus.resolved)
        .order_by(DisruptionCase.resolved_at.desc())
    )
    resolved_cases = list(resolved_res.scalars().all())

    memories = []
    seen = set()

    for rc in resolved_cases:
        content = (
            f"Resolved Case: {rc.title} (Delay: {rc.delay_days} days). "
            f"Mitigation Outcome: {rc.outcome or 'Mitigation protocol successfully completed.'}"
        )
        if content not in seen:
            seen.add(content)
            memories.append({
                "id": str(rc.id),
                "content": content,
                "relevance_score": 1.0,
                "retrieved_at": rc.resolved_at.isoformat() if rc.resolved_at else None,
            })

    for m in raw_hindsight:
        content = m.get("content") if isinstance(m, dict) else str(m)
        if content and content not in seen:
            seen.add(content)
            memories.append({
                "id": str(m.get("id")) if isinstance(m, dict) and "id" in m else None,
                "content": content,
                "relevance_score": float(m.get("relevance_score", 0.92)) if isinstance(m, dict) else 0.92,
                "retrieved_at": m.get("created_at") if isinstance(m, dict) else None,
            })

    return memories


@app.get("/alerts")
async def list_alerts(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Alert).order_by(Alert.created_at.desc()))
    alerts = list(result.scalars().all())
    return [
        {
            "id": str(a.id),
            "disruption_case_id": str(a.disruption_case_id),
            "alert_type": a.alert_type,
            "severity": a.severity.value if a.severity else None,
            "title": a.title,
            "message": a.message,
            "is_read": a.is_read,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in alerts
    ]


@app.post("/alerts/{alert_id}/read")
async def mark_alert_read(
    alert_id: str,
    db: AsyncSession = Depends(get_db),
    _auth: None = Depends(require_api_key),
):
    from uuid import UUID
    result = await db.execute(select(Alert).where(Alert.id == UUID(alert_id)))
    alert = result.scalars().first()
    if not alert:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.is_read = True
    await db.commit()
    return {"message": "Alert marked as read"}
