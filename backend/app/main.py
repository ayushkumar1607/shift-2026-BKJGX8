from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text
from app.db.session import Base, engine, SessionLocal
from app.models.entities import User, Vehicle, Incident
from app.models.entities import Assessment
from app.services.simulator import assess
from app.api.routes import router

app=FastAPI(title="EV Shield API",version="1.0.0",description="Software-first battery security platform. Simulator results are not physical device measurements.")
app.add_middleware(CORSMiddleware,allow_origins=["http://localhost:5173"],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])
app.include_router(router)
# Existing local databases predate phone sign-in; add the nullable contact column in place.
if "users" in inspect(engine).get_table_names() and "phone" not in {c["name"] for c in inspect(engine).get_columns("users")}:
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE users ADD COLUMN phone VARCHAR(32)"))
Base.metadata.create_all(bind=engine)

def seed():
    db=SessionLocal()
    try:
        demo=db.query(User).filter_by(email="demo@evshield.local").first()
        if not demo:
            demo=User(email="demo@evshield.local",role="OWNER_DRIVER",verified=True); db.add(demo); db.commit(); db.refresh(demo)
            db.add_all([Vehicle(registration="UP65-DEMO-042",display_name="Meena Devi's Demo E-Rickshaw",location="Varanasi Demo Zone",organisation="Ganga E-Rickshaw Cooperative (Demo)",bms_profile="EVS-SIM-BMS-01",owner_id=demo.id,demo=True),Vehicle(registration="UP65-DEMO-043",display_name="Demo E-Rickshaw 043",location="Varanasi Demo Zone",organisation="Ganga E-Rickshaw Cooperative (Demo)",bms_profile="EVS-SIM-BMS-01",owner_id=demo.id,demo=True)])
            db.commit()
            primary=db.query(Vehicle).filter_by(registration="UP65-DEMO-042").first(); result=assess(primary); db.add(Assessment(vehicle_id=primary.id,results=result,coverage=result["coverage"],score=result["score"],simulated=True))
            v=db.query(Vehicle).filter_by(registration="UP65-DEMO-043").first(); db.add(Incident(reference="EVS-DEMO-043",category="Bluetooth exposure concern",description="Demonstration report for workflow display. Allegation only; not evidence of wrongdoing.",vehicle_id=v.id,reporter_id=demo.id,demo=True)); db.commit()
    finally: db.close()
seed()

@app.get("/health")
def health(): return {"status":"ok"}
