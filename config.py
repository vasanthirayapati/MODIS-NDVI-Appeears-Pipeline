# ============================================================
# MODIS NDVI Pipeline Configuration
# ============================================================

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ============================================================
# DATE RANGE
# ============================================================

start_date = "2026-07-01"
end_date = "2026-07-31"

# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = PROJECT_DIR / "data"
OUTPUT_DIR = PROJECT_DIR / "outputs"

# ============================================================
# INPUT DATA
# ============================================================

# Area of Interest (AOI)
AOI_PATH = DATA_DIR / "vectors" / "India_States_2025"/ "India_States_2025.shp"

# Administrative boundaries
STATE_BOUNDARY = DATA_DIR / "vectors" / "State_Merge"/ "State_India.shp"
DISTRICT_BOUNDARY = DATA_DIR / "vectors" / "District_Merge" / "India_Districts.shp"

# Optional Agricultural Mask
# Set to None to disable masking
#MASK_PATH = None
MASK_PATH = DATA_DIR / "masks" / "agriculture_mask.tif"



# ============================================================
# OUTPUT
# ============================================================

SAVE_RASTER_OUTPUT = True
SAVE_MAP_OUTPUTS = True

# ============================================================
# OUTPUT FOLDERS
# ============================================================

OUTPUT_RASTER = OUTPUT_DIR / "raster"
OUTPUT_MAPS = OUTPUT_DIR / "maps"

OUTPUT_RASTER.mkdir(parents=True, exist_ok=True)
OUTPUT_MAPS.mkdir(parents=True, exist_ok=True)

# ============================================================
# NASA AppEEARS
# ============================================================

API_URL = "https://appeears.earthdatacloud.nasa.gov/api/"

USERNAME = os.getenv("APPEEARS_USERNAME")
PASSWORD = os.getenv("APPEEARS_PASSWORD")

if not USERNAME or not PASSWORD:
    raise ValueError(
        "Please create a .env file with APPEEARS_USERNAME and APPEEARS_PASSWORD."
    )

# ============================================================
# DOWNLOAD AOI (Bounding Box)
# ============================================================

DOWNLOAD_BBOX = [
    [68.1, 6.5],
    [97.4, 6.5],
    [97.4, 35.5],
    [68.1, 35.5],
    [68.1, 6.5]
]

# ============================================================
# MODIS PRODUCT
# ============================================================

PRODUCT = "MOD13Q1.061"
LAYER = "250m_16_days_NDVI"


# ============================================================
# REGION - this is used for task name given to appeears 
# ============================================================

DOWNLOAD_REGION = "India"

# ============================================================
# MAP GENERATION
# ============================================================

# Generate India NDVI map
GENERATE_INDIA_MAP = True

# Generate State NDVI maps
GENERATE_STATE_MAPS = True

# List of states (used only if GENERATE_STATE_MAPS = True)
STATE_LIST = [
    "Haryana",
    "Odisha"
]

