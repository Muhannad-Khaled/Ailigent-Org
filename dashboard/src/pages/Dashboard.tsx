import { useQuery } from '@tanstack/react-query'
import { FileText, Users, AlertTriangle, CheckCircle } from 'lucide-react'
import api from '../api/client'

export default function Dashboard() {
  const { data: health } = useQuery({
    queryKey: ['health'],
    queryFn: () => api.get('/health/detailed').then(r => r.data),
    refetchInterval: 30000,
  })

  const { data: contracts } = useQuery({
    queryKey: ['contracts-expiring'],
    queryFn: () => api.get('/api/v1/contracts/expiring?days=30').then(r => r.data),
  })

  const { data: leaves } = useQuery({
    queryKey: ['leaves-pending'],
    queryFn: () => api.get('/api/v1/leaves?state=confirm').then(r => r.data),
  })

  const stats = [
    {
      label: 'Expiring Contracts',
      value: contracts?.count || 0,
      icon: FileText,
      color: 'bg-orange-500',
    },
    {
      label: 'Pending Leaves',
      value: leaves?.count || 0,
      icon: Users,
      color: 'bg-blue-500',
    },
    {
      label: 'System Status',
      value: health?.status === 'healthy' ? 'OK' : 'Issue',
      icon: health?.status === 'healthy' ? CheckCircle : AlertTriangle,
      color: health?.status === 'healthy' ? 'bg-green-500' : 'bg-red-500',
    },
  ]

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Dashboard</h1>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        {stats.map((stat) => (
          <div key={stat.label} className="bg-white rounded-xl shadow-sm p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">{stat.label}</p>
                <p className="text-3xl font-bold mt-1">{stat.value}</p>
              </div>
              <div className={`${stat.color} p-3 rounded-lg`}>
                <stat.icon className="w-6 h-6 text-white" />
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Alerts Section */}
      <div className="bg-white rounded-xl shadow-sm p-6 mb-8">
        <h2 className="text-lg font-semibold mb-4">Recent Alerts</h2>
        {contracts?.supports_expiry === false ? (
          <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
            <p className="text-blue-700">
              {contracts.message || 'Contract expiration tracking is not available.'}
            </p>
            <p className="text-sm text-blue-600 mt-1">
              Using model: {contracts.model}
            </p>
          </div>
        ) : contracts?.contracts?.length > 0 ? (
          <div className="space-y-3">
            {contracts.contracts.slice(0, 5).map((c: any) => (
              <div
                key={c.id}
                className="flex items-center justify-between p-3 bg-orange-50 rounded-lg border border-orange-200"
              >
                <div className="flex items-center gap-3">
                  <AlertTriangle className="w-5 h-5 text-orange-500" />
                  <div>
                    <p className="font-medium">{c.name}</p>
                    <p className="text-sm text-gray-500">
                      Expires: {c.end_date} ({c.days_until_expiry} days)
                    </p>
                  </div>
                </div>
                <span className={`px-2 py-1 text-xs rounded-full ${
                  c.urgency === 'CRITICAL' ? 'bg-red-100 text-red-700' : 'bg-orange-100 text-orange-700'
                }`}>
                  {c.urgency}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-gray-500">No expiring contracts in the next 30 days</p>
        )}
      </div>

      {/* System Components */}
      <div className="bg-white rounded-xl shadow-sm p-6">
        <h2 className="text-lg font-semibold mb-4">System Components</h2>
        <div className="grid grid-cols-2 gap-4">
          {health?.components && Object.entries(health.components).map(([name, comp]: [string, any]) => (
            <div key={name} className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
              <span className={`w-3 h-3 rounded-full ${
                comp.status === 'healthy' ? 'bg-green-400' : 'bg-red-400'
              }`}></span>
              <div>
                <p className="font-medium capitalize">{name}</p>
                <p className="text-sm text-gray-500">
                  {comp.version || comp.status}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
