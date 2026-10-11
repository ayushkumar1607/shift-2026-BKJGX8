import { useState } from 'react'
import type { FormEvent, ReactNode } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { ArrowRight, Eye, EyeOff, ShieldCheck } from 'lucide-react'
import { api, ApiError } from './api'
import { Brand } from './components'
import { useAuth } from './context'

function AuthFrame({ children, title, subtitle }: { children: ReactNode; title: string; subtitle: string }) {
  return <main className="auth-screen"><div className="auth-decoration auth-decoration-one" /><div className="auth-decoration auth-decoration-two" /><div className="auth-wrap"><Brand /><div className="auth-card"><div className="auth-lock"><ShieldCheck size={22} /></div><h1>{title}</h1><p className="auth-subtitle">{subtitle}</p>{children}<div className="auth-demo-label"><span /> LOCAL DEMO AUTH MODE <span /></div></div><p className="auth-footnote">Synthetic device profiles · No physical BMS is contacted</p></div></main>
}

export function LoginPage() {
  const { user, signIn } = useAuth()
  const navigate = useNavigate()
  const [identifier, setIdentifier] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  if (user) return <Navigate to="/connection" replace />

  async function submit(event: FormEvent) {
    event.preventDefault(); setError(''); setBusy(true)
    try { await signIn(identifier, password); navigate('/connection') }
    catch (reason) { setError(reason instanceof ApiError ? reason.message : 'Unable to sign in. Try again.') }
    finally { setBusy(false) }
  }

  return <AuthFrame title="Welcome back" subtitle="Sign in to your EV Shield workspace">
    <form onSubmit={submit} className="auth-form">
      <label>Email or phone number<input autoComplete="username" value={identifier} onChange={e => setIdentifier(e.target.value)} placeholder="you@example.com or +1 415 555 0123" required /></label>
      <label>Password<div className="password-input"><input autoComplete="current-password" type={showPassword ? 'text' : 'password'} value={password} onChange={e => setPassword(e.target.value)} placeholder="Enter your password" required /><button className="icon-button" type="button" aria-label={showPassword ? 'Hide password' : 'Show password'} onClick={() => setShowPassword(!showPassword)}>{showPassword ? <EyeOff size={17} /> : <Eye size={17} />}</button></div></label>
      <div className="auth-options"><span className="session-note">Secure session · expires after 12 hours</span><Link to="/forgot">Forgot password?</Link></div>
      {error && <div role="alert" className="inline-error">{error}</div>}
      <button className="button button-primary button-wide" disabled={busy}>{busy ? <span className="spinner" /> : null}{busy ? 'Signing in…' : 'Sign in'}<ArrowRight size={16} /></button>
    </form>
    <div className="auth-divider"><span /> <b>JUDGE DEMO ACCOUNT</b> <span /></div>
    <div className="demo-login"><div><small>EMAIL</small><strong>judge@evshield.demo</strong></div><div><small>PASSWORD</small><strong>Demo@1234</strong></div><button type="button" className="button button-secondary" onClick={() => { setIdentifier('judge@evshield.demo'); setPassword('Demo@1234') }}>Use demo login</button></div>
    <p className="auth-switch">New to EV Shield? <Link to="/signup">Create an account</Link></p>
    <p className="demo-auth-disclaimer">No email or SMS OTP is sent in local demo mode.</p>
  </AuthFrame>
}

export function SignupPage() {
  const { user, signUp } = useAuth()
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [phone, setPhone] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [terms, setTerms] = useState(false)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  if (user) return <Navigate to="/connection" replace />

  async function submit(event: FormEvent) {
    event.preventDefault(); setError('')
    if (!email.trim() && !phone.trim()) { setError('Add an email address or a phone number with country code.'); return }
    if (password !== confirm) { setError('Passwords do not match.'); return }
    setBusy(true)
    try { await signUp({ full_name: name, email: email.trim() || undefined, phone: phone.trim() || undefined, password, confirm_password: confirm, terms_accepted: terms }); navigate('/connection') }
    catch (reason) { setError(reason instanceof ApiError ? reason.message : 'Unable to create the account. Try again.') }
    finally { setBusy(false) }
  }

  return <AuthFrame title="Create your account" subtitle="Start with a secure, simulation-only workspace">
    <form onSubmit={submit} className="auth-form signup-form">
      <label>Full name<input autoComplete="name" value={name} onChange={e => setName(e.target.value)} placeholder="Your name" minLength={2} required /></label>
      <div className="auth-fields-two"><label>Email address <span className="optional">optional</span><input type="email" autoComplete="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="you@example.com" /></label><label>Phone with country code <span className="optional">optional</span><input autoComplete="tel" value={phone} onChange={e => setPhone(e.target.value)} placeholder="+14155550123" /></label></div>
      <label>Password<div className="password-input"><input autoComplete="new-password" type={showPassword ? 'text' : 'password'} value={password} onChange={e => setPassword(e.target.value)} placeholder="10+ characters with a symbol" required /><button className="icon-button" type="button" aria-label={showPassword ? 'Hide password' : 'Show password'} onClick={() => setShowPassword(!showPassword)}>{showPassword ? <EyeOff size={17} /> : <Eye size={17} />}</button></div><small className="field-hint">Uppercase, lowercase, number, and symbol required.</small></label>
      <label>Confirm password<input autoComplete="new-password" type={showPassword ? 'text' : 'password'} value={confirm} onChange={e => setConfirm(e.target.value)} placeholder="Enter password again" required /></label>
      <label className="checkbox-label terms-check"><input type="checkbox" checked={terms} onChange={e => setTerms(e.target.checked)} /> I agree to the terms and privacy notice.</label>
      {error && <div role="alert" className="inline-error">{error}</div>}
      <button className="button button-primary button-wide" disabled={busy}>{busy ? <span className="spinner" /> : null}{busy ? 'Creating account…' : 'Create account'}<ArrowRight size={16} /></button>
    </form>
    <p className="demo-auth-disclaimer">DEMO AUTH MODE is active. Account confirmation email or phone OTP is not sent.</p>
    <p className="auth-switch">Already have an account? <Link to="/login">Sign in</Link></p>
  </AuthFrame>
}

export function ForgotPage() {
  const [identifier, setIdentifier] = useState('')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  async function submit(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError(''); setMessage('')
    try { const result = await api<{ message: string }>('/api/auth/forgot-password', { method: 'POST', body: JSON.stringify({ identifier }) }); setMessage(result.message) }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not request account recovery.') }
    finally { setBusy(false) }
  }
  return <AuthFrame title="Account recovery" subtitle="Request help with your EV Shield sign-in">
    <form onSubmit={submit} className="auth-form"><label>Email or phone number<input value={identifier} onChange={e => setIdentifier(e.target.value)} placeholder="you@example.com or +14155550123" required /></label>
      {message && <div role="status" className="inline-info">{message}</div>}{error && <div role="alert" className="inline-error">{error}</div>}
      <button className="button button-primary button-wide" disabled={busy}>{busy ? 'Checking…' : 'Request recovery'}<ArrowRight size={16} /></button>
    </form><p className="auth-switch"><Link to="/login">Back to sign in</Link></p>
  </AuthFrame>
}

