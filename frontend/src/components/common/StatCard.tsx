import React from 'react';

export function StatCard({ title, value, icon: Icon, colorClass }: { title: string, value: string | number, icon: any, colorClass: string }) {
  return (
    <div className="bg-white p-6 rounded-md shadow-sm border border-slate-200">
      <div className="flex items-center">
        <div className={`p-3 rounded-md ${colorClass}`}>
          <Icon className="w-6 h-6 text-white" />
        </div>
        <div className="ml-5">
          <p className="text-sm font-medium text-slate-500 truncate">{title}</p>
          <p className="mt-1 text-2xl font-semibold text-slate-900">{value}</p>
        </div>
      </div>
    </div>
  );
}

export default StatCard;
