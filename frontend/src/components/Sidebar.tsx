import React from 'react'
import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  FileText,
  Building,
  GitBranch,
  ShieldCheck,
  Activity,
  Users,
  Scale,
  Award,
} from 'lucide-react'

export const Sidebar: React.FC = () => {
  const navItems = [
    { name: 'Command Center', path: '/', icon: LayoutDashboard },
    { name: 'Statutory Applications', path: '/applications', icon: FileText },
    { name: 'EVC Inspections & Pool', path: '/evc', icon: Users },
    { name: 'Committees & Hearings', path: '/committees', icon: Scale },
    { name: 'Statutory Decisions', path: '/decisions', icon: Award },
    { name: 'Institution Registry', path: '/institutions', icon: Building },
    { name: 'Workflow Engine', path: '/workflows', icon: GitBranch },
    { name: 'Audit & Merkle Ledger', path: '/audit', icon: ShieldCheck },
    { name: 'System Diagnostics', path: '/diagnostics', icon: Activity },
  ]

  return (
    <aside className="w-64 bg-slate-900 border-r border-slate-800 flex-shrink-0 flex flex-col justify-between hidden md:flex">
      <div className="p-4 space-y-1">
        <div className="px-3 py-2 text-[11px] font-bold uppercase tracking-wider text-slate-400">
          Statutory Operations
        </div>

        {navItems.map((item) => {
          const Icon = item.icon
          return (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === '/'}
              className={({ isActive }) =>
                `flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                  isActive
                    ? 'bg-blue-600 text-white shadow-sm'
                    : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                }`
              }
            >
              <Icon className="w-4 h-4 mr-3 flex-shrink-0" />
              {item.name}
            </NavLink>
          )
        })}
      </div>

      {/* Statutory Footer Badge */}
      <div className="p-4 border-t border-slate-800 text-slate-400 text-xs">
        <div className="font-semibold text-slate-300">AICTE Regulatory System</div>
        <div className="text-[11px] text-slate-500 mt-0.5">APH 2026-27 Compliant</div>
      </div>
    </aside>
  )
}
