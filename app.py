import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt

API_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="Clinical EMR System",
    layout="wide",
    initial_sidebar_state="expanded"
)

def _safe_json(response):
    try:
        return response.json()
    except:
        return {"error": "Server Error"}

# =====================================================
# LOGIN
# =====================================================

if "doctor" not in st.session_state:

    st.markdown("## 🏥 Clinical EMR System")
    st.markdown("### Doctor Login")

    doctor_id = st.text_input("Doctor ID")
    password = st.text_input("Password", type="password")

    if st.button("Login", use_container_width=True):

        response = requests.post(
            f"{API_URL}/login_doctor",
            json={"doctor_id": doctor_id, "password": password}
        )

        data = _safe_json(response)

        if "error" in data:
            st.error(data["error"])
        else:
            st.session_state["doctor"] = data
            st.success("Login successful")
            st.rerun()

    st.stop()

# =====================================================
# HEADER
# =====================================================

st.title("🏥 Clinical Prescription Management System")
st.caption("Patient-centered medication intelligence dashboard")

st.sidebar.write(f"Logged in as: {st.session_state['doctor']['doctor_id']}")
st.sidebar.header("Navigation")

menu = ["Patient Dashboard", "Add Patient"]

if st.session_state["doctor"].get("role") == "admin":
    menu += ["Delete Patient", "Analytics"]

choice = st.sidebar.radio("Go to", menu)

if st.sidebar.button("Logout"):
    del st.session_state["doctor"]
    st.rerun()

# =====================================================
# ADD PATIENT
# =====================================================

if choice == "Add Patient":

    st.subheader("➕ Create New Patient")

    patient_id = st.text_input("Patient ID")
    medications = st.text_input("Initial Medications (comma separated)")

    if st.button("Create Patient"):

        meds = [m.strip() for m in medications.split(",")] if medications else []

        response = requests.post(
            f"{API_URL}/add_patient",
            json={"patient_id": patient_id, "medications": meds}
        )

        data = _safe_json(response)

        if "error" in data:
            st.error(data["error"])
        else:
            st.success(data["message"])

# =====================================================
# DELETE PATIENT (ADMIN)
# =====================================================

elif choice == "Delete Patient":

    st.subheader("🗑 Delete Patient")

    patient_id = st.text_input("Patient ID to Delete")

    if st.button("Delete Patient"):

        response = requests.delete(
            f"{API_URL}/delete_patient/{patient_id}"
        )

        data = _safe_json(response)

        if "error" in data:
            st.error(data["error"])
        else:
            st.success(data["message"])

# =====================================================
# ANALYTICS
# =====================================================

elif choice == "Analytics":

    st.subheader("📊 System Analytics")

    response = requests.get(f"{API_URL}/analytics")
    data = _safe_json(response)

    if "error" in data:
        st.error("Analytics unavailable")
    else:

        c1, c2, c3, c4 = st.columns(4)

        c1.metric("Patients", data.get("total_patients", 0))
        c2.metric("Prescriptions", data.get("total_prescriptions", 0))
        c3.metric("High Risk", data.get("high_risk", 0))
        c4.metric("Medium Risk", data.get("medium_risk", 0))

        st.markdown("### Risk Distribution")

        labels = ["High", "Medium", "Low", "Safe"]
        values = [
            data.get("high_risk", 0),
            data.get("medium_risk", 0),
            data.get("low_risk", 0),
            data.get("safe", 0)
        ]

        fig, ax = plt.subplots()
        ax.bar(labels, values)
        st.pyplot(fig)

# =====================================================
# PATIENT DASHBOARD
# =====================================================

else:

    st.subheader("🧑‍⚕️ Patient Clinical Dashboard")

    patient_id_input = st.text_input("Enter Patient ID")

    if st.button("Load Patient"):

        response = requests.get(f"{API_URL}/get_patient/{patient_id_input}")
        data = _safe_json(response)

        if "error" in data:
            st.error(data["error"])
        else:
            st.session_state["patient_id"] = patient_id_input
            st.session_state["medications"] = data.get("medications", [])
            st.success("Patient loaded successfully")

    if "patient_id" in st.session_state:

        st.markdown("---")

        # ==========================
        # CURRENT MEDICATIONS
        # ==========================

        st.markdown("### 💊 Current Medications")

        if st.session_state["medications"]:

            for idx, med in enumerate(st.session_state["medications"]):

                col1, col2 = st.columns([4, 1])
                col1.write(med)

                if col2.button("Remove", key=f"remove_{idx}"):

                    requests.delete(
                        f"{API_URL}/delete_medication/{st.session_state['patient_id']}/{med}"
                    )

                    response = requests.get(
                        f"{API_URL}/get_patient/{st.session_state['patient_id']}"
                    )

                    updated = _safe_json(response)
                    st.session_state["medications"] = updated.get("medications", [])
                    st.rerun()

        else:
            st.info("No medications recorded")

        st.markdown("---")

        # ==========================
        # HISTORY TABLE
        # ==========================

        st.markdown("### 📜 Prescription History")

        history_response = requests.get(
            f"{API_URL}/get_history/{st.session_state['patient_id']}"
        )

        history_data = _safe_json(history_response)

        if isinstance(history_data, list) and history_data:

            df = pd.DataFrame(history_data)

            df = df.rename(columns={
                "doctor_id": "Doctor",
                "drugs": "Prescribed Drugs",
                "risk_level": "Risk Level",
                "timestamp": "Date & Time"
            })

            st.dataframe(df, use_container_width=True)

        else:
            st.info("No prescription history available.")

        st.markdown("---")

        # ==========================
        # NEW PRESCRIPTION
        # ==========================

        st.subheader("➕ New Prescription")

        new_drugs = st.text_input("Enter new drugs (comma separated)")

        if st.button("Analyze Prescription"):

            drug_list = [d.strip() for d in new_drugs.split(",")]

            response = requests.post(
                f"{API_URL}/check_with_history",
                json={
                    "patient_id": st.session_state["patient_id"],
                    "new_drugs": drug_list
                }
            )

            data = _safe_json(response)

            if "error" in data:
                st.error(data["error"])
            else:
                st.session_state["analysis"] = data
                st.session_state["pending"] = drug_list

        # ==========================
        # SAFETY RESULT
        # ==========================

        if "analysis" in st.session_state:

            data = st.session_state["analysis"]

            st.markdown("### 🔍 Safety Analysis Report")

            if data["status"] == "Safe":
                st.success("✔ No harmful interactions detected.")
            else:

                if data["status"] == "High Risk":
                    st.error("🚨 HIGH RISK INTERACTION DETECTED")
                elif data["status"] == "Medium Risk":
                    st.warning("⚠ MEDIUM RISK INTERACTION")
                else:
                    st.info("ℹ LOW RISK INTERACTION")

                st.write(f"Total Interactions Found: {data['total_interactions']}")
                st.markdown("---")

                for interaction in data["interactions"]:

                    st.markdown("#### Interaction Details")

                    st.write(f"Drug A: {interaction['drug_a']}")
                    st.write(f"Drug B: {interaction['drug_b']}")
                    st.write(f"Severity: {interaction['severity']}")
                    st.write(f"Mechanism: {interaction['mechanism']}")
                    st.write(f"Clinical Effect: {interaction['effect']}")
                    st.write(f"Safer Alternative: {interaction['safer_alternative']}")
                    st.write(f"Rationale: {interaction['rationale']}")
                    st.markdown("---")

            # 👇 Confirm button OUTSIDE risk condition
            if st.button("Confirm Prescription"):
                confirm = requests.post(
                    f"{API_URL}/confirm_prescription",
                    json={
                        "patient_id": st.session_state["patient_id"],
                        "new_drugs": st.session_state["pending"],
                        "doctor_id": st.session_state["doctor"]["doctor_id"]
                    }
                )

                confirm_data = _safe_json(confirm)

                if "error" in confirm_data:
                    st.error(confirm_data["error"])
                else:
                    st.success(confirm_data["message"])

                    response = requests.get(
                        f"{API_URL}/get_patient/{st.session_state['patient_id']}"
                    )

                    updated = _safe_json(response)
                    st.session_state["medications"] = updated.get("medications", [])

                    st.session_state.pop("analysis")
                    st.session_state.pop("pending")

                    st.rerun()
