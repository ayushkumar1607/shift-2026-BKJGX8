import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import App from './App'
import { AuthProvider } from './context'

const demoUser = { id: 'judge', full_name: 'EV Shield Judge', email: 'judge@evshield.demo', phone: null, demo_auth_mode: true }
const demoDevice = { id: 'EVS-DEMO-001', name: 'SecureBMS-S1', manufacturer: 'EV Shield Demo Labs', model: 'SecureBMS-S1', firmware: '1.4.2', interface: 'Bluetooth / BLE', device_identifier: 'EVS-DEMO-001', documentation_status: 'Simulated documentation confirms password changing', authentication_status: 'PASS', pairing_status: 'PASS', encryption_status: 'PASS', firmware_status: 'PASS', credential_status: 'PASS', summary: 'All checks pass.', credential_rotation_supported: true, demo_profile: true, connection_status: 'AVAILABLE' }
const user = userEvent.setup()

function response(payload: unknown, status = 200) {
  return { ok: status >= 200 && status < 300, status, json: async () => payload } as Response
}

function mockApi(handler: (path: string, init: RequestInit) => Response | Promise<Response>) {
  vi.stubGlobal('fetch', vi.fn((input: RequestInfo | URL, init: RequestInit = {}) => handler(new URL(String(input)).pathname, init)))
}

function renderApp(path: string) {
  return render(<MemoryRouter initialEntries={[path]} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}><AuthProvider><App /></AuthProvider></MemoryRouter>)
}

function authenticatedHandler(path: string, _init: RequestInit) {
  if (path === '/api/auth/me') return response(demoUser)
  if (path === '/api/session') return response({ device: demoDevice, connection_status: 'CONNECTED', operation_mode: 'SIMULATION' })
  if (path === '/api/devices') return response({ items: [demoDevice] })
  if (path.endsWith('/credential-status')) return response({ device_id: demoDevice.id, device_name: demoDevice.name, rotation_supported: true, operation_mode: 'SIMULATION', current_demo_credential_available: true, rotated: false, last_rotation_at: null, last_verification_status: 'NOT_TESTED', rotation_count: 0 })
  if (path.endsWith('/credentials/history')) return response({ items: [] })
  if (path.endsWith('/credentials/rotate')) return response({ detail: 'The current demo password is incorrect.' }, 401)
  if (path.endsWith('/assessments')) return response({ items: [] })
  return response({}, 404)
}

afterEach(() => { cleanup(); vi.unstubAllGlobals() })

describe('EV Shield UI', () => {
  it('protects dashboard routes, redirects to sign in, and accepts demo login', async () => {
    const seen: string[] = []
    mockApi(path => {
      seen.push(path)
      if (path === '/api/auth/me') return response({ detail: 'Sign in to continue.' }, 401)
      if (path === '/api/auth/login') return response({ user: demoUser, message: 'Signed in.' })
      if (path === '/api/session') return response({ device: null, connection_status: 'DISCONNECTED' })
      if (path === '/api/devices') return response({ items: [] })
      return response({ detail: 'Unauthorized' }, 401)
    })
    renderApp('/credentials')
    expect(await screen.findByRole('heading', { name: 'Welcome back' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Use demo login' }))
    expect(screen.getByLabelText(/Email or phone number/)).toHaveValue('judge@evshield.demo')
    await user.click(screen.getByRole('button', { name: /Sign in/ }))
    expect(await screen.findByText('Available demo profiles')).toBeInTheDocument()
    expect(seen).toContain('/api/auth/login')
  })

  it('shows sign-up validation when neither email nor phone is provided', async () => {
    mockApi(path => path === '/api/auth/me' ? response({ detail: 'Sign in to continue.' }, 401) : response({}, 404))
    renderApp('/signup')
    await screen.findByRole('heading', { name: 'Create your account' })
    await user.type(screen.getByLabelText('Full name'), 'Demo User')
    const password = screen.getByPlaceholderText('10+ characters with a symbol')
    await user.type(password, 'Strong@Pass2026')
    await user.type(screen.getByLabelText('Confirm password'), 'Strong@Pass2026')
    await user.click(screen.getByLabelText(/I agree to the terms/))
    await user.click(screen.getByRole('button', { name: /Create account/ }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Add an email address or a phone number')
  })

  it('loads backend profiles and updates active device after connect', async () => {
    const paths: string[] = []
    let resolveDevices!: () => void
    mockApi((path, _init) => {
      paths.push(path)
      if (path === '/api/auth/me') return response(demoUser)
      if (path === '/api/session') return response({ device: null, connection_status: 'DISCONNECTED' })
      if (path === '/api/devices') return new Promise(resolve => { resolveDevices = () => resolve(response({ items: [demoDevice] })) })
      if (path.endsWith('/connect')) return response({ device: { ...demoDevice, connection_status: 'CONNECTED' }, connection_status: 'CONNECTED', operation_mode: 'SIMULATION', identification: { credential_rotation_status: 'READY', last_assessment_at: null } })
      return response({}, 404)
    })
    renderApp('/connection')
    expect(await screen.findByText('Loading simulator profiles…')).toBeInTheDocument()
    resolveDevices()
    expect(await screen.findByText('Available demo profiles')).toBeInTheDocument()
    await user.click(await screen.findByRole('button', { name: /^Connect/ }))
    expect(await screen.findByText(/IDENTIFIED — DEMO PROFILE/)).toBeInTheDocument()
    expect(paths).toContain('/api/devices/EVS-DEMO-001/connect')
  })

  it('shows backend rotation errors and never renders a success result on failure', async () => {
    mockApi(authenticatedHandler)
    renderApp('/credentials')
    expect(await screen.findByText('No rotations yet. The initial demo password remains active.')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /Reveal demo credential/ }))
    expect(screen.getByText('Demo@1234')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /Change Password/ }))
    await user.type(screen.getByLabelText('Current demo password'), 'wrong')
    await user.type(screen.getByLabelText('New password'), 'Strong@Pass2026')
    await user.type(screen.getByLabelText('Confirm new password'), 'Strong@Pass2026')
    await user.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Change Password' }))
    expect(within(screen.getByRole('dialog')).getByRole('alert')).toHaveTextContent('The current demo password is incorrect.')
    expect(screen.queryByText('PASSWORD CHANGED SUCCESSFULLY')).not.toBeInTheDocument()
  })

  it('shows the success panel only after backend verification confirms both credentials', async () => {
    let rotated = false
    mockApi((path, _init) => {
      if (path === '/api/auth/me') return response(demoUser)
      if (path === '/api/session') return response({ device: demoDevice, connection_status: 'CONNECTED', operation_mode: 'SIMULATION' })
      if (path.endsWith('/credential-status')) return response({ device_id: demoDevice.id, device_name: demoDevice.name, rotation_supported: true, operation_mode: 'SIMULATION', current_demo_credential_available: true, rotated, last_rotation_at: rotated ? '2026-01-01T00:00:00Z' : null, last_verification_status: rotated ? 'VERIFIED' : 'NOT_TESTED', rotation_count: rotated ? 1 : 0 })
      if (path.endsWith('/credentials/history')) return response({ items: rotated ? [{ event_id: 'event-123', state: 'VERIFIED', verification_status: 'VERIFIED', new_password_accepted: true, old_password_rejected: true, created_at: '2026-01-01T00:00:00Z' }] : [] })
      if (path.endsWith('/credentials/rotate')) { rotated = true; return response({ device_id: demoDevice.id, device_name: demoDevice.name, credential_update: 'SUCCESS', new_credential_authentication: 'PASS', previous_credential_authentication: 'REJECTED', verification_status: 'VERIFIED', operation_mode: 'SIMULATION', verification_timestamp: '2026-01-01T00:00:00Z', event_id: 'event-123' }) }
      return response({}, 404)
    })
    renderApp('/credentials')
    await screen.findByText('No rotations yet. The initial demo password remains active.')
    await user.click(screen.getByRole('button', { name: /Change Password/ }))
    await user.type(screen.getByLabelText('Current demo password'), 'Demo@1234')
    await user.type(screen.getByLabelText('New password'), 'Strong@Pass2026')
    await user.type(screen.getByLabelText('Confirm new password'), 'Strong@Pass2026')
    await user.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Change Password' }))
    expect(await screen.findByText('SIMULATED ROTATION VERIFIED')).toBeInTheDocument()
    expect(screen.getByText('PASSWORD CHANGED SUCCESSFULLY')).toBeInTheDocument()
    expect(screen.getAllByText('SecureBMS-S1').length).toBeGreaterThan(0)
  })
})

