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
from labels import *

# ============================================================
# PROJECT RESOURCES
# ============================================================

font_path = PROJECT_DIR / "data" / "fonts" / "NotoSansSymbols2-Regular.ttf"


# AUTH
def get_token():
    r = requests.post(f"{API_URL}login", auth=(USERNAME, PASSWORD))
    r.raise_for_status()
    token = r.json()["token"]

    print(" Authentication successful")
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
    start_date = datetime.strptime(start_date, "%m-%d-%Y").date()
    end_date = datetime.strptime(end_date, "%m-%d-%Y").date()

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
    print(f"Task submitted: {task_id}")
    return task_id


# FETCH NDVI DOWNLOAD URL
def get_download_url(token, task_id):

    while True:
        try:
            r = SESSION.get(
                f"{API_URL}task/{task_id}",
                timeout=30
            )
            r.raise_for_status()
        except requests.exceptions.ReadTimeout:
            print("AppEEARS not responding (timeout). Retrying in 90s...")
            time.sleep(120)
            continue
        except requests.exceptions.ConnectionError:
            print("Connection dropped. Retrying in 90s...")
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

            raise RuntimeError("NDVI data for this MODIS window has not yet been published by AppEEARS.")

        elif status == "error":
            raise RuntimeError("AppEEARS task failed")

        print(f" Status: {status} (retry in 120s)")
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

    s = datetime.strptime(start_date,"%m-%d-%Y")
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

    for window_start, window_end in windows:

        start_str = window_start.strftime("%m-%d-%Y")
        end_str   = window_end.strftime("%m-%d-%Y")

        print(f"\nProcessing {start_str} -> {end_str}")


        # checking whether the ndvi is already downloaded or not. if not then download it from appeears
        window_text = format_window_name(start_str, end_str)
        ndvi_tif_name = f"{PRODUCT}_{window_text}.tif"

        
        NDVI_TIF_OUTPUT = OUTPUT_RASTER / ndvi_tif_name

        
        # CHECK IF TIFF EXISTS

        if os.path.exists(NDVI_TIF_OUTPUT):
            print(" NDVI TIFF already exists. Skipping download...")
            print("Using:", NDVI_TIF_OUTPUT)

            ndvi_raster = NDVI_TIF_OUTPUT   # use local file

            use_local_file = True

        else:
            print(" NDVI TIFF not found. Downloading from AppEEARS...")

            use_local_file = False

            task_id = submit_task(token, start_str, end_str)
            ndvi_raster = get_download_url(token, task_id)

    
        

        print(" NDVI raster URL:")
        print(ndvi_raster)


        # Show which NDVI file is used
        ndvi_filename = os.path.basename(ndvi_raster)

        print(" NDVI FILE USED FOR MAP:")
        print(ndvi_filename)
        print("-" * 60)


        # NDVI MAP AUTOMATION 
        
        print(f"Maps will be saved under:\n{OUTPUT_MAPS}")

        output_path = OUTPUT_MAPS / f"NDVI_India_{window_text}.png"
        multi_output_dir = OUTPUT_MAPS

        date_range_text = format_date_range(start_str, end_str)

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
                print(" Reading NDVI from local TIFF...")
                src = rasterio.open(source)
                arr = src.read(1).astype("float32")
                return src, arr, None

            # Download raster from the AppEEARS URL
            print(" Fetching NDVI from AppEEARS...")

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

        def resample_raster(
            source_src,
            source_array,
            target_transform,
            target_shape,
            target_crs,
            resampling=Resampling.nearest,
        ):
            """
            Resample a raster array to match the target raster grid.

            Parameters
            ----------
            source_src : rasterio.DatasetReader
                Source raster dataset.
            source_array : ndarray
                Raster values to resample.
            target_transform : Affine
                Transform of the target raster.
            target_shape : tuple
                (height, width) of the target raster.
            target_crs : CRS
                Coordinate reference system of the target raster.
            resampling : rasterio.warp.Resampling, optional
                Resampling method (default: nearest).

            Returns
            -------
            ndarray
                Raster aligned with the target raster.

            Example
            -------
            Resample an agricultural mask to match a MODIS NDVI raster.
            """

            dst = np.zeros(target_shape, dtype=source_array.dtype)

            reproject(
                source=source_array,
                destination=dst,
                src_transform=source_src.transform,
                src_crs=source_src.crs,
                dst_transform=target_transform,
                dst_crs=target_crs,
                resampling=resampling,
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
        window_text = format_window_name(start_str, end_str)

        ndvi_tif_name = f"{PRODUCT}_{window_text}.tif"


        if not use_local_file:
            print(" Saving NDVI TIFF...")

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

            print(" NDVI TIFF saved:", NDVI_TIF_OUTPUT)

        if MASK_PATH is not None:
            print("Reading AgriMask raster...")
            mask_src = rasterio.open(MASK_PATH)
            mask_raw = mask_src.read(1).astype("float32")

            # Resample mask if needed
            if (mask_src.width != ndvi_src.width) or \
            (mask_src.height != ndvi_src.height) or \
            (mask_src.transform != ndvi_src.transform):
                print("Resampling AgriMask to NDVI resolution...")
                mask = resample_raster(
                    mask_src,
                    mask_raw,
                    ndvi_src.transform,
                    (ndvi_src.height, ndvi_src.width),
                    ndvi_src.crs,
                )
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
        # unique, cnt = np.unique(class_map, return_counts=True)
        # count_dict = {int(k): int(v) for k, v in zip(unique, cnt)}

        
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

        fig = plt.figure(figsize=FIGURE_SIZE)
        ax = plt.axes(projection=ccrs.PlateCarree())

        # Extent
        minx, miny, maxx, maxy = states.total_bounds
        ax.set_extent([
            minx - MAP_PADDING["left"],
            maxx + MAP_PADDING["right"],
            miny - MAP_PADDING["bottom"],
            maxy + MAP_PADDING["top"],
        ])

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
        if SHOW_STATE_LABELS:
            india_proj = india.to_crs(epsg=3857)
            india["centroid"] = india_proj.centroid.to_crs(epsg=4326)

            # Loop through states and add labels
            for _, row in india.iterrows():
                stname = str(row["stname_lab"])
                x, y = row["centroid"].x, row["centroid"].y

                # Apply manual offset if available
                if stname in STATE_LABEL_OFFSETS:
                    dx, dy = STATE_LABEL_OFFSETS[stname]
                    x += dx
                    y += dy

                # Apply manual wrapping if needed
                label_text = STATE_LABEL_WRAP.get(stname, stname)

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
        if SHOW_GRID:

            # Grid + ticks
            lon_ticks = list(range(int(minx)-1, int(maxx)+2, GRID_INTERVAL))
            lat_ticks = list(range(int(miny)-1, int(maxy)+2, GRID_INTERVAL))

            ax.set_xticks(lon_ticks, crs=ccrs.PlateCarree())
            ax.set_yticks(lat_ticks, crs=ccrs.PlateCarree())

            ax.xaxis.set_major_formatter(cticker.LongitudeFormatter())
            ax.yaxis.set_major_formatter(cticker.LatitudeFormatter())

            ax.tick_params(
                labelsize=GRID_LABEL_SIZE,
                top=True,
                bottom=True,
                left=True,
                right=True,
                labeltop=True,
                labelbottom=True,
                labelleft=True,
                labelright=True
            )

            # Rotate latitude labels
            for lbl in ax.get_yticklabels():
                lbl.set_rotation(90)


        # Title
        if SHOW_DATE_RANGE:
            country_title = f"{MAP_TITLE}\n({date_range_text})"
        else:
            country_title = MAP_TITLE

        ax.text(
            maxx - TITLE_X_OFFSET,
            maxy,
            country_title,
            ha="center",
            va="top",
            fontsize=13,
            weight="bold",
            transform=ccrs.PlateCarree()
        )

        #North Arrow
        if SHOW_NORTH_ARROW:
            x, y = NORTH_ARROW_POSITION

            ax.text(
                x, y + 0.04, "N",
                ha="center", va="top",
                fontsize=9,
                fontname="Arial",
                color="black",
                transform=ax.transAxes
            )

            ax.text(
                x, y, "⮝",
                ha="center", va="center",
                fontsize=24,
                fontname="Noto Sans Symbols 2",
                color="black",
                transform=ax.transAxes
            )

        
        # Scale bar
        if SHOW_SCALE_BAR:
            base_lat = SCALE_BAR_BASE_LAT
            mean_lat = (miny + maxy) / 2
            km_per_deg = 111.32 * math.cos(math.radians(mean_lat))

            marks_km = SCALE_BAR_MARKS
            marks_deg = [km/km_per_deg for km in marks_km]

            total_deg = marks_deg[-1]
            center_lon = SCALE_BAR_CENTER_LON
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


    #FROM HERE TOMORROW I HAVE TO CONTINUE CLEANING 

        # Source
        if SHOW_SOURCE:
            x, y_offset = SOURCE_POSITION
            ax.text(
                x,
                base_lat + y_offset,
                SOURCE_TEXT,
                fontsize=5, 
                style='italic',
                transform=ccrs.PlateCarree(), 
                ha="right")

        # Legend

        if SHOW_LEGEND:
            patches = []

            for _, _, label, color in NDVI_CLASSES:
                patches.append(
                    mpatches.Patch(
                        facecolor=color,
                        edgecolor="black",
                        label=label
                    )
                )

            leg = ax.legend(
                handles=patches,
                loc="lower left",
                bbox_to_anchor=LEGEND_POSITION,
                fontsize=7.5,
                frameon=True,            
                handlelength=2.4,           # wider color boxes
                handleheight=1.6,           # taller color boxes
                handletextpad=0.4,          # spacing between box & text
                labelspacing=0.5,           # space between legend rows
                borderpad=0.4,
                facecolor="white", 
                edgecolor="black"
            )

            legend_title_x, legend_title_y = LEGEND_TITLE_POSITION

            ax.text(
                legend_title_x,
                legend_title_y,
                LEGEND_TITLE,
                fontsize=10,
                weight="bold",
                transform=ax.transAxes
            )

        # SAVE
        plt.savefig(output_path, dpi=FIGURE_DPI, bbox_inches='tight', pad_inches=0.1)
        plt.close()

        print(f" NDVI MAP SAVED: {output_path}")


        # ============================================================
        # GENERATE STATE MAPS
        # ============================================================
        print("Generating state-level NDVI maps by using NDVI from India pipeline")
        
        # ---------------- TITLE  ----------------
        if SHOW_DATE_RANGE:
            country_title = f"{MAP_TITLE}\n({date_range_text})"
        else:
            country_title = MAP_TITLE



        # ---------------------- helper functions ----------------------
        def safe_filename(name):
            """
            Convert a string into a filename-safe format.

            Example
            -------
            Input : "Andhra Pradesh"
            Output: "Andhra_Pradesh"
            """
            name = unicodedata.normalize("NFKD", name)
            name = "".join(ch for ch in name if ch.isalnum() or ch in (" ", "_", "-")).rstrip()
            return name.replace(" ", "_")


        def create_classified_image(ndvi_array, classes):
            """
            Convert an NDVI array into a classified RGBA image.

            Parameters
            ----------
            ndvi_array : ndarray
                NDVI values after masking and preprocessing.
            classes : list
                Classification rules in the format:
                (minimum, maximum, label, hex_color)

            Returns
            -------
            rgba_image : ndarray
                RGBA image used for plotting.
            class_map : ndarray
                Integer class index for each pixel.

            Example
            -------
            NDVI = 0.72
                → Moderate Excess
                → #32CD32
            """
            ndvi_array = ndvi_array.astype(np.float32)
            h, w = ndvi_array.shape

            class_map = np.full((h, w), -1, dtype=np.int16)
            for idx, (lo, hi, _, hexcolor) in enumerate(classes):
                sel = (ndvi_array >= lo) & (ndvi_array <= hi)
                class_map[sel] = idx

            rgba_image = np.zeros((h, w, 4), dtype=np.uint8)
            rgba_image[..., 3] = 0
            for idx, (_, _, _, hexcolor) in enumerate(classes):
                r = int(hexcolor[1:3], 16)
                g = int(hexcolor[3:5], 16)
                b = int(hexcolor[5:7], 16)
                class_pixels = class_map == idx
                rgba_image[class_pixels, 0] = r
                rgba_image[class_pixels, 1] = g
                rgba_image[class_pixels, 2] = b
                rgba_image[class_pixels, 3] = 255
            return rgba_image, class_map


        # ============================================================
        # PREPARE DATA FOR STATE MAPS
        # ============================================================
        print("Preparing data for state-level maps...")

        # Compute state centroids for label placement
        states_proj = states.to_crs(3857)
        states["centroid"] = states_proj.centroid.to_crs(4326)

        # ---------------------- State map generator ----------------------
        def make_state_map(
            stname,
            save_dir,
            dpi=FIGURE_DPI,
            figsize=FIGURE_SIZE,
        ):
            print(f"\nGenerating map for: {stname}")

            # Find the selected state boundary
            st_row = states[states['stname_lab'].str.lower() == stname.lower()]
            if st_row.empty:
                st_row = states[states['stname_lab'].str.contains(stname.split()[0], case=False, na=False)]
                if st_row.empty:
                    print(f"   STATE NOT FOUND: {stname}")
                    return

            geom = mapping(st_row.iloc[0].geometry)

            # Clip NDVI raster to the selected state
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


            # Clip agricultural mask to the selected state
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
            except Exception:
                out_shape = ndvi_crop.shape
                geom_mask = geometry_mask([geom], transform=ndvi_transform, invert=True, out_shape=out_shape)
                mask_crop = geom_mask.astype(np.uint8)

            mask_state = np.where(mask_crop > 0, 1, 0)
            ndvi_masked = np.where(mask_state == 1, ndvi_crop, np.nan)

            # Create the classified NDVI image
            ndvi_img_state, class_map_state = create_classified_image(
                ndvi_masked,
                NDVI_CLASSES
            )


            # ============================================================
            # PLOT STATE MAP
            # ============================================================
            fig = plt.figure(figsize=figsize)
            ax = plt.axes(projection=ccrs.PlateCarree())


            # Set map extent
            if stname in REGION_EXTENTS :
                xmin, xmax, ymin, ymax = REGION_EXTENTS [stname]
            else:
                b = st_row.to_crs(4326).total_bounds
                xmin, xmax, ymin, ymax = b[0]-0.2, b[2]+0.2, b[1]-0.2, b[3]+0.2

            ax.set_extent([xmin, xmax, ymin, ymax], crs=ccrs.PlateCarree())

            
            # Set a fixed 1.5 cm margin around the map frame
            fig_width, fig_height = figsize
            margin_inches = 1.5 / 2.54

            left = margin_inches / fig_width
            right = 1 - margin_inches / fig_width
            bottom = margin_inches / fig_height
            top = 1 - margin_inches / fig_height

            # set aspect lock to avoid cartopy stretching later
            ax.set_adjustable('datalim')
            ax.set_aspect('equal', adjustable='datalim')

            # apply initial position
            ax.set_position([left, bottom, right-left, top-bottom])

            
            # DRAW NDVI IMAGE (compute extent from ndvi_transform safely)
            transform = ndvi_transform

        # Extract raster bounds from the affine transform
            # t[0] = a (pixel width), t[4] = e (pixel height, usually negative), t[2] = c (x origin), t[5] = f (y origin)
            left_px = transform[2]
            top_px = transform[5]
            px_w = transform[0]
            px_h = transform[4]


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

            # Debug: compare map and raster extents
            # print("AXES EXTENT:", xmin, xmax, ymin, ymax)
            # print("RASTER EXTENT:", extent)


            ax.imshow(ndvi_img_state, extent=extent, origin="upper",
                    transform=ccrs.PlateCarree(), zorder=2)

            # Keep the manually defined map extent
            ax.autoscale(False)

            # reapply the axes position (Cartopy may have changed it)
            ax.set_position([left, bottom, right-left, top-bottom])


            # Grid lines and coordinate labels 
            lon_ticks = list(range(int(xmin), int(xmax) + 1, GRID_INTERVAL))
            lat_ticks = list(range(int(ymin), int(ymax) + 1, GRID_INTERVAL))


            ax.set_xticks(lon_ticks, crs=ccrs.PlateCarree())
            ax.set_yticks(lat_ticks, crs=ccrs.PlateCarree())
            ax.xaxis.set_major_formatter(cticker.LongitudeFormatter())
            ax.yaxis.set_major_formatter(cticker.LatitudeFormatter())

            ax.tick_params(labelsize=9, top=True, bottom=True, left=True, right=True,
                    labeltop=True, labelbottom=True, labelleft=True, labelright=True)

            # rotate y labels
            for label in ax.get_yticklabels():
                label.set_rotation(90)


            # Select districts belonging to the current state
            st_geom_proj = st_row.to_crs(3857).geometry.union_all()
            districts_proj = districts.to_crs(3857)

            district_mask = districts_proj.geometry.centroid.within(st_geom_proj)
            state_districts = districts[district_mask].copy()

            # Draw district boundaries
            state_districts.plot(ax=ax, facecolor="none",
                                edgecolor="black", linewidth=0.25, zorder=4)

            # Add district labels
            for _, drow in state_districts.iterrows():
                raw_lab = str(drow.get('dtname','') or drow.get('district_name','')).strip()
                if not raw_lab:
                    continue

                label_text = DISTRICT_LABEL_WRAP.get(raw_lab, raw_lab)

                label_point = drow.geometry.representative_point()
                final_x, final_y = label_point.x, label_point.y

                if raw_lab in DISTRICT_LABEL_SHIFT:
                    dx, dy = DISTRICT_LABEL_SHIFT[raw_lab]
                    final_x += dx
                    final_y += dy

                ax.text(
                    final_x, final_y, label_text,
                    fontsize=8, fontweight="bold",
                    ha="center", va="center",
                    transform=ccrs.PlateCarree(),
                    zorder=6,
                    path_effects=[
                        path_effects.withStroke(linewidth=3.8, foreground="white")
                    ]
                )

            # thicker state boundary
            st_row.plot(ax=ax, facecolor="none", edgecolor="black", linewidth=0.8, zorder=5)


            # TITLE (per-state manual positioning)
            if SHOW_DATE_RANGE:
                state_title = f"{MAP_TITLE} - {stname}\n({date_range_text})"
            else:
                state_title = f"{MAP_TITLE} - {stname}"


            # Custom positions for each state
            # Get position (default = center top)
            TX, TY = STATE_TITLE_POSITION.get(stname, (0.50, 0.98))

            # Main title
            ax.text(
                TX, TY,
                state_title,
                ha="center", va="top",
                fontname="Arial", fontsize=18, weight="bold",
                transform=ax.transAxes
            )


            # NORTH ARROW
            arrow_x, arrow_y = STATE_NORTH_ARROW_POSITION

            ax.text(
                arrow_x,
                arrow_y + 0.025,
                "N",
                transform=ax.transAxes,
                ha="center",
                va="bottom",
                fontsize=10,
            )

            ax.text(
                arrow_x,
                arrow_y,
                "⮝",
                transform=ax.transAxes,
                ha="center",
                va="center",
                fontsize=25,
                fontname="Noto Sans Symbols 2",
            )


            # SCALE BAR
            max_km = STATE_SCALEBAR_MAXKM.get(stname, 200)

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
            marks_km = scale_marks(max_km)


            # ----------- Scale bar settings -----------

            total_km = marks_km[-1]

            for i in range(len(marks_km) - 1):
                km0 = marks_km[i]
                km1 = marks_km[i + 1]

                seg_frac = (km1 - km0) / total_km * STATE_SCALEBAR_WIDTH
                seg_left = STATE_SCALEBAR_LEFT + (km0 / total_km) * STATE_SCALEBAR_WIDTH

                color = "black" if i % 2 == 0 else "white"

                rect = Rectangle(
                    (seg_left, STATE_SCALEBAR_Y),
                    seg_frac,
                    STATE_SCALEBAR_HEIGHT,
                    facecolor=color,
                    edgecolor="black",
                    transform=ax.transAxes,
                    zorder=12,
                )
                ax.add_patch(rect)


            # ---------- SCALE BAR LABELS ----------
            for km in marks_km:
                x_frac = STATE_SCALEBAR_LEFT + (km / total_km) * STATE_SCALEBAR_WIDTH

                ax.text(
                    x_frac,
                    STATE_SCALEBAR_Y + STATE_SCALEBAR_HEIGHT * 1.6,
                    f"{int(km)}",
                    fontsize=7,
                    ha="center",
                    transform=ax.transAxes,
                    zorder=13,
                )

            ax.text(
                STATE_SCALEBAR_LEFT + STATE_SCALEBAR_WIDTH + 0.015,
                STATE_SCALEBAR_Y + STATE_SCALEBAR_HEIGHT * 0.6,
                STATE_SCALEBAR_UNIT,
                fontsize=8,
                transform=ax.transAxes,
                zorder=13,
            )


            # Source
            source_x, source_y = STATE_SOURCE_POSITION

            ax.text(
                source_x,
                source_y,
                f"Source: {MAP_SOURCE}",
                fontsize=7,
                style="italic",
                transform=ax.transAxes,
                ha="right",
            )
            

            # LEGEND
            patches = [mpatches.Patch(facecolor=c, edgecolor='black', label=l)
                    for _,_,l,c in NDVI_CLASSES]

            # legend placement based ONLY on state shape
            legend_x, legend_y = STATE_LEGEND_POSITION.get(stname, (0.65, 0.04))

            ax.legend(
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
                legend_x + 0.01,
                legend_y + 0.165,
                LEGEND_TITLE,
                fontsize=10,
                weight="bold",
                transform=ax.transAxes,
            )


            # SAVE OUTPUT
            fname = os.path.join(save_dir, f"NDVI_{safe_filename(stname)}_{window_text}.png")
            os.makedirs(save_dir, exist_ok=True)
            plt.savefig(fname, dpi=dpi, bbox_inches='tight', pad_inches=0.1)
            plt.close(fig)

            print(f" Saved: {fname}")


        # ---------------------- Run generation for selected states ----------------------
        os.makedirs(multi_output_dir, exist_ok=True)
        for state in STATE_LIST:
            try:
                make_state_map(
                    state,
                    multi_output_dir,
                    dpi=FIGURE_DPI,
                    figsize=FIGURE_SIZE,
                )
            except Exception as error:
                print(f"Error generating {state}: {error}")


    # Close datasets after ALL state maps are finished
    ndvi_src.close()

    if MASK_PATH is not None:
        mask_src.close()


    print("\nAll done.")

    if tmp_path:
        os.remove(tmp_path)

if __name__ == "__main__":
    main()
