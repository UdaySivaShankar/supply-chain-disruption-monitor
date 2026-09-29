import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Play, AlertTriangle, CloudRain, Package, Truck } from 'lucide-react';
import { api } from '../api/api';
import { Supplier } from '../api/types';
import LoadingSpinner from '../components/common/LoadingSpinner';

interface SimScenario {
  id: string;
  title: string;
  description: string;
  icon: React.ElementType;
  borderColor: string;
  iconBg: string;
  iconColor: string;
  buildPayload: (suppliers: Supplier[]) => Record<string, unknown>;
}

const SCENARIOS: SimScenario[] = [
  {
    id: 'supplier_delay',
    title: 'Supplier Delay',
    description:
      'Primary steel supplier reports a 10-day delivery delay on critical components due to factory maintenance shutdown.',
    icon: Truck,
    borderColor: 'border-orange-200',
    iconBg: 'bg-orange-50',
    iconColor: 'text-orange-600',
    buildPayload: (sups) => ({
      type: 'supplier_delay',
      supplier_id: sups[0]?.id ?? '',
      description: 'Supplier reports 10-day delivery delay due to scheduled factory maintenance.',
      delay_days: 10,
      severity: 'high',
    }),
  },
  {
    id: 'logistics',
    title: 'Logistics Disruption',
    description:
      'Port congestion causes unexpected 7-day shipment delays across multiple ocean freight routes, affecting inbound deliveries.',
    icon: AlertTriangle,
    borderColor: 'border-blue-200',
    iconBg: 'bg-blue-50',
    iconColor: 'text-blue-600',
    buildPayload: (sups) => ({
      type: 'logistics',
      supplier_id: sups[1]?.id ?? sups[0]?.id ?? '',
      description: 'Port congestion causing 7-day shipment delays on ocean freight routes.',
      delay_days: 7,
      severity: 'medium',
    }),
  },
  {
    id: 'inventory_shortage',
    title: 'Inventory Shortage',
    description:
      'Critical material stock falls below safety threshold unexpectedly after a bad-quality batch was quarantined.',
    icon: Package,
    borderColor: 'border-red-200',
    iconBg: 'bg-red-50',
    iconColor: 'text-red-600',
    buildPayload: (sups) => ({
      type: 'inventory_shortage',
      supplier_id: sups[2]?.id ?? sups[0]?.id ?? '',
      description: 'Critical material stock below safety threshold after quality batch rejection.',
      delay_days: 5,
      severity: 'critical',
    }),
  },
  {
    id: 'weather',
    title: 'Weather Disruption',
    description:
      'Severe typhoon affecting a key supplier region, halting operations and ground transportation for an estimated 14 days.',
    icon: CloudRain,
    borderColor: 'border-slate-200',
    iconBg: 'bg-slate-50',
    iconColor: 'text-slate-600',
    buildPayload: (sups) => ({
      type: 'weather',
      supplier_id: sups[4]?.id ?? sups[0]?.id ?? '',
      description: 'Severe typhoon halting supplier operations and transportation for 14 days.',
      delay_days: 14,
      severity: 'critical',
    }),
  },
];

interface CustomForm {
  type: string;
  supplier_id: string;
  description: string;
  delay_days: number;
  severity: string;
}

export default function Simulator() {
  const navigate = useNavigate();
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [loadingSuppliers, setLoadingSuppliers] = useState(true);
  const [triggering, setTriggering] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<{ case_id: string; message: string } | null>(null);
  const [customForm, setCustomForm] = useState<CustomForm>({
    type: 'supplier_delay',
    supplier_id: '',
    description: '',
    delay_days: 5,
    severity: 'medium',
  });

  useEffect(() => {
    api.getSuppliers().then((data) => {
      setSuppliers(data);
      setCustomForm((f) => ({ ...f, supplier_id: data[0]?.id ?? '' }));
    }).catch(() => {
      setError('Could not load suppliers from backend.');
    }).finally(() => setLoadingSuppliers(false));
  }, []);

  const handleTrigger = async (scenarioId: string, payload: Record<string, unknown>) => {
    if (!payload.supplier_id) {
      setError('No suppliers loaded. Please ensure the backend is running and data is seeded.');
      return;
    }
    setTriggering(scenarioId);
    setError(null);
    setSuccess(null);
    try {
      const res = await api.simulateDisruption(payload);
      setSuccess({ case_id: res.case_id, message: res.message });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Simulation failed';
      setError(msg);
    } finally {
      setTriggering(null);
    }
  };

  const handleCustomSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await handleTrigger('custom', customForm as unknown as Record<string, unknown>);
  };

  if (loadingSuppliers) return <LoadingSpinner />;

  return (
    <div className="space-y-8 max-w-5xl mx-auto">
      {/* Header */}
      <div>
        <div className="flex items-center gap-3 mb-1">
          <h2 className="text-2xl font-bold text-slate-900 tracking-tight">Disruption Simulator</h2>
          <span className="bg-slate-700 text-white text-xs font-semibold px-2 py-1 rounded tracking-wider">
            SIMULATED DATA
          </span>
        </div>
        <p className="text-slate-500 text-sm">
          Trigger controlled disruption scenarios to demonstrate the full agentic workflow.
          All events are clearly marked as simulated and do not reflect real operations.
        </p>
      </div>

      {/* Error / Success Banners */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 p-4 rounded-md text-sm">
          {error}
        </div>
      )}
      {success && (
        <div className="bg-emerald-50 border border-emerald-200 p-4 rounded-md flex justify-between items-center">
          <div>
            <p className="text-emerald-800 font-medium">{success.message}</p>
            <p className="text-sm text-emerald-600 mt-1">
              Case ID: <span className="font-mono">{success.case_id}</span>
            </p>
            <p className="text-xs text-emerald-500 mt-1">
              The 7-agent workflow is now running in the background. Refresh the disruption page in a few seconds.
            </p>
          </div>
          <button
            onClick={() => navigate(`/disruptions/${success.case_id}`)}
            className="ml-4 px-4 py-2 bg-emerald-600 text-white text-sm font-medium rounded-md hover:bg-emerald-700 transition-colors whitespace-nowrap"
          >
            View Analysis
          </button>
        </div>
      )}

      {/* Predefined Scenarios */}
      <div>
        <h3 className="text-sm font-semibold text-slate-700 uppercase tracking-wider mb-4">
          Predefined Scenarios
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {SCENARIOS.map((scenario) => {
            const payload = scenario.buildPayload(suppliers);
            const isLoading = triggering === scenario.id;
            return (
              <div
                key={scenario.id}
                className={`bg-white border ${scenario.borderColor} rounded-md p-5 shadow-sm`}
              >
                <div className="flex items-start gap-4">
                  <div className={`p-3 rounded-md ${scenario.iconBg}`}>
                    <scenario.icon className={`w-5 h-5 ${scenario.iconColor}`} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <h4 className="font-semibold text-slate-900">{scenario.title}</h4>
                    <p className="text-sm text-slate-500 mt-1 mb-4 leading-relaxed">
                      {scenario.description}
                    </p>
                    <div className="text-xs text-slate-400 mb-4">
                      Supplier: <span className="font-medium text-slate-600">
                        {suppliers.find(s => s.id === payload.supplier_id)?.name ?? 'N/A'}
                      </span>
                      &nbsp;&nbsp;Delay: <span className="font-medium text-slate-600">
                        {(payload.delay_days as number) > 0 ? `${payload.delay_days} days` : 'N/A'}
                      </span>
                      &nbsp;&nbsp;Severity: <span className="font-medium text-slate-600 capitalize">
                        {payload.severity as string}
                      </span>
                    </div>
                    <button
                      onClick={() => handleTrigger(scenario.id, payload)}
                      disabled={triggering !== null}
                      className="flex items-center justify-center gap-2 w-full px-4 py-2 bg-slate-800 text-white text-sm font-medium rounded-md hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                      {isLoading ? (
                        <span className="flex items-center gap-2">
                          <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                          </svg>
                          Starting Workflow...
                        </span>
                      ) : (
                        <>
                          <Play className="w-4 h-4" />
                          Trigger Scenario
                        </>
                      )}
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Custom Scenario Form */}
      <div className="bg-white border border-slate-200 rounded-md p-6 shadow-sm">
        <h3 className="text-sm font-semibold text-slate-700 uppercase tracking-wider mb-4">
          Custom Scenario
        </h3>
        <form onSubmit={handleCustomSubmit} className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Disruption Type</label>
            <select
              value={customForm.type}
              onChange={(e) => setCustomForm((f) => ({ ...f, type: e.target.value }))}
              className="w-full border border-slate-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="supplier_delay">Supplier Delay</option>
              <option value="logistics">Logistics Disruption</option>
              <option value="inventory_shortage">Inventory Shortage</option>
              <option value="weather">Weather Disruption</option>
              <option value="other">Other</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Supplier</label>
            <select
              value={customForm.supplier_id}
              onChange={(e) => setCustomForm((f) => ({ ...f, supplier_id: e.target.value }))}
              className="w-full border border-slate-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {suppliers.map((s) => (
                <option key={s.id} value={s.id}>{s.name} ({s.country})</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Severity</label>
            <select
              value={customForm.severity}
              onChange={(e) => setCustomForm((f) => ({ ...f, severity: e.target.value }))}
              className="w-full border border-slate-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
              <option value="critical">Critical</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Delay Days</label>
            <input
              type="number"
              min={0}
              max={90}
              value={customForm.delay_days}
              onChange={(e) => setCustomForm((f) => ({ ...f, delay_days: parseInt(e.target.value) || 0 }))}
              className="w-full border border-slate-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div className="md:col-span-2">
            <label className="block text-xs font-medium text-slate-600 mb-1">Description</label>
            <textarea
              value={customForm.description}
              onChange={(e) => setCustomForm((f) => ({ ...f, description: e.target.value }))}
              rows={2}
              placeholder="Describe the disruption scenario..."
              className="w-full border border-slate-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
            />
          </div>
          <div className="md:col-span-2">
            <button
              type="submit"
              disabled={triggering !== null}
              className="px-6 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {triggering === 'custom' ? 'Triggering...' : 'Trigger Custom Scenario'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
