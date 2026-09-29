from workflows.state import AgentState
from utils.logger import logger
from datetime import datetime, timezone


async def impact_assessment_node(state: AgentState) -> AgentState:
    logger.info(f"Running impact_assessment_node for case {state['case_id']}")

    risk = state.get("stockout_risk", 0.5)
    demand = float(state.get("daily_demand_rate", 25.0) or 25.0)
    delay = state.get("delay_days", 7)
    cov = float(state.get("inventory_coverage_days", 5.0) or 5.0)

    # Unit cost approximation from item if available, or benchmark
    item_cost = state.get("affected_inventory", {}).get("unit_cost", 150.0)
    if not item_cost or item_cost <= 0:
        item_cost = 150.0

    # Operational downtime / stockout impact estimation
    days_short = max(0.0, delay - cov)
    unfulfilled_units = days_short * demand
    direct_materials_at_risk = unfulfilled_units * item_cost

    # Indirect business disruption factor (downtime cost, customer delivery penalty)
    downtime_penalty_per_day = 12000.0
    indirect_penalty = days_short * downtime_penalty_per_day

    total_impact = direct_materials_at_risk + indirect_penalty
    if total_impact == 0:
        # Buffer risk cost
        total_impact = demand * item_cost * delay * 0.15

    state["business_impact"] = {
        "estimated_financial_loss": round(total_impact, 2),
        "direct_materials_at_risk": round(direct_materials_at_risk, 2),
        "indirect_penalty": round(indirect_penalty, 2),
        "days_short": round(days_short, 1),
    }

    analysis = (
        f"Evaluated financial and operational risk exposure across production schedule. "
        f"Material value exposed: ${direct_materials_at_risk:,.2f}. "
        f"Downstream assembly downtime penalties: ${indirect_penalty:,.2f}. "
        f"Combined estimated financial exposure: ${total_impact:,.2f}."
    )

    conclusions = (
        f"Total business risk exposure: ${total_impact:,.2f}. "
        f"Severity requires proactive supplier mitigation and contingency activation."
    )

    trace = {
        "agent": "Impact Assessment",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "analysis": analysis,
        "conclusions": conclusions,
        "data_used": [
            f"Stockout Risk: {int(risk * 100)}%",
            f"Estimated Shortage Window: {days_short:.1f} days",
            f"Direct Material Value: ${direct_materials_at_risk:,.2f}",
            f"Total Business Impact: ${total_impact:,.2f}",
        ]
    }
    state["agent_trace"].append(trace)
    return state
