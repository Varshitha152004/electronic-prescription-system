from sqlalchemy import create_engine, Column, String, Integer, ForeignKey, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from datetime import datetime

DATABASE_URL = "mysql+pymysql://root:Varshi-950@localhost/prescription_db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

Base = declarative_base()

# ============================
# PATIENT TABLE
# ============================

class Patient(Base):
    __tablename__ = "patients"

    patient_id = Column(String(50), primary_key=True)

    medications = relationship(
        "Medication",
        back_populates="patient",
        cascade="all, delete"
    )

    history = relationship(
        "PrescriptionHistory",
        back_populates="patient",
        cascade="all, delete"
    )


# ============================
# MEDICATION TABLE
# ============================

class Medication(Base):
    __tablename__ = "medications"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(String(50), ForeignKey("patients.patient_id"))
    drug_name = Column(String(100))

    patient = relationship("Patient", back_populates="medications")


# ============================
# PRESCRIPTION HISTORY TABLE
# ============================

class PrescriptionHistory(Base):
    __tablename__ = "prescription_history"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(String(50), ForeignKey("patients.patient_id"))
    doctor_id = Column(String(50))
    drugs = Column(String(500))
    risk_level = Column(String(50))
    timestamp = Column(DateTime, default=datetime.utcnow)

    patient = relationship("Patient", back_populates="history")


# ============================
# DOCTOR TABLE
# ============================

class Doctor(Base):
    __tablename__ = "doctors"

    doctor_id = Column(String(50), primary_key=True)
    name = Column(String(100))
    password = Column(String(200))
    role = Column(String(50))


def init_db():
    Base.metadata.create_all(bind=engine)
