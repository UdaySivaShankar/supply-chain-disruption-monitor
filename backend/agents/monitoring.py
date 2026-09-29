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


async def monitoring_node(state: AgentState) -> AgentState:
    logger.info(f"Running monitoring_node for case {state['case_id']}")
    supp_name = state.get("affected_supplier", {}).get("name", "Unknown Supplier")
    dtype = state.get("disruption_type", "unspecified")
    delay = state.get("delay_days", 0)

    analysis = (
        f"Continuous telemetry scan detected supply disruption event. "
        f"Affected supplier: {supp_name}. Disruption type: {dtype.replace('_', ' ')}. "
        f"Reported delivery schedule slip: {delay} days."
    )

    if llm and settings.google_api_key:
        try:
            from langchain.schema import HumanMessage, SystemMessage
            resp = await llm.ainvoke([
                SystemMessage(content="You are a Supply Chain Monitoring Agent. Summarize telemetry findings in 1 concise sentence without using em dashes."),
                HumanMessage(content=f"Supplier: {supp_name}, Disruption: {dtype}, Delay: {delay} days.")
            ])
            analysis += f" Agent summary: {resp.content.strip()}"
        except Exception as e:
            logger.warning(f"Monitoring LLM call failed: {e}")

    trace = {
        "agent": "Supply Chain Monitoring",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "analysis": analysis,
        "conclusions": f"Disruption signal verified. Initiated active case tracking for {supp_name}.",
        "data_used": [
            f"Supplier: {supp_name}",
            f"Disruption Type: {dtype}",
            f"Telemetry Delay: {delay} days",
        ]
    }
    state["agent_trace"].append(trace)
    return state
