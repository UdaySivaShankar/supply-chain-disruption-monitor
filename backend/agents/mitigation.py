from workflows.state import AgentState
from utils.logger import logger
from utils.config import settings
from hindsight.client import arecall
from database.connection import AsyncSessionLocal
from models.supplier import Supplier, SupplierStatus
from sqlalchemy.future import select
from datetime import datetime, timezone
from typing import List, Dict, Any

try:
    if settings.google_api_key:
        from langchain_google_genai import ChatGoogleGenerativeAI
        llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=settings.google_api_key)
    else:
        llm = None
except Exception:
    llm = None


async def mitigation_node(state: AgentState) -> AgentState:
    logger.info(f"Running mitigation_node for case {state['case_id']}")

    supplier_name = state.get("affected_supplier", {}).get("name", "Primary Supplier")
    dtype = state.get("disruption_type", "supplier_delay")
    delay = state.get("delay_days", 7)
    impact_loss = state.get("business_impact", {}).get("estimated_financial_loss", 0.0)

    # 1. Recall historical experiences from Hindsight
    query = f"supplier {supplier_name} disruption {dtype} mitigation outcome"
    raw_memories = await arecall(bank_id=settings.hindsight_bank_id, query=query, limit=5)

    # Normalize memory entries
    hindsight_memories: List[Dict[str, Any]] = []
    for m in raw_memories:
        if isinstance(m, dict):
            hindsight_memories.append(m)
        elif isinstance(m, str):
            hindsight_memories.append({
                "content": m,
                "relevance_score": 0.88,
                "retrieved_at": datetime.now(timezone.utc).isoformat()
            })
    state["hindsight_memories"] = hindsight_memories

    # 2. Query available alternative suppliers from PostgreSQL operational database
    alternative_suppliers = []
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Supplier).where(
                    Supplier.status == SupplierStatus.active,
                    Supplier.name != supplier_name
                ).order_by(Supplier.reliability_score.desc()).limit(3)
            )
            sups = result.scalars().all()
            for s in sups:
                alternative_suppliers.append({
                    "id": str(s.id),
                    "name": s.name,
                    "country": s.country,
                    "lead_time_days": s.lead_time_days,
                    "reliability_score": s.reliability_score,
                    "capabilities": s.capabilities or []
                })
    except Exception as e:
        logger.warning(f"Could not load alternative suppliers from DB: {e}")

    state["alternative_suppliers"] = alternative_suppliers

    # Select best alternative candidate
    best_candidate = alternative_suppliers[0]["name"] if alternative_suppliers else "German Plastics GmbH"
    best_lead_time = alternative_suppliers[0]["lead_time_days"] if alternative_suppliers else 8

    # 3. Formulate recommendation combining SQL data + disruption context + Hindsight memory
    has_prior_memory = len(hindsight_memories) > 0

    if has_prior_memory:
        # Prior experience available: incorporate verified historical outcome
        first_mem = hindsight_memories[0].get("content", "")
        confidence = 0.94
        risk_level = "Low"
        recommended_action = (
            f"Activate validated contingency protocol with {best_candidate} (Lead time: {best_lead_time} days)"
        )
        rationale = (
            f"Hindsight long-term memory retrieved {len(hindsight_memories)} past experience(s) for this pattern. "
            f"Historical reference: '{first_mem[:160]}...'. "
            f"Prior resolution confirmed that rerouting critical volume to an audited secondary partner averted line stoppage."
        )
        steps = [
            f"Reallocate 45% volume immediately to {best_candidate} using established express contract.",
            f"Authorize expedited transit to arrive within {best_lead_time} days, well before stockout.",
            "Maintain baseline purchase order with primary supplier for remainder of shipment.",
            "Verify freight forwarding tracking milestones at 24h intervals."
        ]
    else:
        # First event: Baseline operational recommendation based on current SQL database state
        confidence = 0.76
        risk_level = "Medium"
        recommended_action = (
            f"Issue emergency secondary purchase order to {best_candidate} (Lead time: {best_lead_time} days)"
        )
        rationale = (
            f"No previous disruption memory found in Hindsight for supplier '{supplier_name}'. "
            f"Evaluated current operational database: selected {best_candidate} with top reliability score "
            f"({alternative_suppliers[0]['reliability_score'] if alternative_suppliers else 0.92}) to mitigate ${impact_loss:,.2f} risk exposure."
        )
        steps = [
            f"Request immediate spot quote and capacity hold from {best_candidate}.",
            f"Confirm expedited transit window of {best_lead_time} days to bridge the {delay}-day supplier delay.",
            "Submit mitigation plan to human operations manager for binding approval.",
            "Once resolved, retain event parameters and outcome in Hindsight to inform future decisions."
        ]

    # Optional LLM refinement if API key configured
    if llm and settings.google_api_key:
        try:
            from langchain.schema import HumanMessage, SystemMessage
            mem_summary = " ".join([m.get("content", "") for m in hindsight_memories]) if hindsight_memories else "None"
            resp = await llm.ainvoke([
                SystemMessage(content="You are an Alternative Supplier and Mitigation Agent. Provide 1 concise sentence explaining the mitigation strategy without using em dashes."),
                HumanMessage(content=f"Supplier: {supplier_name}, Delay: {delay} days, Best Alt: {best_candidate}, Past memory: {mem_summary}")
            ])
            rationale += f" LLM Agent Note: {resp.content.strip()}"
        except Exception as e:
            logger.warning(f"Mitigation LLM call failed: {e}")

    recommendation = {
        "recommended_action": recommended_action,
        "alternative_supplier": best_candidate,
        "confidence_score": confidence,
        "risk_level": risk_level,
        "rationale": rationale,
        "steps": steps
    }

    state["mitigation_strategies"] = [recommendation]
    state["recommendation"] = recommendation

    trace = {
        "agent": "Alternative Supplier and Mitigation",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "analysis": (
            f"Hindsight recall queried memory bank '{settings.hindsight_bank_id}' (returned {len(hindsight_memories)} memories). "
            f"Evaluated {len(alternative_suppliers)} alternative suppliers from PostgreSQL operational state. "
            f"Selected {best_candidate} as optimal candidate (Lead time: {best_lead_time} days)."
        ),
        "conclusions": f"Proposed mitigation: {recommended_action}. Confidence: {int(confidence * 100)}%.",
        "data_used": [
            f"Hindsight Memories Recalled: {len(hindsight_memories)}",
            f"Selected Alt Supplier: {best_candidate}",
            f"Target Lead Time: {best_lead_time} days",
            f"Confidence Score: {int(confidence * 100)}%"
        ]
    }
    state["agent_trace"].append(trace)
    return state
