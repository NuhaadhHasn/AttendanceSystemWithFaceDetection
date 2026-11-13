"""Central configuration for the attendance system.

Every value can be overridden with an environment variable, so the Firebase
project, camera or cool-down can change without editing code.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# --- Firebase ---------------------------------------------------------------
SERVICE_ACCOUNT_KEY = Path(os.environ.get("SERVICE_ACCOUNT_KEY", BASE_DIR / "serviceAccountKey.json"))
DATABASE_URL = os.environ.get(
    "FIREBASE_DATABASE_URL",
    "https://attendancewithfacerecogn-5cfbb-default-rtdb.firebaseio.com/",
)
STORAGE_BUCKET = os.environ.get(
    "FIREBASE_STORAGE_BUCKET",
    "attendancewithfacerecogn-5cfbb.appspot.com",
)

# --- Files ------------------------------------------------------------------
IMAGES_DIR = BASE_DIR / "Images"
RESOURCES_DIR = BASE_DIR / "Resources"
MODES_DIR = RESOURCES_DIR / "Modes"
BACKGROUND_IMAGE = RESOURCES_DIR / "background.png"
ENCODINGS_FILE = BASE_DIR / "EncodeFile.p"

# --- Camera and recognition -------------------------------------------------
CAMERA_INDEX = int(os.environ.get("CAMERA_INDEX", 0))
MATCH_TOLERANCE = float(os.environ.get("MATCH_TOLERANCE", 0.6))  # lower = stricter

# --- Attendance rules -------------------------------------------------------
# Seconds before the same person can be marked again. 30 is a demo value;
# use 86400 (24 hours) for real daily attendance.
COOLDOWN_SECONDS = float(os.environ.get("COOLDOWN_SECONDS", 30))
TIME_FORMAT = "%Y-%m-%d %H:%M:%S"

# --- On-screen timing (seconds) ---------------------------------------------
DETAILS_SECONDS = 1.5          # profile card
MARKED_SECONDS = 1.5           # "Marked" confirmation
ALREADY_MARKED_SECONDS = 2.0   # "Already marked" notice
STORE_RETRY_SECONDS = 5.0      # wait before retrying after a database error

PHOTO_SIZE = (216, 216)        # (width, height) of the profile photo on screen
