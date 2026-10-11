import type { ReactNode } from 'react'
import { ArrowUpRight, BatteryCharging, Check, CircleHelp, LockKeyhole, Shield, ShieldAlert, ShieldCheck, Wifi } from 'lucide-react'

export function Brand({ compact = false }: { compact?: boolean }) {
  return <div className={`brand ${compact ? 'brand-compact' : ''}`}><div className="brand-mark"><Shield size={19} strokeWidth={2.4} /><BatteryCharging size={12} className="brand-battery" /></div>{!compact && <div><strong>EV <span>Shield</span></strong><small>BMS SECURITY PLATFORM</small></div>}</div>
}

export function DemoBanner() {
  return <div className="demo-banner"><span className="demo-pulse" /> DEMO MODE <i>All device and credential operations are simulated</i><span className="banner-sim">SIMULATION</span></div>
}

export function StatusPill({ status }: { status: string }) {
  const normalized = status.toLowerCase().replaceAll(' ', '-')
  const icon = status === 'PASS' || status === 'VERIFIED' || status === 'CONNECTED' ? <ShieldCheck size={13} /> : status === 'FINDING' || status.includes('ATTENTION') ? <ShieldAlert size={13} /> : status === 'UNKNOWN' ? <CircleHelp size={13} /> : null
  return <span className={`status-pill status-${normalized}`}>{icon}{status}</span>
}

export function Panel({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <section className={`panel ${className}`}>{children}</section>
}

export function PageTitle({ eyebrow, title, description, action }: { eyebrow: string; title: string; description: string; action?: ReactNode }) {
  return <div className="page-title-row"><div><div className="eyebrow">{eyebrow}</div><h1>{title}</h1><p>{description}</p></div>{action && <div className="page-title-action">{action}</div>}</div>
}

export function EmptyState({ title, children }: { title: string; children: ReactNode }) {
  return <div className="empty-state"><div className="empty-icon"><Wifi size={21} /></div><strong>{title}</strong><p>{children}</p></div>
}

export function Metric({ label, value, detail, icon }: { label: string; value: string | number; detail: string; icon: ReactNode }) {
  return <div className="metric-card"><div className="metric-top"><span>{label}</span><i>{icon}</i></div><strong>{value}</strong><small>{detail}</small></div>
}

export function SectionHeading({ title, aside }: { title: string; aside?: ReactNode }) {
  return <div className="section-heading"><h2>{title}</h2>{aside}</div>
}

export function StepLine({ text, done }: { text: string; done: boolean }) {
  return <div className={`step-line ${done ? 'step-done' : ''}`}><span>{done ? <Check size={13} /> : <span className="step-dot" />}</span>{text}<ArrowUpRight className="step-arrow" size={13} /></div>
}

export function SimulatedNote({ children }: { children: ReactNode }) {
  return <div className="sim-note"><LockKeyhole size={16} /><span>{children}</span></div>
}

