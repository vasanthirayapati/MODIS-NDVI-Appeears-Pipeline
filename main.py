#automatically download modis data from appeears website in the given timeline... downloads all the available data in the time period and generate maps
import os
import time
import math
import calendar
import requests
import rasterio
import tempfile
import unicodedata

import numpy as np
import geopandas as gpd


import cartopy.crs as ccrs
import cartopy.mpl.ticker as cticker


import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import matplotlib.font_manager as fm
import matplotlib.patches as mpatches
import matplotlib.patheffects as path_effects

from rasterio.mask import mask as rio_mask
from rasterio.features import geometry_mask
from rasterio.warp import reproject, Resampling

from matplotlib.patches import Rectangle
from matplotlib.offsetbox import OffsetImage, AnnotationBbox

from PIL import Image, ImageChops
from shapely.geometry import mapping
from datetime import date, datetime, timedelta, timezone 


from config import *
from mapping import *

# ============================================================
# PROJECT RESOURCES
# ============================================================

font_path = PROJECT_DIR / "data" / "fonts" / "NotoSansSymbols2-Regular.ttf"


# AUTH
def get_token():
    r = requests.post(f"{API_URL}login", auth=(USERNAME, PASSWORD))
    r.raise_for_status()
    token = r.json()["token"]

    print("🔐 Authentication successful")
    return token


# MODIS 16-DAY WINDOW HELPERS

def modis_window_for_date(d):
    """
    Given a date, return the MODIS 16-day window (start, end)
    """
    year = d.year
    doy = d.timetuple().tm_yday

    start_doy = ((doy - 1) // 16) * 16 + 1
    start_date = datetime(year, 1, 1).date() + timedelta(days=start_doy - 1)
    end_date = start_date + timedelta(days=15)

    return start_date, end_date


# MODIS DATE WINDOWS

def get_modis_windows(start_date, end_date):
    """
    Return all MODIS 16-day windows overlapping the given date range.

    Parameters
    ----------
    start_date : str
        Start date in YYYY-MM-DD format.
    end_date : str
        End date in YYYY-MM-DD format.

    Returns
    -------
    list of tuple(date, date)
        List of (window_start, window_end) date objects.
    """

    # Convert strings to date objects
    start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
    end_date = datetime.strptime(end_date, "%Y-%m-%d").date()

    # Find the MODIS window containing the start date
    window_start, window_end = modis_window_for_date(start_date)

    windows = []

    while window_start <= end_date:
        windows.append((window_start, window_end))

        # Move to the next 16-day window
        window_start = window_end + timedelta(days=1)
        window_end = window_start + timedelta(days=15)

    return windows


def format_date_range(start_date, end_date):
    """
    Format a date range into a human-readable string.

    Examples
    --------
    07-02-2026 to 07-17-2026 -> 2-17 July
    07-17-2026 to 08-01-2026 -> 17 July-1 August
    """
    s = datetime.strptime(start_date, "%m-%d-%Y")
    e = datetime.strptime(end_date, "%m-%d-%Y")

    # SAME MONTH → 2–17 January
    if s.month == e.month:
        return f"{s.day}-{e.day} {s.strftime('%B')}"

    # DIFFERENT MONTHS → 17 January–1 February
    return f"{s.day} {s.strftime('%B')}-{e.day} {e.strftime('%B')}"


# SUBMIT TASK

def submit_task(token, start_date, end_date):
    """
    Submit a MODIS NDVI extraction task to the NASA AppEEARS API.

    Parameters
    ----------
    token : str
        Authentication token returned by AppEEARS.

    start_date : str
        Start date in MM-DD-YYYY format.

    end_date : str
        End date in MM-DD-YYYY format.

    Returns
    -------
    str
        AppEEARS task ID.
    """


    headers = {"Authorization": f"Bearer {token}"}

    download_geometry = {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [DOWNLOAD_BBOX]
            },
            "properties": {}
        }]
    }

    payload = {
        "task_type": "area",
        "task_name": f"MODIS_NDVI_{DOWNLOAD_REGION}_{end_date}",
        "params": {
            "dates": [{
                "startDate": start_date,
                "endDate": end_date
            }],

            #for MODIS NDVI
            "layers": [{
                "product": PRODUCT,
                "layer": LAYER,
            }],

            "output": {
                "format": {"type": "geotiff"},
                "projection": "geographic"
            },
            "geo": download_geometry
        }
    }

    r = requests.post(f"{API_URL}task", json=payload, headers=headers)
    r.raise_for_status()

    task_id = r.json()["task_id"]
    print(f"📤 Task submitted: {task_id}")
    return task_id


# FETCH NDVI DOWNLOAD URL
def get_download_url(token, task_id):
    #headers = {"Authorization": f"Bearer {token}"}

    while True:
        try:
            r = SESSION.get(
                f"{API_URL}task/{task_id}",
                timeout=30
            )
            r.raise_for_status()
        except requests.exceptions.ReadTimeout:
            print("⚠️ AppEEARS not responding (timeout). Retrying in 90s...")
            time.sleep(120)
            continue
        except requests.exceptions.ConnectionError:
            print("⚠️ Connection dropped. Retrying in 90s...")
            time.sleep(120)
            continue

        r.raise_for_status()
        status = r.json()["status"]

        if status == "done":
            #bundle = requests.get(f"{API_URL}bundle/{task_id}", headers=headers)
            bundle = SESSION.get(f"{API_URL}bundle/{task_id}")

            bundle.raise_for_status()

            for f in bundle.json()["files"]:
                name = f["file_name"]


                # AppEEARS may return additional quality layers (e.g., VI_Quality) along with
                # the NDVI raster. Exclude them to ensure only the NDVI GeoTIFF is downloaded.
                if (
                    name.endswith(".tif")
                    and LAYER in name
                    and "VI_Quality" not in name
                ):
                    file_id = f["file_id"]
                    return f"{API_URL}bundle/{task_id}/{file_id}"

            raise RuntimeError("NDVI file not found")

        elif status == "error":
            raise RuntimeError("AppEEARS task failed")

        print(f"⌛ Status: {status} (retry in 60s)")
        time.sleep(120)

def ordinal(n):
    """
    Convert an integer to its ordinal representation.

    Examples
    --------
    1 -> 1st
    2 -> 2nd
    3 -> 3rd
    4 -> 4th
    11 -> 11th
    22 -> 22nd
    """
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def format_window_name(start_date, end_date):
    """
    Create a formatted name for a MODIS 16-day window.

    Example
    -------
    07-02-2026, 07-17-2026
    ->
    2nd_Jul_17th_Jul
    """

    s = datetime.strptime(start_date, "%m-%d-%Y")
    e = datetime.strptime(end_date, "%m-%d-%Y")

    s_txt = f"{ordinal(s.day)}_{s.strftime('%b')}" 
    e_txt = f"{ordinal(e.day)}_{e.strftime('%b')}"

    return f"{s_txt}_{e_txt}"


# RUN AppEEARS PIPELINE (ONCE)
def main():

    token = get_token()

    # create session ONCE
    session = requests.Session()
    session.headers.update({"Authorization": f"Bearer {token}"})

    # assign to global
    global SESSION
    SESSION = session

    windows = get_modis_windows(start_date, end_date)

    print(f"Found {len(windows)} MODIS window(s).")


# checking whether the ndvi is already downloaded or not. if not then download it from appeears
    window_text = format_window_name(start_date, end_date)
    ndvi_tif_name = f"{PRODUCT}_{window_text}.tif"

    
    NDVI_TIF_OUTPUT = os.path.join(ndvi_year_folder, ndvi_tif_name)

    
    # CHECK IF TIFF EXISTS

    if os.path.exists(NDVI_TIF_OUTPUT):
        print("✅ NDVI TIFF already exists. Skipping download...")
        print("📂 Using:", NDVI_TIF_OUTPUT)

        ndvi_raster = NDVI_TIF_OUTPUT   # use local file

        use_local_file = True

    else:
        print("⬇ NDVI TIFF not found. Downloading from AppEEARS...")

        use_local_file = False

        task_id = submit_task(token, start_date, end_date)
        ndvi_raster = get_download_url(token, task_id)


    print("🔗 NDVI raster URL:")
    print(ndvi_raster)


    # Show which NDVI file is used
    ndvi_filename = os.path.basename(ndvi_raster)

    print("🛰️ NDVI FILE USED FOR MAP:")
    print(ndvi_filename)
    print("-" * 60)


    # NDVI MAP AUTOMATION 
    
    print(f"Maps will be saved under:\n{OUTPUT_MAPS}")

    output_path = OUTPUT_MAPS / "NDVI_India.png"
    multi_output_dir = OUTPUT_MAPS

    date_range_text = format_date_range(start_date, end_date)
    
    if SHOW_DATE_RANGE:
        title_text = f"{MAP_TITLE}\n({date_range_text})"
    else:
        title_text = MAP_TITLE

    fm.fontManager.addfont(font_path)

    india = gpd.read_file(STATE_BOUNDARY).to_crs(epsg=4326)
    districts = gpd.read_file(DISTRICT_BOUNDARY).to_crs(epsg=4326)

    
    # Helper Functions
    def read_raster_flexible(source, token=None):
        """
        Read an NDVI raster from either a local GeoTIFF or an AppEEARS download URL.

        Returns
        -------
        src : rasterio.DatasetReader
        arr : numpy.ndarray
        tmp_path : str or None
            Temporary file path if downloaded from AppEEARS.
        """

        # Read raster from a local GeoTIFF
        if Path(source).exists():
            print("📂 Reading NDVI from local TIFF...")
            src = rasterio.open(source)
            arr = src.read(1).astype("float32")
            return src, arr, None

        # Download raster from the AppEEARS URL
        print("⬇ Fetching NDVI from AppEEARS...")

        headers = {"Authorization": f"Bearer {token}"}

        
        tmp = tempfile.NamedTemporaryFile(suffix=".tif", delete=False)
        tmp_path = tmp.name

        r = requests.get(source, headers=headers, stream=True)
        r.raise_for_status()

        for chunk in r.iter_content(8192):
            tmp.write(chunk)
        tmp.close()

        src = rasterio.open(tmp_path)
        arr = src.read(1).astype("float32")

        return src, arr, tmp_path

    def resample_mask(mask_src, mask_arr, target_src):
        """
        Resample the agricultural mask to match the NDVI raster resolution.
        """
        dst = np.zeros((target_src.height, target_src.width), dtype="float32")

        reproject(
            source=mask_arr,
            destination=dst,
            src_transform=mask_src.transform,
            src_crs=mask_src.crs,
            dst_transform=target_src.transform,
            dst_crs=target_src.crs,
            resampling=Resampling.nearest
        )
        return dst

    def autoscale_modis(ndvi):
        """
        Convert scaled MODIS NDVI values (0–10000) to the standard 0–1 range.
        """

        maxv = np.nanmax(ndvi)
        if maxv > 1.5:   # scaled NDVI
            ndvi = ndvi / 10000.0
            print("Converted MODIS NDVI values from 0–10000 to 0–1.")
        return ndvi

    
    # STEP 1 — Read NDVI raster and apply agricultural mask

    print("Reading NDVI raster...")
    ndvi_src, ndvi_raw, tmp_path = read_raster_flexible(
        ndvi_raster,
        token if not use_local_file else None
    )


    # SAVE NDVI TIFF
    window_text = format_window_name(start_date, end_date)

    ndvi_tif_name = f"{PRODUCT}_{window_text}.tif"

    NDVI_TIF_OUTPUT = OUTPUT_RASTER / ndvi_tif_name

    if not use_local_file:
        print("💾 Saving NDVI TIFF...")

        with rasterio.open(
            NDVI_TIF_OUTPUT,
            "w",
            driver="GTiff",
            height=ndvi_raw.shape[0],
            width=ndvi_raw.shape[1],
            count=1,
            dtype="float32",
            crs=ndvi_src.crs,
            transform=ndvi_src.transform,
            nodata=np.nan
        ) as dst:

            ndvi_scaled = autoscale_modis(ndvi_raw)
            dst.write(ndvi_scaled.astype("float32"), 1)

        print("✅ NDVI TIFF saved:", NDVI_TIF_OUTPUT)

    if MASK_PATH is not None:
        print("Reading AgriMask raster...")
        mask_src = rasterio.open(MASK_PATH)
        mask_raw = mask_src.read(1).astype("float32")

        # Resample mask if needed
        if (mask_src.width != ndvi_src.width) or \
        (mask_src.height != ndvi_src.height) or \
        (mask_src.transform != ndvi_src.transform):
            print("Resampling AgriMask to NDVI resolution...")
            mask = resample_mask(mask_src, mask_raw, ndvi_src)
        else:
            mask = mask_raw

        # Convert to binary mask
        mask_bin = np.where(mask > 0, 1, 0)

    # Handle NDVI nodata
    if ndvi_src.nodata is not None:
        ndvi_raw = np.where(ndvi_raw == ndvi_src.nodata, np.nan, ndvi_raw)

    # Scale MODIS NDVI if needed
    ndvi = autoscale_modis(ndvi_raw)

    # Apply agricultural mask only if provided
    if MASK_PATH is not None:
        ndvi_masked = np.where(mask_bin == 1, ndvi, np.nan)
    else:
        ndvi_masked = ndvi.copy()

    # Mask non-agricultural pixels
    ndvi_masked = np.where(mask_bin == 1, ndvi, np.nan)

    # Removed noise (NDVI < 0.05 irrelevant in my maps)
    # Filter NDVI values outside the configured range
    ndvi_masked[ndvi_masked < MIN_NDVI] = np.nan
    ndvi_masked[ndvi_masked > MAX_NDVI] = np.nan


    # STEP 2 — Classify NDVI values
    h, w = ndvi_masked.shape
    class_map = np.full((h, w), -1, dtype=np.int16)

    for idx, (lo, hi, label, color) in enumerate(NDVI_CLASSES):
        sel = (ndvi_masked >= lo) & (ndvi_masked <= hi)
        class_map[sel] = idx

    # Count class pixels
    unique, cnt = np.unique(class_map, return_counts=True)
    count_dict = {int(k): int(v) for k, v in zip(unique, cnt)}

    
    # STEP 3 — Build Memory-Light RGBA image (uint8)
    ndvi_img = np.zeros((h, w, 4), dtype=np.uint8)
    ndvi_img[..., 3] = 0  # Initialize with a transparent background

    for idx, (_, _, _, hexcolor) in enumerate(NDVI_CLASSES):
        r = int(hexcolor[1:3], 16)
        g = int(hexcolor[3:5], 16)
        b = int(hexcolor[5:7], 16)

        mask_idx = class_map == idx
        ndvi_img[mask_idx, 0] = r
        ndvi_img[mask_idx, 1] = g
        ndvi_img[mask_idx, 2] = b
        ndvi_img[mask_idx, 3] = 255


    # STEP 4 — Read Vector Layers
    states = gpd.read_file(STATE_BOUNDARY).to_crs(4326)
    districts = gpd.read_file(DISTRICT_BOUNDARY).to_crs(4326)

    # Centroids for labels
    if SHOW_STATE_LABELS:
        states_proj = states.to_crs(3857)
        states["centroid"] = states_proj.centroid.to_crs(4326)


    # STEP 5 — PLOT
    print("Plotting map...")

    fig = plt.figure(FIGURE_SIZE)
    ax = plt.axes(projection=ccrs.PlateCarree())

    # Extent
    minx, miny, maxx, maxy = states.total_bounds
    ax.set_extent([minx - .5, maxx + .5, miny - 1, maxy + .5])

    # Layout frame
    fig_w, fig_h = fig.get_size_inches()
    ax.set_position([(1 - 0.80)/2, (1 - 0.80*(fig_w/fig_h))/2 + 0.015, 0.80, 0.80*(fig_w/fig_h)])

    # NDVI image extent
    transform = ndvi_src.transform
    left_x = transform[2]
    top_y = transform[5]
    pixel_w = transform[0]
    pixel_h = transform[4]

    extent = (
        left_x,
        left_x + w * pixel_w,
        top_y + h * pixel_h,
        top_y
    )

    # Draw NDVI image
    ax.imshow(ndvi_img, extent=extent, origin="upper", transform=ccrs.PlateCarree(), zorder=3)

    # District & State boundaries
    districts.plot(ax=ax, facecolor="none", edgecolor="#4D4D4D", linewidth=0.25, zorder=4)
    states.plot(ax=ax, facecolor="none", edgecolor="black", linewidth=0.8, zorder=5)


    # State Labels 
    india_proj = india.to_crs(epsg=3857)
    india["centroid"] = india_proj.centroid.to_crs(epsg=4326)

    # Manual wrapping for selected states only
    manual_wrap = {
        "Andhra Pradesh": "Andhra\nPradesh",
        "Jammu & Kashmir": "Jammu &\nKashmir",
        "Dadra & Nagar Haveli": "Dadra &\nNagar \nHaveli",
        "Himachal Pradesh": "Himachal\nPradesh",
        "Andaman & Nicobar Islands": "Andaman &\nNicobar Islands",
        "West Bengal": "West\nBengal"
    }

    # Manual offsets for fine adjustment (lon, lat)
    offsets = {
        "Kerala": (0.6, -0.5),
        "Tripura": (0, 0.1),
        "Mizoram":(0,-0.6),
        "Manipur": (0.4, 0),
        "Meghalaya":(0,-0.1),
        "Arunachal Pradesh": (0.2,0.2),
        "Andhra Pradesh": (-1.3,-0.9),
        "Karnataka": (-0.55,-0.3),
        "Jharkhand":(-0.2,0.2),
        "West Bengal": (-0.3,-0.8),
        "Assam":(-1,0),
        "Nagaland": (0,-0.2),
        "Punjab": (-0.6,-0.6),
        "Haryana": (0,0.1),
        "Nagaland": (0, 0),
        "Dadra & Nagar Haveli": (0.5, -0.3),
        "Andaman & Nicobar Islands": (0.8, -1.8),
        "Daman & Diu": (-1.2,0),
        
        
    }

    # Loop through states and add labels
    for _, row in india.iterrows():
        stname = str(row["stname_lab"])
        x, y = row["centroid"].x, row["centroid"].y

        # Apply manual offset if available
        if stname in offsets:
            dx, dy = offsets[stname]
            x += dx
            y += dy

        # Apply manual wrapping if needed
        label_text = manual_wrap.get(stname, stname)

        # Add text to map
        ax.text(
            x, y, label_text,
            ha="center", va="center",
            fontsize=6, fontname="Arial", weight="bold",
            color="black", zorder=5,
            path_effects=[path_effects.withStroke(linewidth=3, foreground="white")],
            transform=ccrs.PlateCarree()
        )


    # Grid + ticks
    lon_ticks = list(range(int(minx)-1, int(maxx)+2, 5))
    lat_ticks = list(range(int(miny)-1, int(maxy)+2, 5))

    ax.set_xticks(lon_ticks, crs=ccrs.PlateCarree())
    ax.set_yticks(lat_ticks, crs=ccrs.PlateCarree())
    ax.xaxis.set_major_formatter(cticker.LongitudeFormatter())
    ax.yaxis.set_major_formatter(cticker.LatitudeFormatter())

    ax.tick_params(labelsize=9, top=True, bottom=True, left=True, right=True,
                labeltop=True, labelbottom=True, labelleft=True, labelright=True)

    # rotate y labels
    for lbl in ax.get_yticklabels():
        lbl.set_rotation(90)


    # Title
    ax.text(maxx - 8, maxy, title_text,
            ha="center", va="top",
            fontsize=13, weight="bold",
            transform=ccrs.PlateCarree())

    
    # North arrow
    x, y = 0.05, 0.92
    ax.text(x, y + 0.04, 'N', ha='center', va='top',
            fontsize=9, fontname='Arial', color='black', transform=ax.transAxes)
    ax.text(x, y, '⮝', ha='center', va='center',
            fontsize=24, fontname='Noto Sans Symbols 2', color='black', transform=ax.transAxes)

    
    # Scale bar
    base_lat = 5.5
    mean_lat = (miny + maxy) / 2
    km_per_deg = 111.32 * math.cos(math.radians(mean_lat))

    marks_km = [0, 130, 260, 520, 780, 1040]
    marks_deg = [km/km_per_deg for km in marks_km]

    total_deg = marks_deg[-1]
    center_lon = 82
    left_lon = center_lon - total_deg/2

    for i in range(len(marks_km)-1):
        x0 = left_lon + sum((marks_km[j+1]-marks_km[j])/km_per_deg for j in range(i))
        width = (marks_km[i+1]-marks_km[i]) / km_per_deg
        color = "black" if i % 2 == 0 else "white"

        ax.add_patch(Rectangle(
            (x0, base_lat),
            width, 0.25,
            facecolor=color, edgecolor="black",
            transform=ccrs.PlateCarree(), zorder=8
        ))

    for i, km in enumerate(marks_km):
        ax.text(left_lon + marks_deg[i], base_lat+0.35, f"{km}",
                fontsize=6, transform=ccrs.PlateCarree())

    ax.text(left_lon + total_deg + 0.3, base_lat + 0.1, "Km",
            ha="left", va="center", fontsize=6.2, fontname="Arial", transform=ccrs.PlateCarree())


    # Source
    ax.text(97.6, base_lat - 0.2, "Source: MODIS",
            fontsize=5, style='italic',
            transform=ccrs.PlateCarree(), ha="right")


    # Legend
    patches = []
    for idx, (_, _, label, color) in enumerate(NDVI_CLASSES):
        patches.append(mpatches.Patch(facecolor=color, edgecolor='black',
                                    label=f"{label}"))

    leg = ax.legend(
        handles=patches,
        loc="lower left",
        bbox_to_anchor=(0.435, 0.12),
        fontsize=7.5,
        frameon=True,            
        handlelength=2.4,           # 🔹 wider color boxes
        handleheight=1.6,           # 🔹 taller color boxes
        handletextpad=0.4,          # spacing between box & text
        labelspacing=0.5,           # space between legend rows
        borderpad=0.4,
        facecolor="white", 
        edgecolor="black"
    )

    ax.text(0.44, 0.29, "Legend", fontsize=10, weight="bold", transform=ax.transAxes)


    # SAVE
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=dpi, bbox_inches='tight', pad_inches=0.1)
    plt.close()

    crop_white_margins_all_sides(output_path)

    print(f"  ✅ NDVI MAP SAVED: {output_path}")


    # EXPORT NDVI OBJECTS FOR STATE MAPS (NO STYLE CHANGE)
    NDVI_SRC = ndvi_src
    NDVI_IMG = ndvi_img
    NDVI_MASKED_FULL = ndvi_masked
    MASK_SRC = mask_src
    MASK_FULL = mask
    STATES_GDF = states
    DISTRICTS_GDF = districts

    print("✅ NDVI objects prepared for state-level maps")


    # USE NDVI FROM INDIA PIPELINE (NO RE-READ, NO STYLE CHANGE)

    ndvi_src = NDVI_SRC
    mask_src = MASK_SRC
    mask_full = MASK_FULL

    states = STATES_GDF
    districts = DISTRICTS_GDF

    print("🧠 Using NDVI from India pipeline")


    # Full script — state-level NDVI maps with proper agri-mask and clipped districts
    # (Patched: integer multiples-of-5 ticks, fixed 1.5 cm margins, locked aspect)
    

    # ---------------- TITLE (ArcMap-style two-line title) ----------------
    date_range_text = format_date_range(start_date, end_date)
    title_sub = f"({date_range_text}, {datetime.now().year})"
    title_text = f"Present NDVI\n({start_date} – {end_date})"

    dpi = 300


    # Add symbol font used for north arrow
    fm.fontManager.addfont(r"F:\Automation_Working\Vasanthi\crop_health_report\data\fonts\NotoSansSymbols2-Regular.ttf")

    # States to export
    state_list = [
        "Andhra Pradesh",
        "Haryana",
        "Madhya Pradesh",
        "Rajasthan",
        "Uttar Pradesh",
        "Chhattisgarh",
        "Maharashtra",
        "Odisha",
        "Karnataka",
        "Tamil Nadu"
    ]

    STATE_FIXED_EXTENT = {
        "Andhra Pradesh": [74, 87.5, 12, 20.7],
        "Haryana": [74.2, 78.0, 27.2, 31.5],
        "Madhya Pradesh": [74, 82.9, 20.5, 27.3],
        "Rajasthan": [69, 78.5, 22.8, 32],
        "Uttar Pradesh": [77, 84.5, 23.0, 31.3],
        "Chhattisgarh": [78, 86, 17, 25.5],
        "Maharashtra": [73, 80.57, 15, 23.5],
        "Odisha": [81, 87.7, 18, 22.5],
        "Karnataka": [72, 79.0, 11.0, 19],
        "Tamil Nadu": [75, 81, 7, 14.5]

    }


    # ---------------------- helper functions ----------------------
    def safe_filename(s):
        s = unicodedata.normalize("NFKD", s)
        s = "".join(ch for ch in s if ch.isalnum() or ch in (" ", "_", "-")).rstrip()
        return s.replace(" ", "_")

    def read_raster(path):
        src = rasterio.open(path)
        arr = src.read(1).astype("float32")
        return src, arr

    def resample_mask_states(mask_src, mask_arr, target_transform, target_shape, target_crs):
        """Reproject/resample a mask array (2D) into the target grid defined by transform/shape/crs."""
        dst = np.zeros(target_shape, dtype="float32")
        reproject(
            source=mask_arr,
            destination=dst,
            src_transform=mask_src.transform,
            src_crs=mask_src.crs,
            dst_transform=target_transform,
            dst_crs=target_crs,
            resampling=Resampling.nearest
        )
        return dst


    def build_class_image_from_arrays(ndvi_arr, classes):
        ndvi_arr = ndvi_arr.astype(np.float32)
        h, w = ndvi_arr.shape

        class_map = np.full((h, w), -1, dtype=np.int16)
        for idx, (lo, hi, label, hexcolor) in enumerate(classes):
            sel = (ndvi_arr >= lo) & (ndvi_arr <= hi)
            class_map[sel] = idx

        outimg = np.zeros((h, w, 4), dtype=np.uint8)
        outimg[..., 3] = 0
        for idx, (_, _, label, hexcolor) in enumerate(classes):
            r = int(hexcolor[1:3], 16)
            g = int(hexcolor[3:5], 16)
            b = int(hexcolor[5:7], 16)
            mask_idx = class_map == idx
            outimg[mask_idx, 0] = r
            outimg[mask_idx, 1] = g
            outimg[mask_idx, 2] = b
            outimg[mask_idx, 3] = 255
        return outimg, class_map


    # ---------------------- Read raster + vectors ----------------------
    print("Reading NDVI and AgriMask...")

    mask_bin_full = np.where(mask_full > 0, 1, 0)

    # Use NDVI prepared in India pipeline 
    ndvi_masked_full = NDVI_MASKED_FULL


    # read vectors
    states = STATES_GDF
    india = STATES_GDF
    districts = DISTRICTS_GDF


    # compute simple centroid column (for state labels)
    states_proj = states.to_crs(3857)
    states["centroid"] = states_proj.centroid.to_crs(4326)

    # ---------------------- State map generator ----------------------
    def make_state_map(stname, save_dir, title_text=None, dpi=300, figsize=(8,8.5)):
        print(f"\nGenerating map for: {stname}")

        # find state
        st_row = states[states['stname_lab'].str.lower() == stname.lower()]
        if st_row.empty:
            st_row = states[states['stname_lab'].str.contains(stname.split()[0], case=False, na=False)]
            if st_row.empty:
                print(f"  ⚠️ STATE NOT FOUND: {stname}")
                return

        geom = mapping(st_row.iloc[0].geometry)
        state_geom = st_row.geometry.union_all()


        # crop NDVI
        ndvi_crop, ndvi_transform = rio_mask(
            ndvi_src,
            [geom],
            crop=True,
            filled=True
        )

        ndvi_crop = ndvi_crop[0].astype(np.float32)

        if ndvi_src.nodata is not None:
            ndvi_crop = np.where(ndvi_crop == ndvi_src.nodata, np.nan, ndvi_crop)

        ndvi_crop = autoscale_modis(ndvi_crop)


        # crop mask
        try:
            mask_crop_raw, mask_transform = rio_mask(mask_src, [geom], crop=True, filled=True, invert=False)
            mask_crop = mask_crop_raw[0].astype(np.float32)

            # resample if needed
            if mask_transform != ndvi_transform or mask_crop.shape != ndvi_crop.shape:
                dst = np.zeros_like(ndvi_crop, dtype=np.float32)
                reproject(
                    source=mask_crop,
                    destination=dst,
                    src_transform=mask_transform,
                    src_crs=mask_src.crs,
                    dst_transform=ndvi_transform,
                    dst_crs=ndvi_src.crs,
                    resampling=Resampling.nearest
                )
                mask_crop = dst
        except:
            out_shape = ndvi_crop.shape
            geom_mask = geometry_mask([geom], transform=ndvi_transform, invert=True, out_shape=out_shape)
            mask_crop = geom_mask.astype(np.uint8)

        mask_state = np.where(mask_crop > 0, 1, 0)
        ndvi_masked = np.where(mask_state == 1, ndvi_crop, np.nan)

        # build class image
        ndvi_img_state, class_map_state = build_class_image_from_arrays(
            ndvi_masked,
            NDVI_CLASSES
        )


        # -----------------------   PLOTTING SECTION   ------------------------
        fig = plt.figure(figsize=figsize)
        ax = plt.axes(projection=ccrs.PlateCarree())

        
        #  FIXED EXTENT — DO NOT APPLY ANY DEGREE MARGINS
        minx, miny, maxx, maxy = st_row.total_bounds


        # Add 0.5 cm gap around extent
        if stname in STATE_FIXED_EXTENT:
            xmin, xmax, ymin, ymax = STATE_FIXED_EXTENT[stname]
        else:
            b = st_row.to_crs(4326).total_bounds
            xmin, xmax, ymin, ymax = b[0]-0.2, b[2]+0.2, b[1]-0.2, b[3]+0.2

        ax.set_extent([xmin, xmax, ymin, ymax], crs=ccrs.PlateCarree())

        
        #  FIXED 1.5 CM PHYSICAL MARGIN AROUND THE AXES FRAME
        FIG_W, FIG_H = figsize      # inches
        MARGIN_IN = 1.5 / 2.54      # convert 1.5 cm to inches

        left   = MARGIN_IN / FIG_W
        right  = 1 - MARGIN_IN / FIG_W
        bottom = MARGIN_IN / FIG_H
        top    = 1 - MARGIN_IN / FIG_H

        # set aspect lock to avoid cartopy stretching later
        ax.set_adjustable('datalim')
        ax.set_aspect('equal', adjustable='datalim')

        # apply initial position
        ax.set_position([left, bottom, right-left, top-bottom])

        
        # DRAW NDVI IMAGE (compute extent from ndvi_transform safely)
        t = ndvi_transform

        # Rasterio transform components:
        # t[0] = a (pixel width), t[4] = e (pixel height, usually negative), t[2] = c (x origin), t[5] = f (y origin)
        left_px = t[2]
        top_px = t[5]
        px_w = t[0]
        px_h = t[4]


        # compute right and bottom correctly (bottom may be < top if px_h negative)
        right_px = left_px + ndvi_img_state.shape[1] * px_w
        bottom_px = top_px + ndvi_img_state.shape[0] * px_h


        # apply same padding to raster extent
        extent = (
            left_px,
            right_px,
            bottom_px,
            top_px
        )

        print("AXES EXTENT:", xmin, xmax, ymin, ymax)
        print("RASTER EXTENT:", extent)


        ax.imshow(ndvi_img_state, extent=extent, origin="upper",
                transform=ccrs.PlateCarree(), zorder=2)

        # prevent cartopy from autoscaling the axes area after imshow
        ax.autoscale(False)

        # reapply the axes position (Cartopy may have changed it)
        ax.set_position([left, bottom, right-left, top-bottom])


        # GRID TICKS — multiples of 5 only (integers)    
        lon_ticks = list(range(int(xmin), int(xmax) + 1, 5))
        lat_ticks = list(range(int(ymin), int(ymax) + 1, 5))


        ax.set_xticks(lon_ticks, crs=ccrs.PlateCarree())
        ax.set_yticks(lat_ticks, crs=ccrs.PlateCarree())
        ax.xaxis.set_major_formatter(cticker.LongitudeFormatter())
        ax.yaxis.set_major_formatter(cticker.LatitudeFormatter())

        ax.tick_params(labelsize=9, top=True, bottom=True, left=True, right=True,
                labeltop=True, labelbottom=True, labelleft=True, labelright=True)

        # rotate y labels
        for lbl in ax.get_yticklabels():
            lbl.set_rotation(90)


        # DISTRICT BOUNDARIES + LABELS

        # Define manual wrap and shift inside the function
        manual_wrap_dt = {
            #Chhattisgarh
            "Uttar Bastar Kanker" : "Uttar\nBastar\nKanker",  
            "Dakshin Bastar Dantewada": "Dakshin\nBastar\nDantewada",   
            "Janjgir - Champa": "Janjgir\nChampa",

            #Rajasthan
            "Sawai Madhopur": "Sawai\nMadhopur",

            #Madhya Pradesh
            "Agar Malwa": "Agar\nMalwa",

            #Uttar Pradesh
            "Gautam Buddha Nagar":"Gautam\nBuddha\nNagar",
            "Kanpur Dehat":"Kanpur\nDehat",
            "Kanpur Nagar":"Kanpur\nNagar",
            "Sant Kabir Nagar":"Sant\nKabir\nNagar",
            "Ambedkar Nagar":"Ambedkar\nNagar",
            "Bara Banki":"Bara\nBanki",

            #Andhra Pradesh
            "Sri Potti Sriramulu Nel": "Sri Potti\nSriramulu\nNellore",
            "West Godavari": "West\nGodavari",
            "East Godavari": "East\nGodavari",

            #Meghalaya
            "South West Garo Hills": "South West\nGaro Hills",
            "South West Khasi Hills":"South West\nKhasi Hills",
            "West Garo Hills": "West Garo\nHills",

            #Karnataka
            "Uttara Kannada": "Uttara\nKannada",
            "Dakshina Kannada":"Dakshina\nKannada",
            "Bengaluru Rural": "Bengaluru\nRural",

            #Maharashtra 
            "Mumbai Suburban": "Mumbai\nSuburban",

            #Chhattisgarh 
            "Uttar Bastar Kanker": "Uttar\nBastar\nKanker",
            "Dakshin Bastar Dantewada": "Dakshin\nBastar\nDantewada"
        }

        manual_shift_dt = {
            #Jammu and Kashmir
            "Muzaffarabad": (0,-0.2),

            #Haryana
            "Yamunanagar": (-0.15,0),
            "Kurukshetra": (0,-0.05),
            "Gurugram": (0,0.05),
            "Faridabad": (-0.05,0),
            "Mahendragarh" : (0.15,0.2),

            #Madhya Pradesh 
            "Neemuch": (0,-0.1),
            "Niwari": (0.17,-0.15),
            "Alirajpur": (0.09,-0.02),
            "Burhanpur": (0,0.1),
            "Tikamgarh": (0.03,0.05),
            "Anuppur": (0.15,-0.1),
            "Ratlam": (0,-0.08),
            "Shahdol": (0.22,-0.3),
            "Agar Malwa": (0.1,-0.15),
            "Datia": (-0.02,-0.05),
            "Sehore": (0,-0.1),

            
            #Chhattisgarh
            "Balrampur": (-0.17,0),
            "Raigarh":(-0.05,0.1),
            "Raipur":(0,0.1),
            "Koriya":(0,0.2),
            "Bilaspur": (0.2,-0.2),
            "Mungeli" :(0.15,0.2),
            "Kabeerdham" :(0.1,-0.2),
            "Mahasamund": (0,0.05),
            "Rajnandgaon": (0.2,0.05),
            "Uttar Bastar Kanker":(0,0),
            "Gariaband":(-0.2,-0.05),
            "Kondagaon":(-0.1,0.05),
            "Narayanpur":(0.15,0),
            "Dakshin Bastar Dantewada":(0,0),
            "Sukma":(-0.05,-0.2),

            #Rajasthan
            "Ganganagar":(0.2,0.1),
            "Hanumangarh":(0,-0.2),
            "Churu":(0,0.2),
            "Bharatpur":(-0.2,0),
            "Dhaulpur":(-0.13,0),
            "Karauli":(-0.1,-0.2),
            "Sawai Madhopur":(0,0),
            "Baran": (0,0.25),
            "Jhalawar":(-0.2,0.15),
            "Banswara":(-0.1,0.08),
            "Dungarpur":(0.1,0.15),
            "Pratapgarh":(-0.17,0),
            "Chittaurgarh":(-0.1,0),
            "Tonk":(0,0.05),

            #Uttar Pradesh
            "Saharanpur":(0,-0.2),
            "Shamli":(0.1,-0.1),
            "Muzaffarnagar":(0.15,0.1),
            "Baghpat":(0.2,0.1),
            "Moradabad":(0,0.1),
            "Gautam Buddha Nagar":(0.4,-0.15),
            "Ghaziabad":(0.2,0.05),
            "Mathura":(0.09,0.11),
            "Mainpuri":(0,-0.1),
            "Agra":(0.1,0),
            "Bulandshahr":(-0.1,0.125),
            "Hapur":(0,-0.05),
            "Amroha":(0.13,0),
            "Sambhal":(0.2,0),
            "Etawah":(0,0.16),
            "Kanpur Dehat":(0,-0.1),
            "Amethi":(0,0.1),
            "Firozabad":(0,0.1),
            "Kanpur Nagar":(0.1,-0.2),
            "Jhansi":(0.45,0.15),
            "Lalitpur":(0.1,-0.2),
            "Sonbhadra":(0.04,0.2),
            "Chandauli":(-0.3,0),
            "Varanasi":(0.2,0),
            "Bhadohi":(-0.1,0),
            "Prayagraj":(0,-0.06),
            "Chitrakoot":(0,0.06),
            "Deoria":(0.12,-0.1),
            "Kushinagar":(0.05,-0.2),
            "Mahrajganj":(0,-0.1),
            "Shrawasti":(-0.1,0.1),
            "Siddharthnagar":(-0.3,0),
            "Gorakhpur":(0.15,-0.2),
            "Sant Kabir Nagar":(0.1,0.07),
            "Bahraich":(0.2,-0.3),
            "Balrampur":(0,0.05),
            "Mau":(0.1,0),
            "Pratapgarh":(-0.1,-0.04),
            "Jaunpur":(0.1,-0.1),
            "Bara Banki":(0,0),
            "Gonda":(0,-0.1),
            "Sultanpur":(0,-0.1),
            "Lucknow":(-0.05,0),
            "Hardoi":(0,-0.1),
            "Lucknow":(0,-0.1),

            #Tamil Nadu
            "Ramanathapuram": (-0.18, -0.2),
            "Thoothukkudi": (-0.1,0.2),
            "Thiruvarur": (0, 0.1),
            "Coimbatore": (0,0.2),
            "Karur": (-0.40, 0.1),
            "Nagapattinam":(-0.23, -0.2),
            "Kanniyakumari":(0.2,0),
            "Chennai":(-0.2,0),
            "Kancheepuram":(-0.15,0),
            "The Nilgiris": (0.15,0),
            "Viluppuram": (-0.05,-0.15),
            "Puducherry":(-0.24,0),
            "Karaikal":(-0.18,-0.03),


            #Andhra Pradesh 
            "East Godavari": (0,0.2),
            "Vizianagaram":(0.2,-0.1),

            #Karnataka
            "Davanagere": (0, 0.2),
            "Dharwad": (0,-0.1),
            "Uttara Kannada": (0,0.15),
            "Bhandara": (0,-0.1),
            "Udupi":(0.05,0),
            "Chikkaballapura":(-0.2,0),
            "Chitradurga":(-0.1,-0.1),
            "Kodagu":(0.1,0),
            "Ramanagara":(-0.1,0.05),
            "Dakshina Kannada":(0,0.1),
            "Chamarajanagara":(-0.1,0),

            #Meghalaya 
            "West Garo Hills":(0,0.1),
            "West Jaintia Hills":(0.06,0.1),

            #Odisha
            "Sundargarh":(0,0.1),
            "Nuapada":(0.15,0),
            "Nabarangapur":(0.15,0),
            "Puri":(0.3,0.1),
            "Jagatsinghapur":(-0.15,0.1),
            "Baleshwar":(-0.15,0),
            "Kendrapara":(-0.1,0),
            "Jajapur":(-0.04,0),
            "Balangir":(0,0.05),

            #Maharashtra
            "Gondiya":(-0.1,0.1),
            "Mumbai": (0.3,-0.1),
            "Mumbai Suburban": (0.28,0),
            "Sindhudurg":(0.25,0),
            "Nandurbar":(-0.3,0.2),
            "Ratnagiri":(0.1,0),
            "Raigarh":(0.1,0),
            "Kolhapur":(-0.2,0),
        }


        # --- DISTRICT SELECTION (ROBUST) ---
        st_geom_proj = st_row.to_crs(3857).geometry.union_all()
        districts_proj = districts.to_crs(3857)

        idx = districts_proj.geometry.centroid.within(st_geom_proj)
        state_districts = districts[idx].copy()

        # Plot boundaries
        state_districts.plot(ax=ax, facecolor="none",
                            edgecolor="black", linewidth=0.25, zorder=4)

        # Plot labels
        for _, drow in state_districts.iterrows():
            raw_lab = str(drow.get('dtname','') or drow.get('district_name','')).strip()
            if not raw_lab:
                continue

            lab = manual_wrap_dt.get(raw_lab, raw_lab)

            rp = drow.geometry.representative_point()
            final_x, final_y = rp.x, rp.y

            if raw_lab in manual_shift_dt:
                dx, dy = manual_shift_dt[raw_lab]
                final_x += dx
                final_y += dy

            ax.text(
                final_x, final_y, lab,
                fontsize=8, fontweight="bold",
                ha="center", va="center",
                transform=ccrs.PlateCarree(),
                zorder=6,
                path_effects=[
                    path_effects.withStroke(linewidth=3.8, foreground="white")
                ]
            )

        ZOOM = {
            "Chhattisgarh": 0.85,   # 85% of original size
        }

        z = ZOOM.get(stname, 1.00)


        # thicker state boundary
        st_row.plot(ax=ax, facecolor="none", edgecolor="black", linewidth=0.8, zorder=5)


        # TITLE (per-state manual positioning)
        title_main = f"Present NDVI - {stname}"


        # Custom positions for each state
        TITLE_POS = {
            "Uttar Pradesh":   (0.50, 0.965),
            "Andhra Pradesh":  (0.50, 0.965),
            "Karnataka":       (0.35, 0.965),
            "Odisha":          (0.50, 0.965),
            "Rajasthan":       (0.50, 0.965),
            "Madhya Pradesh":  (0.50, 0.965),
            "Chhattisgarh":    (0.50, 0.965),
            "Maharashtra":     (0.50, 0.965),
            "Haryana":         (0.35, 0.965),
            "Tamil Nadu":      (0.35, 0.965)
        }

        # Get position (default = center top)
        TX, TY = TITLE_POS.get(stname, (0.50, 0.98))

        # GAP between title and subtitle
        LINE_GAP = 0.04   # change this to increase or reduce spacing

        # Main title
        ax.text(
            TX, TY,
            title_main,
            ha="center", va="top",
            fontname="Arial", fontsize=18, weight="bold",
            transform=ax.transAxes
        )

        # Subtitle
        ax.text(
            TX, TY - LINE_GAP,
            title_sub,
            ha="center", va="top",
            fontname="Arial", fontsize=16, weight="bold",
            transform=ax.transAxes
        )


        # NORTH ARROW
        ax.text(0.96, 0.945, 'N', transform=ax.transAxes,
                ha='center', va='bottom', fontsize=10)
        ax.text(0.96, 0.92, '⮝', transform=ax.transAxes,
                ha='center', va='center', fontsize=25,
                fontname='Noto Sans Symbols 2')


        # SCALE BAR
        SCALEBAR_MAXKM = {
            "Rajasthan": 300,
            "Madhya Pradesh": 300,
            "Chhattisgarh": 200,
            "Odisha": 200,
            "Maharashtra": 280,
            "Andhra Pradesh": 240,
            "Uttar Pradesh": 240,
            "Haryana": 100,
            "Karnataka": 160,
            "Tamil Nadu": 160
        }

        def scale_marks(max_km):
            """Return the correct AIC-style scale bar tick marks."""
            if max_km == 300:
                return [0, 37.5, 75, 150, 225, 300]
            elif max_km == 280:
                return [0, 35, 70, 140, 210, 280]
            elif max_km == 240:
                return [0, 30, 60, 120, 180, 240]
            elif max_km == 200:
                return [0, 20, 40, 80, 120, 160, 200]
            elif max_km == 160:
                return [0, 20, 40, 80, 120, 160]
            elif max_km == 100:
                return [0, 25, 50, 75, 100]
            else:
                return [0, max_km/4, max_km/2, 3*max_km/4, max_km]

        # SCALE BAR draw in axes fraction
        max_km = SCALEBAR_MAXKM.get(stname, 200)
        marks_km = scale_marks(max_km)


        # ----------- SIZE SETTINGS  ----------- 
        bar_y_frac = 0.01        # vertical placement 
        bar_height_frac = 0.008   # thickness
        SCALEBAR_WIDTH_FRAC = 0.28   # <<<<< CONSTANT bar length on page (adjust 0.25–0.32)


        # left anchor in axes-fraction (NOT geographic now)
        left_frac = 0.30       # move left/right here (adjust 0.10–0.20)


        # ---------- DRAW SEGMENTS -------------
        total_km = marks_km[-1]    # max scale value

        for i in range(len(marks_km) - 1):
            km0 = marks_km[i]
            km1 = marks_km[i + 1]

            # width of this segment as fraction of bar width
            seg_frac = (km1 - km0) / total_km * SCALEBAR_WIDTH_FRAC
            seg_left = left_frac + (km0 / total_km) * SCALEBAR_WIDTH_FRAC

            color = "black" if i % 2 == 0 else "white"

            rect = Rectangle(
                (seg_left, bar_y_frac), 
                seg_frac,
                bar_height_frac,
                facecolor=color, edgecolor="black",
                transform=ax.transAxes, zorder=12
            )
            ax.add_patch(rect)


        # ---------- LABELS ----------
        for km in marks_km:
            x_frac = left_frac + (km / total_km) * SCALEBAR_WIDTH_FRAC
            ax.text(x_frac,
                    bar_y_frac + bar_height_frac * 1.6,
                    f"{int(km)}",
                    fontsize=7, ha="center",
                    transform=ax.transAxes, zorder=13)

        # unit label
        ax.text(left_frac + SCALEBAR_WIDTH_FRAC + 0.015,
                bar_y_frac + bar_height_frac * 0.6,
                "Km", fontsize=8,
                transform=ax.transAxes, zorder=13)


        # Source
        ax.text(0.99, 0.01, "Source: MODIS",
                fontsize=7, style='italic',
                transform=ax.transAxes, ha="right")
        

        # LEGEND
        patches = [mpatches.Patch(facecolor=c, edgecolor='black', label=l)
                for _,_,l,c in NDVI_CLASSES]

        LEGEND_POS = {
            "Uttar Pradesh":     (0.65, 0.67),
            "Rajasthan":         (0.005, 0.06),
            "Madhya Pradesh":    (0.65, 0.03),
            "Chhattisgarh":      (0.65, 0.03),
            "Odisha":            (0.65, 0.04),
            "Maharashtra":       (0.65, 0.03),
            "Karnataka":         (0.005, 0.06),
            "Tamil Nadu":        (0.005, 0.06),
            "Andhra Pradesh":    (0.65, 0.03),
            "Haryana":           (0.005, 0.06)
            }


        # legend placement based ONLY on state shape
        legend_x, legend_y = LEGEND_POS.get(stname, (0.65, 0.04))

        leg = ax.legend(
            handles=patches,
            loc="lower left",
            bbox_to_anchor=(legend_x, legend_y),
            fontsize=8,
            frameon=True,
            borderpad=0.6,
            handlelength=2.4,
            handleheight=1.6,
            facecolor="white",
            edgecolor="black"
        )

        ax.text(
            legend_x + 0.01 , legend_y + 0.165,
            "Legend", fontsize=10, weight="bold",
            transform=ax.transAxes
        )


        # SAVE OUTPUT
        fname = os.path.join(save_dir, f"NDVI_{safe_filename(stname)}.png")
        os.makedirs(save_dir, exist_ok=True)
        plt.savefig(fname, dpi=dpi, bbox_inches='tight', pad_inches=0.1)
        plt.close(fig)

        crop_white_margins_all_sides(fname)
        print(f"  ✅ Saved: {fname}")


    # ---------------------- Run generation for selected states ----------------------
    os.makedirs(multi_output_dir, exist_ok=True)
    for s in state_list:
        try:
            make_state_map(s, multi_output_dir, title_text=f"Present NDVI\n({s})", dpi=dpi, figsize=(8,8.5))
        except Exception as e:
            print(f"Error generating {s}: {e}")

    print("\nAll done.")

    ndvi_src.close()
    if tmp_path:
        os.remove(tmp_path)

if __name__ == "__main__":
    main()
