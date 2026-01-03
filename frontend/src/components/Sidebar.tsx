import { NavLink } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'
import {
  LayoutDashboard,
  FileText,
  Clock,
  Coffee,
  Search,
  MapPin,
  AlertTriangle,
} from 'lucide-react'

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard, roles: ['admin', 'control', 'patrol', 're_admin'] },
  { name: 'Incident Report', href: '/incidents', icon: FileText, roles: ['admin', 'control', 'patrol', 're_admin'] },
  { name: 'Idle Time Analyzer', href: '/idle-analyzer', icon: Clock, roles: ['admin', 'control', 're_admin'] },
  { name: 'Breaks & Pickups', href: '/breaks-pickups', icon: Coffee, roles: ['admin', 'control', 'patrol', 're_admin'] },
  { name: 'Report Search', href: '/reports', icon: Search, roles: ['admin', 'control', 're_admin'] },
  { name: 'GPS Tracking', href: '/tracking', icon: MapPin, roles: ['admin', 'control', 're_admin'] },
  { name: 'Accident Analysis', href: '/accident-analysis', icon: AlertTriangle, roles: ['re_admin'] },
]

export function Sidebar() {
  const { user } = useAuth()

  const filteredNavigation = navigation.filter((item) =>
    user?.role ? item.roles.includes(user.role) : false
  )

  return (
    <div className="w-64 bg-surface border-r border-border">
      <div className="flex items-center justify-center h-16 border-b border-border">
        <img src="/Kenhalogo.png" alt="Logo" className="h-12" />
      </div>
      <nav className="p-4 space-y-1">
        {filteredNavigation.map((item) => (
          <NavLink
            key={item.name}
            to={item.href}
            className={({ isActive }) =>
              `flex items-center px-4 py-3 text-sm font-medium rounded-lg transition-colors ${
                isActive
                  ? 'bg-primary text-white'
                  : 'text-text-primary hover:bg-background'
              }`
            }
          >
            <item.icon className="w-5 h-5 mr-3" />
            {item.name}
          </NavLink>
        ))}
      </nav>
    </div>
  )
}