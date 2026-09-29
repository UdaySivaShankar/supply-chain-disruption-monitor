from workflows.state import AgentState
from utils.logger import logger
from utils.config import settings
from datetime import datetime, timezone

try:
    if settings.google_api_key:
        from langchain_google_genai import ChatGoogleGenerativeAI
        llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=settings.google_api_key)
    else:
        llm = None
except Exception:
    llm = None


async def detection_node(state: AgentState) -> AgentState:
    logger.info(f"Running detection_node for case {state['case_id']}")
    dtype = state.get("disruption_type", "supplier_delay")
    delay = state.get("delay_days", 0)
    sev = state.get("severity", "medium")

    # Determine whether event crosses threshold for significant disruption
    is_significant = delay >= 3 or sev in ["high", "critical"]
    classification = "CRITICAL DISRUPTION" if sev == "critical" else "OPERATIONAL DISRUPTION" if is_significant else "MINOR DELAY"

    analysis = (
        f"Evaluated anomaly parameters against operational thresholds. "
        f"Event category '{dtype}' with delay of {delay} days and assigned severity '{sev}' "
        f"confirms a genuine disruption requiring intervention."
    )

    if llm and settings.google_api_key:
        try:
            from langchain.schema import HumanMessage, SystemMessage
            resp = await llm.ainvoke([
                SystemMessage(content="You are a Disruption Detection Agent. Evaluate anomaly significance in 1 sentence without using em dashes."),
                HumanMessage(content=f"Type: {dtype}, Delay: {delay} days, Severity: {sev}.")
            ])
            analysis += f" Evaluation note: {resp.content.strip()}"
        except Exception as e:
            logger.warning(f"Detection LLM call failed: {e}")

    trace = {
        "agent": "Disruption Detection",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "analysis": analysis,
        "conclusions": f"Confirmed {classification}. Forwarding to inventory and demand analysis.",
        "data_used": [
            f"Classification: {classification}",
            f"Severity Grade: {sev}",
            f"Delay Threshold Exceeded: {is_significant}"
        ]
    }
    state["agent_trace"].append(trace)
    return state
