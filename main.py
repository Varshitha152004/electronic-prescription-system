from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
from datetime import datetime, timezone

from interaction_engine import check_interactions
from database import (
    SessionLocal,
    init_db,
    Patient as DBPatient,
    Medication,
    PrescriptionHistory,
    Doctor
)

app = FastAPI()
init_db()

# ====================================================
# MODELS
# ====================================================

class DoctorLogin(BaseModel):
    doctor_id: str
    password: str

class PatientCreate(BaseModel):
    patient_id: str
    medications: List[str] = []

class PrescriptionCheck(BaseModel):
    patient_id: str
    new_drugs: List[str]

class PrescriptionConfirm(BaseModel):
    patient_id: str
    new_drugs: List[str]
    doctor_id: str


# ====================================================
# LOGIN
# ====================================================

@app.post("/login_doctor")
def login_doctor(data: DoctorLogin):

    db = SessionLocal()
    try:
        doctor = db.query(Doctor).filter(
            Doctor.doctor_id == data.doctor_id,
            Doctor.password == data.password
        ).first()

        if not doctor:
            return {"error": "Invalid credentials"}

        return {
            "doctor_id": doctor.doctor_id,
            "name": doctor.name,
            "role": doctor.role
        }

    finally:
        db.close()


# ====================================================
# PATIENT CRUD
# ====================================================

@app.post("/add_patient")
def add_patient(data: PatientCreate):

    db = SessionLocal()
    try:
        existing = db.query(DBPatient).filter(
            DBPatient.patient_id == data.patient_id
        ).first()

        if existing:
            return {"error": "Patient already exists"}

        db.add(DBPatient(patient_id=data.patient_id))

        for drug in data.medications:
            db.add(Medication(
                patient_id=data.patient_id,
                drug_name=drug.upper().strip()
            ))

        db.commit()
        return {"message": "Patient created successfully"}

    finally:
        db.close()


@app.delete("/delete_patient/{patient_id}")
def delete_patient(patient_id: str):

    db = SessionLocal()
    try:
        patient = db.query(DBPatient).filter(
            DBPatient.patient_id == patient_id
        ).first()

        if not patient:
            return {"error": "Patient not found"}

        db.delete(patient)
        db.commit()

        return {"message": "Patient deleted successfully"}

    finally:
        db.close()


@app.delete("/delete_medication/{patient_id}/{drug_name}")
def delete_medication(patient_id: str, drug_name: str):

    db = SessionLocal()
    try:
        med = db.query(Medication).filter(
            Medication.patient_id == patient_id,
            Medication.drug_name == drug_name.upper()
        ).first()

        if not med:
            return {"error": "Medication not found"}

        db.delete(med)
        db.commit()

        return {"message": "Medication removed"}

    finally:
        db.close()


@app.get("/get_patient/{patient_id}")
def get_patient(patient_id: str):

    db = SessionLocal()
    try:
        patient = db.query(DBPatient).filter(
            DBPatient.patient_id == patient_id
        ).first()

        if not patient:
            return {"error": "Patient not found"}

        meds = db.query(Medication).filter(
            Medication.patient_id == patient_id
        ).all()

        return {
            "patient_id": patient_id,
            "medications": [m.drug_name for m in meds]
        }

    finally:
        db.close()


# ====================================================
# CHECK PRESCRIPTION
# ====================================================

@app.post("/check_with_history")
def check_with_history(data: PrescriptionCheck):

    db = SessionLocal()
    try:
        # Fetch current medications
        meds = db.query(Medication).filter(
            Medication.patient_id == data.patient_id
        ).all()

        existing = [m.drug_name.upper().strip() for m in meds]
        new_drugs = [d.upper().strip() for d in data.new_drugs]

        combined = list(set(existing + new_drugs))

        engine_result = check_interactions(combined)

        interactions = engine_result.get("interactions", [])
        unknown = engine_result.get("unknown_drugs", [])

        # Determine overall status
        if not interactions:
            status = "Safe"
        else:
            severities = [i["severity"] for i in interactions]

            if "Major" in severities:
                status = "High Risk"
            elif "Moderate" in severities:
                status = "Medium Risk"
            else:
                status = "Low Risk"

        return {
            "status": status,
            "total_interactions": len(interactions),
            "interactions": interactions,
            "unknown_drugs": unknown
        }

    finally:
        db.close()



# ====================================================
# CONFIRM PRESCRIPTION
# ====================================================

@app.post("/confirm_prescription")
def confirm_prescription(data: PrescriptionConfirm):

    db = SessionLocal()
    try:
        meds = db.query(Medication).filter(
            Medication.patient_id == data.patient_id
        ).all()

        existing = [m.drug_name for m in meds]
        new_drugs = [d.upper().strip() for d in data.new_drugs]

        combined = existing + new_drugs

        engine_result = check_interactions(combined)
        results = engine_result.get("interactions", [])

        if not results:
            risk = "Safe"
        else:
            severities = [r["severity"] for r in results]

            if "Major" in severities:
                risk = "High Risk"
            elif "Moderate" in severities:
                risk = "Medium Risk"
            else:
                risk = "Low Risk"

        # Save new medications
        for drug in new_drugs:
            if drug not in existing:
                db.add(Medication(
                    patient_id=data.patient_id,
                    drug_name=drug
                ))

        # Save history record
        db.add(PrescriptionHistory(
            patient_id=data.patient_id,
            doctor_id=data.doctor_id,
            drugs=", ".join(new_drugs),
            risk_level=risk,
            timestamp=datetime.utcnow()
        ))

        db.commit()

        return {"message": f"Prescription saved. Risk Level: {risk}"}

    finally:
        db.close()


# ====================================================
# HISTORY TABLE
# ====================================================

@app.get("/get_history/{patient_id}")
def get_history(patient_id: str):

    db = SessionLocal()
    try:
        records = db.query(PrescriptionHistory).filter(
            PrescriptionHistory.patient_id == patient_id
        ).order_by(PrescriptionHistory.timestamp.desc()).all()

        result = []

        for r in records:
            ts = r.timestamp

            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)

            formatted = ts.astimezone().strftime("%Y-%m-%d %H:%M")

            result.append({
                "doctor_id": r.doctor_id,
                "drugs": r.drugs,
                "risk_level": r.risk_level,
                "timestamp": formatted
            })

        return result

    finally:
        db.close()


# ====================================================
# ANALYTICS
# ====================================================

@app.get("/analytics")
def analytics():

    db = SessionLocal()
    try:
        return {
            "total_patients": db.query(DBPatient).count(),
            "total_prescriptions": db.query(PrescriptionHistory).count(),
            "high_risk": db.query(PrescriptionHistory).filter(
                PrescriptionHistory.risk_level == "High Risk"
            ).count(),
            "medium_risk": db.query(PrescriptionHistory).filter(
                PrescriptionHistory.risk_level == "Medium Risk"
            ).count(),
            "low_risk": db.query(PrescriptionHistory).filter(
                PrescriptionHistory.risk_level == "Low Risk"
            ).count(),
            "safe": db.query(PrescriptionHistory).filter(
                PrescriptionHistory.risk_level == "Safe"
            ).count()
        }

    finally:
        db.close()
