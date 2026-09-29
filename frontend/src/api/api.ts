import axios from 'axios';
import * as Types from './types';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
const API_KEY = import.meta.env.VITE_API_KEY || '';

const client = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
    ...(API_KEY ? { 'X-API-Key': API_KEY } : {}),
  },
});

export const api = {
  // Dashboard
  getDashboardStats: () =>
    client.get<Types.DashboardStats>('/dashboard/stats').then((r) => r.data),

  // Disruptions
  getDisruptions: () =>
    client.get<Types.DisruptionCase[]>('/disruptions').then((r) => r.data),
  getDisruption: (id: string) =>
    client.get<Types.DisruptionCase>(`/disruptions/${id}`).then((r) => r.data),
  simulateDisruption: (data: Record<string, unknown>) =>
    client
      .post<{ case_id: string; message: string }>('/disruptions/simulate', data)
      .then((r) => r.data),
  approveDisruption: (id: string, data: { notes: string }) =>
    client.post(`/disruptions/${id}/approve`, data).then((r) => r.data),
  rejectDisruption: (id: string, data: { notes: string }) =>
    client.post(`/disruptions/${id}/reject`, data).then((r) => r.data),
  resolveDisruption: (id: string, data: { outcome: string }) =>
    client.post(`/disruptions/${id}/resolve`, data).then((r) => r.data),
  getDisruptionMemory: (id: string) =>
    client
      .get<{ hindsight_memories: Types.HindsightMemory[] }>(`/disruptions/${id}/memory`)
      .then((r) => r.data),

  // All Hindsight Memories
  getMemories: () =>
    client.get<Types.HindsightMemory[]>('/memory').then((r) => r.data),

  // Agents
  getAgentTrace: (caseId: string) =>
    client
      .get<{ trace: Types.AgentTraceEntry[] | null }>(`/agents/${caseId}/trace`)
      .then((r) => r.data),

  // Suppliers
  getSuppliers: () =>
    client.get<Types.Supplier[]>('/suppliers').then((r) => r.data),
  getSupplier: (id: string) =>
    client.get<Types.Supplier>(`/suppliers/${id}`).then((r) => r.data),

  // Inventory
  getInventory: () =>
    client.get<Types.InventoryItem[]>('/inventory').then((r) => r.data),

  // Purchase Orders
  getPurchaseOrders: () =>
    client.get<Types.PurchaseOrder[]>('/purchase-orders').then((r) => r.data),

  // Alerts
  getAlerts: () =>
    client.get<Types.Alert[]>('/alerts').then((r) => r.data),
  markAlertRead: (alertId: string) =>
    client.post(`/alerts/${alertId}/read`).then((r) => r.data),
};
