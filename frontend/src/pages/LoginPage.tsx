import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { authService } from '../services/authService'
import { ShieldCheck, Lock, Mail, AlertCircle, ArrowRight, UserCheck, Sparkles, Building2 } from 'lucide-react'

export const LoginPage: React.FC = () => {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  // First-Admin Bootstrap State
  const [isBootstrapAvailable, setIsBootstrapAvailable] = useState(false)
  const [isBootstrapMode, setIsBootstrapMode] = useState(false)
  const [bootstrapFullName, setBootstrapFullName] = useState('')
  const [bootstrapDesignation, setBootstrapDesignation] = useState('Member Secretary, Central Council')
  const [showDemoPersonas, setShowDemoPersonas] = useState(false)

  useEffect(() => {
    authService.checkBootstrapStatus()
      .then((res) => {
        if (res.bootstrap_available) {
          setIsBootstrapAvailable(true)
        }
      })
      .catch(() => {
        // Graceful fallback if backend is offline
      })
  }, [])

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

  const handleBootstrap = async (e: React.FormEvent) => {
    e.preventDefault()
    setErrorMsg(null)
    setIsLoading(true)

    try {
      await authService.bootstrapAdmin({
        email,
        password,
        full_name: bootstrapFullName || 'Central AICTE Administrator',
        designation: bootstrapDesignation,
      })
      navigate('/')
    } catch (err: any) {
      setErrorMsg(err.message || 'Bootstrap initialization failed. Please check your inputs.')
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
      {/* National Tricolor Accent Bar */}
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
          {/* Bootstrap Notification Banner */}
          {isBootstrapAvailable && (
            <div className="mb-6 bg-amber-50 border border-amber-300 p-4 rounded-lg text-amber-900 text-xs">
              <div className="flex items-center space-x-2 font-bold text-sm text-amber-900">
                <Sparkles className="w-4 h-4 text-amber-600 flex-shrink-0" />
                <span>First-Time System Initialization</span>
              </div>
              <p className="mt-1 text-slate-700 leading-relaxed">
                No administrator exists in the production database. Initialize the first Central AICTE Administrator account to unlock statutory dockets.
              </p>
              <button
                type="button"
                onClick={() => {
                  setIsBootstrapMode(!isBootstrapMode)
                  setErrorMsg(null)
                }}
                className="mt-3 inline-flex items-center font-bold text-blue-700 hover:text-blue-900 underline"
              >
                {isBootstrapMode ? '← Back to Standard Sign In' : 'Initialize Central Administrator Account →'}
              </button>
            </div>
          )}

          {errorMsg && (
            <div className="mb-5 bg-rose-50 border-l-4 border-rose-500 p-3 rounded text-rose-800 text-xs flex items-start space-x-2">
              <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
              <span>{errorMsg}</span>
            </div>
          )}

          {isBootstrapMode ? (
            /* First-Admin Bootstrap Form */
            <form className="space-y-4" onSubmit={handleBootstrap}>
              <div className="border-b border-slate-200 pb-2 mb-2">
                <h3 className="text-sm font-bold text-slate-900 flex items-center space-x-2">
                  <UserCheck className="w-4 h-4 text-blue-600" />
                  <span>Bootstrap Initial Super Administrator</span>
                </h3>
                <p className="text-[11px] text-slate-500">
                  Initializes statutory roles & binds this profile with Central AICTE governance authority.
                </p>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider">
                  Full Name
                </label>
                <input
                  type="text"
                  required
                  value={bootstrapFullName}
                  onChange={(e) => setBootstrapFullName(e.target.value)}
                  placeholder="e.g. Dr. Rajesh V. Sharma"
                  className="mt-1 block w-full px-3 py-2 text-sm border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-600 focus:border-blue-600 text-slate-900 bg-white"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider">
                  Designation
                </label>
                <input
                  type="text"
                  value={bootstrapDesignation}
                  onChange={(e) => setBootstrapDesignation(e.target.value)}
                  placeholder="e.g. Member Secretary, Central Council"
                  className="mt-1 block w-full px-3 py-2 text-sm border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-600 focus:border-blue-600 text-slate-900 bg-white"
                />
              </div>

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
                    placeholder="admin@aicte-india.org"
                    className="block w-full pl-9 pr-3 py-2 text-sm border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-600 focus:border-blue-600 text-slate-900 bg-white"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider">
                  Master Password (min 8 characters)
                </label>
                <div className="mt-1 relative rounded-md shadow-sm">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                    <Lock className="h-4 w-4" />
                  </div>
                  <input
                    type="password"
                    required
                    minLength={8}
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
                  className="w-full mt-2 flex justify-center items-center py-2.5 px-4 border border-transparent rounded-md shadow-sm text-sm font-semibold text-white bg-amber-600 hover:bg-amber-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-amber-500 disabled:opacity-50 transition-colors"
                >
                  {isLoading ? (
                    <span>Initializing Security Layer...</span>
                  ) : (
                    <>
                      <span>Initialize & Grant Super Admin</span>
                      <ArrowRight className="ml-2 w-4 h-4" />
                    </>
                  )}
                </button>
              </div>
            </form>
          ) : (
            /* Standard Login Form */
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
          )}

          {/* Optional Demo Personas Toggle */}
          <div className="mt-6 border-t border-slate-200 pt-4">
            <button
              type="button"
              onClick={() => setShowDemoPersonas(!showDemoPersonas)}
              className="text-[11px] font-bold text-slate-500 hover:text-slate-800 flex items-center justify-between w-full"
            >
              <span className="uppercase tracking-wider">SIH Evaluation Demo Personas</span>
              <span>{showDemoPersonas ? '▲ Hide' : '▼ View Personas'}</span>
            </button>

            {showDemoPersonas && (
              <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
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
                  <div className="font-bold text-slate-900 flex items-center space-x-1">
                    <Building2 className="w-3 h-3 text-slate-500" />
                    <span>DITM College</span>
                  </div>
                  <div className="text-[10px] text-slate-500">Institution Signatory</div>
                </button>
              </div>
            )}
          </div>
        </div>

        <div className="mt-4 text-center text-[11px] text-slate-500">
          Authorized personnel only. All access attempts cryptographically logged and audited.
        </div>
      </div>
    </div>
  )
}
