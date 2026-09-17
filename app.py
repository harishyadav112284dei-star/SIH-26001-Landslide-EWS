from pathlib import Path
import pandas as pd
import pickle


# ============================================
# PROJECT PATHS
# ============================================

BASE_DIR = Path(__file__).resolve().parent

TERRAIN_FILE = BASE_DIR / "data" / "terrain_data.csv"
MODEL_FILE = BASE_DIR / "model" / "landslide_model.pkl"


# ============================================
# CHECK FILES
# ============================================

if not TERRAIN_FILE.exists():
    print("ERROR: terrain_data.csv not found!")
    print(TERRAIN_FILE)
    raise SystemExit

if not MODEL_FILE.exists():
    print("ERROR: landslide_model.pkl not found!")
    print(MODEL_FILE)
    raise SystemExit


# ============================================
# LOAD DATA AND MODEL
# ============================================

terrain_data = pd.read_csv(TERRAIN_FILE)

with open(MODEL_FILE, "rb") as file:
    model = pickle.load(file)


# ============================================
# RAINFALL RISK FUNCTION
# ============================================

def calculate_rainfall_risk(rainfall, duration, threshold):
    if duration <= 0:
        return 0, "INVALID"

    intensity = rainfall / duration

    if intensity >= threshold:
        risk = "HIGH"
    else:
        risk = "NORMAL"

    return intensity, risk


# ============================================
# USER INPUT
# ============================================

print("\n==============================================")
print("       LANDSLIDE EARLY WARNING SYSTEM")
print("==============================================")

print("\nAvailable Locations:")
print(terrain_data["location"].tolist())

location = input("\nEnter location: ").strip()

if location not in terrain_data["location"].values:
    print("ERROR: Location not found in terrain data.")
    raise SystemExit


rainfall = float(input("Enter rainfall (mm): "))
duration = float(input("Enter duration (hours): "))


# ============================================
# GET TERRAIN INFORMATION
# ============================================

location_data = terrain_data[
    terrain_data["location"] == location
].iloc[0]

elevation = float(location_data["elevation_m"])
slope = float(location_data["slope_deg"])


# ============================================
# RAINFALL ANALYSIS
# ============================================

threshold = 20

intensity, rainfall_risk = calculate_rainfall_risk(
    rainfall,
    duration,
    threshold
)


# ============================================
# ML PREDICTION
# ============================================

prediction = model.predict([
    [elevation, slope, rainfall]
])[0]

probability = model.predict_proba([
    [elevation, slope, rainfall]
])[0][1] * 100


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
# DISPLAY RESULT
# ============================================

print("\n==============================================")
print("             PREDICTION RESULT")
print("==============================================")

print("Location          :", location)
print("Elevation         :", elevation, "m")
print("Slope             :", slope, "degree")
print("Rainfall          :", rainfall, "mm")
print("Duration          :", duration, "hours")
print("Rainfall Intensity:", round(intensity, 2), "mm/hour")
print("Rainfall Risk     :", rainfall_risk)

print("----------------------------------------------")

if prediction == 1:
    print("ML Prediction     : LANDSLIDE RISK")
else:
    print("ML Prediction     : NO LANDSLIDE RISK")

print("ML Probability    :", round(probability, 2), "%")

print("----------------------------------------------")
print("FINAL RISK LEVEL   :", final_risk)
print("==============================================")