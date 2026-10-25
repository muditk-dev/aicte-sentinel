import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { applicationService } from '../services/applicationService'
import { authService } from '../services/authService'
import { auditService } from '../services/auditService'
import { StatCard } from '../components/StatCard'
import { StatusBadge } from '../components/StatusBadge'
import { formatDate } from '../lib/utils'
import {
  FileText,
  Clock,
  AlertTriangle,
  CheckCircle2,
  ShieldCheck,
  ArrowUpRight,
  Info,
} from 'lucide-react'

export const DashboardPage: React.FC = () => {
  const user = authService.getCurrentUser()

  const { data: applications = [], isLoading } = useQuery({
    queryKey: ['applications'],
    queryFn: () => applicationService.listApplications(),
  })

  const { data: auditVerify } = useQuery({
    queryKey: ['audit-verify'],
    queryFn: () => auditService.verifyLedger(),
  })

  // Calculations
  const totalApps = applications.length
  const underScrutiny = applications.filter((a) => a.current_status === 'UNDER_SCRUTINY').length
  const deficiencies = applications.filter((a) => a.current_status === 'DEFICIENCY_ISSUED').length
  const approved = applications.filter((a) => a.current_status === 'APPROVED').length

  return (
    <div className="space-y-6">
      {/* Welcome Banner */}
      <div className="bg-white rounded-lg border border-slate-200 p-6 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-xl font-bold text-slate-900">
              Regulatory Command Center
            </h1>
            <span className="text-xs px-2 py-0.5 rounded font-semibold bg-blue-100 text-blue-800 border border-blue-200">
              APH 2026-27 Active Cycle
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Logged in as <span className="font-semibold text-slate-800">{user?.full_name}</span> ({user?.roles[0]?.name || 'Officer'})
            {user?.assigned_region && ` • Region: ${user.assigned_region}`}
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <Link
            to="/applications"
            className="inline-flex items-center px-4 py-2 text-xs font-semibold rounded-md text-white bg-blue-700 hover:bg-blue-800 shadow-sm transition-colors"
          >
            <FileText className="w-4 h-4 mr-1.5" />
            Manage Applications
          </Link>
          <Link
            to="/audit"
            className="inline-flex items-center px-4 py-2 text-xs font-semibold rounded-md text-slate-700 bg-white border border-slate-300 hover:bg-slate-50 shadow-sm transition-colors"
          >
            <ShieldCheck className="w-4 h-4 mr-1.5 text-blue-700" />
            Verify Audit Ledger
          </Link>
        </div>
      </div>

      {/* KPI Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Active Dockets"
          value={totalApps}
          subtitle="Statutory applications in cycle"
          icon={FileText}
          tone="default"
        />
        <StatCard
          title="Under Scrutiny"
          value={underScrutiny}
          subtitle="Document verification active"
          icon={Clock}
          tone="accent"
        />
        <StatCard
          title="Deficiencies Pending"
          value={deficiencies}
          subtitle="Awaiting institute resubmission"
          icon={AlertTriangle}
          tone="warning"
        />
        <StatCard
          title="Approvals Granted"
          value={approved}
          subtitle="Final council authorization"
          icon={CheckCircle2}
          tone="success"
        />
      </div>

      {/* Integrity & Compliance Intelligence Banner */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Audit Status */}
        <div className="bg-white rounded-lg border border-slate-200 p-5 shadow-sm lg:col-span-1">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-600 flex items-center">
              <ShieldCheck className="w-4 h-4 mr-1.5 text-blue-700" />
              Cryptographic Integrity
            </h3>
            <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-800 border border-emerald-200">
              SHA-256 Chained
            </span>
          </div>

          <div className="mt-4 space-y-3">
            <div className="flex justify-between items-center text-xs">
              <span className="text-slate-500">Audit Chain Health:</span>
              <span className="font-semibold text-emerald-700 flex items-center">
                <CheckCircle2 className="w-3.5 h-3.5 mr-1" />
                {auditVerify?.is_valid ? 'Valid & Untampered' : 'Verifying...'}
              </span>
            </div>
            <div className="flex justify-between items-center text-xs">
              <span className="text-slate-500">Chained Records:</span>
              <span className="font-mono font-semibold text-slate-800">
                {auditVerify?.total_events_checked ?? '—'} events
              </span>
            </div>
            <div className="flex justify-between items-start text-xs">
              <span className="text-slate-500">Chain Head Hash:</span>
              <span className="font-mono text-[10px] text-slate-700 bg-slate-50 p-1 rounded border border-slate-200 truncate max-w-[170px]">
                {auditVerify?.chain_head_hash || '0000...genesis'}
              </span>
            </div>

            <div className="pt-2">
              <Link
                to="/audit"
                className="w-full text-center block py-1.5 px-3 rounded text-xs font-medium text-blue-700 bg-blue-50 border border-blue-200 hover:bg-blue-100 transition-colors"
              >
                Inspect Full Audit Trail
              </Link>
            </div>
          </div>
        </div>

        {/* Explainable Delay Risk Notice (Advisory Only) */}
        <div className="bg-white rounded-lg border border-slate-200 p-5 shadow-sm lg:col-span-2">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-600 flex items-center">
              <AlertTriangle className="w-4 h-4 mr-1.5 text-amber-600" />
              Compliance Intelligence & Delay-Risk Indicators
            </h3>
            <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-amber-100 text-amber-900 border border-amber-200">
              Advisory Intelligence
            </span>
          </div>

          <div className="mt-3">
            <div className="bg-amber-50 border border-amber-200 rounded p-2.5 text-xs text-amber-900 flex items-start space-x-2">
              <Info className="w-4 h-4 text-amber-700 flex-shrink-0 mt-0.5" />
              <p className="text-[11px] leading-relaxed">
                <strong>Statutory Guardrail Notice:</strong> Risk scores are statistical guidance derived from document completeness and regional historical SLAs. AI does NOT make statutory approval decisions, mutate workflow states, or replace officer scrutiny.
              </p>
            </div>

            <div className="mt-4 space-y-2.5">
              {applications.slice(0, 2).map((app) => {
                let factors: any[] = []
                try {
                  factors = JSON.parse(app.delay_risk_factors_json || '[]')
                } catch {
                  factors = []
                }
                const score = app.delay_risk_score || 0
                return (
                  <div
                    key={app.id}
                    className="p-3 rounded border border-slate-200 bg-slate-50 flex items-center justify-between"
                  >
                    <div>
                      <div className="flex items-center space-x-2">
                        <span className="font-mono text-xs font-bold text-slate-900">
                          {app.application_number}
                        </span>
                        <StatusBadge status={app.current_status} />
                      </div>
                      <p className="text-[11px] text-slate-600 mt-1">
                        Risk Factor: {factors[0]?.factor || 'Standard scrutiny queue'} • {factors[0]?.detail || 'No immediate bottlenecks detected'}
                      </p>
                    </div>

                    <div className="text-right">
                      <div className="text-xs font-bold text-slate-800">
                        {(score * 100).toFixed(0)}% Risk
                      </div>
                      <span className={`text-[10px] font-semibold uppercase px-1.5 py-0.5 rounded ${
                        score > 0.5 ? 'bg-rose-100 text-rose-800' : 'bg-emerald-100 text-emerald-800'
                      }`}>
                        {score > 0.5 ? 'Elevated' : 'Nominal'}
                      </span>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      </div>

      {/* Recent Applications Table */}
      <div className="bg-white rounded-lg border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-200 flex justify-between items-center bg-slate-50">
          <div>
            <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
              Recent Application Dockets
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Live statutory lifecycle status across all jurisdictional dockets
            </p>
          </div>
          <Link
            to="/applications"
            className="text-xs font-semibold text-blue-700 hover:text-blue-900 flex items-center"
          >
            View Complete Registry
            <ArrowUpRight className="w-3.5 h-3.5 ml-1" />
          </Link>
        </div>

        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200 text-left text-xs">
            <thead className="bg-slate-100 text-slate-600 font-bold uppercase tracking-wider">
              <tr>
                <th className="px-6 py-3">Docket Number</th>
                <th className="px-6 py-3">Academic Cycle</th>
                <th className="px-6 py-3">Current Statutory State</th>
                <th className="px-6 py-3">Delay Risk</th>
                <th className="px-6 py-3">Submission Timestamp</th>
                <th className="px-6 py-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 bg-white">
              {isLoading ? (
                <tr>
                  <td colSpan={6} className="px-6 py-8 text-center text-slate-500">
                    Loading statutory applications...
                  </td>
                </tr>
              ) : applications.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-6 py-8 text-center text-slate-500">
                    No application dockets found.
                  </td>
                </tr>
              ) : (
                applications.slice(0, 5).map((app) => (
                  <tr key={app.id} className="hover:bg-slate-50 transition-colors">
                    <td className="px-6 py-4 font-mono font-semibold text-blue-700">
                      {app.application_number}
                    </td>
                    <td className="px-6 py-4 text-slate-700">{app.academic_year}</td>
                    <td className="px-6 py-4">
                      <StatusBadge status={app.current_status} />
                    </td>
                    <td className="px-6 py-4 font-medium text-slate-700">
                      {((app.delay_risk_score || 0) * 100).toFixed(0)}%
                    </td>
                    <td className="px-6 py-4 text-slate-500 font-mono text-[11px]">
                      {formatDate(app.created_at)}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <Link
                        to={`/applications/${app.id}`}
                        className="text-xs font-semibold text-blue-700 hover:underline"
                      >
                        Inspect Docket →
                      </Link>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
