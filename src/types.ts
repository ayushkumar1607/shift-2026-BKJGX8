export type User = { id: string; full_name: string; email: string | null; phone: string | null; demo_auth_mode: boolean }
export type Device = {
  id: string; name: string; manufacturer: string; model: string; firmware: string; interface: string
  device_identifier: string; documentation_status: string; default_credential_status: string; authentication_status: string; pairing_status: string
  encryption_status: string; firmware_status: string; credential_status: string; summary: string
  credential_rotation_supported: boolean; demo_profile: boolean; connection_status: string
}
export type Check = { key: string; title: string; status: string; severity: string; explanation: string; recommendation: string }
export type Assessment = {
  id: string; device_id: string; device_name: string; overall_status: string; score: number
  evidence_coverage: number; is_retest: boolean; created_at: string; checks: Check[]
}
export type CredentialStatus = {
  device_id: string; device_name: string; rotation_supported: boolean; operation_mode: 'SIMULATION'
  current_demo_credential_available: boolean; rotated: boolean; last_rotation_at: string | null
  last_verification_status: string; rotation_count: number
}
export type RotationResult = {
  device_id: string; device_name: string; credential_update: string; new_credential_authentication: string
  previous_credential_authentication: string; verification_status: string; operation_mode: string
  verification_timestamp: string; event_id: string
}

