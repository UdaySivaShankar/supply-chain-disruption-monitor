from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from database.connection import get_db, AsyncSessionLocal
from models.disruption_case import DisruptionCase, DisruptionType, Severity, DisruptionStatus
from models.supplier import Supplier
from models.inventory_item import InventoryItem
from models.approval_request import ApprovalRequest, ApprovalStatus
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from sqlalchemy.future import select
from uuid import UUID
from workflows.disruption_workflow import app as workflow_app
from workflows.state import AgentState
from hindsight.client import aretain
from utils.config import settings
from utils.security import require_api_key
from datetime import datetime, timezone
import json

router = APIRouter(prefix="/disruptions", tags=["Disruptions"])


class SimulateRequest(BaseModel):
    type: DisruptionType
    supplier_id: UUID
    description: str = Field(min_length=5, max_length=1000)
    delay_days: int = Field(ge=0, le=365)
    severity: Severity


class NoteRequest(BaseModel):
    notes: Optional[str] = Field(default="", max_length=2000)


class ResolveRequest(BaseModel):
    outcome: str = Field(min_length=5, max_length=2000)


async def run_workflow(case_id: UUID):
    """Executes the 7-node LangGraph workflow in the background."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(DisruptionCase).where(DisruptionCase.id == case_id))
        case = result.scalars().first()
        if not case:
            return

        # Fetch supplier info
        supp = None
        if case.affected_supplier_id:
            supp_res = await db.execute(select(Supplier).where(Supplier.id == case.affected_supplier_id))
            supp = supp_res.scalars().first()

        # Fetch inventory item linked to supplier
        item = None
        if supp:
            inv_res = await db.execute(
                select(InventoryItem).where(InventoryItem.primary_supplier_id == supp.id)
            )
            item = inv_res.scalars().first()

        # If no item specifically linked, query any primary item
        if not item:
            any_inv = await db.execute(select(InventoryItem).limit(1))
            item = any_inv.scalars().first()

        # Real calculations from database operational state
        if item and item.daily_demand_rate and item.daily_demand_rate > 0:
            demand = float(item.daily_demand_rate)
            cov_days = round(float(item.current_quantity) / demand, 1)
            item_info = {
                "id": str(item.id),
                "name": item.name,
                "sku": item.sku,
                "category": item.category,
                "unit_cost": float(item.unit_cost or 100.0),
                "current_quantity": float(item.current_quantity),
                "daily_demand_rate": demand,
            }
            # Link item to case
            case.affected_inventory_item_id = item.id
            await db.commit()
        else:
            demand = 25.0
            cov_days = 5.0
            item_info = {"name": "Industrial Component", "unit_cost": 120.0}

        initial_state: AgentState = {
            "case_id": str(case.id),
            "disruption_type": case.disruption_type.value,
            "severity": case.severity.value,
            "affected_supplier": {"id": str(supp.id), "name": supp.name} if supp else {},
            "affected_inventory": item_info,
            "affected_order": {},
            "delay_days": case.delay_days,
            "inventory_coverage_days": cov_days,
            "daily_demand_rate": demand,
            "stockout_risk": 0.0,
            "business_impact": {},
            "hindsight_memories": [],
            "alternative_suppliers": [],
            "mitigation_strategies": [],
            "recommendation": {},
            "alerts": [],
            "agent_trace": [],
            "status": case.status.value,
        }

    # Run LangGraph state graph asynchronously
    await workflow_app.ainvoke(initial_state)


@router.get("")
async def list_disruptions(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DisruptionCase).order_by(DisruptionCase.detected_at.desc()))
    return result.scalars().all()


@router.get("/{id}")
async def get_disruption(id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DisruptionCase).where(DisruptionCase.id == id))
    case = result.scalars().first()
    if not case:
        raise HTTPException(status_code=404, detail="Disruption not found")
    return case


@router.post("/simulate")
async def simulate_disruption(
    req: SimulateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    _auth: None = Depends(require_api_key),
):
    supplier_res = await db.execute(select(Supplier).where(Supplier.id == req.supplier_id))
    if not supplier_res.scalars().first():
        raise HTTPException(status_code=404, detail="Supplier not found")

    case = DisruptionCase(
        title=f"Simulated {req.type.value.replace('_', ' ').title()} Disruption",
        disruption_type=req.type,
        severity=req.severity,
        affected_supplier_id=req.supplier_id,
        description=req.description,
        delay_days=req.delay_days,
        status=DisruptionStatus.detecting,
    )
    db.add(case)
    await db.commit()
    await db.refresh(case)

    # Launch LangGraph orchestration in background
    background_tasks.add_task(run_workflow, case.id)
    return {"message": "Simulation started. Agentic workflow dispatched in background.", "case_id": str(case.id)}


@router.post("/{id}/approve")
async def approve_disruption(
    id: UUID,
    req: NoteRequest,
    db: AsyncSession = Depends(get_db),
    _auth: None = Depends(require_api_key),
):
    result = await db.execute(select(DisruptionCase).where(DisruptionCase.id == id))
    case = result.scalars().first()
    if not case:
        raise HTTPException(status_code=404, detail="Disruption not found")

    case.status = DisruptionStatus.approved

    # Add approval step to trace
    trace_entry = {
        "agent": "Human Operations Manager",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "analysis": f"Human review completed. Operator notes: '{req.notes or 'Approved per recommendation'}'.",
        "conclusions": "Recommendation authorized for execution.",
        "data_used": ["Action: Approve", f"Notes: {req.notes or 'None'}"]
    }
    existing_trace = list(case.agent_trace or [])
    existing_trace.append(trace_entry)
    case.agent_trace = existing_trace

    # Update or create ApprovalRequest
    app_res = await db.execute(
        select(ApprovalRequest).where(ApprovalRequest.disruption_case_id == case.id)
    )
    app_req = app_res.scalars().first()
    rec_text = ""
    if isinstance(case.recommendation, dict):
        rec_text = case.recommendation.get("recommended_action") or case.recommendation.get("action") or ""

    if app_req:
        app_req.status = ApprovalStatus.approved
        app_req.reviewer_notes = req.notes
        app_req.decided_at = datetime.now(timezone.utc)
    else:
        app_req = ApprovalRequest(
            disruption_case_id=case.id,
            recommendation_summary=rec_text or "Mitigation plan approved",
            recommended_action=rec_text or "Execute",
            confidence_score=0.9,
            risk_level="Low",
            status=ApprovalStatus.approved,
            reviewer_notes=req.notes,
            decided_at=datetime.now(timezone.utc),
        )
        db.add(app_req)

    await db.commit()
    return {"message": "Recommendation approved by operator.", "status": "approved"}


@router.post("/{id}/reject")
async def reject_disruption(
    id: UUID,
    req: NoteRequest,
    db: AsyncSession = Depends(get_db),
    _auth: None = Depends(require_api_key),
):
    result = await db.execute(select(DisruptionCase).where(DisruptionCase.id == id))
    case = result.scalars().first()
    if not case:
        raise HTTPException(status_code=404, detail="Disruption not found")

    case.status = DisruptionStatus.rejected

    # Add rejection step to trace
    trace_entry = {
        "agent": "Human Operations Manager",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "analysis": f"Human review completed. Operator rejected recommendation. Notes: '{req.notes or 'Rejected by operator'}'.",
        "conclusions": "Proposed mitigation canceled. Manual intervention required.",
        "data_used": ["Action: Reject", f"Notes: {req.notes or 'None'}"]
    }
    existing_trace = list(case.agent_trace or [])
    existing_trace.append(trace_entry)
    case.agent_trace = existing_trace

    app_res = await db.execute(
        select(ApprovalRequest).where(ApprovalRequest.disruption_case_id == case.id)
    )
    app_req = app_res.scalars().first()
    if app_req:
        app_req.status = ApprovalStatus.rejected
        app_req.reviewer_notes = req.notes
        app_req.decided_at = datetime.now(timezone.utc)
    else:
        app_req = ApprovalRequest(
            disruption_case_id=case.id,
            recommendation_summary="Mitigation plan rejected",
            recommended_action="Cancel",
            confidence_score=0.9,
            risk_level="High",
            status=ApprovalStatus.rejected,
            reviewer_notes=req.notes,
            decided_at=datetime.now(timezone.utc),
        )
        db.add(app_req)

    await db.commit()
    return {"message": "Recommendation rejected by operator.", "status": "rejected"}


@router.post("/{id}/resolve")
async def resolve_disruption(
    id: UUID,
    req: ResolveRequest,
    db: AsyncSession = Depends(get_db),
    _auth: None = Depends(require_api_key),
):
    result = await db.execute(select(DisruptionCase).where(DisruptionCase.id == id))
    case = result.scalars().first()
    if not case:
        raise HTTPException(status_code=404, detail="Disruption not found")

    case.status = DisruptionStatus.resolved
    case.outcome = req.outcome
    case.resolved_at = datetime.now(timezone.utc)

    # Retain experiential memory in Hindsight
    supp_res = await db.execute(select(Supplier).where(Supplier.id == case.affected_supplier_id))
    supp = supp_res.scalars().first()
    supp_name = supp.name if supp else "Primary Supplier"

    rec_summary = ""
    if isinstance(case.recommendation, dict):
        rec_summary = case.recommendation.get("recommended_action") or case.recommendation.get("action") or ""

    experience_text = (
        f"Disruption event involving supplier {supp_name} (Type: {case.disruption_type.value}, "
        f"Delay: {case.delay_days} days). "
        f"Mitigation recommended: {rec_summary}. "
        f"Operator decision: Approved. "
        f"Actual outcome: {req.outcome}."
    )

    await aretain(bank_id=settings.hindsight_bank_id, content=experience_text)

    # Append resolution trace
    trace_entry = {
        "agent": "Hindsight Memory System",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "analysis": f"Disruption successfully resolved. Retained complete operational experience in Hindsight bank '{settings.hindsight_bank_id}'.",
        "conclusions": "Historical experience recorded. Available for recall in future disruptions.",
        "data_used": [f"Retained Memory: {experience_text[:120]}..."]
    }
    existing_trace = list(case.agent_trace or [])
    existing_trace.append(trace_entry)
    case.agent_trace = existing_trace

    await db.commit()
    return {"message": "Disruption resolved and experience retained in Hindsight.", "outcome": req.outcome}


@router.get("/{id}/memory")
async def get_disruption_memory(id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DisruptionCase).where(DisruptionCase.id == id))
    case = result.scalars().first()
    if not case:
        raise HTTPException(status_code=404, detail="Disruption not found")
    return {"hindsight_memories": case.hindsight_memories or []}
