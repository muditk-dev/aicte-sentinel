import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { complianceService } from '../services/complianceService'
import { authService } from '../services/authService'
import { formatDate } from '../lib/utils'
import {
  AlertOctagon,
  ShieldAlert,
  RefreshCw,
  CheckCircle2,
  ExternalLink,
} from 'lucide-react'

export const NotificationsEscalationsPage: React.FC = () => {
  const queryClient = useQueryClient()
  const user = authService.getCurrentUser()
  const isOfficerOrAdmin = user?.roles.some((r) =>
    ['SUPER_ADMIN', 'ADMIN', 'REGIONAL_OFFICER', 'SCRUTINY_OFFICER'].includes(r.code)
  )

  const [unresolvedOnly, setUnresolvedOnly] = useState<boolean>(false)

  // Fetch Escalations
  const { data: escalations = [], isLoading, refetch } = useQuery({
    queryKey: ['compliance-escalations', unresolvedOnly],
    queryFn: () => complianceService.listEscalations(unresolvedOnly),
  })

  // Manual Trigger Worker Mutation
  const triggerMutation = useMutation({
    mutationFn: () => complianceService.triggerMonitoringWorker(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['compliance-escalations'] })
      queryClient.invalidateQueries({ queryKey: ['compliance-summary'] })
      queryClient.invalidateQueries({ queryKey: ['compliance-obligations'] })
    },
  })

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight flex items-center">
            <AlertOctagon className="w-6 h-6 mr-2 text-amber-600" />
            Compliance Escalations & Notifications
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Automated statutory reminders, Level 1 (Regional) and Level 2 (Central) overdue escalation alerts
          </p>
        </div>

        <div className="flex items-center space-x-2">
          {isOfficerOrAdmin && (
            <button
              onClick={() => triggerMutation.mutate()}
              disabled={triggerMutation.isPending}
              className="inline-flex items-center px-3 py-1.5 text-xs font-semibold text-slate-700 bg-white border border-slate-300 rounded hover:bg-slate-50 disabled:opacity-50 shadow-sm"
              title="Runs periodic evaluation task to check overdue obligations and trigger escalations"
            >
              <RefreshCw className={`w-3.5 h-3.5 mr-1.5 ${triggerMutation.isPending ? 'animate-spin' : ''}`} />
              Run Monitor Cycle
            </button>
          )}

          <button
            onClick={() => refetch()}
            className="p-1.5 text-slate-600 hover:text-slate-900 bg-white border border-slate-300 rounded shadow-sm"
            title="Refresh escalations"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Trigger Feedback Banner */}
      {triggerMutation.isSuccess && (
        <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-lg text-xs flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
            <span>{triggerMutation.data.message}</span>
          </div>
          <span className="font-mono text-[10px] text-emerald-600">{triggerMutation.data.timestamp}</span>
        </div>
      )}

      {/* Filter Toolbar */}
      <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm flex items-center justify-between text-xs">
        <label className="flex items-center space-x-2 cursor-pointer">
          <input
            type="checkbox"
            checked={unresolvedOnly}
            onChange={(e) => setUnresolvedOnly(e.target.checked)}
            className="rounded text-blue-600 focus:ring-0"
          />
          <span className="font-semibold text-slate-700">Filter Unresolved Escalations Only</span>
        </label>

        <span className="text-slate-500 font-mono text-[11px]">
          Total Recorded Escalations: {escalations.length}
        </span>
      </div>

      {/* Escalation Cards List */}
      <div className="space-y-4">
        {isLoading ? (
          <div className="bg-white p-8 rounded-lg border border-slate-200 text-center text-slate-400">
            <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-amber-600" />
            Loading escalation register...
          </div>
        ) : escalations.length === 0 ? (
          <div className="bg-white p-12 rounded-lg border border-slate-200 text-center">
            <CheckCircle2 className="w-10 h-10 text-emerald-500 mx-auto mb-3" />
            <h3 className="text-sm font-bold text-slate-800">Zero Active Escalations</h3>
            <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
              No statutory compliance dockets are currently escalated or in severe default.
            </p>
          </div>
        ) : (
          escalations.map((esc) => {
            const isLevel2 = esc.escalation_level === 2
            let notifiedRoles: string[] = []
            try {
              notifiedRoles = JSON.parse(esc.notified_roles_json || '[]')
            } catch {
              notifiedRoles = []
            }

            return (
              <div
                key={esc.id}
                className={`p-5 rounded-lg border shadow-sm transition-all bg-white ${
                  isLevel2 ? 'border-red-300 ring-1 ring-red-100' : 'border-amber-300 ring-1 ring-amber-100'
                }`}
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 pb-3 text-xs">
                  <div className="flex items-center space-x-2">
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                        isLevel2 ? 'bg-red-100 text-red-800' : 'bg-amber-100 text-amber-800'
                      }`}
                    >
                      {isLevel2 ? 'Level 2: Central Authority' : 'Level 1: Regional Officer'}
                    </span>

                    <span className="font-mono text-[11px] text-slate-400">
                      Trigger: {esc.trigger_reason}
                    </span>

                    <span className="px-1.5 py-0.2 bg-slate-100 text-slate-600 rounded text-[9px] font-mono">
                      IN_APP_DELIVERED
                    </span>
                  </div>

                  <span className="font-mono text-[11px] text-slate-500">
                    Recorded: {formatDate(esc.created_at)}
                  </span>
                </div>

                <div className="mt-3 flex flex-col md:flex-row md:items-center justify-between gap-4">
                  <div className="space-y-1 text-xs">
                    <h3 className="text-sm font-bold text-slate-900 flex items-center">
                      <ShieldAlert className={`w-4 h-4 mr-1.5 ${isLevel2 ? 'text-red-600' : 'text-amber-600'}`} />
                      Compliance Default Overdue for {esc.days_overdue} Days
                    </h3>

                    <p className="text-slate-600">
                      Institutional statutory cure window expired. Supervisory alerts dispatched to regional desk.
                    </p>

                    <div className="flex items-center space-x-2 pt-1 text-[11px] text-slate-500">
                      <span>Notified Roles:</span>
                      <div className="flex gap-1">
                        {notifiedRoles.map((r) => (
                          <span key={r} className="px-1.5 py-0.5 rounded bg-slate-100 text-slate-700 font-mono text-[10px]">
                            {r}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center space-x-2">
                    <Link
                      to={`/compliance/obligations/${esc.obligation_id}`}
                      className="px-3 py-1.5 text-xs font-semibold text-blue-700 bg-blue-50 hover:bg-blue-100 rounded border border-blue-200 transition-colors inline-flex items-center"
                    >
                      Review Docket
                      <ExternalLink className="w-3.5 h-3.5 ml-1.5" />
                    </Link>
                  </div>
                </div>
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
