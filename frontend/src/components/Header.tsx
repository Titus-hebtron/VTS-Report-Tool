import { useAuth } from '@/contexts/AuthContext'
import { LogOut, User } from 'lucide-react'

export function Header() {
  const { user, logout } = useAuth()

  return (
    <header className="h-16 bg-surface border-b border-border flex items-center justify-between px-6">
      <h1 className="heading-2">VTS REPORT TOOL</h1>
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 text-sm">
          <User className="w-4 h-4" />
          <span className="font-medium">{user?.username}</span>
          <span className="text-text-secondary">({user?.contractor})</span>
        </div>
        <button
          onClick={logout}
          className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-primary rounded-lg hover:bg-secondary transition-colors"
        >
          <LogOut className="w-4 h-4" />
          Logout
        </button>
      </div>
    </header>
  )
}