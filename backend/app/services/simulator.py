from datetime import datetime, timezone

CHECKS = [
    ("PROFILE_CONSISTENCY", "Integration", "PASS", "Low", "Simulator profile metadata", "Profile matches the demonstration profile."),
    ("CONFIG_AUTH", "Authentication and authorization", "FINDING", "High", "Simulated shim policy test", "Sensitive configuration was accepted without expected authentication."),
    ("PAIRING_RESTRICTION", "Bluetooth exposure", "UNKNOWN", None, "Not tested", "Pairing restrictions have not been measured."),
    ("FIRMWARE_INTEGRITY", "Firmware integrity", "UNKNOWN", None, "Not tested", "No verified firmware integrity evidence is available."),
    ("TRANSPORT_ENCRYPTION", "Transport protection", "UNKNOWN", None, "Not tested", "Transport encryption has not been tested."),
]

def assess(vehicle):
    rows=[]
    for ident, category, status, severity, evidence, explanation in CHECKS:
        if ident == "CONFIG_AUTH" and vehicle.policy_enabled:
            status, severity, evidence, explanation = "PASS", None, "Simulated unauthorized and authorized request trace", "Unauthorized request rejected by shim; authorized request succeeded."
        rows.append({"check_id":ident,"category":category,"status":status,"severity":severity,"evidence_source":evidence,"explanation":explanation,"recommended_action":"Apply simulated authentication policy" if status=="FINDING" else "Review when documented evidence is available","simulated":True,"timestamp":datetime.now(timezone.utc).isoformat()})
    completed=[r for r in rows if r["status"] in ("PASS","FINDING")]
    score=round(100*sum(r["status"]=="PASS" for r in completed)/max(1,len(completed)))
    return {"checks":rows,"coverage":round(100*len(completed)/len(rows)),"score":score,"score_note":"Score uses completed checks only; unknown checks are excluded.","simulated":True}

def shim_request(vehicle, authorized=False, action="READ_CONFIG"):
    if action == "CONTROL_BATTERY": return {"accepted":False,"forwarded":False,"reason":"CONTROL_BATTERY is blocked by policy."}
    if not authorized and vehicle.policy_enabled:
        return {"accepted":False,"forwarded":False,"reason":"Simulated shim rejected unauthorized request; it was not forwarded."}
    if not authorized:
        return {"accepted":True,"forwarded":True,"reason":"Initial demonstration policy allowed the request; finding recorded."}
    return {"accepted":True,"forwarded":True,"reason":"Authorized simulated request succeeded."}
