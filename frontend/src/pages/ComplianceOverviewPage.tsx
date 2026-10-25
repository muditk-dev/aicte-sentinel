import React from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { complianceService } from '../services/complianceService'
import { authService } from '../services/authService'
import {
  ShieldCheck,
  AlertTriangle,
  Clock,
  FileText,
  Calendar,
  AlertOctagon,
  RefreshCw,
  BarChart3,
  CheckCircle2,
  FileSpreadsheet,
} from 'lucide-react'

export const ComplianceOverviewPage: React.FC = () => {
  const queryClient = useQueryClient()
  const user = authService.getCurrentUser()
  const isOfficerOrAdmin = user?.roles.some((r) =>
    ['SUPER_ADMIN', 'ADMIN', 'REGIONAL_OFFICER', 'SCRUTINY_OFFICER'].includes(r.code)
  )

  const { data: summary, isLoading, isError, refetch } = useQuery({
    queryKey: ['compliance-summary'],
    queryFn: () => complianceService.getSummaryReport(),
  })

  const triggerMutation = useMutation({
    mutationFn: () => complianceService.triggerMonitoringWorker(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['compliance-summary'] })
      queryClient.invalidateQueries({ queryKey: ['compliance-obligations'] })
    },
  })

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center p-12 space-y-3">
        <RefreshCw className="w-8 h-8 animate-spin text-blue-600" />
        <p className="text-sm text-slate-500">Loading statutory compliance intelligence...</p>
      </div>
    )
  }

  if (isError || !summary) {
    return (
      <div className="p-6 bg-red-50 border border-red-200 rounded-lg text-center">
        <AlertTriangle className="w-8 h-8 text-red-600 mx-auto mb-2" />
        <h3 className="text-sm font-bold text-red-900">Failed to load compliance overview</h3>
        <p className="text-xs text-red-700 mt-1">Please verify backend service availability and try again.</p>
        <button
          onClick={() => refetch()}
          className="mt-3 px-3 py-1.5 text-xs font-semibold text-white bg-red-600 rounded hover:bg-red-700"
        >
          Retry
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight flex items-center">
            <ShieldCheck className="w-6 h-6 mr-2 text-blue-700" />
            Post-Approval Compliance & Monitoring
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            M14–M16: Statutory obligation tracking, automated deadline monitoring, renewal alerts, and compliance intelligence
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {isOfficerOrAdmin && (
            <button
              onClick={() => triggerMutation.mutate()}
              disabled={triggerMutation.isPending}
              className="inline-flex items-center px-3 py-1.5 text-xs font-semibold text-slate-700 bg-white border border-slate-300 rounded hover:bg-slate-50 disabled:opacity-50 shadow-sm"
              title="Runs deadline evaluation, overdue state transitions, and escalation notifications"
            >
              <RefreshCw className={`w-3.5 h-3.5 mr-1.5 ${triggerMutation.isPending ? 'animate-spin' : ''}`} />
              Run Monitor Cycle
            </button>
          )}

          <Link
            to="/compliance/reports"
            className="inline-flex items-center px-3 py-1.5 text-xs font-semibold text-white bg-blue-700 rounded hover:bg-blue-800 shadow-sm"
          >
            <BarChart3 className="w-3.5 h-3.5 mr-1.5" />
            Compliance Reports
          </Link>
        </div>
      </div>

      {/* Synthetic Demonstration Banner */}
      {summary.is_synthetic_demonstration && (
        <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg flex items-start space-x-2 text-xs text-amber-900">
          <AlertTriangle className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
          <div>
            <span className="font-bold">Synthetic Demonstration Environment:</span> Data includes sample statutory obligations (FSR, Fire NOC, Endowment FDR) modeled after official AICTE Approval Process Handbook (APH 2026-27) norms for SIH demonstration.
          </div>
        </div>
      )}

      {/* Top Level KPIs */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-4">
        <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 block">Total Obligations</span>
          <div className="mt-2 flex items-baseline justify-between">
            <span className="text-2xl font-bold text-slate-900">{summary.total_obligations}</span>
            <FileText className="w-4 h-4 text-slate-400" />
          </div>
          <span className="text-[10px] text-slate-500 mt-1 block">Assigned compliance dockets</span>
        </div>

        <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-emerald-600 block">Compliant</span>
          <div className="mt-2 flex items-baseline justify-between">
            <span className="text-2xl font-bold text-emerald-700">{summary.total_compliant}</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-500" />
          </div>
          <span className="text-[10px] text-slate-500 mt-1 block">Verified & compliant</span>
        </div>

        <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-blue-600 block">Pending Review</span>
          <div className="mt-2 flex items-baseline justify-between">
            <span className="text-2xl font-bold text-blue-700">{summary.total_pending + summary.total_under_review}</span>
            <Clock className="w-4 h-4 text-blue-500" />
          </div>
          <span className="text-[10px] text-slate-500 mt-1 block">Awaiting submission / review</span>
        </div>

        <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-amber-600 block">Deficient</span>
          <div className="mt-2 flex items-baseline justify-between">
            <span className="text-2xl font-bold text-amber-700">{summary.total_deficient}</span>
            <AlertTriangle className="w-4 h-4 text-amber-500" />
          </div>
          <span className="text-[10px] text-slate-500 mt-1 block">Under statutory cure window</span>
        </div>

        <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-red-600 block">Overdue</span>
          <div className="mt-2 flex items-baseline justify-between">
            <span className="text-2xl font-bold text-red-700">{summary.total_overdue}</span>
            <AlertOctagon className="w-4 h-4 text-red-500" />
          </div>
          <span className="text-[10px] text-slate-500 mt-1 block">Past statutory due date</span>
        </div>

        <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-purple-600 block">Escalations</span>
          <div className="mt-2 flex items-baseline justify-between">
            <span className="text-2xl font-bold text-purple-700">{summary.active_escalations_count}</span>
            <ShieldCheck className="w-4 h-4 text-purple-500" />
          </div>
          <span className="text-[10px] text-slate-500 mt-1 block">Active supervisory alerts</span>
        </div>
      </div>

      {/* Compliance Health & Quick Nav */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Compliance Rate Gauge Panel */}
        <div className="bg-white p-6 rounded-lg border border-slate-200 shadow-sm">
          <h2 className="text-sm font-bold text-slate-900 tracking-tight flex items-center justify-between">
            <span>Overall Statutory Compliance Rate</span>
            <span className="text-lg font-mono font-bold text-blue-700">{summary.compliance_rate_percent}%</span>
          </h2>
          <div className="w-full bg-slate-100 rounded-full h-3 mt-4 overflow-hidden">
            <div
              className={`h-3 rounded-full transition-all duration-500 ${
                summary.compliance_rate_percent >= 80
                  ? 'bg-emerald-600'
                  : summary.compliance_rate_percent >= 60
                  ? 'bg-amber-500'
                  : 'bg-red-600'
              }`}
              style={{ width: `${Math.min(100, Math.max(0, summary.compliance_rate_percent))}%` }}
            />
          </div>
          <p className="text-xs text-slate-500 mt-3 leading-relaxed">
            Measures compliant statutory dockets against total active obligations. Institutions falling below 70% threshold are automatically prioritized for regional scrutiny and Standing Hearing Committee review.
          </p>

          <div className="mt-6 pt-4 border-t border-slate-100 grid grid-cols-2 gap-3 text-xs">
            <div className="p-2.5 rounded bg-slate-50 border border-slate-100">
              <span className="text-slate-400 block text-[10px] font-semibold uppercase">Closed Dockets</span>
              <span className="text-sm font-bold text-slate-800">{summary.total_closed}</span>
            </div>
            <div className="p-2.5 rounded bg-slate-50 border border-slate-100">
              <span className="text-slate-400 block text-[10px] font-semibold uppercase">Pending Actions</span>
              <span className="text-sm font-bold text-slate-800">{summary.total_pending + summary.total_deficient + summary.total_overdue}</span>
            </div>
          </div>
        </div>

        {/* Quick Nav Hub */}
        <div className="bg-white p-6 rounded-lg border border-slate-200 shadow-sm lg:col-span-2">
          <h2 className="text-sm font-bold text-slate-900 tracking-tight mb-4">Compliance Operations Hub</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <Link
              to="/compliance/obligations"
              className="p-4 rounded-lg border border-slate-200 hover:border-blue-500 hover:bg-blue-50/30 transition-all flex items-start space-x-3 group"
            >
              <div className="p-2 bg-blue-100 text-blue-700 rounded group-hover:bg-blue-700 group-hover:text-white transition-colors">
                <FileText className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-xs font-bold text-slate-900 group-hover:text-blue-700">Obligations Register</h3>
                <p className="text-[11px] text-slate-500 mt-0.5">Track, filter, and verify institutional statutory obligations</p>
              </div>
            </Link>

            <Link
              to="/compliance/calendar"
              className="p-4 rounded-lg border border-slate-200 hover:border-purple-500 hover:bg-purple-50/30 transition-all flex items-start space-x-3 group"
            >
              <div className="p-2 bg-purple-100 text-purple-700 rounded group-hover:bg-purple-700 group-hover:text-white transition-colors">
                <Calendar className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-xs font-bold text-slate-900 group-hover:text-purple-700">Renewal & Expiry Calendar</h3>
                <p className="text-[11px] text-slate-500 mt-0.5">Timeline monitoring for approvals, fire NOCs, and leases</p>
              </div>
            </Link>

            <Link
              to="/compliance/escalations"
              className="p-4 rounded-lg border border-slate-200 hover:border-amber-500 hover:bg-amber-50/30 transition-all flex items-start space-x-3 group"
            >
              <div className="p-2 bg-amber-100 text-amber-700 rounded group-hover:bg-amber-700 group-hover:text-white transition-colors">
                <AlertOctagon className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-xs font-bold text-slate-900 group-hover:text-amber-700">Escalation & Audit Feed</h3>
                <p className="text-[11px] text-slate-500 mt-0.5">Level 1 and Level 2 overdue notifications and alerts</p>
              </div>
            </Link>

            <Link
              to="/compliance/reports"
              className="p-4 rounded-lg border border-slate-200 hover:border-emerald-500 hover:bg-emerald-50/30 transition-all flex items-start space-x-3 group"
            >
              <div className="p-2 bg-emerald-100 text-emerald-700 rounded group-hover:bg-emerald-700 group-hover:text-white transition-colors">
                <FileSpreadsheet className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-xs font-bold text-slate-900 group-hover:text-emerald-700">Compliance Analytics & Export</h3>
                <p className="text-[11px] text-slate-500 mt-0.5">Institution compliance rankings and sanitized CSV exports</p>
              </div>
            </Link>
          </div>
        </div>
      </div>

      {/* Norm Category Breakdown */}
      <div className="bg-white rounded-lg border border-slate-200 shadow-sm p-6">
        <h2 className="text-sm font-bold text-slate-900 tracking-tight mb-4">APH Norm Category Breakdown</h2>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200 text-xs">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-4 py-2.5 text-left font-bold text-slate-700 uppercase tracking-wider">Norm Category</th>
                <th className="px-4 py-2.5 text-center font-bold text-slate-700 uppercase tracking-wider">Total</th>
                <th className="px-4 py-2.5 text-center font-bold text-emerald-700 uppercase tracking-wider">Compliant</th>
                <th className="px-4 py-2.5 text-center font-bold text-blue-700 uppercase tracking-wider">Pending</th>
                <th className="px-4 py-2.5 text-center font-bold text-amber-700 uppercase tracking-wider">Deficient</th>
                <th className="px-4 py-2.5 text-center font-bold text-red-700 uppercase tracking-wider">Overdue</th>
                <th className="px-4 py-2.5 text-center font-bold text-slate-700 uppercase tracking-wider">Health</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {summary.categories_breakdown.map((cat) => {
                const compRate = cat.total > 0 ? Math.round((cat.compliant / cat.total) * 100) : 100
                return (
                  <tr key={cat.category} className="hover:bg-slate-50/50">
                    <td className="px-4 py-3 font-semibold text-slate-800">{cat.category.replace('_', ' ')}</td>
                    <td className="px-4 py-3 text-center text-slate-600 font-mono">{cat.total}</td>
                    <td className="px-4 py-3 text-center font-mono font-semibold text-emerald-700">{cat.compliant}</td>
                    <td className="px-4 py-3 text-center font-mono text-blue-700">{cat.pending}</td>
                    <td className="px-4 py-3 text-center font-mono text-amber-700">{cat.deficient}</td>
                    <td className="px-4 py-3 text-center font-mono text-red-700 font-bold">{cat.overdue}</td>
                    <td className="px-4 py-3 text-center">
                      <span
                        className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold ${
                          compRate >= 75
                            ? 'bg-emerald-100 text-emerald-800'
                            : compRate >= 50
                            ? 'bg-amber-100 text-amber-800'
                            : 'bg-red-100 text-red-800'
                        }`}
                      >
                        {compRate}%
                      </span>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
