import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { CheckCircle2, Server, Database, RefreshCw } from 'lucide-react'

export const DiagnosticsPage: React.FC = () => {
  const {
    data: health,
    refetch: refetchHealth,
  } = useQuery({
    queryKey: ['health'],
    queryFn: async () => {
      const res = await fetch('/api/health')
      return res.json()
    },
    refetchInterval: 10000,
  })

  const {
    data: ready,
    refetch: refetchReady,
  } = useQuery({
    queryKey: ['ready'],
    queryFn: async () => {
      const res = await fetch('/api/ready')
      return res.json()
    },
    refetchInterval: 10000,
  })

  const refreshAll = () => {
    refetchHealth()
    refetchReady()
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">
            System Health & Dependency Diagnostics
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Real-time liveness and readiness probes monitoring database connectivity and core services
          </p>
        </div>

        <button
          onClick={refreshAll}
          className="inline-flex items-center px-4 py-2 border border-slate-300 rounded-md shadow-sm text-xs font-semibold text-slate-700 bg-white hover:bg-slate-50 transition-colors"
        >
          <RefreshCw className="w-3.5 h-3.5 mr-1.5" />
          Poll Probes
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Liveness Probe */}
        <div className="bg-white rounded-lg border border-slate-200 p-6 shadow-sm">
          <div className="flex items-center justify-between pb-4 border-b border-slate-100">
            <div className="flex items-center space-x-3">
              <div className="p-2 rounded bg-blue-50 text-blue-700">
                <Server className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-slate-900">API Liveness Probe</h3>
                <span className="font-mono text-xs text-slate-500">GET /api/health</span>
              </div>
            </div>

            <span className="text-xs font-bold px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 border border-emerald-200 flex items-center">
              <CheckCircle2 className="w-3.5 h-3.5 mr-1" />
              {health?.status || 'HEALTHY'}
            </span>
          </div>

          <div className="mt-4 space-y-2 text-xs">
            <div className="flex justify-between py-1 border-b border-slate-100">
              <span className="text-slate-500">Service:</span>
              <span className="font-semibold text-slate-800">{health?.service || 'AICTE Sentinel'}</span>
            </div>
            <div className="flex justify-between py-1 border-b border-slate-100">
              <span className="text-slate-500">Version:</span>
              <span className="font-mono text-slate-800">{health?.version || '1.0.0'}</span>
            </div>
            <div className="flex justify-between py-1 border-b border-slate-100">
              <span className="text-slate-500">Environment:</span>
              <span className="font-mono uppercase text-slate-800">{health?.environment || 'development'}</span>
            </div>
            <div className="flex justify-between py-1">
              <span className="text-slate-500">Timestamp:</span>
              <span className="font-mono text-[11px] text-slate-700">{health?.timestamp || '—'}</span>
            </div>
          </div>
        </div>

        {/* Readiness Probe */}
        <div className="bg-white rounded-lg border border-slate-200 p-6 shadow-sm">
          <div className="flex items-center justify-between pb-4 border-b border-slate-100">
            <div className="flex items-center space-x-3">
              <div className="p-2 rounded bg-indigo-50 text-indigo-700">
                <Database className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-slate-900">Dependency Readiness</h3>
                <span className="font-mono text-xs text-slate-500">GET /api/ready</span>
              </div>
            </div>

            <span className="text-xs font-bold px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 border border-emerald-200 flex items-center">
              <CheckCircle2 className="w-3.5 h-3.5 mr-1" />
              {ready?.status || 'READY'}
            </span>
          </div>

          <div className="mt-4 space-y-2 text-xs">
            <div className="flex justify-between py-1 border-b border-slate-100">
              <span className="text-slate-500">Database Connectivity:</span>
              <span className="font-semibold text-emerald-700 flex items-center">
                <CheckCircle2 className="w-3.5 h-3.5 mr-1" />
                {ready?.dependencies?.database?.healthy ? 'Connected' : 'Unavailable'}
              </span>
            </div>
            <div className="flex justify-between py-1 border-b border-slate-100">
              <span className="text-slate-500">Database Dialect:</span>
              <span className="font-mono uppercase text-slate-800">
                {ready?.dependencies?.database?.dialect || 'sqlite'}
              </span>
            </div>
            <div className="flex justify-between py-1 border-b border-slate-100">
              <span className="text-slate-500">Object Storage Provider:</span>
              <span className="font-semibold text-slate-800">
                {ready?.dependencies?.storage?.provider || 'MinIO / S3'}
              </span>
            </div>
            <div className="flex justify-between py-1">
              <span className="text-slate-500">Last Probe Check:</span>
              <span className="font-mono text-[11px] text-slate-700">{ready?.timestamp || '—'}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
