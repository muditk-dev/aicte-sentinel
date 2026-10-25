import React from 'react'

interface StatusBadgeProps {
  status: string
  className?: string
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, className = '' }) => {
  const getBadgeConfig = (st: string) => {
    switch (st.toUpperCase()) {
      case 'DRAFT':
        return {
          label: 'Draft Docket',
          classes: 'bg-slate-100 text-slate-700 border-slate-300',
        }
      case 'SUBMITTED':
        return {
          label: 'Application Submitted',
          classes: 'bg-blue-50 text-blue-700 border-blue-300',
        }
      case 'UNDER_SCRUTINY':
        return {
          label: 'Under Scrutiny',
          classes: 'bg-indigo-50 text-indigo-700 border-indigo-300',
        }
      case 'DEFICIENCY_ISSUED':
        return {
          label: 'Deficiency Issued',
          classes: 'bg-amber-50 text-amber-800 border-amber-300',
        }
      case 'RESUBMITTED':
        return {
          label: 'Resubmitted by Institute',
          classes: 'bg-sky-50 text-sky-800 border-sky-300',
        }
      case 'EVC_SCHEDULED':
        return {
          label: 'EVC Inspection Scheduled',
          classes: 'bg-purple-50 text-purple-800 border-purple-300',
        }
      case 'EVC_CONDUCTED':
        return {
          label: 'EVC Conducted',
          classes: 'bg-purple-50 text-purple-900 border-purple-400',
        }
      case 'RECOMMENDED_APPROVAL':
        return {
          label: 'Recommended for Approval',
          classes: 'bg-teal-50 text-teal-800 border-teal-300',
        }
      case 'STANDING_HEARING':
        return {
          label: 'Standing Hearing Committee',
          classes: 'bg-orange-50 text-orange-800 border-orange-300',
        }
      case 'APPROVED':
        return {
          label: 'Statutory Approval Granted',
          classes: 'bg-emerald-50 text-emerald-800 border-emerald-300 font-semibold',
        }
      case 'REJECTED':
        return {
          label: 'Application Rejected',
          classes: 'bg-rose-50 text-rose-800 border-rose-300 font-semibold',
        }
      case 'COMPLIANT':
        return {
          label: 'Compliant & Verified',
          classes: 'bg-emerald-50 text-emerald-800 border-emerald-300 font-semibold',
        }
      case 'DEFICIENT':
        return {
          label: 'Deficiency Flagged',
          classes: 'bg-amber-50 text-amber-800 border-amber-300 font-semibold',
        }
      case 'OVERDUE':
        return {
          label: 'Statutory Overdue',
          classes: 'bg-red-50 text-red-800 border-red-300 font-semibold animate-pulse',
        }
      case 'PENDING':
        return {
          label: 'Pending Action',
          classes: 'bg-slate-100 text-slate-700 border-slate-300',
        }
      case 'UNDER_REVIEW':
        return {
          label: 'Under Officer Review',
          classes: 'bg-indigo-50 text-indigo-700 border-indigo-300',
        }
      case 'CLOSED':
        return {
          label: 'Obligation Closed',
          classes: 'bg-slate-200 text-slate-800 border-slate-400 font-medium',
        }
      default:
        return {
          label: st,
          classes: 'bg-slate-50 text-slate-600 border-slate-200',
        }
    }
  }

  const { label, classes } = getBadgeConfig(status)

  return (
    <span
      className={`inline-flex items-center px-2.5 py-1 rounded-md text-xs font-medium border ${classes} ${className}`}
    >
      <span className="w-1.5 h-1.5 rounded-full bg-current mr-1.5 opacity-80" />
      {label}
    </span>
  )
}
