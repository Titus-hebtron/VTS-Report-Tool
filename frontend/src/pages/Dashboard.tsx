import { useAuth } from '@/contexts/AuthContext'
import { FileText, Clock, Coffee, MapPin } from 'lucide-react'

export function Dashboard() {
  const { user } = useAuth()

  const stats = [
    { name: 'Total Incidents', value: '24', icon: FileText, color: 'bg-blue-500' },
    { name: 'Idle Reports', value: '156', icon: Clock, color: 'bg-yellow-500' },
    { name: 'Breaks Logged', value: '89', icon: Coffee, color: 'bg-green-500' },
    { name: 'Active Vehicles', value: '8', icon: MapPin, color: 'bg-purple-500' },
  ]

  return (
    <div>
      <div className="mb-8">
        <h1 className="heading-1 mb-2">Dashboard</h1>
        <p className="text-text-secondary">
          Welcome back, {user?.username}! Here's your overview.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {stats.map((stat) => (
          <div key={stat.name} className="bg-surface rounded-lg shadow p-6">
            <div className="flex items-center justify-between mb-4">
              <div className={`${stat.color} p-3 rounded-lg`}>
                <stat.icon className="w-6 h-6 text-white" />
              </div>
            </div>
            <h3 className="text-2xl font-bold mb-1">{stat.value}</h3>
            <p className="text-text-secondary text-sm">{stat.name}</p>
          </div>
        ))}
      </div>

      <div className="bg-surface rounded-lg shadow p-6">
        <h2 className="heading-3 mb-4">Recent Activity</h2>
        <p className="text-text-secondary">No recent activity to display.</p>
      </div>
    </div>
  )
}