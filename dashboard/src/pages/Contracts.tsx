import { useQuery } from '@tanstack/react-query'
import { FileText, AlertTriangle, Clock, CheckCircle } from 'lucide-react'
import api from '../api/client'

export default function Contracts() {
  const { data: contracts, isLoading } = useQuery({
    queryKey: ['contracts'],
    queryFn: () => api.get('/api/v1/contracts?limit=50').then(r => r.data),
  })

  const { data: expiring } = useQuery({
    queryKey: ['contracts-expiring'],
    queryFn: () => api.get('/api/v1/contracts/expiring?days=30').then(r => r.data),
  })

  const { data: summary } = useQuery({
    queryKey: ['contracts-summary'],
    queryFn: () => api.get('/api/v1/contracts/summary').then(r => r.data),
  })

  const getStateColor = (state: string) => {
    switch (state) {
      case 'open': return 'bg-green-100 text-green-700'
      case 'draft': return 'bg-gray-100 text-gray-700'
      case 'close': return 'bg-red-100 text-red-700'
      default: return 'bg-gray-100 text-gray-700'
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Contracts</h1>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <div className="bg-white rounded-xl shadow-sm p-5">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-100 rounded-lg">
              <FileText className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <p className="text-sm text-gray-500">Total</p>
              <p className="text-2xl font-bold">{summary?.total || 0}</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-xl shadow-sm p-5">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-green-100 rounded-lg">
              <CheckCircle className="w-5 h-5 text-green-600" />
            </div>
            <div>
              <p className="text-sm text-gray-500">Active</p>
              <p className="text-2xl font-bold">{summary?.by_state?.open || 0}</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-xl shadow-sm p-5">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-orange-100 rounded-lg">
              <Clock className="w-5 h-5 text-orange-600" />
            </div>
            <div>
              <p className="text-sm text-gray-500">Draft</p>
              <p className="text-2xl font-bold">{summary?.by_state?.draft || 0}</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-xl shadow-sm p-5">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-red-100 rounded-lg">
              <AlertTriangle className="w-5 h-5 text-red-600" />
            </div>
            <div>
              <p className="text-sm text-gray-500">Expiring Soon</p>
              <p className="text-2xl font-bold">{summary?.expiring_soon || 0}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Expiring Contracts Alert */}
      {expiring?.contracts?.length > 0 && (
        <div className="bg-orange-50 border border-orange-200 rounded-xl p-4 mb-6">
          <div className="flex items-center gap-2 mb-3">
            <AlertTriangle className="w-5 h-5 text-orange-500" />
            <h3 className="font-semibold text-orange-700">
              Contracts Expiring Soon ({expiring.count})
            </h3>
          </div>
          <div className="space-y-2">
            {expiring.contracts.slice(0, 3).map((c: any) => (
              <div key={c.id} className="flex items-center justify-between text-sm">
                <span>{c.name} - {c.partner}</span>
                <span className={`px-2 py-0.5 rounded text-xs ${
                  c.urgency === 'CRITICAL' ? 'bg-red-100 text-red-700' : 'bg-orange-100 text-orange-700'
                }`}>
                  {c.days_until_expiry} days
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Contracts Table */}
      <div className="bg-white rounded-xl shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b">
          <h2 className="text-lg font-semibold">All Contracts</h2>
        </div>
        {isLoading ? (
          <div className="p-8 text-center text-gray-500">Loading...</div>
        ) : (
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Partner</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Start Date</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">End Date</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">State</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {contracts?.contracts?.map((contract: any) => (
                <tr key={contract.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="font-medium text-gray-900">{contract.name}</div>
                    <div className="text-sm text-gray-500">ID: {contract.id}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-gray-500">
                    {contract.partner}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-gray-500">
                    {contract.start_date || '-'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-gray-500">
                    {contract.end_date || '-'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`px-2 py-1 text-xs rounded-full ${getStateColor(contract.state)}`}>
                      {contract.state}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
