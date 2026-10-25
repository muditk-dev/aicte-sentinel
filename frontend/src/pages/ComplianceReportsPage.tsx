import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { complianceService } from '../services/complianceService'
import { formatDate } from '../lib/utils'
import {
  Download,
  CheckCircle2,
  RefreshCw,
  BarChart3,
  ExternalLink,
  ShieldCheck,
} from 'lucide-react'

export const ComplianceReportsPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'INSTITUTIONS' | 'DEFICIENCIES' | 'SUMMARY'>('INSTITUTIONS')
  const [regionFilter, setRegionFilter] = useState<string>('')

  // Summary Report
  const { data: summary } = useQuery({
    queryKey: ['compliance-summary-report'],
    queryFn: () => complianceService.getSummaryReport(),
  })

  // Institution Breakdown
  const { data: institutions = [], isLoading: loadingInst } = useQuery({
    queryKey: ['compliance-institution-reports', regionFilter],
    queryFn: () => complianceService.getInstitutionReports(regionFilter || undefined),
    enabled: activeTab === 'INSTITUTIONS',
  })

  // Deficiencies Review Queue
  const { data: deficiencies = [], isLoading: loadingDef } = useQuery({
    queryKey: ['compliance-deficiencies-report'],
    queryFn: () => complianceService.getDeficienciesReport(),
    enabled: activeTab === 'DEFICIENCIES',
  })

  const exportUrl = complianceService.getExportCSVUrl()

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight flex items-center">
            <BarChart3 className="w-6 h-6 mr-2 text-blue-700" />
            Statutory Compliance Reports & Analytics
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            M16: Institution compliance rankings, outstanding deficiency queues, and formula-injection-safe CSV exports
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <a
            href={exportUrl}
            download
            className="inline-flex items-center px-3 py-1.5 text-xs font-semibold text-white bg-emerald-700 hover:bg-emerald-800 rounded shadow-sm transition-colors"
          >
            <Download className="w-3.5 h-3.5 mr-1.5" />
            Export Compliance CSV
          </a>
        </div>
      </div>

      {/* OWASP & Transparency Notice */}
      <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg flex items-start space-x-2 text-xs text-slate-600">
        <ShieldCheck className="w-4 h-4 text-emerald-600 flex-shrink-0 mt-0.5" />
        <div>
          <span className="font-bold text-slate-800">Security & Reporting Policy:</span> All CSV downloads are sanitized against OWASP spreadsheet formula injection (leading '=', '+', '-', '@' characters safely escaped with apostrophe). Synthetic demonstration records are explicitly labeled.
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-slate-200 flex space-x-6 text-xs font-semibold">
        <button
          onClick={() => setActiveTab('INSTITUTIONS')}
          className={`pb-2.5 transition-colors border-b-2 ${
            activeTab === 'INSTITUTIONS'
              ? 'border-blue-700 text-blue-700'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          Institution Compliance Ratings
        </button>

        <button
          onClick={() => setActiveTab('DEFICIENCIES')}
          className={`pb-2.5 transition-colors border-b-2 ${
            activeTab === 'DEFICIENCIES'
              ? 'border-blue-700 text-blue-700'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          Outstanding Deficiencies Queue
        </button>

        <button
          onClick={() => setActiveTab('SUMMARY')}
          className={`pb-2.5 transition-colors border-b-2 ${
            activeTab === 'SUMMARY'
              ? 'border-blue-700 text-blue-700'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          Norm Category Summary
        </button>
      </div>

      {/* Tab 1: Institution Compliance Ratings */}
      {activeTab === 'INSTITUTIONS' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between bg-white p-3 rounded-lg border border-slate-200 shadow-sm text-xs">
            <span className="text-slate-500">Filter by Regional Jurisdiction:</span>
            <select
              value={regionFilter}
              onChange={(e) => setRegionFilter(e.target.value)}
              className="px-2.5 py-1 border border-slate-300 rounded bg-white text-slate-700"
            >
              <option value="">All Regions</option>
              <option value="Northern">Northern Region</option>
              <option value="Western">Western Region</option>
              <option value="Southern">Southern Region</option>
              <option value="Eastern">Eastern Region</option>
              <option value="Central">Central Region</option>
            </select>
          </div>

          <div className="bg-white rounded-lg border border-slate-200 shadow-sm overflow-hidden">
            {loadingInst ? (
              <div className="p-8 text-center text-slate-400">
                <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-blue-600" />
                Aggregating institutional records...
              </div>
            ) : institutions.length === 0 ? (
              <div className="p-8 text-center text-slate-500 text-xs">No institutional records found.</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-slate-200 text-xs">
                  <thead className="bg-slate-50">
                    <tr>
                      <th className="px-4 py-2.5 text-left font-bold text-slate-700 uppercase">Institution Name & Code</th>
                      <th className="px-4 py-2.5 text-left font-bold text-slate-700 uppercase">Region / State</th>
                      <th className="px-4 py-2.5 text-center font-bold text-slate-700 uppercase">Total Dockets</th>
                      <th className="px-4 py-2.5 text-center font-bold text-emerald-700 uppercase">Compliant</th>
                      <th className="px-4 py-2.5 text-center font-bold text-blue-700 uppercase">Pending</th>
                      <th className="px-4 py-2.5 text-center font-bold text-amber-700 uppercase">Deficient</th>
                      <th className="px-4 py-2.5 text-center font-bold text-red-700 uppercase">Overdue</th>
                      <th className="px-4 py-2.5 text-center font-bold text-slate-700 uppercase">Compliance %</th>
                      <th className="px-4 py-2.5 text-center font-bold text-slate-700 uppercase">Standing</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {institutions.map((item) => (
                      <tr key={item.institution_id} className="hover:bg-slate-50/70">
                        <td className="px-4 py-3">
                          <span className="font-bold text-slate-900 block">{item.institution_name}</span>
                          <span className="text-[10px] font-mono text-slate-400">Code: {item.institution_code}</span>
                        </td>

                        <td className="px-4 py-3 text-slate-600">
                          <span>{item.region}</span>
                          <span className="text-[10px] text-slate-400 block">{item.state}</span>
                        </td>

                        <td className="px-4 py-3 text-center font-mono font-semibold text-slate-800">{item.total_obligations}</td>
                        <td className="px-4 py-3 text-center font-mono font-bold text-emerald-700">{item.compliant_count}</td>
                        <td className="px-4 py-3 text-center font-mono text-blue-700">{item.pending_count}</td>
                        <td className="px-4 py-3 text-center font-mono text-amber-700">{item.deficient_count}</td>
                        <td className="px-4 py-3 text-center font-mono font-bold text-red-700">{item.overdue_count}</td>

                        <td className="px-4 py-3 text-center">
                          <span
                            className={`font-mono font-bold text-xs ${
                              item.compliance_percentage >= 80
                                ? 'text-emerald-700'
                                : item.compliance_percentage >= 50
                                ? 'text-amber-700'
                                : 'text-red-700'
                            }`}
                          >
                            {item.compliance_percentage}%
                          </span>
                        </td>

                        <td className="px-4 py-3 text-center">
                          {item.is_fully_compliant ? (
                            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-200">
                              Fully Compliant
                            </span>
                          ) : item.overdue_count > 0 ? (
                            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-red-100 text-red-800 border border-red-200">
                              Default Notice
                            </span>
                          ) : (
                            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-800 border border-amber-200">
                              Active Action
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tab 2: Outstanding Deficiencies Queue */}
      {activeTab === 'DEFICIENCIES' && (
        <div className="bg-white rounded-lg border border-slate-200 shadow-sm overflow-hidden">
          {loadingDef ? (
            <div className="p-8 text-center text-slate-400">
              <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-amber-600" />
              Loading deficiency queue...
            </div>
          ) : deficiencies.length === 0 ? (
            <div className="p-12 text-center">
              <CheckCircle2 className="w-10 h-10 text-emerald-500 mx-auto mb-3" />
              <h3 className="text-sm font-bold text-slate-800">Deficiency Queue Clear</h3>
              <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
                No institutions are currently overdue or pending deficiency cure verification.
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-slate-200 text-xs">
                <thead className="bg-slate-50">
                  <tr>
                    <th className="px-4 py-2.5 text-left font-bold text-slate-700 uppercase">Obligation</th>
                    <th className="px-4 py-2.5 text-left font-bold text-slate-700 uppercase">Institution</th>
                    <th className="px-4 py-2.5 text-left font-bold text-slate-700 uppercase">Norm Category</th>
                    <th className="px-4 py-2.5 text-left font-bold text-slate-700 uppercase">Due Date</th>
                    <th className="px-4 py-2.5 text-center font-bold text-red-700 uppercase">Days Overdue</th>
                    <th className="px-4 py-2.5 text-left font-bold text-slate-700 uppercase">Last Scrutiny Finding</th>
                    <th className="px-4 py-2.5 text-right font-bold text-slate-700 uppercase">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {deficiencies.map((d) => (
                    <tr key={d.obligation_id} className="hover:bg-slate-50/70">
                      <td className="px-4 py-3">
                        <span className="font-mono text-[10px] font-bold text-blue-800 block">{d.obligation_code}</span>
                        <span className="font-semibold text-slate-900">{d.title}</span>
                      </td>

                      <td className="px-4 py-3">
                        <span className="font-semibold text-slate-800 block">{d.institution_name}</span>
                        <span className="text-[10px] text-slate-400">Reviewer: {d.assigned_officer_name}</span>
                      </td>

                      <td className="px-4 py-3 text-slate-600">
                        <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-700 font-medium text-[10px]">
                          {d.category.replace('_', ' ')}
                        </span>
                        <span className="text-[10px] text-slate-400 font-mono block mt-0.5">{d.source_reference}</span>
                      </td>

                      <td className="px-4 py-3 font-mono text-slate-700">{formatDate(d.due_date)}</td>

                      <td className="px-4 py-3 text-center">
                        <span className="px-2 py-0.5 rounded font-mono font-bold text-xs bg-red-100 text-red-800">
                          +{d.days_overdue} d
                        </span>
                      </td>

                      <td className="px-4 py-3 text-slate-600 max-w-xs truncate" title={d.last_review_comments || ''}>
                        {d.last_review_comments || 'Under statutory review'}
                      </td>

                      <td className="px-4 py-3 text-right">
                        <Link
                          to={`/compliance/obligations/${d.obligation_id}`}
                          className="inline-flex items-center px-2 py-1 text-xs font-semibold text-blue-700 bg-blue-50 hover:bg-blue-100 rounded border border-blue-200"
                        >
                          Scrutinize
                          <ExternalLink className="w-3 h-3 ml-1" />
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Tab 3: Norm Category Summary */}
      {activeTab === 'SUMMARY' && (
        <div className="bg-white rounded-lg border border-slate-200 shadow-sm p-6 space-y-4">
          <h2 className="text-sm font-bold text-slate-900 tracking-tight">AICTE Approval Process Handbook Norm Categories</h2>
          {summary && (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {summary.categories_breakdown.map((cat) => (
                <div key={cat.category} className="p-4 rounded-lg bg-slate-50 border border-slate-200 text-xs space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-slate-900">{cat.category.replace('_', ' ')}</span>
                    <span className="font-mono text-slate-500 font-bold">{cat.total} total</span>
                  </div>

                  <div className="grid grid-cols-2 gap-2 text-[11px] pt-1 border-t border-slate-200">
                    <span className="text-emerald-700">Compliant: {cat.compliant}</span>
                    <span className="text-blue-700">Pending: {cat.pending}</span>
                    <span className="text-amber-700">Deficient: {cat.deficient}</span>
                    <span className="text-red-700 font-bold">Overdue: {cat.overdue}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
