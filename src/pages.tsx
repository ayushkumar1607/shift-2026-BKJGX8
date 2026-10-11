import { useEffect, useMemo, useState } from 'react'
import type { CSSProperties, FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { AlertTriangle, ArrowRight, BatteryCharging, Bluetooth, Check, CircleHelp, ClipboardCheck, Clock3, Cpu, Fingerprint, KeyRound, LockKeyhole, RefreshCcw, RotateCcw, Shield, ShieldCheck, Signal, X } from 'lucide-react'
import { api } from './api'
import { EmptyState, Metric, PageTitle, Panel, SectionHeading, SimulatedNote, StatusPill, StepLine } from './components'
import { useAuth } from './context'
import type { Assessment, Check as SecurityCheck, CredentialStatus, Device, RotationResult } from './types'

function errorMessage(error: unknown) { return error instanceof Error ? error.message : 'Unable to complete that action. Try again.' }
function prettyDate(value: string | null | undefined) { return value ? new Date(value).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' }) : 'Not yet' }

export function ConnectionPage() {
  const { activeDevice, setActiveDevice } = useAuth()
  const [devices, setDevices] = useState<Device[]>([])
  const [loading, setLoading] = useState(true)
  const [connecting, setConnecting] = useState<string | null>(null)
  const [mode, setMode] = useState<'simulator' | 'real'>('simulator')
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')
  const [realDeviceName, setRealDeviceName] = useState('')
  const [manualDetails, setManualDetails] = useState({ manufacturer: '', model: '', firmware: '' })
  const [showManual, setShowManual] = useState(false)
  const [realMessage, setRealMessage] = useState('')
  const [identification, setIdentification] = useState<{ credential_rotation_status: string; last_assessment_at: string | null } | null>(null)

  async function loadDevices() {
    setLoading(true); setError('')
    try { const result = await api<{ items: Device[] }>('/api/devices'); setDevices(result.items) }
    catch (reason) { setError(errorMessage(reason)) }
    finally { setLoading(false) }
  }
  useEffect(() => { void loadDevices() }, [])
  useEffect(() => {
    setIdentification(null)
    if (activeDevice) api<{ credential_rotation_status: string; last_assessment_at: string | null }>(`/api/devices/${activeDevice.id}/identification`).then(setIdentification).catch(() => setIdentification(null))
  }, [activeDevice?.id])

  async function connect(device: Device) {
    setConnecting(device.id); setError(''); setNotice('')
    try {
      const result = await api<{ device: Device; identification: { credential_rotation_status: string; last_assessment_at: string | null } }>(`/api/devices/${device.id}/connect`, { method: 'POST' })
      setActiveDevice(result.device)
      setIdentification(result.identification)
      setNotice(`${result.device.name} identified from the Synthetic Demo Registry.`)
    } catch (reason) { setError(errorMessage(reason)) }
    finally { setConnecting(null) }
  }

  async function connectReal() {
    setError(''); setRealMessage('')
    const bluetooth = (navigator as Navigator & { bluetooth?: { requestDevice(options: { acceptAllDevices: boolean }): Promise<{ name?: string | null }> } }).bluetooth
    if (!window.isSecureContext || !bluetooth) {
      setError('Web Bluetooth is unavailable in this browser or context. Simulator Mode is ready to use.'); return
    }
    try {
      const device = await bluetooth.requestDevice({ acceptAllDevices: true })
      setRealDeviceName(device.name?.trim() || 'Unnamed Bluetooth device')
      setManualDetails({ manufacturer: '', model: '', firmware: '' })
      setShowManual(false)
      setRealMessage('Device selected by the browser. EV Shield has not connected to its services or read manufacturer data.')
    } catch (reason) {
      if (reason instanceof Error && reason.name === 'NotFoundError') return
      setError('Bluetooth device access was not completed. No device data was read.')
    }
  }

  async function resetDemo() {
    if (!window.confirm('Reset this account’s synthetic demo data? All demo passwords, assessments, and rotation history will return to their initial state. No physical device is affected.')) return
    setError(''); setNotice('')
    try {
      const result = await api<{ message: string }>('/api/demo/reset', { method: 'POST', body: JSON.stringify({ confirm: true }) })
      setActiveDevice(null); setRealDeviceName(''); setNotice(result.message); await loadDevices()
    } catch (reason) { setError(errorMessage(reason)) }
  }

  return <div className="page-stack">
    <PageTitle eyebrow="DEVICE LINK · 01" title="Bluetooth Connection" description="Connect to a synthetic BMS profile and automatically load its identity." action={<button className="button button-quiet" onClick={resetDemo}><RotateCcw size={15} /> Reset demo data</button>} />
    {error && <div className="toast toast-error" role="alert"><AlertTriangle size={16} />{error}<button className="icon-button" aria-label="Dismiss error" onClick={() => setError('')}><X size={15} /></button></div>}
    {notice && <div className="toast toast-success" role="status"><Check size={16} />{notice}<button className="icon-button" aria-label="Dismiss notification" onClick={() => setNotice('')}><X size={15} /></button></div>}
    <div className="mode-switch-card">
      <div className="mode-switch-copy"><div className="mode-orb"><Bluetooth size={20} /></div><div><span className="eyebrow">CONNECTION MODE</span><h2>{mode === 'simulator' ? 'Simulator Mode' : 'Real Bluetooth'}</h2><p>{mode === 'simulator' ? 'Explore five preloaded BMS profiles. No hardware required.' : 'Read-only browser device picker. Physical writes are disabled.'}</p></div></div>
      <div className="segmented-control" role="tablist" aria-label="Connection mode"><button role="tab" aria-selected={mode === 'simulator'} className={mode === 'simulator' ? 'selected' : ''} onClick={() => { setMode('simulator'); setError('') }}><Cpu size={15} /> Simulator</button><button role="tab" aria-selected={mode === 'real'} className={mode === 'real' ? 'selected' : ''} onClick={() => { setMode('real'); setError('') }}><Bluetooth size={15} /> Real Bluetooth</button></div>
    </div>

    {mode === 'simulator' ? <>
      {activeDevice && <Panel className="identified-panel"><div className="identified-top"><div className="identified-icon"><BatteryCharging size={21} /></div><div><div className="identified-tags"><span className="tag tag-demo">DEMO PROFILE</span><StatusPill status="CONNECTED" /></div><h2>{activeDevice.name}</h2><p>IDENTIFIED — DEMO PROFILE <span className="inline-dot">·</span> Synthetic Demo Registry</p></div><span className="identified-check"><ShieldCheck size={20} /> Identified</span></div>
        <div className="identified-details"><InfoCell label="Manufacturer" value={activeDevice.manufacturer} /><InfoCell label="Model" value={activeDevice.model} /><InfoCell label="Firmware" value={activeDevice.firmware} /><InfoCell label="Interface" value={activeDevice.interface} /><InfoCell label="Device ID" value={activeDevice.id} /><InfoCell label="Default credential" value={activeDevice.default_credential_status} /><InfoCell label="Credential rotation" value="Supported in simulation" /></div>
        <div className="identified-bottom"><span><LockKeyhole size={14} /> Authentication: {activeDevice.authentication_status}</span><span><Signal size={14} /> Pairing: {activeDevice.pairing_status}</span><span><Shield size={14} /> Encryption: {activeDevice.encryption_status}</span><span><RefreshCcw size={14} /> Credential rotation: {identification?.credential_rotation_status ?? 'READY'}</span><span><Clock3 size={14} /> Last assessment: {prettyDate(identification?.last_assessment_at)}</span></div>
      </Panel>}

      <div className="section-heading device-heading"><div><h2>Available demo profiles</h2><p>Choose a profile to see its unique simulated security posture.</p></div><span className="profile-count"><span className="status-dot" /> {devices.length} PROFILES READY</span></div>
      {loading ? <div className="loading-card"><span className="spinner" />Loading simulator profiles…</div> : <div className="device-grid">{devices.map((device, index) => <DeviceCard key={device.id} device={device} index={index} connecting={connecting === device.id} active={activeDevice?.id === device.id} onConnect={() => void connect(device)} />)}</div>}

      <div className="connection-lower-grid">
        <Panel className="judge-guide"><SectionHeading title="Judge demo guide" aside={<span className="mini-tag">2 MIN</span>} /><p>Run the complete simulated BMS security story in a few steps.</p><div className="guide-steps"><GuideStep number="01" text="Connect SecureBMS-S1" /><GuideStep number="02" text="Run its security assessment" /><GuideStep number="03" text="Reveal the demo password" /><GuideStep number="04" text="Rotate and verify credentials" /><GuideStep number="05" text="Compare LegacyBMS-L1 findings" /></div><div className="guide-note"><CircleHelp size={14} /> Demo login is available on the sign-in screen.</div></Panel>
        <Panel className="real-safety-card"><div className="real-safety-icon"><LockKeyhole size={18} /></div><div><div className="eyebrow">HARDWARE SAFETY</div><h3>Real BMS writes stay disabled</h3><p>There is no validated model-specific hardware adapter in this demo. Simulator credentials never authorize physical writes.</p><span className="safety-label">NO VALIDATED HARDWARE ADAPTER</span></div></Panel>
      </div>
    </> : <>
      <Panel className="real-mode-panel"><div className="real-mode-heading"><div className="real-icon"><Bluetooth size={22} /></div><div><span className="tag tag-neutral">READ ONLY</span><h2>Connect to a nearby device</h2><p>Web Bluetooth is used only when supported by a secure browser. The picker opens after you choose Connect.</p></div></div><div className="real-mode-warning"><AlertTriangle size={16} /><span>Device names are not proof of identity. EV Shield will not guess a model or send commands.</span></div><p className="safety-label real-write-label">NO VALIDATED HARDWARE ADAPTER — SIMULATION ONLY</p><button className="button button-primary" onClick={connectReal}><Bluetooth size={16} /> Choose Bluetooth device</button>
        {!window.isSecureContext && <p className="field-hint">A secure context is required. Localhost counts as secure for development.</p>}
      </Panel>
      {error && null}
      {realMessage && <Panel className="real-selection"><div className="real-selection-head"><span className="tag tag-warning">IDENTIFICATION UNVERIFIED</span><span className="tag tag-neutral">REAL DEVICE · READ ONLY</span></div><h3>{realDeviceName}</h3><p>{realMessage}</p><div className="unverified-grid"><InfoCell label="Manufacturer" value={manualDetails.manufacturer || 'Unknown'} /><InfoCell label="Model" value={manualDetails.model || 'Unknown'} /><InfoCell label="Firmware" value={manualDetails.firmware || 'Unknown'} /><InfoCell label="Interface" value="Bluetooth / BLE · detected by browser" /></div><button className="text-button" onClick={() => setShowManual(!showManual)}>{showManual ? 'Hide' : 'Add'} missing details</button>{showManual && <div className="manual-fields"><label>Manufacturer<input value={manualDetails.manufacturer} onChange={e => setManualDetails({ ...manualDetails, manufacturer: e.target.value })} placeholder="Only if known" /></label><label>Model<input value={manualDetails.model} onChange={e => setManualDetails({ ...manualDetails, model: e.target.value })} placeholder="Only if known" /></label><label>Firmware<input value={manualDetails.firmware} onChange={e => setManualDetails({ ...manualDetails, firmware: e.target.value })} placeholder="Only if known" /></label><p>These are user-supplied notes, not verified identification. They are not saved to the demo registry.</p></div>}</Panel>}
      {!realMessage && <EmptyState title="No real device selected">Choose a Bluetooth device to inspect what the browser can identify. Physical credential writes are disabled.</EmptyState>}
    </>}
  </div>
}

function InfoCell({ label, value }: { label: string; value: string }) { return <div className="info-cell"><small>{label}</small><strong>{value}</strong></div> }
function GuideStep({ number, text }: { number: string; text: string }) { return <div className="guide-step"><span>{number}</span><p>{text}</p><Check size={14} /></div> }

function DeviceCard({ device, index, connecting, active, onConnect }: { device: Device; index: number; connecting: boolean; active: boolean; onConnect: () => void }) {
  const checks = [device.authentication_status, device.pairing_status, device.encryption_status, device.firmware_status]
  const findings = checks.filter(status => status === 'FINDING').length
  const unknowns = checks.filter(status => status === 'UNKNOWN').length
  const summary = findings ? `${findings} finding${findings > 1 ? 's' : ''} · ${unknowns} unknown` : unknowns ? `${unknowns} check${unknowns > 1 ? 's' : ''} unknown` : 'All checks passing'
  return <Panel className={`device-card ${active ? 'device-card-active' : ''}`}>
    <div className="device-card-top"><div className={`device-symbol symbol-${index + 1}`}><BatteryCharging size={20} /></div><span className="tag tag-demo">DEMO PROFILE</span></div>
    <div className="device-name-row"><h3>{device.name}</h3>{active && <span className="active-chip"><span /> ACTIVE</span>}</div><p className="device-maker">{device.manufacturer}</p>
    <div className="device-meta"><span><small>MODEL</small>{device.model}</span><span><small>FIRMWARE</small>{device.firmware}</span></div>
    <div className="device-meta"><span><small>INTERFACE</small>{device.interface}</span><span><small>ROTATION</small><b className="rotation-supported"><Check size={12} /> Supported</b></span></div>
    <div className="device-meta device-meta-single"><span><small>DEFAULT CREDENTIAL</small>{device.default_credential_status}</span></div>
    <div className="device-summary"><span className={`summary-dot ${findings ? 'summary-warning' : unknowns ? 'summary-unknown' : ''}`} />{summary}</div>
    <button className={`button ${active ? 'button-connected' : 'button-card'}`} disabled={connecting} onClick={onConnect}>{connecting ? <><span className="spinner" /> Connecting…</> : active ? <><Check size={15} /> Connected</> : <>Connect <ArrowRight size={15} /></>}</button>
  </Panel>
}

export function AssessmentPage() {
  const { activeDevice } = useAuth()
  const [assessment, setAssessment] = useState<Assessment | null>(null)
  const [history, setHistory] = useState<Assessment[]>([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  async function loadHistory(deviceId: string) {
    const result = await api<{ items: Assessment[] }>(`/api/devices/${deviceId}/assessments`)
    setHistory(result.items); setAssessment(result.items[0] ?? null)
  }
  useEffect(() => { setAssessment(null); setHistory([]); setError(''); setNotice(''); if (activeDevice) void loadHistory(activeDevice.id).catch(reason => setError(errorMessage(reason))) }, [activeDevice?.id])

  async function run() {
    if (!activeDevice) return
    setBusy(true); setError('')
    try { const result = await api<Assessment>(`/api/devices/${activeDevice.id}/assessments`, { method: 'POST' }); setAssessment(result); setHistory(current => [result, ...current]) }
    catch (reason) { setError(errorMessage(reason)) }
    finally { setBusy(false) }
  }
  async function retest() {
    if (!activeDevice || !assessment) return
    setBusy(true); setError('')
    try { const result = await api<{ assessment: Assessment; comparison: { previous_status: string; current_status: string } }>(`/api/devices/${activeDevice.id}/assessments/${assessment.id}/retest`, { method: 'POST' }); setAssessment(result.assessment); setHistory(current => [result.assessment, ...current]); setNotice(`Retest compared ${result.comparison.previous_status} → ${result.comparison.current_status}. Unknown checks remain open until new evidence is available.`) }
    catch (reason) { setError(errorMessage(reason)) }
    finally { setBusy(false) }
  }

  return <div className="page-stack">
    <PageTitle eyebrow="SECURITY REVIEW · 02" title="BMS Security Assessment" description="Review simulated evidence by check, severity, and coverage." action={activeDevice && <button className="button button-primary" disabled={busy} onClick={run}>{busy ? <span className="spinner" /> : <RefreshCcw size={15} />}Run Assessment</button>} />
    {error && <div className="toast toast-error" role="alert"><AlertTriangle size={16} />{error}</div>}
    {notice && <div className="toast toast-success" role="status"><Check size={16} />{notice}<button className="icon-button" aria-label="Dismiss notification" onClick={() => setNotice('')}><X size={15} /></button></div>}
    {!activeDevice ? <Panel><EmptyState title="Connect a demo profile first">Go to <Link to="/connection">Bluetooth Connection</Link>, choose a synthetic BMS, and its assessment will appear here.</EmptyState></Panel> : !assessment ? <Panel className="assessment-welcome"><div className="assessment-hero-icon"><ClipboardCheckIcon /></div><div><span className="tag tag-demo">SIMULATION</span><h2>Assessment ready for {activeDevice.name}</h2><p>Run the backend assessment to calculate a score, evidence coverage, and device-specific findings.</p></div><button className="button button-primary" onClick={run} disabled={busy}>{busy ? <span className="spinner" /> : <RefreshCcw size={15} />} Run Assessment</button></Panel> : <>
      <div className="assessment-device-strip"><div><span className="tag tag-demo">DEMO PROFILE</span><strong>{activeDevice.name}</strong><span>{activeDevice.model} · FW {activeDevice.firmware}</span></div><span className="assessment-time"><Clock3 size={14} /> {prettyDate(assessment.created_at)}</span></div>
    <div className="assessment-metrics"><Panel className="score-panel"><div className="score-ring" style={{ '--score': `${assessment.score}%` } as CSSProperties}><div><strong>{assessment.score}</strong><small>/ 100</small></div></div><div className="score-copy"><span className="eyebrow">SECURITY SCORE</span><StatusPill status={assessment.overall_status} /><p>Calculated from assessed checks. Unknown results are excluded from the score.</p></div></Panel>
        <Metric label="Evidence coverage" value={`${assessment.evidence_coverage}%`} detail="Known results out of 5 checks" icon={<Signal size={16} />} />
        <Metric label="Security findings" value={assessment.checks.filter(item => item.status === 'FINDING').length} detail="Require a documented action" icon={<AlertTriangle size={16} />} />
        <Metric label="Unknown checks" value={assessment.checks.filter(item => item.status === 'UNKNOWN').length} detail="Evidence not established" icon={<CircleHelp size={16} />} />
      </div>
      <Panel className="checks-panel"><SectionHeading title="Assessment checks" aside={<button className="button button-quiet button-small" onClick={retest} disabled={busy || !assessment}>{busy ? 'Retesting…' : 'Retest latest'}</button>} /><div className="checks-list">{assessment.checks.map(item => <CheckCard key={item.key} check={item} />)}</div></Panel>
      <Panel className="history-panel"><SectionHeading title="Assessment history" aside={<span className="history-count">{history.length} RECORD{history.length === 1 ? '' : 'S'}</span>} />{history.length ? <div className="history-list">{history.slice(0, 5).map((item, index) => <div className="history-row" key={item.id}><span className="history-index">{String(index + 1).padStart(2, '0')}</span><div><strong>{item.is_retest ? 'Assessment retest' : 'Security assessment'}</strong><small>{prettyDate(item.created_at)}</small></div><span>{item.score}/100</span><StatusPill status={item.overall_status} /></div>)}</div> : <p className="muted-text">Assessment history will appear here.</p>}</Panel>
    </>}
    <SimulatedNote>Assessment results describe the selected synthetic demo profile. They do not represent a physical manufacturer device.</SimulatedNote>
  </div>
}

function ClipboardCheckIcon() { return <ClipboardCheck size={23} /> }
function CheckCard({ check }: { check: SecurityCheck }) {
  return <article className={`check-card check-${check.status.toLowerCase().replaceAll(' ', '-')}`}><div className="check-card-top"><div className="check-name"><span className="check-icon">{check.status === 'PASS' ? <ShieldCheck size={16} /> : check.status === 'FINDING' ? <AlertTriangle size={16} /> : <CircleHelp size={16} />}</span><div><h3>{check.title}</h3><small>Severity · {check.severity}</small></div></div><StatusPill status={check.status} /></div><p>{check.explanation}</p><div className="recommendation"><strong>Recommended action</strong><span>{check.recommendation}</span></div></article>
}

type RotationHistory = { event_id: string; state: string; verification_status: string; new_password_accepted: boolean; old_password_rejected: boolean; created_at: string }

export function CredentialsPage() {
  const { activeDevice } = useAuth()
  const navigate = useNavigate()
  const [status, setStatus] = useState<CredentialStatus | null>(null)
  const [history, setHistory] = useState<RotationHistory[]>([])
  const [result, setResult] = useState<RotationResult | null>(null)
  const [showModal, setShowModal] = useState(false)
  const [verifyModal, setVerifyModal] = useState(false)
  const [showDemoHelp, setShowDemoHelp] = useState(false)
  const [showPasswords, setShowPasswords] = useState(false)
  const [current, setCurrent] = useState('')
  const [next, setNext] = useState('')
  const [confirm, setConfirm] = useState('')
  const [verificationCurrent, setVerificationCurrent] = useState('')
  const [verificationPrevious, setVerificationPrevious] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  async function load(device: Device) {
    setError('')
    try {
      const [credentialStatus, rotations] = await Promise.all([
        api<CredentialStatus>(`/api/devices/${device.id}/credential-status`),
        api<{ items: RotationHistory[] }>(`/api/devices/${device.id}/credentials/history`),
      ])
      setStatus(credentialStatus); setHistory(rotations.items)
      const last = rotations.items[0]
      if (last?.verification_status === 'VERIFIED' && last.new_password_accepted && last.old_password_rejected) {
        setResult({ device_id: device.id, device_name: device.name, credential_update: 'SUCCESS', new_credential_authentication: 'PASS', previous_credential_authentication: 'REJECTED', verification_status: 'VERIFIED', operation_mode: 'SIMULATION', verification_timestamp: last.created_at, event_id: last.event_id })
      }
    } catch (reason) { setError(errorMessage(reason)); setStatus(null); setHistory([]) }
  }
  useEffect(() => { setStatus(null); setHistory([]); setResult(null); setShowModal(false); setVerifyModal(false); setMessage(''); if (activeDevice) void load(activeDevice) }, [activeDevice?.id])

  async function rotate(event: FormEvent) {
    event.preventDefault(); setError(''); setMessage('')
    if (next !== confirm) { setError('New password and confirmation do not match.'); return }
    if (next.length < 10 || !/[A-Z]/.test(next) || !/[a-z]/.test(next) || !/\d/.test(next) || !/[^A-Za-z0-9]/.test(next)) { setError('Use 10+ characters with uppercase, lowercase, number, and symbol.'); return }
    if (current === next) { setError('Choose a password different from the current password.'); return }
    if (!activeDevice) return
    setBusy(true)
    try {
      const response = await api<RotationResult>(`/api/devices/${activeDevice.id}/credentials/rotate`, { method: 'POST', body: JSON.stringify({ current_password: current, new_password: next, confirm_password: confirm }) })
      if (response.verification_status !== 'VERIFIED' || response.new_credential_authentication !== 'PASS' || response.previous_credential_authentication !== 'REJECTED') throw new Error('The backend did not confirm both credential checks. No success result is shown.')
      setResult(response); setCurrent(''); setNext(''); setConfirm(''); setShowModal(false); setShowDemoHelp(false); setMessage('Backend verification confirmed the credential rotation.'); await load(activeDevice)
    } catch (reason) { setError(errorMessage(reason)) }
    finally { setBusy(false) }
  }

  async function verifyAgain(event: FormEvent) {
    event.preventDefault(); setError(''); setMessage('')
    if (!activeDevice) return
    setBusy(true)
    try {
      const response = await api<RotationResult>(`/api/devices/${activeDevice.id}/credentials/verify`, { method: 'POST', body: JSON.stringify({ current_password: verificationCurrent, previous_password: verificationPrevious }) })
      if (response.verification_status !== 'VERIFIED' || response.new_credential_authentication !== 'PASS' || response.previous_credential_authentication !== 'REJECTED') throw new Error('Verification did not confirm both credential checks.')
      setResult(response); setVerificationCurrent(''); setVerificationPrevious(''); setVerifyModal(false); setMessage('Verification passed: new password accepted and previous password rejected.'); await load(activeDevice)
    } catch (reason) { setError(errorMessage(reason)) }
    finally { setBusy(false) }
  }

  const passwordStrength = useMemo(() => {
    let score = 0
    if (next.length >= 10) score++
    if (/[A-Z]/.test(next) && /[a-z]/.test(next)) score++
    if (/\d/.test(next)) score++
    if (/[^A-Za-z0-9]/.test(next)) score++
    return score
  }, [next])

  return <div className="page-stack">
    <PageTitle eyebrow="CREDENTIAL CONTROL · 03" title="Hardware Credential Management" description="Rotate and verify credentials for the active synthetic BMS profile." action={activeDevice && <span className="page-device-tag"><span className="status-dot" />{activeDevice.name}</span>} />
    {error && <div className="toast toast-error" role="alert"><AlertTriangle size={16} />{error}<button className="icon-button" aria-label="Dismiss error" onClick={() => setError('')}><X size={15} /></button></div>}
    {message && <div className="toast toast-success" role="status"><Check size={16} />{message}<button className="icon-button" aria-label="Dismiss message" onClick={() => setMessage('')}><X size={15} /></button></div>}
    {!activeDevice ? <Panel><EmptyState title="No active simulator device">Choose a BMS in <Link to="/connection">Bluetooth Connection</Link> before managing its demo credential.</EmptyState></Panel> : <>
      <SimulatedNote><strong>Simulation only.</strong> This workflow changes the backend’s simulated credential state, not a physical BMS.</SimulatedNote>
      <div className="credential-overview-grid"><Panel className="credential-device-card"><div className="credential-device-head"><div className="credential-device-icon"><KeyRound size={20} /></div><span className="tag tag-demo">DEMO PROFILE</span></div><span className="eyebrow">ACTIVE BMS IDENTITY</span><h2>{activeDevice.name}</h2><p>{activeDevice.manufacturer} · {activeDevice.model}</p><div className="credential-device-meta"><InfoCell label="Firmware" value={activeDevice.firmware} /><InfoCell label="Interface" value={activeDevice.interface} /></div></Panel>
        <div className="credential-stat-stack"><Metric label="Rotation status" value={status?.rotated ? 'Rotated' : 'Ready'} detail={status?.last_rotation_at ? `Last change ${prettyDate(status.last_rotation_at)}` : 'Demo credential available'} icon={<RefreshCcw size={16} />} /><Metric label="Verification" value={status?.last_verification_status ?? 'NOT TESTED'} detail={status?.last_verification_status === 'VERIFIED' ? 'Backend confirmed' : 'Run after rotation'} icon={<ShieldCheck size={16} />} /><Metric label="Rotation history" value={status?.rotation_count ?? 0} detail="For this account and profile" icon={<Clock3 size={16} />} /></div></div>

      {result && result.verification_status === 'VERIFIED' && <Panel className="rotation-success"><div className="success-title"><div className="success-icon"><Check size={22} /></div><div><span className="tag tag-success">SIMULATED ROTATION VERIFIED</span><h2>PASSWORD CHANGED SUCCESSFULLY</h2><p>{result.device_name} · Operation mode: simulation</p></div></div><div className="success-results"><ResultItem title="Credential update" value="SUCCESS" passed /><ResultItem title="New credential authentication" value="PASS" passed /><ResultItem title="Previous credential authentication" value="REJECTED" passed /><ResultItem title="Verification status" value="VERIFIED" passed /></div><div className="success-steps"><StepLine text="Current credential authenticated" done /><StepLine text="New credential applied" done /><StepLine text="New credential accepted" done /><StepLine text="Old credential rejected" done /><StepLine text="Rotation verified" done /></div><div className="success-meta"><span><Clock3 size={14} /> {prettyDate(result.verification_timestamp)}</span><span><Fingerprint size={14} /> Audit event · <code>{result.event_id}</code></span></div><div className="success-actions"><button className="button button-secondary" onClick={() => setVerifyModal(true)}><RefreshCcw size={15} /> Run Verification Again</button><button className="button button-quiet" onClick={() => navigate('/assessment')}>View Security Assessment <ArrowRight size={15} /></button></div></Panel>}

      {!status?.rotated && <Panel className="demo-help"><div className="demo-help-icon"><CircleHelp size={18} /></div><div className="demo-help-copy"><span className="eyebrow">SIMULATOR-ONLY HELP</span><h3>Need the initial demo password?</h3><p>This credential is seeded separately for your account on each synthetic demo profile.</p></div><button className="button button-secondary" onClick={() => setShowDemoHelp(!showDemoHelp)}>{showDemoHelp ? 'Hide credential' : 'Reveal demo credential'}</button>{showDemoHelp && <div className="revealed-credential"><span>INITIAL DEMO PASSWORD</span><code>Demo@1234</code><small>Use before the first rotation. It will stop working as soon as you change it.</small></div>}</Panel>}

      {status?.rotated && !result && <Panel className="rotated-summary"><div><span className="tag tag-success">ROTATED</span><h3>Credential state persists for {activeDevice.name}</h3><p>The current password is private to you. Use verification to retest it and reject the previous password.</p></div><button className="button button-secondary" onClick={() => setVerifyModal(true)}><RefreshCcw size={15} /> Verify credentials</button></Panel>}

      <Panel className="rotation-action-panel"><div className="rotation-action-copy"><div className="rotation-icon"><KeyRound size={19} /></div><div><span className="eyebrow">PASSWORD ROTATION</span><h2>{status?.rotated ? 'Change the simulated password again' : 'Ready to change this demo password?'}</h2><p>Current password is checked by the backend. New credentials are hashed and never returned or written to the audit log.</p></div></div><button className="button button-primary" onClick={() => { setShowModal(true); setError('') }}><KeyRound size={15} /> Change Password</button></Panel>

      <Panel className="credential-history"><SectionHeading title="Rotation history" aside={<span className="history-count">{history.length} RECORD{history.length === 1 ? '' : 'S'}</span>} />{history.length ? <div className="history-list">{history.map((entry, i) => <div className="history-row" key={entry.event_id}><span className="history-index">{String(i + 1).padStart(2, '0')}</span><div><strong>Simulated password rotation</strong><small>{prettyDate(entry.created_at)} · {entry.state}</small></div><span>{entry.new_password_accepted ? 'New accepted' : 'New not verified'}</span><StatusPill status={entry.verification_status} /></div>)}</div> : <div className="history-empty"><Clock3 size={16} /> No rotations yet. The initial demo password remains active.</div>}</Panel>
    </>}

    {showModal && activeDevice && <div className="modal-backdrop" role="presentation"><div className="modal-card" role="dialog" aria-modal="true" aria-labelledby="rotate-title"><div className="modal-header"><div><span className="eyebrow">SIMULATED OPERATION</span><h2 id="rotate-title">Change demo password</h2></div><button className="icon-button" aria-label="Close" onClick={() => setShowModal(false)}><X size={18} /></button></div><p className="modal-device"><BatteryCharging size={15} /> {activeDevice.name}</p><form className="auth-form rotation-form" onSubmit={rotate}><label>Current demo password<input type={showPasswords ? 'text' : 'password'} autoComplete="current-password" value={current} onChange={e => setCurrent(e.target.value)} required /></label><label>New password<input type={showPasswords ? 'text' : 'password'} autoComplete="new-password" value={next} onChange={e => setNext(e.target.value)} required /></label><div className="strength-meter" aria-label={`Password strength ${passwordStrength} of 4`}>{[1, 2, 3, 4].map(i => <span key={i} className={passwordStrength >= i ? `strength-${passwordStrength}` : ''} />)}<small>{passwordStrength < 2 ? 'Weak' : passwordStrength < 4 ? 'Fair' : 'Strong'}</small></div><label>Confirm new password<input type={showPasswords ? 'text' : 'password'} autoComplete="new-password" value={confirm} onChange={e => setConfirm(e.target.value)} required /></label><label className="checkbox-label show-password-check"><input type="checkbox" checked={showPasswords} onChange={e => setShowPasswords(e.target.checked)} /> Show passwords</label><p className="field-hint">At least 10 characters with uppercase, lowercase, number, and symbol.</p>{error && <div role="alert" className="inline-error">{error}</div>}<div className="modal-actions"><button type="button" className="button button-quiet" onClick={() => setShowModal(false)}>Cancel</button><button className="button button-primary" disabled={busy}>{busy ? <span className="spinner" /> : <KeyRound size={15} />}{busy ? 'Verifying…' : 'Change Password'}</button></div></form></div></div>}

    {verifyModal && activeDevice && <div className="modal-backdrop" role="presentation"><div className="modal-card" role="dialog" aria-modal="true" aria-labelledby="verify-title"><div className="modal-header"><div><span className="eyebrow">BACKEND VERIFICATION</span><h2 id="verify-title">Verify the rotation again</h2></div><button className="icon-button" aria-label="Close" onClick={() => setVerifyModal(false)}><X size={18} /></button></div><p className="modal-description">Enter the active password and the previous password. EV Shield will confirm the active one succeeds and the previous one fails.</p><form className="auth-form rotation-form" onSubmit={verifyAgain}><label>Current demo password<input type={showPasswords ? 'text' : 'password'} autoComplete="current-password" value={verificationCurrent} onChange={e => setVerificationCurrent(e.target.value)} required /></label><label>Previous demo password<input type={showPasswords ? 'text' : 'password'} autoComplete="current-password" value={verificationPrevious} onChange={e => setVerificationPrevious(e.target.value)} required /></label><label className="checkbox-label show-password-check"><input type="checkbox" checked={showPasswords} onChange={e => setShowPasswords(e.target.checked)} /> Show passwords</label>{error && <div role="alert" className="inline-error">{error}</div>}<div className="modal-actions"><button type="button" className="button button-quiet" onClick={() => setVerifyModal(false)}>Cancel</button><button className="button button-primary" disabled={busy}>{busy ? <span className="spinner" /> : <ShieldCheck size={15} />}{busy ? 'Checking…' : 'Run Verification'}</button></div></form></div></div>}
  </div>
}

function ResultItem({ title, value, passed }: { title: string; value: string; passed: boolean }) { return <div className="result-item"><span className={`result-check ${passed ? '' : 'result-failed'}`}>{passed ? <Check size={13} /> : <X size={13} />}</span><div><small>{title}</small><strong>{value}</strong></div></div> }

