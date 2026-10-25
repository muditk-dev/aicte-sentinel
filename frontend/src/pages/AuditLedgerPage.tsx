import React from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { auditService } from '../services/auditService'
import { formatDate } from '../lib/utils'
import { ShieldCheck, RefreshCw } from 'lucide-react'

export const AuditLedgerPage: React.FC = () => {
  const queryClient = useQueryClient()

  const { data: auditEvents = [], isLoading: eventsLoading } = useQuery({
    queryKey: ['audit-events'],
    queryFn: () => auditService.listEvents(50),
  })

  const { data: verification } = useQuery({
    queryKey: ['audit-verify'],
    queryFn: () => auditService.verifyLedger(),
  })

  const recheckMutation = useMutation({
    mutationFn: () => auditService.verifyLedger(),
    onSuccess: (data) => {
      queryClient.setQueryData(['audit-verify'], data)
    },
  })

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">
            Tamper-Evident Cryptographic Audit Ledger
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Immutable SHA-256 hash-chained statutory event log with automated continuous verification
          </p>
        </div>

        <button
          onClick={() => recheckMutation.mutate()}
          disabled={recheckMutation.isPending}
          className="inline-flex items-center px-4 py-2 border border-slate-300 rounded-md shadow-sm text-xs font-semibold text-slate-700 bg-white hover:bg-slate-50 disabled:opacity-50 transition-colors"
        >
          <RefreshCw className={`w-3.5 h-3.5 mr-1.5 ${recheckMutation.isPending ? 'animate-spin' : ''}`} />
          Run Cryptographic Hash Check
        </button>
      </div>

      {/* Verification Health Panel */}
      <div className="bg-white rounded-lg border border-slate-200 p-6 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-100">
          <div className="flex items-center space-x-3">
            <div className="p-2.5 rounded-lg bg-emerald-50 text-emerald-700 border border-emerald-200">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-slate-900 flex items-center space-x-2">
                <span>Cryptographic Chain Status:</span>
                <span className="text-emerald-700 font-extrabold uppercase">
                  {verification?.is_valid ? 'Verified Untampered' : 'Integrity Issue'}
                </span>
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                {verification?.verification_message || 'Validating cryptographic block hashes...'}
              </p>
            </div>
          </div>

          <div className="text-left sm:text-right">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 block">
              Total Sequenced Records
            </span>
            <span className="font-mono text-base font-bold text-slate-800">
              {verification?.total_events_checked ?? '0'} Events Verified
            </span>
          </div>
        </div>

        <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          <div className="p-3 rounded bg-slate-50 border border-slate-200">
            <span className="text-slate-500 font-semibold block mb-1">
              Active Chain Head SHA-256 Hash
            </span>
            <span className="font-mono text-[11px] text-slate-800 break-all select-all">
              {verification?.chain_head_hash || '0000000000000000000000000000000000000000000000000000000000000000'}
            </span>
          </div>
          <div className="p-3 rounded bg-slate-50 border border-slate-200">
            <span className="text-slate-500 font-semibold block mb-1">
              Public Ledger Verification Guarantee
            </span>
            <p className="text-[11px] text-slate-600 leading-relaxed">
              Every statutory transition is cryptographically bound to its predecessor via SHA-256 chaining. Any database modification or sequence deletion immediately breaks the chain.
            </p>
          </div>
        </div>
      </div>

      {/* Audit Log Table */}
      <div className="bg-white rounded-lg border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-200 bg-slate-50">
          <h2 className="text-xs font-bold uppercase tracking-wider text-slate-700">
            Chronological Audit Ledger Trail (Recent 50 Events)
          </h2>
        </div>

        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200 text-left text-xs">
            <thead className="bg-slate-100 text-slate-600 font-bold uppercase tracking-wider">
              <tr>
                <th className="px-4 py-3">Seq #</th>
                <th className="px-4 py-3">Timestamp</th>
                <th className="px-4 py-3">Action</th>
                <th className="px-4 py-3">Actor ID</th>
                <th className="px-4 py-3">Target Resource</th>
                <th className="px-4 py-3 font-mono">Entry Hash (SHA-256)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 bg-white">
              {eventsLoading ? (
                <tr>
                  <td colSpan={6} className="px-6 py-8 text-center text-slate-500">
                    Loading audit trail...
                  </td>
                </tr>
              ) : auditEvents.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-6 py-8 text-center text-slate-500">
                    No audit records recorded yet.
                  </td>
                </tr>
              ) : (
                auditEvents.map((event) => (
                  <tr key={event.id} className="hover:bg-slate-50 transition-colors font-mono text-[11px]">
                    <td className="px-4 py-3 font-bold text-slate-900">
                      #{event.sequence_number}
                    </td>
                    <td className="px-4 py-3 text-slate-600 whitespace-nowrap">
                      {formatDate(event.created_at)}
                    </td>
                    <td className="px-4 py-3">
                      <span className="font-sans font-semibold text-blue-700 bg-blue-50 px-2 py-0.5 rounded border border-blue-200">
                        {event.action}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-700 font-sans truncate max-w-[150px]">
                      {event.actor_id}
                    </td>
                    <td className="px-4 py-3 text-slate-700 font-sans">
                      {event.resource_type} ({event.resource_id.substring(0, 8)}...)
                    </td>
                    <td className="px-4 py-3 text-slate-600 text-[10px] truncate max-w-[200px]" title={event.entry_hash}>
                      {event.entry_hash.substring(0, 16)}...{event.entry_hash.substring(48)}
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
