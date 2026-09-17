import streamlit as st
import pandas as pd
import pickle
from pathlib import Path
import folium
from streamlit_folium import st_folium
import urllib.request
import json
import urllib.parse
import base64
import math
from datetime import datetime

def search_location(city):

    url = (
        "https://geocoding-api.open-meteo.com/v1/search"
        f"?name={urllib.parse.quote(city)}"
        "&count=5"
        "&language=en"
        "&format=json"
    )

    try:

        with urllib.request.urlopen(
            url,
            timeout=15
        ) as response:

            data = json.loads(
                response.read().decode("utf-8")
            )

        results = data.get("results", [])

        indian_results = []

        for result in results:

            if result.get("country_code") == "IN":
                indian_results.append(result)

        return indian_results

    except Exception as e:

        print("Location search error:", e)

        return []

# ============================================================
# TERRAIN DATA FUNCTION
# ============================================================

def get_terrain_data(latitude, longitude):

    try:

        offset = 0.001

        latitudes = [
            latitude,
            latitude + offset,
            latitude - offset,
            latitude,
            latitude
        ]

        longitudes = [
            longitude,
            longitude,
            longitude,
            longitude + offset,
            longitude - offset
        ]

        lat_string = ",".join(
            str(x) for x in latitudes
        )

        lon_string = ",".join(
            str(x) for x in longitudes
        )

        url = (
            "https://api.open-meteo.com/v1/elevation"
            f"?latitude={lat_string}"
            f"&longitude={lon_string}"
        )

        with urllib.request.urlopen(
            url,
            timeout=15
        ) as response:

            data = json.loads(
                response.read().decode("utf-8")
            )

        elevations = data.get("elevation")

        if not elevations or len(elevations) < 5:
            return None, None

        center = float(elevations[0])
        north = float(elevations[1])
        south = float(elevations[2])
        east = float(elevations[3])
        west = float(elevations[4])

        import math

        lat_distance = 111320 * offset

        lon_distance = (
            111320
            * offset
            * max(
                0.01,
                abs(
                    math.cos(
                        math.radians(latitude)
                    )
                )
            )
        )

        dz_dy = (
            north - south
        ) / (
            2 * lat_distance
        )

        dz_dx = (
            east - west
        ) / (
            2 * lon_distance
        )

        gradient = math.sqrt(
            dz_dx ** 2 +
            dz_dy ** 2
        )

        slope = math.degrees(
            math.atan(gradient)
        )

        return center, slope

    except Exception as e:

        print("Terrain API error:", e)

        return None, None
# ============================================================
# PROJECT PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

TERRAIN_FILE = BASE_DIR / "terrain_data.csv"
MODEL_FILE = BASE_DIR / "landslide_model.pkl"


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Landslide Early Warning System",
    page_icon="⚠️",
    layout="wide"
)

st.markdown("""
<style>
.stApp {
    background-color: #f4f7fb;
}

.block-container {
    padding-top: 2rem;
    padding-bottom: 3rem;
    padding-left: 3rem;
    padding-right: 3rem;
}

h1 {
    color: #102a43 !important;
    font-weight: 800 !important;
}

h2 {
    color: #16324f !important;
    font-weight: 750 !important;
}

h3 {
    color: #243b53 !important;
    font-weight: 700 !important;
}

.stButton > button {
    width: 100%;
    border-radius: 10px;
    background-color: #1565c0;
    color: white;
    font-weight: 700;
    border: none;
}

[data-testid="stMetric"] {
    background-color: white;
    border-radius: 14px;
    padding: 18px;
    border: 1px solid #d9e2ec;
    box-shadow: 0 3px 12px rgba(16,42,67,0.07);
}

[data-testid="stMetricLabel"] {
    color: #627d98 !important;
}

[data-testid="stMetricValue"] {
    color: #102a43 !important;
}

.stTextInput input,
.stNumberInput input {
    border-radius: 10px !important;
    background-color: white !important;
}

.stCheckbox {
    background-color: white;
    padding: 8px 12px;
    border-radius: 10px;
    border: 1px solid #d9e2ec;
}

[data-testid="stAlert"] {
    border-radius: 12px !important;
}

</style>
""", unsafe_allow_html=True)


# ============================================================
# CHECK FILES
# ============================================================

if not TERRAIN_FILE.exists():

    st.error("terrain_data.csv not found")

    st.write("Expected:")
    st.code(str(TERRAIN_FILE))

    st.stop()


if not MODEL_FILE.exists():

    st.error("landslide_model.pkl not found")

    st.write("Expected:")
    st.code(str(MODEL_FILE))

    st.stop()


# ============================================================
# LOAD TERRAIN DATA
# ============================================================

try:

    terrain_data = pd.read_csv(TERRAIN_FILE)

except Exception as e:

    st.error("Could not read terrain_data.csv")

    st.write(str(e))

    st.stop()


# ============================================================
# LOAD MODEL
# ============================================================

try:

    with open(MODEL_FILE, "rb") as f:
        model = pickle.load(f)

except Exception as e:

    st.error("Could not load landslide_model.pkl")

    st.write(str(e))

    st.stop()


# ============================================================
# CHECK COLUMNS
# ============================================================

required_columns = [
    "location",
    "elevation_m",
    "slope_deg"
]

for column in required_columns:

    if column not in terrain_data.columns:

        st.error(
            f"Column '{column}' is missing from terrain_data.csv"
        )

        st.write(
            "Available columns:",
            terrain_data.columns.tolist()
        )

        st.stop()


# ============================================================
# TITLE
# ============================================================

st.title("⚠️ LANDSLIDE EARLY WARNING SYSTEM")

st.write(
    "Rainfall and Terrain Based Landslide Risk Assessment"
)


# ============================================================
# LIVE RAINFALL
# ============================================================

def get_live_rainfall(latitude, longitude):

    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={latitude}"
        f"&longitude={longitude}"
        "&current=rain"
        "&timezone=auto"
    )

    try:

        with urllib.request.urlopen(
            url,
            timeout=15
        ) as response:

            data = json.loads(
                response.read().decode("utf-8")
            )

        rain = data.get(
            "current",
            {}
        ).get("rain")

        if rain is None:
            return None

        return float(rain)

    except Exception:

        return None



# ============================================================
# EARTHQUAKE MONITORING FUNCTION
# ============================================================

@st.cache_data(ttl=300)
def get_nearby_earthquakes(latitude, longitude, radius_km=300):

    try:

        # USGS earthquake API
        url = (
            "https://earthquake.usgs.gov/fdsnws/event/1/query"
            "?format=geojson"
            f"&latitude={latitude}"
            f"&longitude={longitude}"
            f"&maxradiuskm={radius_km}"
            "&minmagnitude=2.5"
            "&orderby=time"
            "&limit=100"
        )

        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Landslide-EWS-Prototype"
            }
        )

        with urllib.request.urlopen(
            request,
            timeout=15
        ) as response:

            data = json.loads(
                response.read().decode("utf-8")
            )

        features = data.get(
            "features",
            []
        )

        earthquakes = []

        for feature in features:

            properties = feature.get(
                "properties",
                {}
            )

            geometry = feature.get(
                "geometry",
                {}
            )

            coordinates = geometry.get(
                "coordinates",
                []
            )

            if len(coordinates) < 3:
                continue

            longitude_eq = float(
                coordinates[0]
            )

            latitude_eq = float(
                coordinates[1]
            )

            depth_km = float(
                coordinates[2]
            )

            magnitude = properties.get(
                "mag"
            )

            place = properties.get(
                "place",
                "Unknown location"
            )

            timestamp = properties.get(
                "time"
            )

            if magnitude is None:
                continue

            # Distance calculation using Haversine formula
            earth_radius = 6371.0

            lat1 = math.radians(
                latitude
            )

            lat2 = math.radians(
                latitude_eq
            )

            delta_lat = math.radians(
                latitude_eq - latitude
            )

            delta_lon = math.radians(
                longitude_eq - longitude
            )

            a = (
                math.sin(delta_lat / 2) ** 2
                +
                math.cos(lat1)
                * math.cos(lat2)
                * math.sin(delta_lon / 2) ** 2
            )

            c = (
                2
                * math.atan2(
                    math.sqrt(a),
                    math.sqrt(1 - a)
                )
            )

            distance_km = (
                earth_radius * c
            )

            if timestamp is not None:

                event_time = datetime.fromtimestamp(
                    timestamp / 1000
                ).strftime(
                    "%Y-%m-%d %H:%M"
                )

            else:

                event_time = "Unknown"

            earthquakes.append({

                "magnitude": float(
                    magnitude
                ),

                "latitude": latitude_eq,

                "longitude": longitude_eq,

                "depth_km": depth_km,

                "distance_km": distance_km,

                "place": place,

                "time": event_time

            })

        return earthquakes

    except Exception as e:

        print(
            "Earthquake API error:",
            e
        )

        return []


# ============================================================
# CURRENT CONDITIONS - LOCATION SEARCH
# ============================================================

st.header("Current Conditions")

city_search = st.text_input(
    "Search City / Location",
    placeholder="Example: Dehradun, Shimla, Srinagar, Guwahati"
)

search_button = st.button("Search Location")


# ============================================================
# SESSION STATE
# ============================================================

if "selected_location" not in st.session_state:
    st.session_state.selected_location = None

if "latitude" not in st.session_state:
    st.session_state.latitude = None

if "longitude" not in st.session_state:
    st.session_state.longitude = None

if "elevation" not in st.session_state:
    st.session_state.elevation = None

if "slope" not in st.session_state:
    st.session_state.slope = None


# ============================================================
# SEARCH LOCATION
# ============================================================

if search_button:

    if city_search.strip() == "":
        st.warning("Please enter a city or location.")

    else:

        results = search_location(
            city_search.strip()
        )

        if len(results) == 0:

            st.error(
                "No Indian location found. "
                "Please try another city."
            )

        else:

            location_names = []

            for result in results:

                name = result.get(
                    "name",
                    "Unknown"
                )

                state = result.get(
                    "admin1",
                    ""
                )

                country = result.get(
                    "country",
                    "India"
                )

                display_name = (
                    f"{name}, {state}, {country}"
                )

                location_names.append(
                    display_name
                )


            selected_name = st.selectbox(
                "Select Location",
                location_names,
                key="searched_location"
            )


            selected_index = location_names.index(
                selected_name
            )

            selected_result = results[
                selected_index
            ]


            latitude = float(
                selected_result["latitude"]
            )

            longitude = float(
                selected_result["longitude"]
            )


            # Get elevation and slope
            elevation, slope = get_terrain_data(
                latitude,
                longitude
            )


            # Save selected location
            st.session_state.selected_location = (
                selected_name
            )

            st.session_state.latitude = latitude
            st.session_state.longitude = longitude

            st.session_state.elevation = elevation
            st.session_state.slope = slope


# ============================================================
# CHECK LOCATION
# ============================================================

if st.session_state.selected_location is None:

    st.info(
        "Search an Indian city/location "
        "and click Search Location."
    )

    st.stop()


# ============================================================
# SELECTED LOCATION INFORMATION
# ============================================================

location = st.session_state.selected_location

latitude = st.session_state.latitude

longitude = st.session_state.longitude

elevation = st.session_state.elevation

slope = st.session_state.slope


st.success(
    f"Selected Location: {location}"
)

st.write(
    f"Latitude: {latitude:.4f}"
)

st.write(
    f"Longitude: {longitude:.4f}"
)


if elevation is not None:

    st.write(
        f"Elevation: {elevation:.1f} m"
    )

    st.write(
        f"Estimated Terrain Slope: {slope:.2f}°"
    )

else:

    st.warning(
        "Terrain information is unavailable."
    )


# ============================================================
# AUTO REFRESH
# ============================================================

refresh_seconds = st.number_input(
    "Auto Refresh Interval (seconds)",
    min_value=10,
    value=60,
    step=10
)

if st.button("Refresh Now"):
    st.rerun()


# ============================================================
# RAINFALL
# ============================================================

use_live = st.checkbox(
    "Use Live Rainfall Data"
)


if use_live:

    live_rainfall = get_live_rainfall(
        latitude,
        longitude
    )

    if live_rainfall is not None:

        rainfall = live_rainfall

        st.success(
            f"Live Rainfall: {rainfall:.2f} mm"
        )

    else:

        st.warning(
            "Live rainfall data unavailable. "
            "Using manual rainfall input."
        )

        rainfall = st.number_input(
            "Rainfall (mm)",
            min_value=0.0,
            value=60.0,
            step=1.0
        )

else:

    rainfall = st.number_input(
        "Rainfall (mm)",
        min_value=0.0,
        value=60.0,
        step=1.0
    )


# ============================================================
# RAINFALL DURATION
# ============================================================

duration = st.number_input(
    "Rainfall Duration (hours)",
    min_value=0.1,
    value=4.0,
    step=0.5
)


# ============================================================
# RAINFALL RISK
# ============================================================

intensity = rainfall / duration


threshold = 20


if intensity >= threshold:

    rainfall_risk = "HIGH"

else:

    rainfall_risk = "NORMAL"


# ============================================================
# ML PREDICTION
# ============================================================

try:

    prediction = model.predict(
        [[
            elevation,
            slope,
            rainfall
        ]]
    )[0]


    probability = (
        model.predict_proba(
            [[
                elevation,
                slope,
                rainfall
            ]]
        )[0][1]
        * 100
    )

except Exception as e:

    st.error("ML prediction failed")

    st.write(str(e))

    st.stop()


# ============================================================
# FINAL RISK
# ============================================================

if (
    rainfall_risk == "HIGH"
    and prediction == 1
):

    final_risk = "CRITICAL"

elif (
    rainfall_risk == "HIGH"
    or prediction == 1
):

    final_risk = "HIGH"

else:

    final_risk = "LOW"


# ============================================================
# RISK ASSESSMENT
# ============================================================

st.header("Risk Assessment")


c1, c2, c3, c4 = st.columns(4)


with c1:

    st.metric(
        "Rainfall",
        f"{rainfall:.1f} mm"
    )


with c2:

    st.metric(
        "Intensity",
        f"{intensity:.2f} mm/hr"
    )


with c3:

    st.metric(
        "Elevation",
        f"{elevation:.0f} m"
    )


with c4:

    st.metric(
        "Slope",
        f"{slope:.0f}°"
    )


# ============================================================
# RISK DETAILS
# ============================================================

st.subheader("Risk Details")


st.write(
    "Rainfall Risk:",
    rainfall_risk
)


if prediction == 1:

    st.write(
        "ML Prediction: LANDSLIDE RISK"
    )

else:

    st.write(
        "ML Prediction: NO LANDSLIDE RISK"
    )


st.write(
    "ML Probability:",
    f"{probability:.2f}%"
)


# ============================================================
# PC ALARM FUNCTION
# ============================================================

def play_alarm():

    alarm_html = """
    <audio autoplay>
        <source src="data:audio/wav;base64,{{ALARM_SOUND}}" type="audio/wav">
    </audio>
    """

    import numpy as np
    import wave
    import io

    sample_rate = 44100
    duration = 1.0

    t = np.linspace(
        0,
        duration,
        int(sample_rate * duration),
        False
    )

    tone = (
        0.5 * np.sin(2 * np.pi * 1000 * t)
        + 0.3 * np.sin(2 * np.pi * 1500 * t)
    )

    audio = np.int16(
        tone / np.max(np.abs(tone)) * 32767
    )

    buffer = io.BytesIO()

    with wave.open(buffer, "wb") as wav_file:

        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio.tobytes())

    encoded = base64.b64encode(
        buffer.getvalue()
    ).decode()

    alarm_html = alarm_html.replace(
        "{{ALARM_SOUND}}",
        encoded
    )

    st.components.v1.html(
        alarm_html,
        height=1
    )

# ============================================================
# FINAL RISK LEVEL
# ============================================================

st.subheader("FINAL RISK LEVEL")


if final_risk == "CRITICAL":

    st.error(
        "CRITICAL - Immediate attention required"
    )

elif final_risk == "HIGH":

    st.warning(
        "HIGH - Landslide risk detected"
    )

else:

    st.success(
        "LOW - No immediate high-risk condition detected"
    )
if final_risk == "CRITICAL":

    st.error(
        "CRITICAL - Immediate attention required"
    )

    play_alarm()

elif final_risk == "HIGH":

    st.warning(
        "HIGH - Landslide risk detected"
    )

    play_alarm()

else:

    st.success(
        "LOW - No immediate high-risk condition detected"
    )


# ============================================================
# EARLY WARNING
# ============================================================

st.header("Early Warning Alert")


if final_risk == "CRITICAL":

    st.error(
        "CRITICAL ALERT: Very high landslide risk detected. "
        "Immediate monitoring and safety action are recommended."
    )

elif final_risk == "HIGH":

    st.warning(
        "HIGH ALERT: Landslide risk detected. "
        "Increase monitoring and be prepared for preventive action."
    )

else:

    st.success(
        "NORMAL: Current conditions do not indicate an immediate "
        "high landslide risk."
    )

# ============================================================
# EARTHQUAKE MONITORING
# ============================================================

st.markdown("---")

st.header("🌍 Earthquake Monitoring")

earthquakes = get_nearby_earthquakes(
    st.session_state.latitude,
    st.session_state.longitude,
    radius_km=300
)

if earthquakes:

    latest_eq = earthquakes[-1]

    st.subheader("Latest Nearby Earthquake")

    e1, e2, e3, e4 = st.columns(4)

    with e1:
        st.metric(
            "Magnitude",
            f"{latest_eq['magnitude']:.1f}"
        )

    with e2:
        st.metric(
            "Distance",
            f"{latest_eq['distance_km']:.1f} km"
        )

    with e3:
        st.metric(
            "Depth",
            f"{latest_eq['depth_km']:.1f} km"
        )

    with e4:
        st.metric(
            "Recent Events",
            len(earthquakes)
        )

    st.write(
        f"**Location:** {latest_eq['place']}"
    )

    st.write(
        f"**Time:** {latest_eq['time']}"
    )

    st.subheader("Earthquake Risk Contribution")

    max_magnitude = max(
        eq["magnitude"]
        for eq in earthquakes
    )

    nearest_distance = min(
        eq["distance_km"]
        for eq in earthquakes
    )

    if (
        max_magnitude >= 5.5
        and nearest_distance <= 100
    ):

        earthquake_risk = "HIGH"

        st.error(
            "🔴 HIGH — Significant nearby earthquake activity detected."
        )

    elif (
        max_magnitude >= 4.0
        and nearest_distance <= 150
    ):

        earthquake_risk = "MODERATE"

        st.warning(
            "🟠 MODERATE — Moderate nearby earthquake activity detected."
        )

    else:

        earthquake_risk = "LOW"

        st.success(
            "🟢 LOW — No significant nearby earthquake activity detected."
        )

    st.subheader("Recent Nearby Earthquakes")

    earthquake_table = pd.DataFrame([

        {
            "Magnitude": round(
                eq["magnitude"],
                1
            ),

            "Location": eq["place"],

            "Distance (km)": round(
                eq["distance_km"],
                1
            ),

            "Depth (km)": round(
                eq["depth_km"],
                1
            ),

            "Time": eq["time"]
        }

        for eq in reversed(earthquakes)

    ])

    st.dataframe(
        earthquake_table,
        use_container_width=True,
        hide_index=True
    )

else:

    earthquake_risk = "LOW"

    st.success(
        "🟢 No recent M2.5+ earthquake detected "
        "within 300 km of the selected location."
    )


# ============================================================
# RISK COMPARISON
# ============================================================

st.header("Risk Comparison")


risk_values = []


for _, row in terrain_data.iterrows():

    zone = str(row["location"])

    zone_elevation = float(
        row["elevation_m"]
    )

    zone_slope = float(
        row["slope_deg"]
    )


    try:

        zone_probability = (
            model.predict_proba(
                [[
                    zone_elevation,
                    zone_slope,
                    rainfall
                ]]
            )[0][1]
            * 100
        )

    except Exception:

        zone_probability = 0


    if zone_probability >= 70:

        risk_score = 3

    elif zone_probability >= 40:

        risk_score = 2

    else:

        risk_score = 1


    risk_values.append({

        "Location": zone,

        "Risk Score": risk_score,

        "Probability (%)": round(
            zone_probability,
            2
        )

    })


risk_table = pd.DataFrame(
    risk_values
)


st.dataframe(
    risk_table,
    use_container_width=True
)


# ============================================================
# CHART
# ============================================================

st.subheader(
    "Landslide Risk Probability"
)


chart_data = risk_table.set_index(
    "Location"
)["Probability (%)"]


st.bar_chart(
    chart_data
)


# ============================================================
# DYNAMIC CITY / STATE SEARCH
# ============================================================

def search_location(place):

    try:

        encoded_place = urllib.parse.quote(
            place + ", India"
        )

        url = (
            "https://nominatim.openstreetmap.org/search"
            f"?q={encoded_place}"
            "&format=json"
            "&limit=1"
        )

        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Landslide-EWS-Prototype"
            }
        )

        with urllib.request.urlopen(
            request,
            timeout=10
        ) as response:

            data = json.loads(
                response.read().decode("utf-8")
            )

        if not data:
            return None

        return (
            float(data[0]["lat"]),
            float(data[0]["lon"])
        )

    except Exception as e:

        print("Location search error:", e)

        return None


def generate_city_zones(latitude, longitude):

    return {

        "Zone_A": [
            latitude + 0.020,
            longitude - 0.020
        ],

        "Zone_B": [
            latitude + 0.020,
            longitude + 0.020
        ],

        "Zone_C": [
            latitude,
            longitude
        ],

        "Zone_D": [
            latitude - 0.020,
            longitude - 0.020
        ],

        "Zone_E": [
            latitude - 0.020,
            longitude + 0.020
        ]

    }

# ============================================================
# CITY / STATE LOCATION SEARCH
# ============================================================

@st.cache_data(ttl=3600)
def get_location_coordinates(place):

    try:

        search_place = urllib.parse.quote(
            str(place) + ", India"
        )

        url = (
            "https://nominatim.openstreetmap.org/search"
            f"?q={search_place}"
            "&format=json"
            "&limit=1"
        )

        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Landslide-Early-Warning-System"
            }
        )

        with urllib.request.urlopen(
            request,
            timeout=15
        ) as response:

            data = json.loads(
                response.read().decode("utf-8")
            )

        if not data:
            return None

        latitude = float(data[0]["lat"])
        longitude = float(data[0]["lon"])

        return latitude, longitude

    except Exception as e:

        print("Location search error:", e)

        return None


# ============================================================
# LOCATION MAP
# ============================================================

st.header("Location Map")

# Selected city ke coordinates
map_latitude = st.session_state.latitude
map_longitude = st.session_state.longitude

# ============================================================
# CREATE 5 ZONES AROUND SELECTED CITY
# ============================================================

coordinates = {
    "Zone_A": [
        map_latitude + 0.020,
        map_longitude - 0.020
    ],

    "Zone_B": [
        map_latitude + 0.020,
        map_longitude + 0.020
    ],

    "Zone_C": [
        map_latitude,
        map_longitude
    ],

    "Zone_D": [
        map_latitude - 0.020,
        map_longitude - 0.020
    ],

    "Zone_E": [
        map_latitude - 0.020,
        map_longitude + 0.020
    ]
}

# ============================================================
# CREATE MAP AT SELECTED CITY
# ============================================================

risk_map = folium.Map(
    location=[
        map_latitude,
        map_longitude
    ],
    zoom_start=12
)

# ============================================================
# SELECTED LOCATION MARKER
# ============================================================

folium.Marker(
    location=[
        map_latitude,
        map_longitude
    ],
    popup=folium.Popup(
        f"""
        <b>Selected Location</b><br>
        {st.session_state.selected_location}<br>
        Latitude: {map_latitude:.4f}<br>
        Longitude: {map_longitude:.4f}
        """,
        max_width=300
    ),
    tooltip=f"Selected: {st.session_state.selected_location}",
    icon=folium.Icon(
        color="blue",
        icon="info-sign"
    )
).add_to(risk_map)


# ============================================================
# PROJECT ZONES
# ============================================================

# Zone_A to Zone_E ko preserve rakho.
# Ye zones tumhare existing terrain_data/model ke comparison ke liye hain.

for _, row in terrain_data.iterrows():

    zone = str(row["location"])

    # Sirf un zones ko map par show karo
    # jinke coordinates available hain
    if zone not in coordinates:
        continue

    zone_elevation = float(
        row["elevation_m"]
    )

    zone_slope = float(
        row["slope_deg"]
    )

    try:

        zone_prediction = model.predict(
            [[
                zone_elevation,
                zone_slope,
                rainfall
            ]]
        )[0]

        zone_probability = (
            model.predict_proba(
                [[
                    zone_elevation,
                    zone_slope,
                    rainfall
                ]]
            )[0][1]
            * 100
        )

    except Exception:

        zone_prediction = 0
        zone_probability = 0


    # Risk calculation
    if (
        intensity >= threshold
        and zone_prediction == 1
    ):

        zone_risk = "CRITICAL"

    elif (
        intensity >= threshold
        or zone_prediction == 1
    ):

        zone_risk = "HIGH"

    else:

        zone_risk = "LOW"


    # Marker colour
    if zone_risk == "CRITICAL":

        zone_color = "red"

    elif zone_risk == "HIGH":

        zone_color = "orange"

    else:

        zone_color = "green"


    lat, lon = coordinates[zone]


    folium.CircleMarker(
        location=[
            lat,
            lon
        ],
        radius=10,
        color=zone_color,
        fill=True,
        fill_color=zone_color,
        fill_opacity=0.85,

        popup=folium.Popup(
            f"""
            <b>{zone}</b><br>
            Risk: {zone_risk}<br>
            Probability: {zone_probability:.2f}%<br>
            Elevation: {zone_elevation:.0f} m<br>
            Slope: {zone_slope:.2f}°
            """,
            max_width=300
        ),

        tooltip=f"{zone} - {zone_risk}"
    ).add_to(risk_map)


# ============================================================
# MAP LEGEND
# ============================================================

legend = """
<div style="
    position: fixed;
    bottom: 30px;
    left: 30px;
    width: 170px;
    background-color: white;
    border: 2px solid grey;
    z-index: 9999;
    padding: 10px;
    font-size: 14px;
">

<b>Risk Level</b><br><br>

<span style="color:green;">●</span> LOW<br>

<span style="color:orange;">●</span> HIGH<br>

<span style="color:red;">●</span> CRITICAL<br>

<span style="color:blue;">●</span> SELECTED LOCATION

</div>
"""

risk_map.get_root().html.add_child(
    folium.Element(legend)
)


# ============================================================
# DISPLAY MAP
# ============================================================

st_folium(
    risk_map,
    width=900,
    height=500
)


# ============================================================
# EMERGENCY ALERT SYSTEM
# ============================================================

st.header("Emergency Alert System")


if final_risk == "CRITICAL":

    st.error(
        "🚨 CRITICAL ALERT ACTIVE"
    )


    if st.button(
        "Acknowledge Critical Alert"
    ):

        st.success(
            "Alert acknowledged."
        )


elif final_risk == "HIGH":

    st.warning(
        "⚠️ HIGH RISK ALERT ACTIVE"
    )


    if st.button(
        "Acknowledge High Risk Alert"
    ):

        st.success(
            "Alert acknowledged."
        )


else:

    st.success(
        "✅ No Emergency Alert"
    )


    if st.button(
        "Acknowledge Normal Status"
    ):

        st.info(
            "Normal status acknowledged."
        )


# ============================================================
# SYSTEM STATUS
# ============================================================

st.header("System Status")


s1, s2, s3 = st.columns(3)


with s1:

    st.metric(
        "Data Source",
        "Rainfall + Terrain"
    )


with s2:

    st.metric(
        "Prediction Model",
        "Machine Learning"
    )


with s3:

    st.metric(
        "Monitoring Status",
        "ACTIVE"
    )


# ============================================================
# FOOTER
# ============================================================

st.markdown("---")


st.caption(
    "Landslide Early Warning System - Prototype"
)
