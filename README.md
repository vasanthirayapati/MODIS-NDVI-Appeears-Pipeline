# MODIS NDVI AppEEARS Automation Pipeline

An automated Python pipeline for downloading MODIS NDVI data from NASA AppEEARS, processing the data, applying an agricultural mask, classifying NDVI values, and generating India-level and state-level NDVI maps.

# Overview

This project automates the workflow of retrieving MODIS NDVI data from NASA's AppEEARS API and generating map outputs for agricultural monitoring.

The pipeline:

- Authenticates with NASA AppEEARS
- Identifies MODIS 16-day composite windows within a specified date range
- Downloads available MODIS NDVI data automatically
- Saves each MODIS composite as a GeoTIFF
- Converts scaled MODIS NDVI values to the standard NDVI range
- Applies an agricultural mask
- Classifies NDVI into five vegetation-condition classes
- Generates an India-level NDVI map
- Generates state-level NDVI maps
- Adds administrative boundaries, district labels, legends, scale bars, north arrows, and source information
- Avoids re-downloading data that already exists locally

### Data Source

# MODIS NDVI

Product:

**MOD13Q1.061 – MODIS/Terra Vegetation Indices 16-Day L3 Global 250m SIN Grid**

NDVI layer:

`250m_16_days_NDVI`

Data are accessed programmatically through NASA AppEEARS.

# Workflow

```text
User-defined date range
        │
        ▼
Identify MODIS 16-day windows
        │
        ▼
Check whether composite already exists
        │
        ├── Yes ──► Use local GeoTIFF
        │
        └── No ───► Submit AppEEARS task
                         │
                         ▼
                   Wait for processing
                         │
                         ▼
                   Download NDVI
                         │
                         ▼
                   Save GeoTIFF
                         │
                         ▼
                  Apply agricultural mask
                         │
                         ▼
                  NDVI classification
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
        India-level map       State-level maps
