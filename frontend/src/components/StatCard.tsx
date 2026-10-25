import React from 'react'
import { LucideIcon } from 'lucide-react'

interface StatCardProps {
  title: string
  value: string | number
  subtitle?: string
  icon: LucideIcon
  tone?: 'default' | 'accent' | 'warning' | 'success'
}

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  subtitle,
  icon: Icon,
  tone = 'default',
}) => {
  const getIconWrapper = () => {
    switch (tone) {
      case 'accent':
        return 'bg-blue-50 text-blue-700'
      case 'warning':
        return 'bg-amber-50 text-amber-700'
      case 'success':
        return 'bg-emerald-50 text-emerald-700'
      default:
        return 'bg-slate-100 text-slate-700'
    }
  }

  return (
    <div className="bg-white rounded-lg border border-slate-200 p-5 shadow-sm hover:border-slate-300 transition-colors">
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
          {title}
        </p>
        <div className={`p-2 rounded-md ${getIconWrapper()}`}>
          <Icon className="w-5 h-5" />
        </div>
      </div>
      <div className="mt-3">
        <h3 className="text-2xl font-bold text-slate-900 tracking-tight">{value}</h3>
        {subtitle && (
          <p className="mt-1 text-xs text-slate-500 font-medium">{subtitle}</p>
        )}
      </div>
    </div>
  )
}
