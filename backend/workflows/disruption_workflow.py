from langgraph.graph import StateGraph, END
from .state import AgentState
from agents.monitoring import monitoring_node
from agents.detection import detection_node
from agents.inventory_analysis import inventory_analysis_node
from agents.impact_assessment import impact_assessment_node
from agents.mitigation import mitigation_node
from agents.alert_planning import alert_planning_node
from agents.reviewer import reviewer_node
from services.disruption_service import update_disruption_status
from datetime import datetime, timezone


async def human_approval_node(state: AgentState) -> AgentState:
    state["status"] = "pending_approval"
    trace = {
        "agent": "Human Approval Gatekeeper",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "analysis": "7-agent reasoning sequence concluded. Prepared complete mitigation proposal with risk score.",
        "conclusions": "Automated action paused. Operational policy strictly requires human approval before executing supplier rerouting or emergency purchase orders.",
        "data_used": ["System Safety Invariant: Human-in-the-loop mandatory for consequential actions"]
    }
    state["agent_trace"].append(trace)

    # Save complete analysis and metrics to database
    impact_data = state.get("business_impact") or {}
    financial_loss = impact_data.get("estimated_financial_loss", 0.0)

    await update_disruption_status(
        case_id=state["case_id"],
        status="pending_approval",
        agent_trace=state["agent_trace"],
        recommendation=state.get("recommendation"),
        hindsight_memories=state.get("hindsight_memories"),
        inventory_coverage_days=state.get("inventory_coverage_days"),
        stockout_risk=state.get("stockout_risk"),
        estimated_impact_value=financial_loss,
        alerts=state.get("alerts"),
    )

    return state


workflow = StateGraph(AgentState)

workflow.add_node("monitoring", monitoring_node)
workflow.add_node("detection", detection_node)
workflow.add_node("inventory_analysis", inventory_analysis_node)
workflow.add_node("impact_assessment", impact_assessment_node)
workflow.add_node("mitigation", mitigation_node)
workflow.add_node("alert_planning", alert_planning_node)
workflow.add_node("reviewer", reviewer_node)
workflow.add_node("human_approval", human_approval_node)

workflow.set_entry_point("monitoring")
workflow.add_edge("monitoring", "detection")
workflow.add_edge("detection", "inventory_analysis")
workflow.add_edge("inventory_analysis", "impact_assessment")
workflow.add_edge("impact_assessment", "mitigation")
workflow.add_edge("mitigation", "alert_planning")
workflow.add_edge("alert_planning", "reviewer")
workflow.add_edge("reviewer", "human_approval")
workflow.add_edge("human_approval", END)

app = workflow.compile()
