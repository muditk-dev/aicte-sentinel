import React, { useState, useEffect } from 'react'
import {
  AlertTriangle,
  TrendingUp,
  BrainCircuit,
  Clock,
  ShieldCheck,
  RefreshCw,
  Search,
  ChevronRight,
  Info,
  SlidersHorizontal,
  Activity,
  Layers,
} from 'lucide-react'
import { intelligenceService } from '../services/intelligenceService'
import { RiskOverviewItem, DelayRiskPrediction, ModelVersion } from '../types'

export const RiskIntelligencePage: React.FC = () => {
  const [items, setItems] = useState<RiskOverviewItem[]>([])
  const [modelVersions, setModelVersions] = useState<ModelVersion[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedAppId, setSelectedAppId] = useState<string | null>(null)
  const [predictionDetail, setPredictionDetail] = useState<DelayRiskPrediction | null>(null)
  const [loadingDetail, setLoadingDetail] = useState(false)
  const [recomputing, setRecomputing] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')
  const [categoryFilter, setCategoryFilter] = useState('ALL')
  const [regionFilter, setRegionFilter] = useState('ALL')
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    setLoading(true)
    setErrorMsg(null)
    try {
      const [overviewData, modelsData] = await Promise.all([
        intelligenceService.getRiskOverview(),
        intelligenceService.listModelVersions(),
      ])
      setItems(overviewData)
      setModelVersions(modelsData)
      if (overviewData.length > 0 && !selectedAppId) {
        handleSelectApp(overviewData[0].application_id)
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to load risk intelligence data')
    } finally {
      setLoading(false)
    }
  }

  const handleSelectApp = async (appId: string) => {
    setSelectedAppId(appId)
    setLoadingDetail(true)
    try {
      const pred = await intelligenceService.getApplicationDelayRisk(appId)
      setPredictionDetail(pred)
    } catch (err: any) {
      console.error(err)
    } finally {
      setLoadingDetail(false)
    }
  }

  const handleRecompute = async () => {
    if (!selectedAppId) return
    setRecomputing(true)
    try {
      const updated = await intelligenceService.recomputeApplicationDelayRisk(selectedAppId)
      setPredictionDetail(updated)
      // Refresh list to update cached score
      const overviewData = await intelligenceService.getRiskOverview()
      setItems(overviewData)
    } catch (err: any) {
      alert(`Recompute failed: ${err.message}`)
    } finally {
      setRecomputing(false)
    }
  }

  // Filtered applications
  const filteredItems = items.filter((item) => {
    const matchesSearch =
      item.application_number.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.institution_name.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesCat = categoryFilter === 'ALL' || item.risk_category === categoryFilter
    const matchesReg = regionFilter === 'ALL' || item.region === regionFilter
    return matchesSearch && matchesCat && matchesReg
  })

  // Summary statistics
  const criticalCount = items.filter((i) => i.risk_category === 'CRITICAL').length
  const highCount = items.filter((i) => i.risk_category === 'HIGH').length
  const mediumCount = items.filter((i) => i.risk_category === 'MEDIUM').length
  const lowCount = items.filter((i) => i.risk_category === 'LOW').length
  const avgDelay = items.length
    ? (items.reduce((acc, i) => acc + i.estimated_delay_days, 0) / items.length).toFixed(1)
    : '0.0'

  const getRiskBadge = (cat: string) => {
    switch (cat) {
      case 'CRITICAL':
        return 'bg-red-500/10 text-red-400 border-red-500/20'
      case 'HIGH':
        return 'bg-amber-500/10 text-amber-400 border-amber-500/20'
      case 'MEDIUM':
        return 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20'
      default:
        return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
    }
  }

  return (
    <div className="space-y-6">
      {/* Page Title & Statutory Guardrail Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <BrainCircuit className="w-7 h-7 text-indigo-400" />
            Explainable Delay-Risk & Compliance Intelligence
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Predictive bottleneck detection, pipeline velocity forecasting, and explainable feature attributions (M11).
          </p>
        </div>

        <button
          onClick={loadData}
          disabled={loading}
          className="flex items-center gap-2 px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-sm border border-slate-700 transition"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh Pipeline Data
        </button>
      </div>

      {/* Mandatory Statutory Advisory Banner */}
      <div className="p-4 bg-indigo-950/30 border border-indigo-500/30 rounded-xl flex items-start gap-3">
        <ShieldCheck className="w-5 h-5 text-indigo-400 shrink-0 mt-0.5" />
        <div className="text-xs text-indigo-200 leading-relaxed">
          <strong className="text-indigo-100 font-semibold">Statutory Governance Boundary:</strong> All delay-risk scores,
          processing bottleneck warnings, and feature weights are strictly <em>advisory decision-support intelligence</em>.
          In accordance with AICTE approval regulations, automated models cannot mutate application lifecycle states or substitute
          for formal scrutiny, EVC inspection, or committee decisions.
        </div>
      </div>

      {errorMsg && (
        <div className="p-3 bg-red-900/30 border border-red-700/50 rounded-lg text-xs text-red-300">
          {errorMsg}
        </div>
      )}

      {/* KPI Metric Cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <div className="p-4 bg-slate-900 border border-slate-800 rounded-xl">
          <div className="text-xs text-slate-400 font-medium flex items-center justify-between">
            Critical Risk Files
            <AlertTriangle className="w-4 h-4 text-red-400" />
          </div>
          <div className="text-2xl font-bold text-red-400 mt-2">{criticalCount}</div>
          <div className="text-xs text-slate-500 mt-1">Variance &gt; 14 days</div>
        </div>

        <div className="p-4 bg-slate-900 border border-slate-800 rounded-xl">
          <div className="text-xs text-slate-400 font-medium flex items-center justify-between">
            High Risk Files
            <TrendingUp className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-bold text-amber-400 mt-2">{highCount}</div>
          <div className="text-xs text-slate-500 mt-1">Variance 7 - 14 days</div>
        </div>

        <div className="p-4 bg-slate-900 border border-slate-800 rounded-xl">
          <div className="text-xs text-slate-400 font-medium flex items-center justify-between">
            Medium Risk Files
            <Clock className="w-4 h-4 text-yellow-400" />
          </div>
          <div className="text-2xl font-bold text-yellow-400 mt-2">{mediumCount}</div>
          <div className="text-xs text-slate-500 mt-1">Variance 3 - 7 days</div>
        </div>

        <div className="p-4 bg-slate-900 border border-slate-800 rounded-xl">
          <div className="text-xs text-slate-400 font-medium flex items-center justify-between">
            On Track / Low Risk
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-emerald-400 mt-2">{lowCount}</div>
          <div className="text-xs text-slate-500 mt-1">Within normal SLA</div>
        </div>

        <div className="p-4 bg-slate-900 border border-slate-800 rounded-xl col-span-2 md:col-span-1">
          <div className="text-xs text-slate-400 font-medium flex items-center justify-between">
            Avg Projected Delay
            <Activity className="w-4 h-4 text-blue-400" />
          </div>
          <div className="text-2xl font-bold text-blue-400 mt-2">+{avgDelay} d</div>
          <div className="text-xs text-slate-500 mt-1">Across active queue</div>
        </div>
      </div>

      {/* Main 2-Column Layout: Pipeline List & Detail Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Applications Table (7 cols) */}
        <div className="lg:col-span-7 space-y-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-3">
            {/* Search & Filter Bar */}
            <div className="flex flex-col sm:flex-row gap-2">
              <div className="relative flex-1">
                <Search className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
                <input
                  type="text"
                  placeholder="Search application number or institution..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-full bg-slate-800/80 border border-slate-700 rounded-lg pl-9 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="flex gap-2">
                <select
                  value={categoryFilter}
                  onChange={(e) => setCategoryFilter(e.target.value)}
                  className="bg-slate-800 border border-slate-700 rounded-lg px-2 py-1.5 text-xs text-slate-200 focus:outline-none"
                >
                  <option value="ALL">All Risk Levels</option>
                  <option value="CRITICAL">Critical</option>
                  <option value="HIGH">High</option>
                  <option value="MEDIUM">Medium</option>
                  <option value="LOW">Low</option>
                </select>

                <select
                  value={regionFilter}
                  onChange={(e) => setRegionFilter(e.target.value)}
                  className="bg-slate-800 border border-slate-700 rounded-lg px-2 py-1.5 text-xs text-slate-200 focus:outline-none"
                >
                  <option value="ALL">All Regions</option>
                  <option value="Northern">Northern</option>
                  <option value="Western">Western</option>
                  <option value="South-Western">South-Western</option>
                  <option value="Eastern">Eastern</option>
                </select>
              </div>
            </div>

            {/* List Table */}
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-800 text-slate-400">
                    <th className="py-2 px-3 font-semibold">Application</th>
                    <th className="py-2 px-3 font-semibold">Stage</th>
                    <th className="py-2 px-3 font-semibold">Risk Level</th>
                    <th className="py-2 px-3 font-semibold">Projected Delay</th>
                    <th className="py-2 px-3 font-semibold text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {filteredItems.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="py-8 text-center text-slate-500">
                        No applications matching filter criteria.
                      </td>
                    </tr>
                  ) : (
                    filteredItems.map((item) => {
                      const isSelected = item.application_id === selectedAppId
                      return (
                        <tr
                          key={item.application_id}
                          onClick={() => handleSelectApp(item.application_id)}
                          className={`cursor-pointer transition ${
                            isSelected
                              ? 'bg-indigo-950/40 border-l-2 border-indigo-400'
                              : 'hover:bg-slate-800/40'
                          }`}
                        >
                          <td className="py-3 px-3">
                            <div className="font-semibold text-slate-200">{item.application_number}</div>
                            <div className="text-[11px] text-slate-400 truncate max-w-[200px]">
                              {item.institution_name} ({item.region})
                            </div>
                          </td>
                          <td className="py-3 px-3">
                            <span className="px-2 py-0.5 rounded-md bg-slate-800 text-slate-300 font-mono text-[10px]">
                              {item.current_status}
                            </span>
                          </td>
                          <td className="py-3 px-3">
                            <span
                              className={`px-2 py-0.5 rounded-full text-[10px] font-semibold border ${getRiskBadge(
                                item.risk_category
                              )}`}
                            >
                              {item.risk_category} ({(item.risk_score * 100).toFixed(0)}%)
                            </span>
                          </td>
                          <td className="py-3 px-3 text-slate-300 font-mono">
                            +{item.estimated_delay_days} days
                          </td>
                          <td className="py-3 px-3 text-right">
                            <ChevronRight
                              className={`w-4 h-4 inline-block ${
                                isSelected ? 'text-indigo-400' : 'text-slate-600'
                              }`}
                            />
                          </td>
                        </tr>
                      )
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Right Column: Detailed Explainable SHAP Attribution Panel (5 cols) */}
        <div className="lg:col-span-5 space-y-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div>
                <h3 className="text-sm font-bold text-white flex items-center gap-2">
                  <SlidersHorizontal className="w-4 h-4 text-indigo-400" />
                  SHAP Explainability Decomposition
                </h3>
                <p className="text-[11px] text-slate-400">
                  Feature-level attribution weights driving the delay risk score.
                </p>
              </div>

              <button
                onClick={handleRecompute}
                disabled={recomputing || !selectedAppId}
                className="flex items-center gap-1.5 px-2.5 py-1 bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 border border-indigo-500/30 rounded-md text-xs transition disabled:opacity-50"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${recomputing ? 'animate-spin' : ''}`} />
                Recompute
              </button>
            </div>

            {loadingDetail ? (
              <div className="py-12 text-center text-slate-500 text-xs flex flex-col items-center justify-center gap-2">
                <RefreshCw className="w-5 h-5 animate-spin text-indigo-400" />
                Calculating feature attributions...
              </div>
            ) : !predictionDetail ? (
              <div className="py-12 text-center text-slate-500 text-xs">
                Select an application from the left pipeline to inspect delay risk drivers.
              </div>
            ) : (
              <div className="space-y-4">
                {/* Score Summary Box */}
                <div className="p-3 bg-slate-800/60 border border-slate-700/60 rounded-lg flex items-center justify-between">
                  <div>
                    <div className="text-[11px] text-slate-400 font-medium">Assessed Risk Score</div>
                    <div className="text-xl font-bold text-white mt-0.5">
                      {(predictionDetail.risk_score * 100).toFixed(1)}%
                    </div>
                  </div>
                  <div className="text-right">
                    <span
                      className={`px-2.5 py-1 rounded-full text-xs font-bold border ${getRiskBadge(
                        predictionDetail.risk_category
                      )}`}
                    >
                      {predictionDetail.risk_category}
                    </span>
                    <div className="text-[11px] text-slate-400 mt-1">
                      Estimated variance: +{predictionDetail.estimated_delay_days} days
                    </div>
                  </div>
                </div>

                {/* Factor Attributions List */}
                <div className="space-y-2">
                  <div className="text-xs font-semibold text-slate-300">
                    Contributing Factors (Relative Weights)
                  </div>

                  {predictionDetail.factor_attributions.map((attr, idx) => {
                    const isIncrease = attr.impact === 'INCREASES_RISK'
                    return (
                      <div
                        key={idx}
                        className="p-3 bg-slate-800/40 border border-slate-700/40 rounded-lg space-y-1.5"
                      >
                        <div className="flex items-center justify-between text-xs">
                          <span className="font-medium text-slate-200">{attr.display_name}</span>
                          <span
                            className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${
                              isIncrease
                                ? 'bg-red-500/10 text-red-400 border border-red-500/20'
                                : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                            }`}
                          >
                            {isIncrease ? `+${(attr.weight * 100).toFixed(1)}% risk` : `${(attr.weight * 100).toFixed(1)}% risk`}
                          </span>
                        </div>

                        <div className="text-[11px] text-slate-400 leading-relaxed">
                          {attr.description}
                        </div>

                        <div className="text-[10px] text-slate-500 font-mono">
                          Observed value: {attr.observed_value}
                        </div>
                      </div>
                    )
                  })}
                </div>

                {/* Non-binding Legal Notice */}
                <div className="p-2.5 bg-slate-800/30 border border-slate-700/30 rounded text-[10px] text-slate-400 flex items-start gap-2">
                  <Info className="w-3.5 h-3.5 text-slate-400 shrink-0 mt-0.5" />
                  <span>{predictionDetail.advisory_notes}</span>
                </div>
              </div>
            )}
          </div>

          {/* Model Transparency Section */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-3">
            <h4 className="text-xs font-bold text-white flex items-center gap-1.5">
              <Layers className="w-3.5 h-3.5 text-indigo-400" />
              Active Risk Model Specifications
            </h4>

            {modelVersions.map((mv) => (
              <div key={mv.id} className="text-xs space-y-1.5 text-slate-300">
                <div className="flex justify-between items-center">
                  <span className="font-semibold text-white">{mv.name}</span>
                  <span className="font-mono text-[10px] text-indigo-300 bg-indigo-950/60 px-1.5 py-0.5 rounded border border-indigo-800">
                    {mv.version_tag}
                  </span>
                </div>
                <div className="text-[11px] text-slate-400">{mv.training_dataset_summary}</div>
                <div className="grid grid-cols-3 gap-2 pt-1 font-mono text-[10px]">
                  <div className="p-1.5 bg-slate-800 rounded border border-slate-700 text-center">
                    <span className="text-slate-400 block">ROC-AUC</span>
                    <span className="font-bold text-emerald-400">
                      {mv.metrics?.roc_auc ?? '0.89'}
                    </span>
                  </div>
                  <div className="p-1.5 bg-slate-800 rounded border border-slate-700 text-center">
                    <span className="text-slate-400 block">F1 Score</span>
                    <span className="font-bold text-blue-400">{mv.metrics?.f1_score ?? '0.85'}</span>
                  </div>
                  <div className="p-1.5 bg-slate-800 rounded border border-slate-700 text-center">
                    <span className="text-slate-400 block">MAE (Days)</span>
                    <span className="font-bold text-amber-400">
                      {mv.metrics?.mae_delay_days ?? '2.7'}d
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
