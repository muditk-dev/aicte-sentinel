import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { authService } from '../services/authService'
import { notificationService } from '../services/notificationService'
import { formatDate } from '../lib/utils'
import { ShieldCheck, LogOut, Building2, Bell, Check, ExternalLink } from 'lucide-react'
import { Link } from 'react-router-dom'

export const Header: React.FC = () => {
  const user = authService.getCurrentUser()
  const queryClient = useQueryClient()
  const [showNotifications, setShowNotifications] = useState(false)

  const { data: notifications = [] } = useQuery({
    queryKey: ['notifications'],
    queryFn: () => notificationService.listNotifications(),
    refetchInterval: 15000,
  })

  const markReadMutation = useMutation({
    mutationFn: notificationService.markRead,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] })
    },
  })

  const markAllReadMutation = useMutation({
    mutationFn: notificationService.markAllRead,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] })
    },
  })

  const unreadCount = notifications.filter((n) => !n.is_read).length

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
            {/* Notifications Bell */}
            <div className="relative">
              <button
                onClick={() => setShowNotifications(!showNotifications)}
                className="relative p-1.5 rounded-full text-slate-500 hover:text-slate-700 hover:bg-slate-100 focus:outline-none"
                title="Notifications"
              >
                <Bell className="w-5 h-5" />
                {unreadCount > 0 && (
                  <span className="absolute top-0 right-0 w-4 h-4 bg-rose-600 text-white text-[10px] font-bold rounded-full flex items-center justify-center ring-2 ring-white">
                    {unreadCount}
                  </span>
                )}
              </button>

              {/* Notification Popup */}
              {showNotifications && (
                <div className="absolute right-0 mt-2 w-80 sm:w-96 bg-white rounded-lg shadow-xl border border-slate-200 py-2 z-50">
                  <div className="px-4 py-2 border-b border-slate-100 flex items-center justify-between">
                    <span className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                      Statutory Notifications ({unreadCount} unread)
                    </span>
                    {unreadCount > 0 && (
                      <button
                        onClick={() => markAllReadMutation.mutate()}
                        className="text-[11px] text-blue-700 hover:underline flex items-center"
                      >
                        <Check className="w-3 h-3 mr-1" />
                        Mark all read
                      </button>
                    )}
                  </div>

                  <div className="max-h-72 overflow-y-auto divide-y divide-slate-100">
                    {notifications.length === 0 ? (
                      <div className="p-4 text-center text-xs text-slate-400">
                        No notifications.
                      </div>
                    ) : (
                      notifications.map((n) => (
                        <div
                          key={n.id}
                          className={`p-3 text-xs transition-colors ${
                            n.is_read ? 'bg-white' : 'bg-blue-50/60'
                          }`}
                        >
                          <div className="flex justify-between items-start">
                            <span className="font-bold text-slate-900 leading-tight">
                              {n.title}
                            </span>
                            {!n.is_read && (
                              <button
                                onClick={() => markReadMutation.mutate(n.id)}
                                className="text-[10px] text-slate-400 hover:text-slate-600 ml-2"
                              >
                                Mark read
                              </button>
                            )}
                          </div>
                          <p className="mt-1 text-slate-600 text-[11px] leading-relaxed">
                            {n.message}
                          </p>
                          <div className="mt-2 flex items-center justify-between text-[10px] text-slate-400 font-mono">
                            <span>{formatDate(n.created_at)}</span>
                            {n.link_url && (
                              <Link
                                to={n.link_url}
                                onClick={() => setShowNotifications(false)}
                                className="text-blue-700 font-semibold flex items-center hover:underline"
                              >
                                View Docket <ExternalLink className="w-2.5 h-2.5 ml-1" />
                              </Link>
                            )}
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              )}
            </div>

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
