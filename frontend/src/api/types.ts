export interface Supplier {
  id: string;
  name: string;
  country: string;
  city: string;
  contact_email: string;
  lead_time_days: number;
  reliability_score: number;
  capabilities: string[];
  status: 'active' | 'inactive' | 'suspended';
}

export interface InventoryItem {
  id: string;
  name: string;
  sku: string;
  category: string;
  current_quantity: number;
  unit: string;
  daily_demand_rate: number;
  safety_stock: number;
  reorder_point: number;
  primary_supplier_id: string;
  unit_cost: number;
}

export interface PurchaseOrder {
  id: string;
  order_number: string;
  supplier_id: string;
  supplier_name?: string;
  inventory_item_id: string;
  item_name?: string;
  quantity: number;
  unit_cost: number;
  total_cost: number;
  status: 'pending' | 'confirmed' | 'in_transit' | 'delayed' | 'delivered' | 'cancelled';
  order_date: string;
  expected_delivery_date: string;
  actual_delivery_date?: string;
  delay_days?: number;
  notes?: string;
}

export interface DisruptionCase {
  id: string;
  title: string;
  disruption_type: 'supplier_delay' | 'logistics' | 'inventory_shortage' | 'weather' | 'other';
  severity: 'low' | 'medium' | 'high' | 'critical';
  status: 'detecting' | 'analyzing' | 'recommending' | 'pending_approval' | 'approved' | 'rejected' | 'resolved';
  affected_supplier_id?: string;
  description: string;
  detected_at: string;
  resolved_at?: string;
  delay_days: number;
  inventory_coverage_days: number;
  stockout_risk: number;
  estimated_impact_value: number;
  agent_trace?: AgentTraceEntry[];
  recommendation?: Recommendation;
  hindsight_memories?: HindsightMemory[];
  outcome?: string;
}

export interface AgentTraceEntry {
  agent: string;
  timestamp: string;
  analysis: string;
  conclusions: string;
  data_used?: string[];
}

export interface Recommendation {
  recommended_action: string;
  alternative_supplier?: string;
  confidence_score: number;
  risk_level: string;
  rationale: string;
  steps: string[];
}

export interface HindsightMemory {
  id?: string;
  content: string;
  relevance_score?: number;
  retrieved_at?: string;
}

export interface Alert {
  id: string;
  disruption_case_id: string;
  alert_type: string;
  severity: string;
  title: string;
  message: string;
  is_read: boolean;
  created_at: string;
}

export interface ApprovalRequest {
  id: string;
  disruption_case_id: string;
  recommendation_summary: string;
  recommended_action: string;
  confidence_score: number;
  risk_level: string;
  status: 'pending' | 'approved' | 'rejected';
  reviewer_notes?: string;
  created_at: string;
  decided_at?: string;
}

export interface DashboardStats {
  active_disruptions: number;
  pending_approvals: number;
  affected_suppliers: number;
  inventory_at_risk: number;
  recent_alerts: Alert[];
  active_disruption_list: DisruptionCase[];
}
