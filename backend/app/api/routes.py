import secrets
import re
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Header
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.entities import User, Vehicle, Assessment, AuditEvent, Incident, RotationJob
from app.core.config import SECRET_KEY, REAL_BMS_WRITES, OTP_MODE
from app.services.simulator import assess, shim_request

router=APIRouter(prefix="/api/v1")
_otp={}
_otp_sent={}

def user_dep(authorization: str|None=Header(default=None), db:Session=Depends(get_db)):
    if not authorization: raise HTTPException(401,"Sign in required")
    try: uid=jwt.decode(authorization.removeprefix("Bearer "),SECRET_KEY,algorithms=["HS256"]).get("sub")
    except JWTError: raise HTTPException(401,"Invalid or expired session")
    user=db.get(User,int(uid))
    if not user: raise HTTPException(401,"Session user not found")
    return user

def get_vehicle(db,user,vehicle_id):
    v=db.get(Vehicle,vehicle_id)
    if not v or (user.role != "PLATFORM_ADMIN" and v.owner_id != user.id): raise HTTPException(404,"Vehicle not found")
    return v

@router.post("/auth/request-otp")
def request_otp(body:dict,db:Session=Depends(get_db)):
    email=str(body.get("email","")).lower().strip()
    phone=re.sub(r"[\s().-]", "", str(body.get("phone", "")))
    if email:
        if "@" not in email: raise HTTPException(422,"Valid email is required")
        channel, contact, key = "email", email, email
        user=db.query(User).filter_by(email=email).first()
    else:
        if not re.fullmatch(r"\+[1-9]\d{7,14}", phone):
            raise HTTPException(422,"Enter a phone number with country code, such as +91 98765 43210")
        channel, contact, key = "phone", phone, phone
        user=db.query(User).filter_by(phone=phone).first()
    current=datetime.now(timezone.utc)
    prior=_otp_sent.get(key)
    if prior and (current-prior).total_seconds()<30: raise HTTPException(429,"Please wait before requesting another code")
    _otp_sent[key]=current
    if not user:
        user=User(email=email or f"phone-{phone[1:]}@phone.evshield.local", phone=phone or None)
        db.add(user); db.commit(); db.refresh(user)
    # Demonstration challenge is process-local and never logged. Real providers are intentionally opt-in.
    code=f"{secrets.randbelow(1_000_000):06d}"
    _otp[(channel,contact)]=(code,current+timedelta(minutes=5))
    message="No email provider is configured; no email was sent." if channel=="email" else "SMS delivery is not configured; no text message was sent."
    return {"channel":channel,"message":message,"development_otp":code if OTP_MODE=="development" else None}

@router.post("/auth/verify-otp")
def verify_otp(body:dict,db:Session=Depends(get_db)):
    email=str(body.get("email","")).lower().strip()
    phone=re.sub(r"[\s().-]", "", str(body.get("phone", "")))
    channel, contact = ("email", email) if email else ("phone", phone)
    item=_otp.get((channel,contact))
    if not item or item[0]!=str(body.get("otp","")) or item[1]<datetime.now(timezone.utc): raise HTTPException(401,"Invalid or expired OTP")
    _otp.pop((channel,contact),None)
    user=db.query(User).filter_by(email=email).first() if channel=="email" else db.query(User).filter_by(phone=phone).first()
    if not user: raise HTTPException(401,"Sign-in account not found")
    user.verified=True; db.commit()
    token=jwt.encode({"sub":str(user.id),"exp":datetime.now(timezone.utc)+timedelta(hours=8)},SECRET_KEY,algorithm="HS256")
    return {"access_token":token,"token_type":"bearer","user":{"id":user.id,"email":user.email,"phone":user.phone,"role":user.role}}

@router.get("/me")
def me(user:User=Depends(user_dep)): return {"id":user.id,"email":user.email,"phone":user.phone,"role":user.role}

@router.get("/vehicles")
def vehicles(db:Session=Depends(get_db),user:User=Depends(user_dep)):
    q=db.query(Vehicle)
    if user.role != "PLATFORM_ADMIN": q=q.filter_by(owner_id=user.id)
    return [vehicle_dict(v) for v in q.all()]

def vehicle_dict(v): return {"id":v.id,"registration":v.registration,"display_name":v.display_name,"location":v.location,"organisation":v.organisation,"bms_profile":v.bms_profile,"demo":v.demo,"pairing":v.pairing,"firmware":v.firmware,"encryption":v.encryption}

@router.post("/vehicles")
def create_vehicle(body:dict,db:Session=Depends(get_db),user:User=Depends(user_dep)):
    if user.role not in ("OWNER_DRIVER","FLEET_MANAGER","PLATFORM_ADMIN"): raise HTTPException(403,"This role cannot register vehicles")
    if not body.get("registration") or not body.get("display_name"): raise HTTPException(422,"Registration and display name are required")
    if db.query(Vehicle).filter_by(registration=body["registration"]).first(): raise HTTPException(409,"Registration already exists")
    v=Vehicle(registration=body["registration"],display_name=body["display_name"],location=body.get("location","Unknown"),organisation=body.get("organisation",""),bms_profile=body.get("bms_profile","UNVERIFIED"),owner_id=user.id)
    db.add(v); db.commit(); db.refresh(v); return vehicle_dict(v)

@router.get("/vehicles/{vehicle_id}/assessment")
def get_assessment(vehicle_id:int,db:Session=Depends(get_db),user:User=Depends(user_dep)):
    v=get_vehicle(db,user,vehicle_id); a=db.query(Assessment).filter_by(vehicle_id=v.id).order_by(Assessment.id.desc()).first()
    return {"vehicle":vehicle_dict(v),**(a.results if a else assess(v)),"assessment_id":a.id if a else None,"coverage":a.coverage if a else assess(v)["coverage"],"score":a.score if a else assess(v)["score"]}

@router.post("/vehicles/{vehicle_id}/assessment")
def run_assessment(vehicle_id:int,db:Session=Depends(get_db),user:User=Depends(user_dep)):
    v=get_vehicle(db,user,vehicle_id); result=assess(v)
    a=Assessment(vehicle_id=v.id,results=result,coverage=result["coverage"],score=result["score"]); db.add(a); db.commit(); db.refresh(a)
    return {**result,"assessment_id":a.id}

@router.post("/vehicles/{vehicle_id}/remediation")
def remediate(vehicle_id:int,body:dict,db:Session=Depends(get_db),user:User=Depends(user_dep)):
    v=get_vehicle(db,user,vehicle_id)
    if user.role not in ("OWNER_DRIVER","WORKSHOP_TECH","FLEET_MANAGER","PLATFORM_ADMIN"): raise HTTPException(403,"This role cannot request remediation")
    if body.get("action")=="CONTROL_BATTERY":
        result=shim_request(v,False,"CONTROL_BATTERY")
    elif not v.demo: raise HTTPException(409,"Real-device remediation is unavailable: no validated adapter is registered.")
    else:
        v.policy_enabled=True; result=shim_request(v,False); authorized=shim_request(v,True)
        result={"policy_applied":True,"unauthorized_probe":result,"authorized_probe":authorized,"forwarded":False,"simulated":True}
    db.add(AuditEvent(vehicle_id=v.id,kind=body.get("action","APPLY_AUTH_POLICY"),outcome="BLOCKED" if result.get("accepted") is False else "COMPLETED",detail=str(result),simulated=True)); db.commit()
    return result

@router.get("/vehicles/{vehicle_id}/events")
def events(vehicle_id:int,db:Session=Depends(get_db),user:User=Depends(user_dep)):
    v=get_vehicle(db,user,vehicle_id)
    return [{"id":e.id,"kind":e.kind,"outcome":e.outcome,"detail":e.detail,"simulated":e.simulated,"created_at":e.created_at.isoformat()} for e in db.query(AuditEvent).filter_by(vehicle_id=v.id).order_by(AuditEvent.id.desc()).limit(100)]

@router.post("/vehicles/{vehicle_id}/bluetooth-events")
def bluetooth_event(vehicle_id:int,body:dict,db:Session=Depends(get_db),user:User=Depends(user_dep)):
    v=get_vehicle(db,user,vehicle_id)
    if user.role not in ("OWNER_DRIVER","WORKSHOP_TECH","FLEET_MANAGER","PLATFORM_ADMIN"):
        raise HTTPException(403,"This role cannot connect to vehicle devices")
    if v.demo:
        raise HTTPException(409,"Demo records cannot be used to connect to physical hardware")
    outcome=str(body.get("outcome",""))
    if outcome not in ("CONNECTED","DISCONNECTED","FAILED"):
        raise HTTPException(422,"Unsupported Bluetooth connection event")
    # Device names, Bluetooth identifiers, services and characteristic values are never accepted or logged.
    event=AuditEvent(vehicle_id=v.id,kind="BLE_GATT_LINK",outcome=outcome,detail="Browser Bluetooth link event recorded. No BMS services or characteristics were read or written.",simulated=False)
    db.add(event); db.commit(); db.refresh(event)
    return {"id":event.id,"outcome":event.outcome,"created_at":event.created_at.isoformat(),"data_access":"NONE"}

@router.get("/vehicles/{vehicle_id}/passport")
def passport(vehicle_id:int,db:Session=Depends(get_db),user:User=Depends(user_dep)):
    v=get_vehicle(db,user,vehicle_id); assessments=db.query(Assessment).filter_by(vehicle_id=v.id).order_by(Assessment.id.desc()).all()
    return {"vehicle":vehicle_dict(v),"notice":"DEMO DATA — NOT A REAL VEHICLE ASSESSMENT" if v.demo else None,"assessments":[{"id":a.id,"created_at":a.created_at.isoformat(),"coverage":a.coverage,"score":a.score,"results":a.results} for a in assessments],"events":[{"kind":e.kind,"outcome":e.outcome,"detail":e.detail,"created_at":e.created_at.isoformat()} for e in db.query(AuditEvent).filter_by(vehicle_id=v.id).all()]}

@router.post("/compatibility")
def compatibility(body:dict,user:User=Depends(user_dep)):
    complete=all(body.get(k) for k in ("manufacturer","model","firmware"))
    return {"status":"UNVERIFIED" if not complete else "NEEDS_CONFIGURATION","real_writes_enabled":False,"reason":"No device-specific adapter has completed documented protocol review and physical validation. Bluetooth availability does not establish credential-change support."}

@router.post("/vehicles/{vehicle_id}/rotation")
def rotation(vehicle_id:int,db:Session=Depends(get_db),user:User=Depends(user_dep)):
    v=get_vehicle(db,user,vehicle_id)
    if user.role not in ("OWNER_DRIVER","WORKSHOP_TECH","FLEET_MANAGER","PLATFORM_ADMIN"): raise HTTPException(403,"This role cannot request credential operations")
    job=RotationJob(vehicle_id=v.id,requested_by=user.id,status="UNSUPPORTED" if not v.demo else "SIMULATED_ONLY",detail="No documented validated credential-change operation. No physical change was attempted.",simulated=v.demo)
    db.add(job); db.flush()
    db.add(AuditEvent(vehicle_id=v.id,kind="CREDENTIAL_ROTATION",outcome=job.status,detail=job.detail,simulated=v.demo)); db.commit(); db.refresh(job)
    return {"job_id":job.id,"status":job.status,"real_write_performed":False,"timeline":[{"status":"REQUESTED"},{"status":"COMPATIBILITY_CHECKED","result":"No validated adapter"},{"status":"FAILED","reason":job.detail}]}

@router.get("/rotation-jobs/{job_id}")
def rotation_status(job_id:int,db:Session=Depends(get_db),user:User=Depends(user_dep)):
    job=db.get(RotationJob,job_id)
    if not job: raise HTTPException(404,"Rotation job not found")
    get_vehicle(db,user,job.vehicle_id)
    return {"job_id":job.id,"vehicle_id":job.vehicle_id,"status":job.status,"detail":job.detail,"simulated":job.simulated,"created_at":job.created_at.isoformat()}

@router.get("/incidents")
def incidents(db:Session=Depends(get_db),user:User=Depends(user_dep)):
    q=db.query(Incident)
    if user.role not in ("PLATFORM_ADMIN","AUTHORITY_REVIEWER","DISTRICT_ADMIN"): q=q.filter(Incident.reporter_id==user.id)
    return [incident_dict(i) for i in q.all()]

def incident_dict(i): return {"reference":i.reference,"category":i.category,"description":i.description,"status":i.status,"demo":i.demo,"created_at":i.created_at.isoformat()}

@router.post("/incidents")
def create_incident(body:dict,db:Session=Depends(get_db),user:User=Depends(user_dep)):
    v=get_vehicle(db,user,int(body["vehicle_id"])) if body.get("vehicle_id") else None
    i=Incident(reference="EVS-"+secrets.token_hex(4).upper(),category=body.get("category","Other"),description=body.get("description",""),reporter_id=user.id,vehicle_id=v.id if v else None,demo=bool(v and v.demo))
    db.add(i); db.commit(); db.refresh(i); return incident_dict(i)

@router.get("/dashboard")
def dashboard(db:Session=Depends(get_db),user:User=Depends(user_dep)):
    q=db.query(Vehicle)
    if user.role != "PLATFORM_ADMIN": q=q.filter_by(owner_id=user.id)
    vs=q.all(); return {"vehicles":len(vs),"assessments":sum(db.query(Assessment).filter_by(vehicle_id=v.id).count() for v in vs),"open_incidents":db.query(Incident).filter(Incident.status!="CLOSED").count(),"demo_vehicles":sum(v.demo for v in vs),"writes_enabled":REAL_BMS_WRITES}

@router.get("/safety/aggregate")
def aggregate(user:User=Depends(user_dep),db:Session=Depends(get_db)):
    if user.role not in ("AUTHORITY_REVIEWER","DISTRICT_ADMIN","PLATFORM_ADMIN"): raise HTTPException(403,"Authority role required")
    count=db.query(Incident).count()
    return {"threshold":5,"suppressed":count<5,"incident_count":None if count<5 else count,"message":"Counts below five are suppressed to protect privacy." if count<5 else "Aggregate reports are allegations and are not proof of wrongdoing."}
