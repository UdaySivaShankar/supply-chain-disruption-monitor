import React from 'react';

export function StatusBadge({ status, type = 'status' }: { status: string, type?: 'status' | 'severity' }) {
  let bg = 'bg-slate-100';
  let text = 'text-slate-800';

  if (type === 'severity') {
    switch (status.toLowerCase()) {
      case 'critical': bg = 'bg-red-100'; text = 'text-red-800'; break;
      case 'high': bg = 'bg-orange-100'; text = 'text-orange-800'; break;
      case 'medium': bg = 'bg-yellow-100'; text = 'text-yellow-800'; break;
      case 'low': bg = 'bg-blue-100'; text = 'text-blue-800'; break;
    }
  } else {
    switch (status.toLowerCase()) {
      case 'resolved':
      case 'approved':
      case 'delivered':
        bg = 'bg-emerald-100'; text = 'text-emerald-800'; break;
      case 'pending_approval':
      case 'pending':
        bg = 'bg-amber-100'; text = 'text-amber-800'; break;
      case 'rejected':
      case 'cancelled':
        bg = 'bg-red-100'; text = 'text-red-800'; break;
      case 'in_transit':
        bg = 'bg-blue-100'; text = 'text-blue-800'; break;
      case 'delayed':
        bg = 'bg-orange-100'; text = 'text-orange-800'; break;
    }
  }

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-md text-xs font-medium uppercase tracking-wider ${bg} ${text}`}>
      {status.replace('_', ' ')}
    </span>
  );
}

export default StatusBadge;
