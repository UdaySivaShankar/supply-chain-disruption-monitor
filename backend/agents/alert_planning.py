from workflows.state import AgentState
from utils.logger import logger
from datetime import datetime, timezone


async def alert_planning_node(state: AgentState) -> AgentState:
    logger.info(f"Running alert_planning_node for case {state['case_id']}")

    supp_name = state.get("affected_supplier", {}).get("name", "Unknown Supplier")
    dtype = state.get("disruption_type", "supplier_delay")
    sev = state.get("severity", "medium")
    rec = state.get("recommendation", {})
    action = rec.get("recommended_action", "Review proposed mitigation")

    alert = {
        "alert_type": "disruption_response_alert",
        "severity": sev,
        "title": f"Disruption Response Required: {supp_name} ({dtype.replace('_', ' ').title()})",
        "message": (
            f"Action plan prepared for {supp_name}. Proposed response: {action}. "
            f"Awaiting mandatory human operator authorization."
        )
    }

    state["alerts"] = [alert]

    trace = {
        "agent": "Alert and Response Planning",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "analysis": f"Constructed prioritized alert payload for operational stakeholders and dashboard.",
        "conclusions": f"Generated alert for case '{state['case_id']}'. Notification queued for operations dashboard.",
        "data_used": [
            f"Alert Severity: {sev}",
            f"Target Channel: Operations Dashboard & Monitoring Stream",
            f"Response Plan: {action[:80]}..."
        ]
    }
    state["agent_trace"].append(trace)
    return state
