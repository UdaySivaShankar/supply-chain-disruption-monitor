import React from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, AlertTriangle, Users, Package, ShoppingCart, BarChart3, BrainCircuit, PlaySquare } from 'lucide-react';

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Disruptions', href: '/disruptions', icon: AlertTriangle },
  { name: 'Suppliers', href: '/suppliers', icon: Users },
  { name: 'Inventory', href: '/inventory', icon: Package },
  { name: 'Purchase Orders', href: '/purchase-orders', icon: ShoppingCart },
  { name: 'Analytics', href: '/analytics', icon: BarChart3 },
  { name: 'Memory (Hindsight)', href: '/memory', icon: BrainCircuit },
  { name: 'Simulator', href: '/simulator', icon: PlaySquare },
];

export default function Sidebar() {
  return (
    <div className="flex flex-col w-64 bg-navy-900 border-r border-slate-700 min-h-screen fixed left-0 top-0 text-slate-300">
      <div className="flex items-center h-16 px-6 bg-slate-900">
        <span className="text-lg font-bold text-white tracking-wide">AI Ops Center</span>
      </div>
      <nav className="flex-1 px-4 py-6 space-y-1 overflow-y-auto">
        {navigation.map((item) => (
          <NavLink
            key={item.name}
            to={item.href}
            className={({ isActive }) =>
              `flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                isActive
                  ? 'bg-accent-blue text-white'
                  : 'text-slate-300 hover:bg-slate-800 hover:text-white'
              }`
            }
          >
            <item.icon className="mr-3 h-5 w-5 flex-shrink-0" aria-hidden="true" />
            {item.name}
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
