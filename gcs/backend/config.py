"""
Eqaab GCS Backend — Configuration
"""

# --- Server ---
HOST = "0.0.0.0"
PORT = 8000
CORS_ORIGINS = ["http://localhost:3000", "http://localhost:5173"]

# --- Drone Simulator ---
SIMULATOR_ENABLED = True
TELEMETRY_RATE_HZ = 2            # telemetry updates per second
DETECTION_INTERVAL_SEC = 8       # average seconds between detections

# --- Drone Home / Launch Point (Taif area) ---
HOME_LAT = 21.2854
HOME_LON = 40.4183
HOME_ALT = 0.0

# --- Patrol Waypoints (simulated mission near Taif) ---
PATROL_WAYPOINTS = [
    {"lat": 21.2870, "lon": 40.4200, "alt": 40.0},
    {"lat": 21.2890, "lon": 40.4225, "alt": 45.0},
    {"lat": 21.2880, "lon": 40.4255, "alt": 50.0},
    {"lat": 21.2855, "lon": 40.4245, "alt": 45.0},
    {"lat": 21.2840, "lon": 40.4215, "alt": 40.0},
    {"lat": 21.2838, "lon": 40.4185, "alt": 42.0},
]

# --- Geofence (polygon around patrol area) ---
GEOFENCE = [
    {"lat": 21.2910, "lon": 40.4160},
    {"lat": 21.2910, "lon": 40.4270},
    {"lat": 21.2820, "lon": 40.4270},
    {"lat": 21.2820, "lon": 40.4160},
]

# --- Battery ---
BATTERY_FULL = 100.0
BATTERY_DRAIN_PER_SEC = 0.03     # ~30 min flight time
BATTERY_RTL_THRESHOLD = 20.0     # auto-RTL below this

# --- Detection Classes ---
DETECTION_CLASSES = ["person", "car", "drone"]
DETECTION_WEIGHTS = [0.50, 0.30, 0.20]  # probability weights

# --- IFF Friendly Drone IDs ---
FRIENDLY_DRONE_IDS = ["EQAAB-01", "EQAAB-02"]
