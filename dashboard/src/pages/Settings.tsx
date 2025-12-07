import { useQuery } from '@tanstack/react-query'
import { Server, Database, Bot, Globe } from 'lucide-react'
import api from '../api/client'

export default function Settings() {
  const { data: health } = useQuery({
    queryKey: ['health-detailed'],
    queryFn: () => api.get('/health/detailed').then(r => r.data),
    refetchInterval: 10000,
  })

  const { data: agents } = useQuery({
    queryKey: ['agents-status'],
    queryFn: () => api.get('/api/v1/agents/status').then(r => r.data),
  })

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Settings & Status</h1>

      {/* System Status */}
      <div className="bg-white rounded-xl shadow-sm p-6 mb-6">
        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Server className="w-5 h-5" />
          System Status
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="p-4 bg-gray-50 rounded-lg">
            <div className="flex items-center gap-3">
              <span className={`w-3 h-3 rounded-full ${
                health?.status === 'healthy' ? 'bg-green-400' : 'bg-red-400'
              }`}></span>
              <div>
                <p className="font-medium">Overall Status</p>
                <p className="text-sm text-gray-500 capitalize">{health?.status || 'Unknown'}</p>
              </div>
            </div>
          </div>
          <div className="p-4 bg-gray-50 rounded-lg">
            <div className="flex items-center gap-3">
              <Globe className="w-5 h-5 text-gray-400" />
              <div>
                <p className="font-medium">Version</p>
                <p className="text-sm text-gray-500">{health?.version || '0.1.0'}</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Components */}
      <div className="bg-white rounded-xl shadow-sm p-6 mb-6">
        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Database className="w-5 h-5" />
          Components
        </h2>
        <div className="space-y-3">
          {health?.components && Object.entries(health.components).map(([name, comp]: [string, any]) => (
            <div key={name} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
              <div className="flex items-center gap-3">
                <span className={`w-3 h-3 rounded-full ${
                  comp.status === 'healthy' ? 'bg-green-400' : 'bg-red-400'
                }`}></span>
                <div>
                  <p className="font-medium capitalize">{name}</p>
                  <p className="text-sm text-gray-500">
                    {comp.error || comp.version || comp.status}
                  </p>
                </div>
              </div>
              <span className={`px-2 py-1 text-xs rounded-full ${
                comp.status === 'healthy'
                  ? 'bg-green-100 text-green-700'
                  : 'bg-red-100 text-red-700'
              }`}>
                {comp.status}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Agents */}
      <div className="bg-white rounded-xl shadow-sm p-6">
        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Bot className="w-5 h-5" />
          Agent Configuration
        </h2>
        <div className="space-y-3">
          {agents?.agents && Object.entries(agents.agents).map(([key, agent]: [string, any]) => (
            <div key={key} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
              <div>
                <p className="font-medium">{agent.name}</p>
                <p className="text-sm text-gray-500">{agent.role}</p>
              </div>
              <span className={`px-2 py-1 text-xs rounded-full ${
                agent.status === 'active'
                  ? 'bg-green-100 text-green-700'
                  : 'bg-gray-100 text-gray-700'
              }`}>
                {agent.status}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* API Info */}
      <div className="mt-6 p-4 bg-blue-50 rounded-lg border border-blue-200">
        <h3 className="font-medium text-blue-700 mb-2">API Documentation</h3>
        <p className="text-sm text-blue-600">
          Access the interactive API documentation at{' '}
          <a href="/docs" target="_blank" className="underline">/docs</a>
        </p>
      </div>
    </div>
  )
}
