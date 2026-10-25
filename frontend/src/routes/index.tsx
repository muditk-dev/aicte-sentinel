import React from 'react'
import { createBrowserRouter, Navigate } from 'react-router-dom'
import { authService } from '../services/authService'
import { DashboardLayout } from '../layouts/DashboardLayout'
import { LoginPage } from '../pages/LoginPage'
import { DashboardPage } from '../pages/DashboardPage'
import { ApplicationsPage } from '../pages/ApplicationsPage'
import { ApplicationDetailPage } from '../pages/ApplicationDetailPage'
import { InstitutionsPage } from '../pages/InstitutionsPage'
import { WorkflowsPage } from '../pages/WorkflowsPage'
import { AuditLedgerPage } from '../pages/AuditLedgerPage'
import { DiagnosticsPage } from '../pages/DiagnosticsPage'
import { EVCPage } from '../pages/EVCPage'
import { CommitteesPage } from '../pages/CommitteesPage'
import { DecisionsPage } from '../pages/DecisionsPage'
import { RiskIntelligencePage } from '../pages/RiskIntelligencePage'
import { APHAssistantPage } from '../pages/APHAssistantPage'

interface ProtectedRouteProps {
  children: React.ReactNode
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children }) => {
  if (!authService.isAuthenticated()) {
    return <Navigate to="/login" replace />
  }
  return <>{children}</>
}

export const router = createBrowserRouter([
  {
    path: '/login',
    element: <LoginPage />,
  },
  {
    path: '/',
    element: (
      <ProtectedRoute>
        <DashboardLayout />
      </ProtectedRoute>
    ),
    children: [
      {
        index: true,
        element: <DashboardPage />,
      },
      {
        path: 'applications',
        element: <ApplicationsPage />,
      },
      {
        path: 'applications/:id',
        element: <ApplicationDetailPage />,
      },
      {
        path: 'intelligence',
        element: <RiskIntelligencePage />,
      },
      {
        path: 'aph-assistant',
        element: <APHAssistantPage />,
      },
      {
        path: 'evc',
        element: <EVCPage />,
      },
      {
        path: 'committees',
        element: <CommitteesPage />,
      },
      {
        path: 'decisions',
        element: <DecisionsPage />,
      },
      {
        path: 'institutions',
        element: <InstitutionsPage />,
      },
      {
        path: 'workflows',
        element: <WorkflowsPage />,
      },
      {
        path: 'audit',
        element: <AuditLedgerPage />,
      },
      {
        path: 'diagnostics',
        element: <DiagnosticsPage />,
      },
    ],
  },
  {
    path: '*',
    element: <Navigate to="/" replace />,
  },
])
