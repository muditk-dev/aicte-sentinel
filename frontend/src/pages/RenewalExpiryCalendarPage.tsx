import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { complianceService } from '../services/complianceService'
import { formatDate } from '../lib/utils'
import {
  Calendar,
  Clock,
  AlertTriangle,
  AlertOctagon,
  CheckCircle2,
  Building,
  RefreshCw,
  ExternalLink,
} from 'lucide-react'

export const RenewalExpiryCalendarPage: React.FC = () => {
  const [daysAhead, setDaysAhead] = useState<number>(60)
  const [urgencyFilter, setUrgencyFilter] = useState<string>('')
  const [searchQuery, setSearchQuery] = useState<string>('')

  const { data: deadlines = [], isLoading, refetch } = useQuery({
    queryKey: ['compliance-deadlines', daysAhead],
    queryFn: () => complianceService.getDeadlinesReport(daysAhead),
  })

  const filteredItems = deadlines.filter((item) => {
    if (urgencyFilter && item.urgency_status !== urgencyFilter) return false
    if (searchQuery) {
      const q = searchQuery.toLowerCase()
      return (
        item.title.toLowerCase().includes(q) ||
        item.reference_code.toLowerCase().includes(q) ||
        item.institution_name.toLowerCase().includes(q)
      )
    }
    return true
  })

  const getUrgencyBadge = (urgency: string, daysRemaining: number) => {
    switch (urgency) {
      case 'OVERDUE':
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold bg-red-100 text-red-800 border border-red-300 animate-pulse">
            <AlertOctagon className="w-3 h-3 mr-1" />
            Overdue by {Math.abs(daysRemaining)} days
          </span>
        )
      case 'DUE_TODAY':
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold bg-orange-100 text-orange-800 border border-orange-300">
            <AlertTriangle className="w-3 h-3 mr-1" />
            Due Today
          </span>
        )
      case 'CRITICAL_7_DAYS':
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-800 border border-amber-300">
            <Clock className="w-3 h-3 mr-1" />
            Due in {daysRemaining} days
          </span>
        )
      case 'APPROACHING_30_DAYS':
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-blue-100 text-blue-800 border border-blue-200">
            <Clock className="w-3 h-3 mr-1" />
            {daysRemaining} days remaining
          </span>
        )
      default:
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-emerald-100 text-emerald-800 border border-emerald-200">
            <CheckCircle2 className="w-3 h-3 mr-1" />
            {daysRemaining} days remaining
          </span>
        )
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight flex items-center">
            <Calendar className="w-6 h-6 mr-2 text-purple-700" />
            Renewal & Expiry Tracking Calendar
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Automated statutory deadline calendar for obligations, Fire NOCs, safety clearances, and approval expirations
          </p>
        </div>

        <button
          onClick={() => refetch()}
          className="p-1.5 text-slate-600 hover:text-slate-900 bg-white border border-slate-300 rounded shadow-sm self-start sm:self-auto"
          title="Refresh calendar"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {/* Filter Toolbar */}
      <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm flex flex-col md:flex-row gap-3">
        <input
          type="text"
          placeholder="Search by title, code, or institution..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="flex-1 px-3 py-1.5 text-xs border border-slate-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
        />

        <div className="flex flex-wrap items-center gap-2 text-xs">
          <select
            value={urgencyFilter}
            onChange={(e) => setUrgencyFilter(e.target.value)}
            className="px-2.5 py-1.5 border border-slate-300 rounded bg-white text-slate-700"
          >
            <option value="">All Urgency Levels</option>
            <option value="OVERDUE">Overdue Items Only</option>
            <option value="CRITICAL_7_DAYS">Critical (Due in 7 Days)</option>
            <option value="APPROACHING_30_DAYS">Approaching (Due in 30 Days)</option>
            <option value="HEALTHY">Healthy Timeline</option>
          </select>

          <select
            value={daysAhead}
            onChange={(e) => setDaysAhead(Number(e.target.value))}
            className="px-2.5 py-1.5 border border-slate-300 rounded bg-white text-slate-700"
          >
            <option value={30}>Lookahead: 30 Days</option>
            <option value={60}>Lookahead: 60 Days</option>
            <option value={90}>Lookahead: 90 Days</option>
            <option value={180}>Lookahead: 180 Days</option>
          </select>
        </div>
      </div>

      {/* Deadlines List */}
      <div className="bg-white rounded-lg border border-slate-200 shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-slate-400">
            <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-purple-600" />
            Loading deadline calendar...
          </div>
        ) : filteredItems.length === 0 ? (
          <div className="p-12 text-center">
            <CheckCircle2 className="w-10 h-10 text-emerald-500 mx-auto mb-3" />
            <h3 className="text-sm font-bold text-slate-800">No Approaching Deadlines</h3>
            <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
              All statutory obligations and renewals within this horizon are healthy or verified.
            </p>
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {filteredItems.map((item) => (
              <div
                key={item.id}
                className="p-4 hover:bg-slate-50/70 transition-colors flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs"
              >
                <div className="space-y-1">
                  <div className="flex items-center space-x-2">
                    <span className="font-mono text-[10px] font-bold text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded">
                      {item.reference_code}
                    </span>
                    <span className="px-1.5 py-0.5 rounded text-[10px] bg-purple-50 text-purple-700 font-semibold">
                      {item.category.replace('_', ' ')}
                    </span>
                    {getUrgencyBadge(item.urgency_status, item.days_remaining)}
                  </div>

                  <h3 className="font-bold text-slate-900 text-sm">{item.title}</h3>

                  <div className="flex items-center space-x-3 text-slate-500 text-[11px]">
                    <span className="flex items-center">
                      <Building className="w-3 h-3 mr-1 text-slate-400" />
                      {item.institution_name}
                    </span>
                    <span>•</span>
                    <span className="font-mono">Deadline: {formatDate(item.due_date)}</span>
                  </div>
                </div>

                <div className="flex items-center space-x-2 self-start sm:self-auto">
                  <Link
                    to={`/compliance/obligations/${item.id}`}
                    className="inline-flex items-center px-3 py-1 text-xs font-semibold text-blue-700 bg-blue-50 hover:bg-blue-100 rounded border border-blue-200 transition-colors"
                  >
                    Inspect
                    <ExternalLink className="w-3 h-3 ml-1" />
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
