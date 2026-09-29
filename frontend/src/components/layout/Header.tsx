import React from 'react';
import { ShieldCheck, Database } from 'lucide-react';

export default function Header() {
  return (
    <header className="bg-white border-b border-slate-200 h-16 flex items-center px-8 fixed top-0 right-0 left-64 z-10">
      <div className="flex flex-1 justify-between items-center">
        <h1 className="text-xl font-semibold text-slate-800 tracking-tight">Agentic AI Supply Chain Disruption Monitoring</h1>
        <div className="flex items-center space-x-3">
          <div className="flex items-center space-x-2 bg-slate-100 text-slate-600 px-3 py-1.5 rounded-md border border-slate-200">
            <Database className="w-4 h-4" />
            <span className="text-sm font-medium">Simulated Dataset</span>
          </div>
          <div className="flex items-center space-x-2 bg-emerald-50 text-emerald-700 px-3 py-1.5 rounded-md border border-emerald-200">
            <ShieldCheck className="w-4 h-4" />
            <span className="text-sm font-medium">System Active</span>
          </div>
        </div>
      </div>
    </header>
  );
}
