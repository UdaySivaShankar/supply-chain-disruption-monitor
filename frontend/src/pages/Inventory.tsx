import React, { useEffect, useState } from 'react';
import { api } from '../api/api';
import { InventoryItem } from '../api/types';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { ErrorMessage } from '../components/common/ErrorMessage';

export default function Inventory() {
  const [data, setData] = useState<InventoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getInventory()
      .then(setData)
      .catch(err => setError(err.message || 'Failed to load inventory'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorMessage message={error} />;

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-slate-900 tracking-tight">Inventory</h2>
      
      <div className="bg-white shadow-sm rounded-md border border-slate-200 overflow-hidden">
        <table className="min-w-full divide-y divide-slate-200">
          <thead className="bg-slate-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">SKU / Name</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Category</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Quantity</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Daily Demand</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Coverage</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Status</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-slate-200">
            {data.map((item) => {
              const coverage = Math.floor(item.current_quantity / item.daily_demand_rate);
              const coverageColor = coverage < 3 ? 'text-red-600 font-semibold' : coverage < 7 ? 'text-orange-600' : 'text-emerald-600';
              const isBelowSafety = item.current_quantity <= item.safety_stock;
              return (
                <tr key={item.id} className="hover:bg-slate-50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm font-medium text-slate-900">{item.name}</div>
                    <div className="text-sm text-slate-500">{item.sku}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-500">{item.category}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-900">{item.current_quantity} {item.unit}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-500">{item.daily_demand_rate} / day</td>
                  <td className={`px-6 py-4 whitespace-nowrap text-sm ${coverageColor}`}>{coverage} days</td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    {isBelowSafety ? (
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-md text-xs font-medium bg-red-100 text-red-800">Critical Low</span>
                    ) : (
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-md text-xs font-medium bg-emerald-100 text-emerald-800">Healthy</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
