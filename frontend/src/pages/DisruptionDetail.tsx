import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ShieldAlert, BrainCircuit, Activity, CheckCircle, XCircle, CheckSquare, ArrowLeft } from 'lucide-react';
import { api } from '../api/api';
import { DisruptionCase, Supplier } from '../api/types';
import { StatusBadge } from '../components/common/StatusBadge';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { ErrorMessage } from '../components/common/ErrorMessage';

export default function DisruptionDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [data, setData] = useState<DisruptionCase | null>(null);
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [approvalNotes, setApprovalNotes] = useState('');
  const [outcomeText, setOutcomeText] = useState('');
  const [actionLoading, setActionLoading] = useState(false);

  const loadData = () => {
    if (!id) return;
    setLoading(true);
    api.getDisruption(id)
      .then(setData)
      .catch(err => setError(err.message || 'Failed to load disruption details'))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadData();
  }, [id]);

  useEffect(() => {
    api.getSuppliers().then(setSuppliers).catch(() => setSuppliers([]));
  }, []);

  const handleApprove = async () => {
    if (!id) return;
    setActionLoading(true);
    try {
      await api.approveDisruption(id, { notes: approvalNotes || 'Mitigation plan approved by operator.' });
      loadData();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to approve';
      alert(msg);
    } finally {
      setActionLoading(false);
    }
  };

  const handleReject = async () => {
    if (!id) return;
    setActionLoading(true);
    try {
      await api.rejectDisruption(id, { notes: approvalNotes || 'Mitigation plan rejected by operator.' });
      loadData();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to reject';
      alert(msg);
    } finally {
      setActionLoading(false);
    }
  };

  const handleResolve = async () => {
    if (!id) return;
    if (!outcomeText.trim()) {
      alert('Please describe the actual operational outcome before resolving.');
      return;
    }
    setActionLoading(true);
    try {
      await api.resolveDisruption(id, { outcome: outcomeText });
      loadData();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to resolve';
      alert(msg);
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorMessage message={error} />;
  if (!data) return <ErrorMessage message="Disruption not found" />;

  const isPending = data.status === 'pending_approval';
  const isApproved = data.status === 'approved';
  const isResolved = data.status === 'resolved';

  const supplier = suppliers.find((s) => s.id === data.affected_supplier_id);
  const delayDays = data.delay_days || 0;
  const coverageDays = data.inventory_coverage_days || 0;
  const coverageGap = Math.max(0, delayDays - coverageDays);

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Top Navigation & Status */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <button
            onClick={() => navigate('/disruptions')}
            className="inline-flex items-center text-xs font-medium text-slate-500 hover:text-slate-800 mb-2 transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5 mr-1" /> Back to Disruptions
          </button>
          <h2 className="text-2xl font-bold text-slate-900 tracking-tight">{data.title}</h2>
          <p className="text-sm text-slate-500 mt-1">
            ID: <span className="font-mono text-xs">{data.id}</span> &bull; Detected: {new Date(data.detected_at).toLocaleString()}
          </p>
        </div>
        <div className="flex space-x-3">
          <StatusBadge status={data.severity} type="severity" />
          <StatusBadge status={data.status} />
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Event Summary */}
        <div className="bg-white rounded-md shadow-sm border border-slate-200 p-6">
          <h3 className="text-lg font-medium text-slate-900 mb-4 flex items-center">
            <ShieldAlert className="w-5 h-5 mr-2 text-slate-500" /> Event Summary
          </h3>
          <p className="text-slate-700 leading-relaxed">{data.description}</p>
          <div className="mt-4 grid grid-cols-2 gap-4 text-sm pt-4 border-t border-slate-100">
            <div>
              <span className="text-slate-500">Type:</span>
              <span className="ml-2 font-medium capitalize">{data.disruption_type.replace('_', ' ')}</span>
            </div>
            <div>
              <span className="text-slate-500">Delay:</span>
              <span className="ml-2 font-medium text-red-600">{data.delay_days} days</span>
            </div>
          </div>
        </div>

        {/* Impact Assessment */}
        <div className="bg-white rounded-md shadow-sm border border-slate-200 p-6">
          <h3 className="text-lg font-medium text-slate-900 mb-4 flex items-center">
            <Activity className="w-5 h-5 mr-2 text-slate-500" /> Impact Assessment
          </h3>
          <div className="space-y-4">
            <div>
              <div className="flex justify-between text-sm mb-1">
                <span className="text-slate-500">Stockout Risk</span>
                <span className="font-medium">{((data.stockout_risk || 0) * 100).toFixed(0)}%</span>
              </div>
              <div className="w-full bg-slate-200 rounded-full h-2">
                <div
                  className={`h-2 rounded-full ${
                    (data.stockout_risk || 0) > 0.7
                      ? 'bg-red-500'
                      : (data.stockout_risk || 0) > 0.4
                      ? 'bg-orange-500'
                      : 'bg-emerald-500'
                  }`}
                  style={{ width: `${Math.min(100, Math.max(5, (data.stockout_risk || 0) * 100))}%` }}
                ></div>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4 text-sm pt-2">
              <div>
                <span className="text-slate-500">Inventory Coverage:</span>
                <span className="ml-2 font-medium">{data.inventory_coverage_days} days</span>
              </div>
              <div>
                <span className="text-slate-500">Est. Impact Value:</span>
                <span className="ml-2 font-medium">${(data.estimated_impact_value || 0).toLocaleString()}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Supplier and Risk Factors */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white rounded-md shadow-sm border border-slate-200 p-6">
          <h3 className="text-lg font-medium text-slate-900 mb-4">Affected Supplier</h3>
          {supplier ? (
            <div className="space-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-slate-500">Supplier</span>
                <span className="font-medium text-slate-900">{supplier.name}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Location</span>
                <span className="font-medium text-slate-900">{supplier.city}, {supplier.country}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Lead Time</span>
                <span className="font-medium text-slate-900">{supplier.lead_time_days} days</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Reliability Score</span>
                <span className="font-medium text-slate-900">{(supplier.reliability_score * 100).toFixed(0)}%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Capabilities</span>
                <span className="font-medium text-slate-900 text-right">{(supplier.capabilities || []).join(', ')}</span>
              </div>
            </div>
          ) : (
            <p className="text-sm text-slate-500">
              No supplier record is linked to this case.
            </p>
          )}
        </div>

        <div className="bg-white rounded-md shadow-sm border border-slate-200 p-6">
          <h3 className="text-lg font-medium text-slate-900 mb-4">Risk Factors</h3>
          <ul className="space-y-3 text-sm">
            <li className="flex justify-between">
              <span className="text-slate-500">Declared Severity</span>
              <span className="font-medium text-slate-900 capitalize">{data.severity}</span>
            </li>
            <li className="flex justify-between">
              <span className="text-slate-500">Delay Against Inventory Cover</span>
              <span className={`font-medium ${coverageGap > 0 ? 'text-red-600' : 'text-emerald-600'}`}>
                {coverageGap > 0 ? `${coverageGap} day coverage gap` : 'Cover absorbs the delay'}
              </span>
            </li>
            <li className="flex justify-between">
              <span className="text-slate-500">Stockout Risk</span>
              <span className="font-medium text-slate-900">{((data.stockout_risk || 0) * 100).toFixed(0)}%</span>
            </li>
            <li className="flex justify-between">
              <span className="text-slate-500">Inventory Cover Remaining</span>
              <span className="font-medium text-slate-900">{coverageDays} days</span>
            </li>
            <li className="flex justify-between">
              <span className="text-slate-500">Exposure To Stockout</span>
              <span className="font-medium text-slate-900">
                {coverageGap > 0 ? 'Stock runs out before replenishment arrives' : 'No projected stockout'}
              </span>
            </li>
          </ul>
        </div>
      </div>

      {/* Recommendations & Approvals */}
      {data.recommendation && (
        <div className="bg-white rounded-md shadow-sm border border-slate-200 p-6">
          <h3 className="text-lg font-medium text-slate-900 mb-4">Agent Recommendation</h3>
          <div className="bg-blue-50 border border-blue-200 rounded-md p-5 mb-4">
            <h4 className="font-semibold text-blue-900 text-lg mb-2">
              {data.recommendation.recommended_action || (data.recommendation as any).action}
            </h4>
            {data.recommendation.rationale && (
              <p className="text-blue-800 text-sm mb-4 leading-relaxed">{data.recommendation.rationale}</p>
            )}
            <div className="flex flex-wrap gap-4 text-sm text-blue-700">
              <span>
                Confidence: <strong>{(((data.recommendation.confidence_score ?? (data.recommendation as any).confidence) || 0.8) * 100).toFixed(0)}%</strong>
              </span>
              {data.recommendation.risk_level && (
                <span>Risk Level: <strong>{data.recommendation.risk_level}</strong></span>
              )}
              {data.recommendation.alternative_supplier && (
                <span>Alt Supplier: <strong>{data.recommendation.alternative_supplier}</strong></span>
              )}
            </div>

            {data.recommendation.steps && data.recommendation.steps.length > 0 && (
              <div className="mt-4 pt-4 border-t border-blue-200">
                <h5 className="text-xs font-semibold text-blue-900 uppercase tracking-wider mb-2">Execution Steps:</h5>
                <ul className="list-disc list-inside text-sm text-blue-800 space-y-1">
                  {data.recommendation.steps.map((step, idx) => (
                    <li key={idx}>{step}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {/* Pending Approval Controls */}
          {isPending && (
            <div className="mt-6 border-t border-slate-200 pt-6">
              <h4 className="text-sm font-semibold text-slate-800 uppercase tracking-wider mb-3">Human Approval Required</h4>
              <p className="text-xs text-slate-500 mb-3">
                Autonomous action is halted. Human review and explicit approval are required before any operational changes are executed.
              </p>
              <textarea
                value={approvalNotes}
                onChange={(e) => setApprovalNotes(e.target.value)}
                placeholder="Enter operator review notes or instructions (optional)..."
                className="w-full border border-slate-300 rounded-md p-3 text-sm focus:ring-blue-500 focus:border-blue-500 mb-4"
                rows={2}
              />
              <div className="flex space-x-3">
                <button
                  onClick={handleApprove}
                  disabled={actionLoading}
                  className="inline-flex items-center px-4 py-2 bg-emerald-600 text-white rounded-md text-sm font-medium hover:bg-emerald-700 disabled:opacity-50 transition-colors"
                >
                  <CheckCircle className="w-4 h-4 mr-2" /> Approve Recommendation
                </button>
                <button
                  onClick={handleReject}
                  disabled={actionLoading}
                  className="inline-flex items-center px-4 py-2 bg-red-600 text-white rounded-md text-sm font-medium hover:bg-red-700 disabled:opacity-50 transition-colors"
                >
                  <XCircle className="w-4 h-4 mr-2" /> Reject Recommendation
                </button>
              </div>
            </div>
          )}

          {/* Approved: Option to Resolve and Retain in Hindsight */}
          {isApproved && (
            <div className="mt-6 border-t border-emerald-200 bg-emerald-50 p-5 rounded-md">
              <div className="flex items-center gap-2 mb-2 text-emerald-800 font-semibold text-sm">
                <CheckCircle className="w-4 h-4" /> Recommendation Approved by Operator
              </div>
              <p className="text-xs text-emerald-700 mb-4">
                Mitigation execution underway. Once operational outcome is known, record the results below to retain this experience in Hindsight long-term memory.
              </p>
              <textarea
                value={outcomeText}
                onChange={(e) => setOutcomeText(e.target.value)}
                placeholder="Example: Alternative supplier delivered 100 tonnes on day 4. Production line maintained without stoppage. Cost increase was 8%."
                className="w-full border border-emerald-300 rounded-md p-3 text-sm focus:ring-emerald-500 focus:border-emerald-500 mb-3 bg-white"
                rows={3}
              />
              <button
                onClick={handleResolve}
                disabled={actionLoading}
                className="inline-flex items-center px-4 py-2 bg-emerald-700 text-white rounded-md text-sm font-medium hover:bg-emerald-800 disabled:opacity-50 transition-colors"
              >
                <CheckSquare className="w-4 h-4 mr-2" /> Resolve Disruption & Retain in Hindsight
              </button>
            </div>
          )}

          {/* Resolved Outcome Banner */}
          {isResolved && (
            <div className="mt-6 border border-emerald-200 bg-emerald-50 p-5 rounded-md">
              <div className="flex items-center gap-2 text-emerald-800 font-semibold text-sm mb-2">
                <CheckCircle className="w-4 h-4 text-emerald-600" /> Disruption Case Resolved
              </div>
              <p className="text-sm text-emerald-900 font-medium">Outcome Recorded:</p>
              <p className="text-sm text-emerald-800 mt-1 bg-white p-3 rounded border border-emerald-200">
                {data.outcome || 'Mitigation successfully concluded.'}
              </p>
              {data.resolved_at && (
                <p className="text-xs text-emerald-600 mt-3">
                  Resolved at: {new Date(data.resolved_at).toLocaleString()} &bull; Stored in Hindsight Memory
                </p>
              )}
            </div>
          )}
        </div>
      )}

      {/* Agent Trace */}
      {data.agent_trace && data.agent_trace.length > 0 && (
        <div className="bg-white rounded-md shadow-sm border border-slate-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-medium text-slate-900">Agent Reasoning Timeline</h3>
            <span className="text-xs text-slate-400 font-mono">{data.agent_trace.length} stages recorded</span>
          </div>
          <div className="space-y-4">
            {data.agent_trace.map((trace: any, idx: number) => {
              const isString = typeof trace === 'string';
              const agentName = isString ? 'Agent Node' : trace.agent || 'Agent Step';
              const analysisText = isString ? trace : trace.analysis || '';
              const conclusionText = isString ? '' : trace.conclusions || '';
              const timeString = (!isString && trace.timestamp) ? new Date(trace.timestamp).toLocaleTimeString() : '';

              return (
                <div key={idx} className="flex items-start gap-4 p-4 rounded-md border border-slate-200 bg-slate-50">
                  <div className="flex items-center justify-center w-8 h-8 rounded-full bg-blue-100 text-blue-700 shrink-0 mt-0.5">
                    <BrainCircuit className="w-4 h-4" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2 mb-1">
                      <span className="font-semibold text-slate-900 text-sm">{agentName}</span>
                      {timeString && <span className="text-xs text-slate-400">{timeString}</span>}
                    </div>
                    <p className="text-xs text-slate-600 leading-relaxed">{analysisText}</p>
                    {conclusionText && (
                      <p className="text-xs font-medium text-slate-800 mt-2 pt-2 border-t border-slate-200">
                        Conclusion: {conclusionText}
                      </p>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Hindsight Memories */}
      {data.hindsight_memories && data.hindsight_memories.length > 0 ? (
        <div className="bg-slate-50 rounded-md shadow-sm border border-slate-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-medium text-slate-900 flex items-center">
              <BrainCircuit className="w-5 h-5 mr-2 text-blue-600" /> Historical Memory from Hindsight
            </h3>
            <span className="text-xs bg-blue-100 text-blue-800 font-semibold px-2 py-1 rounded uppercase tracking-wider">
              {data.hindsight_memories.length} Memories Recalled
            </span>
          </div>
          <div className="space-y-3">
            {data.hindsight_memories.map((memory: any, idx: number) => {
              const content = typeof memory === 'string' ? memory : memory.content || JSON.stringify(memory);
              return (
                <div key={idx} className="bg-white border border-slate-200 p-4 rounded-md shadow-sm">
                  <div className="flex items-start">
                    <span className="bg-blue-100 text-blue-800 text-xs font-bold px-2 py-0.5 rounded uppercase tracking-wider mr-3 mt-0.5 shrink-0">
                      [HINDSIGHT MEMORY]
                    </span>
                    <p className="text-sm text-slate-700 flex-1 leading-relaxed">{content}</p>
                  </div>
                  {memory.relevance_score && (
                    <div className="mt-2 text-xs text-slate-500 text-right">
                      Relevance Score: {(memory.relevance_score * 100).toFixed(0)}%
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      ) : (
        <div className="bg-slate-50 rounded-md border border-slate-200 p-6">
          <h3 className="text-sm font-semibold text-slate-700 uppercase tracking-wider mb-2">Hindsight Memory Status</h3>
          <p className="text-xs text-slate-500 leading-relaxed">
            No prior disruption experiences found in Hindsight for this supplier or disruption pattern.
            The system used standard baseline operational data.
            Once this disruption is resolved, its outcome will be retained in Hindsight to inform future decisions.
          </p>
        </div>
      )}
    </div>
  );
}
