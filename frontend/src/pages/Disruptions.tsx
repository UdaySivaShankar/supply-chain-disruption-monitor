import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/api';
import { DisruptionCase } from '../api/types';
import { StatusBadge } from '../components/common/StatusBadge';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { ErrorMessage } from '../components/common/ErrorMessage';

export default function Disruptions() {
  const navigate = useNavigate();
  const [data, setData] = useState<DisruptionCase[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getDisruptions()
      .then(setData)
      .catch(err => setError(err.message || 'Failed to load disruptions'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorMessage message={error} />;

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-slate-900 tracking-tight">Disruption Cases</h2>
      
      <div className="bg-white shadow-sm rounded-md border border-slate-200 overflow-hidden">
        <table className="min-w-full divide-y divide-slate-200">
          <thead className="bg-slate-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">ID / Title</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Type</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Severity</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Status</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Detected At</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Coverage</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-slate-200">
            {data.map((d) => (
              <tr key={d.id} className="hover:bg-slate-50 cursor-pointer transition-colors" onClick={() => navigate(`/disruptions/${d.id}`)}>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm font-medium text-slate-900">{d.title}</div>
                  <div className="text-sm text-slate-500">{d.id.substring(0, 8)}</div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-500 capitalize">{d.disruption_type.replace('_', ' ')}</td>
                <td className="px-6 py-4 whitespace-nowrap"><StatusBadge status={d.severity} type="severity" /></td>
                <td className="px-6 py-4 whitespace-nowrap"><StatusBadge status={d.status} /></td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-500">{new Date(d.detected_at).toLocaleDateString()}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-500">{d.inventory_coverage_days} days</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
