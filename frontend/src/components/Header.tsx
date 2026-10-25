import React from 'react'
import { authService } from '../services/authService'
import { ShieldCheck, LogOut, Building2 } from 'lucide-react'

export const Header: React.FC = () => {
  const user = authService.getCurrentUser()

  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-30">
      {/* Subtle National Tricolor Accent Bar */}
      <div className="h-1 w-full flex">
        <div className="bg-[#FF9933] w-1/3" />
        <div className="bg-white w-1/3 border-y border-slate-200" />
        <div className="bg-[#138808] w-1/3" />
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Official AICTE Branding */}
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded bg-[#0A2540] flex items-center justify-center text-white shadow-sm border border-slate-300">
              <ShieldCheck className="w-6 h-6 text-amber-400" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-base font-bold text-slate-900 tracking-tight">
                  AICTE SENTINEL
                </span>
                <span className="text-[10px] font-semibold uppercase px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 border border-slate-200">
                  SIH 26262
                </span>
              </div>
              <p className="text-[11px] text-slate-500 font-medium leading-none mt-0.5">
                All India Council for Technical Education • Regulatory Approval & Compliance
              </p>
            </div>
          </div>

          {/* User Profile & Actions */}
          <div className="flex items-center space-x-4">
            {user && (
              <div className="flex items-center space-x-3 text-right">
                <div className="hidden md:block">
                  <div className="text-sm font-semibold text-slate-800 leading-tight">
                    {user.full_name}
                  </div>
                  <div className="text-xs text-slate-500 flex items-center justify-end space-x-1 mt-0.5">
                    {user.institution_name ? (
                      <span className="flex items-center text-blue-700 font-medium">
                        <Building2 className="w-3 h-3 mr-1 inline" />
                        {user.institution_name}
                      </span>
                    ) : (
                      <span className="text-slate-600">{user.designation || 'Statutory Official'}</span>
                    )}
                  </div>
                </div>

                <div className="flex items-center space-x-1.5">
                  <span className="px-2 py-0.5 rounded text-xs font-semibold uppercase bg-slate-100 text-slate-700 border border-slate-200">
                    {user.roles[0]?.code || 'PUBLIC'}
                  </span>
                </div>
              </div>
            )}

            <button
              onClick={() => authService.logout()}
              title="Sign Out of Portal"
              className="inline-flex items-center px-3 py-1.5 border border-slate-300 text-xs font-medium rounded-md text-slate-700 bg-white hover:bg-slate-50 hover:text-slate-900 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
            >
              <LogOut className="w-3.5 h-3.5 mr-1.5 text-slate-500" />
              Sign Out
            </button>
          </div>
        </div>
      </div>
    </header>
  )
}
