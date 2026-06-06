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

# --- Drone Home / Launch Point (Jeddah area) ---
HOME_LAT = 21.4858
HOME_LON = 39.1925
HOME_ALT = 0.0

# --- Patrol Waypoints (simulated mission near Jeddah) ---
PATROL_WAYPOINTS = [
    {"lat": 21.4870, "lon": 39.1940, "alt": 40.0},
    {"lat": 21.4885, "lon": 39.1960, "alt": 45.0},
    {"lat": 21.4878, "lon": 39.1985, "alt": 50.0},
    {"lat": 21.4860, "lon": 39.1975, "alt": 45.0},
    {"lat": 21.4848, "lon": 39.1950, "alt": 40.0},
    {"lat": 21.4845, "lon": 39.1920, "alt": 42.0},
]

# --- Geofence (polygon around patrol area) ---
GEOFENCE = [
    {"lat": 21.4900, "lon": 39.1900},
    {"lat": 21.4900, "lon": 39.2000},
    {"lat": 21.4830, "lon": 39.2000},
    {"lat": 21.4830, "lon": 39.1900},
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
