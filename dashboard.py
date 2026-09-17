import streamlit as st
import pandas as pd
from pathlib import Path
import pickle


# ============================================
# PROJECT PATHS
# ============================================

BASE_DIR = Path(r"C:\Users\huggi\Documents\SIH26001_Landslide_EWS").parent.parent

TERRAIN_FILE = BASE_DIR / "data" / "terrain_data.csv"
MODEL_FILE = BASE_DIR / "model" / "landslide_model.pkl"


# ============================================
# PAGE SETTINGS
# ============================================

st.set_page_config(
    page_title="Landslide Early Warning System",
    page_icon="⚠️",
    layout="wide"
)


# ============================================
# LOAD DATA
# ============================================

terrain_data = pd.read_csv(TERRAIN_FILE)

with open(MODEL_FILE, "rb") as file:
    model = pickle.load(file)


# ============================================
# TITLE
# ============================================

st.title("Landslide Early Warning System")
st.write("Rainfall and Terrain Based Risk Assessment")


# ============================================
# USER INPUT
# ============================================

st.header("Enter Current Conditions")

location = st.selectbox(
    "Select Location",
    terrain_data["location"].tolist()
)

rainfall = st.number_input(
    "Rainfall (mm)",
    min_value=0.0,
    value=60.0,
    step=1.0
)

duration = st.number_input(
    "Rainfall Duration (hours)",
    min_value=0.1,
    value=4.0,
    step=0.5
)


# ============================================
# TERRAIN DATA
# ============================================

location_data = terrain_data[
    terrain_data["location"] == location
].iloc[0]

elevation = float(location_data["elevation_m"])
slope = float(location_data["slope_deg"])


# ============================================
# CALCULATE RAINFALL
# ============================================

intensity = rainfall / duration

threshold = 20

if intensity >= threshold:
    rainfall_risk = "HIGH"
else:
    rainfall_risk = "NORMAL"


# ============================================
# ML PREDICTION
# ============================================

prediction = model.predict(
    [[elevation, slope, rainfall]]
)[0]

probability = model.predict_proba(
    [[elevation, slope, rainfall]]
)[0][1] * 100


# ============================================
# FINAL RISK
# ============================================

if rainfall_risk == "HIGH" and prediction == 1:
    final_risk = "CRITICAL"

elif rainfall_risk == "HIGH" or prediction == 1:
    final_risk = "HIGH"

else:
    final_risk = "LOW"


# ============================================
# DISPLAY RESULTS
# ============================================

st.header("Risk Assessment")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Rainfall", f"{rainfall:.1f} mm")

with col2:
    st.metric("Intensity", f"{intensity:.2f} mm/hr")

with col3:
    st.metric("Elevation", f"{elevation:.0f} m")

with col4:
    st.metric("Slope", f"{slope:.0f}°")


st.subheader("Assessment")

st.write("Rainfall Risk:", rainfall_risk)

if prediction == 1:
    st.write("ML Prediction: LANDSLIDE RISK")
else:
    st.write("ML Prediction: NO LANDSLIDE RISK")

st.write(
    "ML Landslide Probability:",
    f"{probability:.2f}%"
)

st.subheader("Final Risk Level")

if final_risk == "CRITICAL":
    st.error("CRITICAL — Immediate attention required")

elif final_risk == "HIGH":
    st.warning("HIGH — Landslide risk detected")

else:
    st.success("LOW — No immediate high-risk condition detected")
