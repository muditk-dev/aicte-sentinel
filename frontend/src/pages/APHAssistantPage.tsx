import React, { useState, useEffect, useRef } from 'react'
import {
  BookOpen,
  Send,
  ThumbsUp,
  ThumbsDown,
  ExternalLink,
  ShieldAlert,
  FileText,
  Search,
  Sparkles,
} from 'lucide-react'
import { aphService } from '../services/aphService'
import { APHQueryResponse, APHClause, APHSourceDocument } from '../types'

export const APHAssistantPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'chat' | 'handbook'>('chat')
  const [messages, setMessages] = useState<APHQueryResponse[]>([])
  const [inputQuery, setInputQuery] = useState('')
  const [asking, setAsking] = useState(false)
  const [clauses, setClauses] = useState<APHClause[]>([])
  const [sources, setSources] = useState<APHSourceDocument[]>([])
  const [categoryFilter, setCategoryFilter] = useState('ALL')
  const [handbookSearch, setHandbookSearch] = useState('')
  const chatBottomRef = useRef<HTMLDivElement>(null)

  const quickPrompts = [
    'What is the minimum land requirement for engineering colleges in mega & metro cities?',
    'What are the mandatory fire safety and sprinkler requirements for buildings over 15 meters?',
    'What are the conflict of interest rules for Expert Visit Committee (EVC) panel members?',
    'What is the mandatory Faculty-to-Student Ratio (FSR) for Degree Engineering programmes?',
    'What is the maximum statutory cure period for institutional deficiency notices?',
  ]

  useEffect(() => {
    loadInitialData()
  }, [])

  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const loadInitialData = async () => {
    try {
      const [historyData, clausesData, sourcesData] = await Promise.all([
        aphService.getHistory(),
        aphService.listClauses(),
        aphService.listSources(),
      ])
      // History is newest first, reverse for chat stream
      setMessages([...historyData].reverse())
      setClauses(clausesData)
      setSources(sourcesData)
    } catch (err) {
      console.error('Failed to load APH initial data:', err)
    }
  }

  const handleSend = async (queryText?: string) => {
    const text = (queryText || inputQuery).trim()
    if (!text || asking) return

    setAsking(true)
    if (!queryText) setInputQuery('')

    try {
      const response = await aphService.askAssistant({ query_text: text })
      setMessages((prev) => [...prev, response])
    } catch (err: any) {
      alert(`Assistant error: ${err.message}`)
    } finally {
      setAsking(false)
    }
  }

  const handleFeedback = async (queryId: string, rating: number) => {
    try {
      const updated = await aphService.submitFeedback(queryId, rating)
      setMessages((prev) =>
        prev.map((msg) => (msg.id === queryId ? { ...msg, feedback_rating: updated.feedback_rating } : msg))
      )
    } catch (err) {
      console.error('Feedback failed:', err)
    }
  }

  // Filter handbook clauses
  const filteredClauses = clauses.filter((c) => {
    const matchesCat = categoryFilter === 'ALL' || c.norm_category === categoryFilter
    const matchesSearch =
      c.clause_number.toLowerCase().includes(handbookSearch.toLowerCase()) ||
      c.clause_title.toLowerCase().includes(handbookSearch.toLowerCase()) ||
      c.content_text.toLowerCase().includes(handbookSearch.toLowerCase())
    return matchesCat && matchesSearch
  })

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <BookOpen className="w-7 h-7 text-indigo-400" />
            AICTE Approval Process Handbook (APH) Assistant
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Grounded regulatory question answering with authoritative clause citations from APH 2026-27 (M13).
          </p>
        </div>

        {/* Tab Switcher */}
        <div className="flex bg-slate-900 border border-slate-800 p-1 rounded-lg">
          <button
            onClick={() => setActiveTab('chat')}
            className={`px-4 py-1.5 rounded-md text-xs font-semibold transition ${
              activeTab === 'chat'
                ? 'bg-indigo-600 text-white'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Regulatory Q&A Chat
          </button>
          <button
            onClick={() => setActiveTab('handbook')}
            className={`px-4 py-1.5 rounded-md text-xs font-semibold transition ${
              activeTab === 'handbook'
                ? 'bg-indigo-600 text-white'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Handbook Clause Explorer
          </button>
        </div>
      </div>

      {activeTab === 'chat' ? (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Main Chat Stream (8 cols) */}
          <div className="lg:col-span-8 flex flex-col h-[750px] bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
            {/* Regulatory Disclaimer Bar */}
            <div className="px-4 py-2.5 bg-indigo-950/40 border-b border-indigo-900/40 flex items-center justify-between text-[11px] text-indigo-300">
              <span className="flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
                Grounded Retrieval against AICTE APH 2026-27. Zero speculation guarantee.
              </span>
              <span className="text-slate-400">Strictly Non-Binding Statutory Advisory</span>
            </div>

            {/* Messages Body */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {messages.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-center p-6 space-y-4">
                  <div className="p-4 bg-indigo-600/10 border border-indigo-500/20 rounded-2xl">
                    <BookOpen className="w-10 h-10 text-indigo-400" />
                  </div>
                  <div>
                    <h3 className="text-base font-semibold text-white">
                      Ask the Approval Process Handbook Assistant
                    </h3>
                    <p className="text-xs text-slate-400 max-w-md mt-1">
                      Query AICTE norms regarding land requirements, fire safety, built-up area,
                      EVC panel independence, faculty cadre ratios, and deficiency cure windows.
                    </p>
                  </div>

                  {/* Quick Prompts */}
                  <div className="w-full max-w-lg space-y-2 pt-2">
                    <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider text-left">
                      Suggested Regulatory Inquiries
                    </div>
                    {quickPrompts.map((prompt, idx) => (
                      <button
                        key={idx}
                        onClick={() => handleSend(prompt)}
                        className="w-full text-left p-2.5 bg-slate-800/60 hover:bg-slate-800 border border-slate-700/60 hover:border-indigo-500/40 rounded-lg text-xs text-slate-300 hover:text-white transition flex items-center justify-between group"
                      >
                        <span className="truncate">{prompt}</span>
                        <Send className="w-3 h-3 text-slate-500 group-hover:text-indigo-400 shrink-0 ml-2" />
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                messages.map((msg) => (
                  <div key={msg.id} className="space-y-3">
                    {/* User Query Bubble */}
                    <div className="flex justify-end">
                      <div className="max-w-[80%] bg-indigo-600 text-white rounded-2xl rounded-tr-sm px-4 py-2.5 text-xs shadow-md">
                        {msg.query_text}
                      </div>
                    </div>

                    {/* Assistant Response Bubble */}
                    <div className="flex justify-start">
                      <div className="max-w-[88%] bg-slate-800/90 border border-slate-700/70 rounded-2xl rounded-tl-sm p-4 space-y-3 text-xs text-slate-200">
                        {/* Uncertainty Notice if triggered */}
                        {msg.uncertainty_warning && (
                          <div className="p-3 bg-amber-500/10 border border-amber-500/20 rounded-lg flex items-start gap-2.5 text-amber-300">
                            <ShieldAlert className="w-4 h-4 shrink-0 mt-0.5" />
                            <div className="text-[11px] leading-relaxed">
                              <strong>Uncertainty Guardrail:</strong> {msg.uncertainty_warning}
                            </div>
                          </div>
                        )}

                        {/* Text Output */}
                        <div className="prose prose-invert prose-xs leading-relaxed max-w-none whitespace-pre-line">
                          {msg.response_text}
                        </div>

                        {/* Citations Cards */}
                        {msg.citations && msg.citations.length > 0 && (
                          <div className="pt-2 border-t border-slate-700/60 space-y-2">
                            <div className="text-[11px] font-semibold text-indigo-300 flex items-center gap-1.5">
                              <FileText className="w-3.5 h-3.5" />
                              Authoritative Sources Cited ({msg.citations.length})
                            </div>

                            <div className="grid grid-cols-1 gap-2">
                              {msg.citations.map((cit, cIdx) => (
                                <div
                                  key={cIdx}
                                  className="p-2.5 bg-slate-900/80 border border-slate-700/60 rounded-lg space-y-1.5"
                                >
                                  <div className="flex items-center justify-between">
                                    <span className="font-semibold text-white flex items-center gap-1.5">
                                      <span className="px-1.5 py-0.5 bg-indigo-500/20 text-indigo-300 rounded font-mono text-[10px]">
                                        Clause {cit.clause_number}
                                      </span>
                                      <span className="text-[11px]">{cit.clause_title}</span>
                                    </span>
                                    <span className="text-[10px] text-slate-400">
                                      Chapter {cit.chapter_number} · Page {cit.page_number}
                                    </span>
                                  </div>

                                  <div className="text-[11px] text-slate-400 italic bg-slate-950/40 p-2 rounded border border-slate-800">
                                    "{cit.quote_excerpt}"
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Bottom Feedback Bar */}
                        <div className="flex items-center justify-between pt-1 text-[10px] text-slate-400">
                          <span className="font-mono text-slate-500">
                            Mode: {msg.retrieval_mode}
                          </span>

                          <div className="flex items-center gap-2">
                            <span>Was this regulatory citation helpful?</span>
                            <button
                              onClick={() => handleFeedback(msg.id, 1)}
                              className={`p-1 rounded hover:bg-slate-700 transition ${
                                msg.feedback_rating === 1 ? 'text-emerald-400 font-bold' : ''
                              }`}
                              title="Helpful"
                            >
                              <ThumbsUp className="w-3.5 h-3.5" />
                            </button>
                            <button
                              onClick={() => handleFeedback(msg.id, -1)}
                              className={`p-1 rounded hover:bg-slate-700 transition ${
                                msg.feedback_rating === -1 ? 'text-red-400 font-bold' : ''
                              }`}
                              title="Not helpful"
                            >
                              <ThumbsDown className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                ))
              )}
              <div ref={chatBottomRef} />
            </div>

            {/* Input Bar */}
            <div className="p-3 bg-slate-900 border-t border-slate-800">
              <form
                onSubmit={(e) => {
                  e.preventDefault()
                  handleSend()
                }}
                className="flex items-center gap-2"
              >
                <input
                  type="text"
                  placeholder="Ask any regulatory rule or norm from APH 2026-27..."
                  value={inputQuery}
                  onChange={(e) => setInputQuery(e.target.value)}
                  disabled={asking}
                  className="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                />
                <button
                  type="submit"
                  disabled={asking || !inputQuery.trim()}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold transition disabled:opacity-50 flex items-center gap-1.5"
                >
                  <Send className="w-3.5 h-3.5" />
                  Ask
                </button>
              </form>
            </div>
          </div>

          {/* Right Column: Grounded Corpus Information & Quick Guide (4 cols) */}
          <div className="lg:col-span-4 space-y-4">
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-3">
              <h3 className="text-xs font-bold text-white flex items-center gap-2">
                <BookOpen className="w-4 h-4 text-indigo-400" />
                Indexed Handbook Edition
              </h3>

              {sources.map((src) => (
                <div key={src.id} className="p-3 bg-slate-800/50 border border-slate-700/50 rounded-lg space-y-2">
                  <div className="text-xs font-semibold text-white">{src.title}</div>
                  <div className="text-[11px] text-slate-400">
                    Regulatory Cycle: <span className="text-indigo-300 font-mono">{src.edition}</span>
                  </div>
                  <div className="text-[10px] text-slate-500 font-mono truncate">
                    SHA-256 Digest: {src.sha256_hash}
                  </div>
                  {src.official_reference_url && (
                    <a
                      href={src.official_reference_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-[11px] text-indigo-400 hover:text-indigo-300"
                    >
                      Official AICTE Handbook PDF <ExternalLink className="w-3 h-3" />
                    </a>
                  )}
                </div>
              ))}
            </div>

            <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-3">
              <h3 className="text-xs font-bold text-white flex items-center gap-2">
                <ShieldAlert className="w-4 h-4 text-amber-400" />
                Mandatory AI Safety Constraints
              </h3>

              <div className="text-[11px] text-slate-300 space-y-2 leading-relaxed">
                <p>
                  1. <strong>Strict Grounding:</strong> The assistant strictly retrieves from the official
                  indexed APH corpus. It will refuse to guess regulatory requirements if no matching clause exists.
                </p>
                <p>
                  2. <strong>Exact Citations:</strong> Every assertion is linked to an exact chapter, clause number,
                  and page in the official handbook.
                </p>
                <p>
                  3. <strong>Human Primacy:</strong> Assistant advice does not grant approval or waive deficiencies.
                  Statutory decisions require formal human officer sign-off.
                </p>
              </div>
            </div>
          </div>
        </div>
      ) : (
        /* Handbook Explorer Tab */
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
          <div className="flex flex-col sm:flex-row justify-between gap-3">
            <div className="relative flex-1 max-w-md">
              <Search className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
              <input
                type="text"
                placeholder="Search clause number, keyword, or norm..."
                value={handbookSearch}
                onChange={(e) => setHandbookSearch(e.target.value)}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg pl-9 pr-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
              />
            </div>

            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-200 focus:outline-none"
            >
              <option value="ALL">All Norm Categories</option>
              <option value="LAND_REQUIREMENT">Land Requirements</option>
              <option value="SAFETY_COMPLIANCE">Fire & Safety Compliance</option>
              <option value="EVC_NORMS">EVC Committee Norms</option>
              <option value="FACULTY_RATIO">Faculty Cadre & Ratio</option>
              <option value="INFRASTRUCTURE">Built-Up Area & Infrastructure</option>
              <option value="DEFICIENCY_TIMELINES">Deficiency Curing Timelines</option>
              <option value="HEARING_NORMS">Hearing & Appellate Norms</option>
            </select>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {filteredClauses.map((clause) => (
              <div
                key={clause.id}
                className="p-4 bg-slate-800/40 border border-slate-700/60 rounded-xl space-y-2 hover:border-indigo-500/30 transition"
              >
                <div className="flex items-center justify-between">
                  <span className="px-2 py-0.5 bg-indigo-500/20 text-indigo-300 rounded font-mono text-xs font-bold">
                    Clause {clause.clause_number}
                  </span>
                  <span className="text-[10px] text-slate-400 font-medium">
                    Chapter {clause.chapter_number} · Page {clause.page_number}
                  </span>
                </div>

                <h4 className="text-sm font-semibold text-white">{clause.clause_title}</h4>
                <div className="text-xs text-slate-400 leading-relaxed">{clause.content_text}</div>

                <div className="pt-2 flex items-center justify-between border-t border-slate-800 text-[10px] text-slate-500">
                  <span className="font-mono">Category: {clause.norm_category}</span>
                  <button
                    onClick={() => {
                      setActiveTab('chat')
                      handleSend(`Explain requirements of Clause ${clause.clause_number}: ${clause.clause_title}`)
                    }}
                    className="text-indigo-400 hover:text-indigo-300 font-semibold flex items-center gap-1"
                  >
                    Ask Assistant about this clause &rarr;
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
