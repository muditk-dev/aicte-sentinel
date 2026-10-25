import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { workflowService } from '../services/workflowService'
import { CheckCircle2, Layers } from 'lucide-react'

export const WorkflowsPage: React.FC = () => {
  const { data: templates = [], isLoading } = useQuery({
    queryKey: ['workflow-templates'],
    queryFn: () => workflowService.listTemplates(),
  })

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-slate-900 tracking-tight">
          Configurable Statutory Workflows
        </h1>
        <p className="text-xs text-slate-500 mt-1">
          Versioned approval workflows with maker-checker governance and explicit state transition guards
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {isLoading ? (
          <div className="col-span-3 text-center py-8 text-slate-500 text-xs">
            Loading workflow definitions...
          </div>
        ) : (
          templates.map((tmpl) => (
            <div
              key={tmpl.id}
              className="bg-white rounded-lg border border-slate-200 p-5 shadow-sm flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs font-bold text-slate-700 bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
                    {tmpl.code}
                  </span>
                  <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-800 border border-emerald-200 flex items-center">
                    <CheckCircle2 className="w-3 h-3 mr-1 text-emerald-600" />
                    ACTIVE
                  </span>
                </div>

                <h3 className="mt-3 text-sm font-bold text-slate-900 leading-snug">
                  {tmpl.name}
                </h3>
                <p className="text-xs text-slate-500 mt-1 leading-relaxed">
                  {tmpl.description}
                </p>

                <div className="mt-4 pt-3 border-t border-slate-100 space-y-2 text-xs">
                  <div className="flex justify-between items-center text-slate-600">
                    <span>Discipline Category:</span>
                    <span className="font-semibold text-slate-800">{tmpl.category}</span>
                  </div>
                  <div className="flex justify-between items-center text-slate-600">
                    <span>Published Versions:</span>
                    <span className="font-semibold text-slate-800">{tmpl.versions.length} editions</span>
                  </div>
                  {tmpl.versions[0] && (
                    <div className="flex justify-between items-center text-slate-600">
                      <span>Active Handbook:</span>
                      <span className="font-semibold text-blue-700 bg-blue-50 px-2 py-0.5 rounded">
                        {tmpl.versions[0].aph_edition}
                      </span>
                    </div>
                  )}
                </div>
              </div>

              <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
                <span className="flex items-center">
                  <Layers className="w-3.5 h-3.5 mr-1 text-slate-400" />
                  Maker-Checker Guarded
                </span>
                <span className="font-semibold text-blue-700">View State Machine</span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
