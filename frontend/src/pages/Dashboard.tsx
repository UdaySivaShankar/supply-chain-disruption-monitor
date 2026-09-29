import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { AlertTriangle, Clock, Users, PackageX, PlaySquare } from 'lucide-react';
import { api } from '../api/api';
import { DashboardStats } from '../api/types';
import { StatCard } from '../components/common/StatCard';
import { StatusBadge } from '../components/common/StatusBadge';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { ErrorMessage } from '../components/common/ErrorMessage';

export default function Dashboard() {
  const navigate = useNavigate();
  const [data, setData] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getDashboardStats()
      .then(setData)
      .catch(err => setError(err.message || 'Failed to load dashboard stats'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorMessage message={error} />;
  if (!data) return null;

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-slate-900 tracking-tight">Operations Overview</h2>
        <button
          onClick={() => navigate('/simulator')}
          className="inline-flex items-center px-4 py-2 bg-accent-blue text-white text-sm font-medium rounded-md hover:bg-blue-700 transition-colors"
        >
          <PlaySquare className="w-4 h-4 mr-2" />
          Run Simulator
        </button>
      </div>

      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard title="Active Disruptions" value={data.active_disruptions} icon={AlertTriangle} colorClass="bg-red-500" />
        <StatCard title="Pending Approvals" value={data.pending_approvals} icon={Clock} colorClass="bg-amber-500" />
        <StatCard title="Affected Suppliers" value={data.affected_suppliers} icon={Users} colorClass="bg-blue-500" />
        <StatCard title="Items at Risk" value={data.inventory_at_risk} icon={PackageX} colorClass="bg-orange-500" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-white shadow-sm rounded-md border border-slate-200">
          <div className="px-6 py-4 border-b border-slate-200">
            <h3 className="text-lg font-medium text-slate-900">Active Disruptions</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200">
              <thead className="bg-slate-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">ID / Title</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Severity</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Status</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Risk Level</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-slate-200">
                {data.active_disruption_list.map((d) => (
                  <tr key={d.id} className="hover:bg-slate-50 cursor-pointer transition-colors" onClick={() => navigate(`/disruptions/${d.id}`)}>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm font-medium text-slate-900">{d.title}</div>
                      <div className="text-sm text-slate-500">{d.id.substring(0, 8)}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap"><StatusBadge status={d.severity} type="severity" /></td>
                    <td className="px-6 py-4 whitespace-nowrap"><StatusBadge status={d.status} /></td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-500">
                      {d.stockout_risk > 0.7 ? 'High' : d.stockout_risk > 0.4 ? 'Medium' : 'Low'}
                    </td>
                  </tr>
                ))}
                {data.active_disruption_list.length === 0 && (
                  <tr>
                    <td colSpan={4} className="px-6 py-8 text-center text-sm text-slate-500">
                      No active disruptions. System is operating normally.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        <div className="bg-white shadow-sm rounded-md border border-slate-200">
          <div className="px-6 py-4 border-b border-slate-200">
            <h3 className="text-lg font-medium text-slate-900">Recent Alerts</h3>
          </div>
          <div className="p-4 space-y-4 max-h-[400px] overflow-y-auto">
            {data.recent_alerts.map((alert) => (
              <div key={alert.id} className="bg-slate-50 rounded-md p-4 border border-slate-200 flex space-x-3">
                <AlertTriangle className={`w-5 h-5 flex-shrink-0 ${alert.severity === 'critical' ? 'text-red-500' : 'text-amber-500'}`} />
                <div>
                  <h4 className="text-sm font-medium text-slate-900">{alert.title}</h4>
                  <p className="text-sm text-slate-600 mt-1">{alert.message}</p>
                  <p className="text-xs text-slate-400 mt-2">{new Date(alert.created_at).toLocaleString()}</p>
                </div>
              </div>
            ))}
            {data.recent_alerts.length === 0 && (
              <p className="text-sm text-slate-500 text-center py-4">No recent alerts.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
