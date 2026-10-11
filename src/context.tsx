import { createContext, useContext, useEffect, useMemo, useState } from 'react'
import type { PropsWithChildren } from 'react'
import { authApi, api } from './api'
import type { Device, User } from './types'

type AuthContextType = {
  user: User | null; loading: boolean; activeDevice: Device | null
  setActiveDevice: (device: Device | null) => void; refreshSession: () => Promise<void>
  signIn: (identifier: string, password: string) => Promise<void>
  signUp: (data: Parameters<typeof authApi.signup>[0]) => Promise<void>
  signOut: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | null>(null)

export function AuthProvider({ children }: PropsWithChildren) {
  const [user, setUser] = useState<User | null>(null)
  const [activeDevice, setActiveDevice] = useState<Device | null>(null)
  const [loading, setLoading] = useState(true)

  const refreshSession = async () => {
    try {
      const session = await api<{ device: Device | null }>('/api/session')
      setActiveDevice(session.device)
    } catch { setActiveDevice(null) }
  }

  useEffect(() => {
    let mounted = true
    authApi.me().then(async (current) => {
      if (!mounted) return
      setUser(current)
      await refreshSession()
    }).catch(() => { if (mounted) setUser(null) }).finally(() => { if (mounted) setLoading(false) })
    return () => { mounted = false }
  }, [])

  const value = useMemo<AuthContextType>(() => ({
    user, loading, activeDevice, setActiveDevice, refreshSession,
    signIn: async (identifier, password) => { const result = await authApi.login(identifier, password); setUser(result.user); await refreshSession() },
    signUp: async (data) => { const result = await authApi.signup(data); setUser(result.user); setActiveDevice(null) },
    signOut: async () => { await authApi.logout(); setUser(null); setActiveDevice(null) },
  }), [user, loading, activeDevice])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const value = useContext(AuthContext)
  if (!value) throw new Error('useAuth must be used inside AuthProvider')
  return value
}

