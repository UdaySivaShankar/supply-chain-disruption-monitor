from workflows.state import AgentState
from utils.logger import logger
from datetime import datetime, timezone


async def inventory_analysis_node(state: AgentState) -> AgentState:
    logger.info(f"Running inventory_analysis_node for case {state['case_id']}")

    delay = state.get("delay_days", 0)
    cov = float(state.get("inventory_coverage_days", 5.0) or 5.0)
    demand = float(state.get("daily_demand_rate", 25.0) or 25.0)

    # Calculate stockout risk and expected supply gap
    if delay >= cov:
        # Stock runs out before the delayed delivery arrives
        gap_days = delay - cov
        stockout_risk = min(0.95, 0.70 + (gap_days / max(delay, 1)) * 0.25)
        supply_gap_units = gap_days * demand
    else:
        # Coverage exceeds delay, but buffer is compressed
        gap_days = 0.0
        remaining_buffer = cov - delay
        stockout_risk = 0.40 if remaining_buffer < 3.0 else 0.15
        supply_gap_units = 0.0

    state["inventory_coverage_days"] = round(cov, 1)
    state["stockout_risk"] = round(stockout_risk, 2)

    analysis = (
        f"Assessed on-hand inventory position. Current coverage is {cov:.1f} days at daily consumption rate of {demand:.1f} units. "
        f"With an announced delay of {delay} days, "
        + (f"a projected stockout deficit of {gap_days:.1f} days ({supply_gap_units:.0f} units) occurs prior to replenishment." if gap_days > 0
           else f"remaining inventory safety cushion is compressed to {remaining_buffer:.1f} days.")
    )

    conclusions = (
        f"Stockout risk evaluated at {int(stockout_risk * 100)}%. "
        + (f"High vulnerability: emergency supply gap of {supply_gap_units:.0f} units projected." if stockout_risk > 0.5
           else "Moderate vulnerability: buffer compressed but immediate stockout avoidable if no further delays.")
    )

    trace = {
        "agent": "Inventory and Demand Analysis",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "analysis": analysis,
        "conclusions": conclusions,
        "data_used": [
            f"Coverage: {cov:.1f} days",
            f"Daily Demand Rate: {demand:.1f} units/day",
            f"Disruption Delay: {delay} days",
            f"Projected Deficit Window: {gap_days:.1f} days",
        ]
    }
    state["agent_trace"].append(trace)
    return state
