import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { authService } from '../services/authService'
import { ShieldCheck, Lock, Mail, AlertCircle, ArrowRight } from 'lucide-react'

export const LoginPage: React.FC = () => {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setErrorMsg(null)
    setIsLoading(true)

    try {
      await authService.login(email, password)
      navigate('/')
    } catch (err: any) {
      setErrorMsg(err.message || 'Authentication failed. Please verify credentials.')
    } finally {
      setIsLoading(false)
    }
  }

  const fillDemoCredentials = (demoEmail: string, demoPass: string) => {
    setEmail(demoEmail)
    setPassword(demoPass)
    setErrorMsg(null)
  }

  return (
    <div className="min-h-screen bg-slate-100 flex flex-col justify-center py-12 sm:px-6 lg:px-8 font-sans">
      {/* Subtle National Tricolor Accent Bar */}
      <div className="fixed top-0 left-0 w-full h-1 flex z-50">
        <div className="bg-[#FF9933] w-1/3" />
        <div className="bg-white w-1/3" />
        <div className="bg-[#138808] w-1/3" />
      </div>

      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <div className="flex justify-center">
          <div className="w-14 h-14 rounded-lg bg-[#0A2540] flex items-center justify-center text-white shadow-md border border-slate-300">
            <ShieldCheck className="w-9 h-9 text-amber-400" />
          </div>
        </div>
        <h2 className="mt-4 text-center text-2xl font-bold text-slate-900 tracking-tight">
          AICTE SENTINEL
        </h2>
        <p className="mt-1 text-center text-xs font-semibold text-slate-600 uppercase tracking-wider">
          Statutory Regulatory Workflow & Compliance Portal
        </p>
        <p className="text-center text-[11px] text-slate-500 mt-0.5">
          Problem Statement 26262 • APH 2026-27 Compliant
        </p>
      </div>

      <div className="mt-6 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white py-8 px-6 shadow-md rounded-lg sm:px-10 border border-slate-200">
          {errorMsg && (
            <div className="mb-5 bg-rose-50 border-l-4 border-rose-500 p-3 rounded text-rose-800 text-xs flex items-start space-x-2">
              <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
              <span>{errorMsg}</span>
            </div>
          )}

          <form className="space-y-5" onSubmit={handleLogin}>
            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider">
                Official Email Address
              </label>
              <div className="mt-1 relative rounded-md shadow-sm">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                  <Mail className="h-4 w-4" />
                </div>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="officer@aicte-india.org"
                  className="block w-full pl-9 pr-3 py-2 text-sm border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-600 focus:border-blue-600 text-slate-900 bg-white"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider">
                Password
              </label>
              <div className="mt-1 relative rounded-md shadow-sm">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                  <Lock className="h-4 w-4" />
                </div>
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  className="block w-full pl-9 pr-3 py-2 text-sm border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-600 focus:border-blue-600 text-slate-900 bg-white"
                />
              </div>
            </div>

            <div>
              <button
                type="submit"
                disabled={isLoading}
                className="w-full flex justify-center items-center py-2.5 px-4 border border-transparent rounded-md shadow-sm text-sm font-semibold text-white bg-blue-700 hover:bg-blue-800 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 transition-colors"
              >
                {isLoading ? (
                  <span>Authenticating via Argon2id...</span>
                ) : (
                  <>
                    <span>Authenticate & Access Docket</span>
                    <ArrowRight className="ml-2 w-4 h-4" />
                  </>
                )}
              </button>
            </div>
          </form>

          {/* Quick Demo Role Picker (Active in dev or when explicitly enabled) */}
          {(import.meta.env.DEV || import.meta.env.VITE_ENABLE_DEMO_LOGIN === 'true') && (
            <div className="mt-6 border-t border-slate-200 pt-5">
              <p className="text-[11px] font-bold uppercase tracking-wider text-slate-500 mb-2">
                Select Demo Statutory Identity:
              </p>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <button
                  type="button"
                  onClick={() => fillDemoCredentials('superadmin@aicte-india.org', 'Sentinel@Admin2026!')}
                  className="p-2 border border-slate-200 rounded text-left hover:bg-blue-50 hover:border-blue-300 transition-colors"
                >
                  <div className="font-bold text-slate-900">Central Admin</div>
                  <div className="text-[10px] text-slate-500">Super Administrator</div>
                </button>

                <button
                  type="button"
                  onClick={() => fillDemoCredentials('ro.delhi@aicte-india.org', 'Regional@2026!')}
                  className="p-2 border border-slate-200 rounded text-left hover:bg-blue-50 hover:border-blue-300 transition-colors"
                >
                  <div className="font-bold text-slate-900">Regional Officer</div>
                  <div className="text-[10px] text-slate-500">Northern Region</div>
                </button>

                <button
                  type="button"
                  onClick={() => fillDemoCredentials('scrutiny.lead@aicte-india.org', 'Scrutiny@2026!')}
                  className="p-2 border border-slate-200 rounded text-left hover:bg-blue-50 hover:border-blue-300 transition-colors"
                >
                  <div className="font-bold text-slate-900">Scrutiny Desk</div>
                  <div className="text-[10px] text-slate-500">Scrutiny Officer</div>
                </button>

                <button
                  type="button"
                  onClick={() => fillDemoCredentials('director@ditm-delhi.edu.in', 'College@2026!')}
                  className="p-2 border border-slate-200 rounded text-left hover:bg-blue-50 hover:border-blue-300 transition-colors"
                >
                  <div className="font-bold text-slate-900">College Signatory</div>
                  <div className="text-[10px] text-slate-500">DITM (Institution)</div>
                </button>
              </div>
            </div>
          )}
        </div>

        <div className="mt-4 text-center text-[11px] text-slate-500">
          Authorized personnel only. All access attempts cryptographically logged and audited.
        </div>
      </div>
    </div>
  )
}
