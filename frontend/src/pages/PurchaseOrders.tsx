import React, { useEffect, useState } from 'react';
import { api } from '../api/api';
import { PurchaseOrder } from '../api/types';
import { StatusBadge } from '../components/common/StatusBadge';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { ErrorMessage } from '../components/common/ErrorMessage';

export default function PurchaseOrders() {
  const [data, setData] = useState<PurchaseOrder[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getPurchaseOrders()
      .then(setData)
      .catch(err => setError(err.message || 'Failed to load purchase orders'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorMessage message={error} />;

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-slate-900 tracking-tight">Purchase Orders</h2>
      
      <div className="bg-white shadow-sm rounded-md border border-slate-200 overflow-hidden">
        <table className="min-w-full divide-y divide-slate-200">
          <thead className="bg-slate-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">PO Number</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Supplier</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Item</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Quantity</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Status</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Expected Delivery</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Delay</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-slate-200">
            {data.map((po) => (
              <tr key={po.id} className="hover:bg-slate-50">
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-slate-900">{po.order_number}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-500">{po.supplier_name || po.supplier_id}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-500">{po.item_name || po.inventory_item_id}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-900">{po.quantity}</td>
                <td className="px-6 py-4 whitespace-nowrap"><StatusBadge status={po.status} /></td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-500">{new Date(po.expected_delivery_date).toLocaleDateString()}</td>
                <td className={`px-6 py-4 whitespace-nowrap text-sm ${po.delay_days && po.delay_days > 0 ? 'text-red-600 font-medium' : 'text-slate-500'}`}>
                  {po.delay_days ? `${po.delay_days} days` : '-'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
