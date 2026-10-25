import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { institutionService } from '../services/institutionService'
import { Building, Search, MapPin, Mail, Phone } from 'lucide-react'

export const InstitutionsPage: React.FC = () => {
  const [regionFilter, setRegionFilter] = useState('')
  const [searchTerm, setSearchTerm] = useState('')

  const { data: institutions = [], isLoading } = useQuery({
    queryKey: ['institutions', regionFilter],
    queryFn: () => institutionService.listInstitutions(regionFilter || undefined),
  })

  const filtered = institutions.filter(
    (inst) =>
      inst.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      inst.code.toLowerCase().includes(searchTerm.toLowerCase())
  )

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-slate-900 tracking-tight">
          Technical Institutions Registry
        </h1>
        <p className="text-xs text-slate-500 mt-1">
          Registered and affiliated technical education institutions under AICTE regulatory governance
        </p>
      </div>

      <div className="bg-white rounded-lg border border-slate-200 p-4 shadow-sm flex flex-col md:flex-row gap-4 justify-between items-center">
        <div className="relative w-full md:w-80">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
            <Search className="h-4 w-4" />
          </div>
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search by name or AICTE Permanent Code..."
            className="block w-full pl-9 pr-3 py-1.5 text-xs border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-600"
          />
        </div>

        <div className="flex items-center space-x-2">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Region:</span>
          <select
            value={regionFilter}
            onChange={(e) => setRegionFilter(e.target.value)}
            className="text-xs border border-slate-300 rounded-md py-1.5 px-3 bg-white text-slate-800"
          >
            <option value="">All Regions</option>
            <option value="Northern">Northern Region</option>
            <option value="Western">Western Region</option>
            <option value="Southern">Southern Region</option>
            <option value="South-Western">South-Western Region</option>
            <option value="Central">Central Region</option>
            <option value="Eastern">Eastern Region</option>
          </select>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {isLoading ? (
          <div className="col-span-3 text-center py-8 text-slate-500 text-xs">
            Loading institutions...
          </div>
        ) : filtered.length === 0 ? (
          <div className="col-span-3 text-center py-8 text-slate-500 text-xs">
            No matching institutions found.
          </div>
        ) : (
          filtered.map((inst) => (
            <div
              key={inst.id}
              className="bg-white rounded-lg border border-slate-200 p-5 shadow-sm hover:border-slate-300 transition-colors"
            >
              <div className="flex items-start justify-between">
                <div>
                  <span className="font-mono text-xs font-bold text-blue-700 bg-blue-50 px-2 py-0.5 rounded border border-blue-200">
                    {inst.code}
                  </span>
                  <span className="ml-2 text-[10px] font-semibold uppercase px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-800 border border-emerald-200">
                    {inst.status}
                  </span>
                </div>
                <Building className="w-5 h-5 text-slate-400" />
              </div>

              <h3 className="mt-3 text-sm font-bold text-slate-900 leading-snug line-clamp-2">
                {inst.name}
              </h3>
              <p className="text-xs text-slate-500 mt-1">{inst.institution_type}</p>

              <div className="mt-4 pt-3 border-t border-slate-100 space-y-1.5 text-xs text-slate-600">
                <div className="flex items-center">
                  <MapPin className="w-3.5 h-3.5 mr-2 text-slate-400 flex-shrink-0" />
                  <span>
                    {inst.district}, {inst.state} ({inst.region} Region)
                  </span>
                </div>
                <div className="flex items-center">
                  <Mail className="w-3.5 h-3.5 mr-2 text-slate-400 flex-shrink-0" />
                  <span className="truncate">{inst.contact_email}</span>
                </div>
                <div className="flex items-center">
                  <Phone className="w-3.5 h-3.5 mr-2 text-slate-400 flex-shrink-0" />
                  <span>{inst.contact_phone}</span>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
