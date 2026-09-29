from typing import TypedDict, List, Dict, Any

class AgentState(TypedDict):
    case_id: str
    disruption_type: str
    severity: str
    affected_supplier: dict
    affected_inventory: dict
    affected_order: dict
    delay_days: int
    inventory_coverage_days: float
    daily_demand_rate: float
    stockout_risk: float
    business_impact: dict
    hindsight_memories: list
    alternative_suppliers: list
    mitigation_strategies: list
    recommendation: dict
    alerts: list
    agent_trace: list
    status: str
