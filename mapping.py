# NDVI FILTER

MIN_NDVI = 0.05
MAX_NDVI = 1.00


# NDVI CLASSIFICATION

NDVI_CLASSES = [
    (0.05, 0.20, "0.05–0.20 (Extreme Deficit)", "#FF0000"),
    (0.21, 0.40, "0.21–0.40 (Moderate Deficit)", "#FF8C00"),
    (0.41, 0.60, "0.41–0.60 (Normal)", "#ADFF2F"),
    (0.61, 0.80, "0.61–0.80 (Moderate Excess)", "#32CD32"),
    (0.81, 1.00, "0.81–1.00 (Extreme Excess)", "#006400"),
]


# MAP SETTINGS

FIGURE_SIZE = (8, 8.5)
FIGURE_DPI = 300
TITLE_FONT_SIZE = 16


# MAP TITLE

MAP_TITLE = "MODIS NDVI"
SHOW_DATE_RANGE = True
TITLE_X_OFFSET = 8


# MAP PADDING

MAP_PADDING = {
    "left": 0.5,
    "right": 0.5,
    "bottom": 1.0,
    "top": 0.5
}


# STATE LABELS

# Display state labels on the map
SHOW_STATE_LABELS = True


# GRID

SHOW_GRID = True
GRID_INTERVAL = 5
GRID_LABEL_SIZE = 9



# NORTH ARROW

SHOW_NORTH_ARROW = True
NORTH_ARROW_POSITION = (0.05, 0.92)


# SCALE BAR

SHOW_SCALE_BAR = True
SCALE_BAR_BASE_LAT = 5.5
SCALE_BAR_CENTER_LON = 82
SCALE_BAR_MARKS = [0, 130, 260, 520, 780, 1040]



# SOURCE

SHOW_SOURCE = True
SOURCE_TEXT = "Source: MODIS"
SOURCE_POSITION = (97.6, -0.2)   # (x, y offset from scale bar)


# LEGEND

SHOW_LEGEND = True
LEGEND_TITLE = "Legend"
LEGEND_POSITION = (0.435, 0.12)
LEGEND_TITLE_POSITION = (0.44, 0.29)



#  STATE MAP SETTINGS 

REGION_EXTENTS  = {
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

STATE_TITLE_POSITION = {
    "Uttar Pradesh":   (0.50, 0.965),
    "Andhra Pradesh":  (0.50, 0.965),
    "Karnataka":       (0.35, 0.965),
    "Odisha":          (0.50, 0.965),
    "Rajasthan":       (0.50, 0.965),
    "Madhya Pradesh":  (0.50, 0.965),
    "Chhattisgarh":    (0.50, 0.965),
    "Maharashtra":     (0.50, 0.965),
    "Haryana":         (0.35, 0.965),
    "Tamil Nadu":      (0.35, 0.965),
}


# STATE NORTH ARROW POSITION

STATE_NORTH_ARROW_POSITION = (0.96, 0.92)



# SCALE BAR MAX KM SEEN FOR STATE
STATE_SCALEBAR_MAXKM = {
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


# SCALE BAR STYLING

STATE_SCALEBAR_Y = 0.01
STATE_SCALEBAR_HEIGHT = 0.008
STATE_SCALEBAR_WIDTH = 0.28
STATE_SCALEBAR_LEFT = 0.30
STATE_SCALEBAR_UNIT = "Km"



# SOURCE

MAP_SOURCE = "MODIS"
STATE_SOURCE_POSITION = (0.99, 0.01)


# LEGEND POSITIONS

STATE_LEGEND_POSITION = {
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
