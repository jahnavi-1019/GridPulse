"""Configuration and path management for GridPulse."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict


# Official NWS VTEC Phenomenon Code Dictionary (for the 18 codes in harmonized EAGLE-I + top NWS codes)
VTEC_PHENOM_LABELS: Dict[str, str] = {
    "SV": "Severe Thunderstorm (SV)",
    "HT": "Heat Advisory (HT)",
    "WI": "Wind Advisory (WI)",
    "WW": "Winter Weather Advisory (WW)",
    "TO": "Tornado Warning/Watch (TO)",
    "FW": "Fire Weather / Red Flag (FW)",
    "TR": "Tropical Storm (TR)",
    "EH": "Excessive Heat (EH)",
    "FZ": "Freeze Warning/Watch (FZ)",
    "WS": "Winter Storm (WS)",
    "WC": "Wind Chill (WC)",
    "HW": "High Wind (HW)",
    "HZ": "Hard Freeze (HZ)",
    "HU": "Hurricane (HU)",
    "IS": "Ice Storm (IS)",
    "ZR": "Freezing Rain (ZR)",
    "BZ": "Blizzard (BZ)",
    "EW": "Extreme Wind / Eyewall (EW)",
    "FA": "Areal Flood (FA)",
    "FL": "Flood (FL)",
    "FF": "Flash Flood (FF)",
    "MA": "Marine (MA)",
    "SC": "Small Craft Advisory (SC)",
}

# Approximate geographic centroids (lat, lon) and USPS 2-letter codes for all 49 US states + DC in the dataset
STATE_METADATA: Dict[str, Dict[str, object]] = {
    "Alabama": {"abbr": "AL", "lat": 32.806671, "lon": -86.791130},
    "Arizona": {"abbr": "AZ", "lat": 33.729759, "lon": -111.431221},
    "Arkansas": {"abbr": "AR", "lat": 34.969704, "lon": -92.373123},
    "California": {"abbr": "CA", "lat": 36.116203, "lon": -119.681564},
    "Colorado": {"abbr": "CO", "lat": 39.059811, "lon": -105.311104},
    "Connecticut": {"abbr": "CT", "lat": 41.597782, "lon": -72.755371},
    "Delaware": {"abbr": "DE", "lat": 39.318523, "lon": -75.507141},
    "District of Columbia": {"abbr": "DC", "lat": 38.897438, "lon": -77.026817},
    "Florida": {"abbr": "FL", "lat": 27.766279, "lon": -81.686783},
    "Georgia": {"abbr": "GA", "lat": 33.040619, "lon": -83.643074},
    "Idaho": {"abbr": "ID", "lat": 44.240459, "lon": -114.478828},
    "Illinois": {"abbr": "IL", "lat": 40.349457, "lon": -88.986137},
    "Indiana": {"abbr": "IN", "lat": 39.849426, "lon": -86.258278},
    "Iowa": {"abbr": "IA", "lat": 42.011539, "lon": -93.210526},
    "Kansas": {"abbr": "KS", "lat": 38.526600, "lon": -96.726486},
    "Kentucky": {"abbr": "KY", "lat": 37.668140, "lon": -84.670067},
    "Louisiana": {"abbr": "LA", "lat": 31.169546, "lon": -91.867805},
    "Maine": {"abbr": "ME", "lat": 44.693947, "lon": -69.381927},
    "Maryland": {"abbr": "MD", "lat": 39.063946, "lon": -76.802101},
    "Massachusetts": {"abbr": "MA", "lat": 42.230171, "lon": -71.530106},
    "Michigan": {"abbr": "MI", "lat": 43.326618, "lon": -84.536095},
    "Minnesota": {"abbr": "MN", "lat": 45.694454, "lon": -93.900192},
    "Mississippi": {"abbr": "MS", "lat": 32.741646, "lon": -89.678696},
    "Missouri": {"abbr": "MO", "lat": 38.456085, "lon": -92.288368},
    "Montana": {"abbr": "MT", "lat": 46.921925, "lon": -110.454353},
    "Nebraska": {"abbr": "NE", "lat": 41.125370, "lon": -98.268082},
    "Nevada": {"abbr": "NV", "lat": 38.313515, "lon": -117.055374},
    "New Hampshire": {"abbr": "NH", "lat": 43.452492, "lon": -71.563896},
    "New Jersey": {"abbr": "NJ", "lat": 40.298904, "lon": -74.521011},
    "New Mexico": {"abbr": "NM", "lat": 34.840515, "lon": -106.248482},
    "New York": {"abbr": "NY", "lat": 42.165726, "lon": -74.948051},
    "North Carolina": {"abbr": "NC", "lat": 35.630066, "lon": -79.806419},
    "North Dakota": {"abbr": "ND", "lat": 47.528912, "lon": -99.784012},
    "Ohio": {"abbr": "OH", "lat": 40.388783, "lon": -82.764915},
    "Oklahoma": {"abbr": "OK", "lat": 35.565342, "lon": -96.928917},
    "Oregon": {"abbr": "OR", "lat": 44.572021, "lon": -122.070938},
    "Pennsylvania": {"abbr": "PA", "lat": 40.590752, "lon": -77.209755},
    "Rhode Island": {"abbr": "RI", "lat": 41.680893, "lon": -71.511780},
    "South Carolina": {"abbr": "SC", "lat": 33.856892, "lon": -80.945007},
    "South Dakota": {"abbr": "SD", "lat": 44.299782, "lon": -99.438828},
    "Tennessee": {"abbr": "TN", "lat": 35.747845, "lon": -86.692345},
    "Texas": {"abbr": "TX", "lat": 31.054487, "lon": -97.563461},
    "Utah": {"abbr": "UT", "lat": 40.150032, "lon": -111.862434},
    "Vermont": {"abbr": "VT", "lat": 44.045876, "lon": -72.710686},
    "Virginia": {"abbr": "VA", "lat": 37.769337, "lon": -78.169968},
    "Washington": {"abbr": "WA", "lat": 47.400902, "lon": -121.490494},
    "West Virginia": {"abbr": "WV", "lat": 38.491226, "lon": -80.954453},
    "Wisconsin": {"abbr": "WI", "lat": 44.268543, "lon": -89.616508},
    "Wyoming": {"abbr": "WY", "lat": 42.755966, "lon": -107.302490},
}


@dataclass
class GridPulseConfig:
    """Centralized, configurable paths and parameters for the GridPulse pipeline."""

    project_root: Path = field(
        default_factory=lambda: Path(
            os.environ.get("GRIDPULSE_ROOT", Path(__file__).resolve().parents[2])
        )
    )

    # Raw dataset filenames (located in project_root or data/raw)
    eagle_vtec_filename: str = "Eagle_I_US_2024_with_VTEC_Updated.csv"
    nws_warnings_filename: str = "NWS_WARNINGS_COMBINED_data_Updated.csv"
    availability_filename: str = "EAGLEI_Source_Record_Availability.csv"
    sensitivity_filename: str = "Missing_Data_Sensitivity_Summary.csv"

    # Spark settings
    spark_master: str = field(
        default_factory=lambda: os.environ.get("GRIDPULSE_SPARK_MASTER", "local[*]")
    )
    spark_driver_memory: str = field(
        default_factory=lambda: os.environ.get("GRIDPULSE_SPARK_MEMORY", "4g")
    )

    # Modeling temporal split boundaries (strictly chronological to prevent future leakage)
    train_end_year: int = 2020
    val_year: int = 2021
    test_year: int = 2022

    # High-severity target threshold (Max_outage >= 100 affected customers)
    high_severity_threshold: float = 100.0
    major_severity_threshold: float = 500.0

    def resolve_raw_file(self, filename: str) -> Path:
        """Locate a raw file in data/raw first, then project_root without moving original files."""
        env_override = os.environ.get(f"GRIDPULSE_FILE_{filename.split('.')[0].upper()}")
        if env_override and Path(env_override).exists():
            return Path(env_override)
        in_raw = self.project_root / "data" / "raw" / filename
        if in_raw.exists():
            return in_raw
        in_root = self.project_root / filename
        if in_root.exists():
            return in_root
        raise FileNotFoundError(
            f"Required source file '{filename}' not found in '{in_raw}' or '{in_root}'. "
            "Configure GRIDPULSE_ROOT or place the dataset in the workspace root."
        )

    @property
    def eagle_vtec_path(self) -> Path:
        return self.resolve_raw_file(self.eagle_vtec_filename)

    @property
    def nws_warnings_path(self) -> Path:
        return self.resolve_raw_file(self.nws_warnings_filename)

    @property
    def availability_path(self) -> Path:
        return self.resolve_raw_file(self.availability_filename)

    @property
    def sensitivity_path(self) -> Path:
        return self.resolve_raw_file(self.sensitivity_filename)

    @property
    def processed_dir(self) -> Path:
        p = self.project_root / "data" / "processed"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def features_dir(self) -> Path:
        p = self.project_root / "data" / "features"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def models_dir(self) -> Path:
        p = self.project_root / "models"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def metrics_dir(self) -> Path:
        p = self.project_root / "outputs" / "metrics"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def reports_dir(self) -> Path:
        p = self.project_root / "outputs" / "reports"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def figures_dir(self) -> Path:
        p = self.project_root / "outputs" / "figures"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def docs_dir(self) -> Path:
        p = self.project_root / "docs"
        p.mkdir(parents=True, exist_ok=True)
        return p
