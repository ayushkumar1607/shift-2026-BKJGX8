import { Navigate, NavLink, Outlet, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { useState } from 'react'
import type { ReactNode } from 'react'
import { Bluetooth, ClipboardCheck, KeyRound, LogOut, Menu, Shield, Wifi } from 'lucide-react'
import { Brand, DemoBanner } from './components'
import { ForgotPage, LoginPage, SignupPage } from './auth'
import { useAuth } from './context'
import { AssessmentPage, ConnectionPage, CredentialsPage } from './pages'

function Protected({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth()
  const location = useLocation()
  if (loading) return <div className="app-loading"><span className="spinner spinner-large" /><span>Securing your session…</span></div>
  if (!user) return <Navigate to="/login" state={{ from: location }} replace />
  return <>{children}</>
}

const navItems = [
  { to: '/connection', label: 'Bluetooth Connection', icon: Bluetooth },
  { to: '/assessment', label: 'BMS Security Assessment', icon: ClipboardCheck },
  { to: '/credentials', label: 'Hardware Credential Management', icon: KeyRound },
]

function Shell() {
  const { user, activeDevice, signOut } = useAuth()
  const [mobileMenu, setMobileMenu] = useState(false)
  const location = useLocation()
  const navigate = useNavigate()
  const title = navItems.find(item => location.pathname.startsWith(item.to))?.label ?? 'Bluetooth Connection'
  async function logout() { await signOut(); navigate('/login', { replace: true }) }

  return <div className="app-shell">
    <aside className={`sidebar ${mobileMenu ? 'sidebar-open' : ''}`}>
      <div className="sidebar-brand"><Brand /></div>
      <div className="sidebar-label">WORKSPACE</div>
      <nav className="side-nav" aria-label="Primary navigation">{navItems.map(item => {
        const Icon = item.icon
        return <NavLink key={item.to} to={item.to} onClick={() => setMobileMenu(false)} className={({ isActive }) => `nav-link ${isActive ? 'nav-link-active' : ''}`}><Icon size={17} /><span>{item.label}</span>{item.to === '/connection' && <span className="nav-live-dot" />}</NavLink>
      })}</nav>
      <div className="sidebar-footer">
        <div className="sidebar-mode"><span className="mode-icon"><Shield size={16} /></span><div><strong>Simulator mode</strong><small>Real writes disabled</small></div><span className="status-dot" /></div>
        <div className="profile-row"><div className="avatar">{user?.full_name?.slice(0, 1).toUpperCase() ?? 'U'}</div><div className="profile-info"><strong>{user?.full_name}</strong><small>{user?.email ?? user?.phone}</small></div><button className="icon-button logout-button" onClick={logout} title="Log out" aria-label="Log out"><LogOut size={16} /></button></div>
      </div>
    </aside>
    {mobileMenu && <button aria-label="Close menu" className="sidebar-backdrop" onClick={() => setMobileMenu(false)} />}
    <div className="main-area">
      <DemoBanner />
      <header className="topbar">
        <button className="icon-button mobile-menu-button" aria-label="Open menu" onClick={() => setMobileMenu(!mobileMenu)}><Menu size={19} /></button>
        <div className="crumb"><span>Workspace</span><b>/</b><strong>{title}</strong></div>
        <div className="topbar-status"><span className={`connection-dot ${activeDevice ? 'is-online' : ''}`} /><span>{activeDevice ? 'Connected' : 'No device connected'}</span><span className="top-device">{activeDevice?.name ?? 'Select a simulator'}</span><span className="top-simulation"><Wifi size={13} /> SIMULATED</span></div>
      </header>
      <main className="content-area"><Outlet /></main>
      <footer className="app-footer"><span>EV Shield <i>v1.0 demo</i></span><span><span className="connection-dot is-online" /> Simulation service active</span></footer>
    </div>
  </div>
}

export default function App() {
  return <Routes>
    <Route path="/login" element={<LoginPage />} />
    <Route path="/signup" element={<SignupPage />} />
    <Route path="/forgot" element={<ForgotPage />} />
    <Route path="/" element={<Protected><Shell /></Protected>}>
      <Route index element={<Navigate to="/connection" replace />} />
      <Route path="connection" element={<ConnectionPage />} />
      <Route path="assessment" element={<AssessmentPage />} />
      <Route path="credentials" element={<CredentialsPage />} />
      <Route path="*" element={<Navigate to="/connection" replace />} />
    </Route>
  </Routes>
}

