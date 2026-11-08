# GridPulse Dataset Schema and Data Dictionary

This data dictionary documents the exact schema, physical/statistical definitions, temporal formats, geographic identifiers, coverage boundaries, and known limitations of the four actual input datasets located in the project root directory (`../` relative to `GridPulse_Part1_Team_Evaluation/`).

## 1. Overview of Available Datasets

| Filename | File Size (Bytes) | Row Count | Observational Unit | Temporal Coverage | Geographic Scope |
| :--- | ---: | ---: | :--- | :--- | :--- |
| `Eagle_I_US_2024_with_VTEC_Updated.csv` | 366,933,304 | 3,572,394 | County-Hour during a VTEC-matched outage event `(fips_code, Hour)` | `2015-01-02T03:00:00Z` to `2023-01-03T01:00:00Z` | 3,010 U.S. counties across 49 states/territories and 115 NWS WFOs |
| `EAGLEI_Source_Record_Availability.csv` | 32,427,674 | 1,048,575 | County-Day `(fips_code, Date)` | `1/1/2015` to `9/9/2024` (3,653 dates) | 288 U.S. counties (`fips_code` `1001` to `12033`; truncated at $2^{20}-1$ rows) |
| `NWS_WARNINGS_COMBINED_data_Updated.csv` | 832,283,249 | 4,152,437 | Individual NWS VTEC bulletin/warning segment | `2015-01-01` to `2024-09-09` (mixed timestamp formats) | 125 NWS Weather Forecast Offices (WFOs) |
| `Missing_Data_Sensitivity_Summary.csv` | 232 | 4 | Completeness tier summary across raw observations | 2015–2024 aggregate | National summary across 91,522,025 total observations |

---

## 2. Dataset 1: `Eagle_I_US_2024_with_VTEC_Updated.csv`

### 2.1 Description & Observational Unit
- **Primary Key / Analytical Grain:** `(fips_code, Hour)` — verified **0 exact duplicate rows** and **0 duplicate `(fips_code, Hour)` keys** across all 3,572,394 rows.
- **Inclusion Criterion:** Contains hourly county outage observations that belong to a contiguous county outage event (`new_event_no`) **and** co-occur with at least one active National Weather Service (NWS) VTEC hazard (`Matched_Count >= 1`).
- **Event Structure:** Across the dataset, there are **1,374,112 distinct `(fips_code, new_event_no)` outage events**. Event-level attributes (`evDur_Hr`, `evDur_day`, `Max_outage`, `event_mean_completeness_pct`, `event_min_completeness_pct`) are computed over the *entire* contiguous outage event (including event hours before/after the active weather warning window) and repeated on every hourly row belonging to that event.
  - **CRITICAL LEAKAGE WARNING:** Because `Max_outage`, `evDur_Hr`, `evDur_day`, `event_mean_completeness_pct`, and `event_min_completeness_pct` summarize the entire multi-hour event (`new_event_no`), they contain future information relative to individual hourly rows `(fips_code, Hour)` and tautological relationships with one another at the event level (`Max_outage` equals the maximum of `max_rolling_avg` across the event). Any hourly prediction model **must exclude** event-summary columns from its feature matrix if predicting hourly outage magnitude, or must aggregate to the **event level** `(fips_code, new_event_no)` and strictly isolate pre-event/concurrent features from post-event outcomes.

### 2.2 Column Schema and Empirical Profile

| Column Name | Spark Data Type | Null Count | Empirical Range / Distinct Values | Exact Meaning & Measurement Limitations |
| :--- | :--- | ---: | :--- | :--- |
| `fips_code` | `IntegerType` (`INT`) | 0 | `1001` to `56045` (3,010 unique counties) | 5-digit (or 4-digit when leading zero is omitted for states `01`–`09`) U.S. County FIPS identifier. Format as 5-character zero-padded string (`LPAD(CAST(fips_code AS STRING), 5, '0')`) when standardizing. |
| `Hour` | `StringType` -> `TimestampType` | 0 | `2015-01-02T03:00:00Z` to `2023-01-03T01:00:00Z` | ISO-8601 UTC hourly timestamp (`yyyy-MM-dd'T'HH:mm:ss'Z'`). Note: Despite `2024` in the filename, hourly VTEC-matched outage records span 2015–2022 plus 1,644 carryover hours on Jan 1–3, 2023. |
| `max_rolling_avg` | `DoubleType` (`DOUBLE`) | 0 | Min: `0.0625`, Median: `4.375`, Mean: `284.39`, P90: `231.375`, P95: `614.25`, Max: `840,141.875` | 4-hour rolling average of customer outages reported during the hour, quantized in increments of $\frac{1}{16} = 0.0625$ (sum of observed 15-minute customer outage counts in a 16-slot 4-hour window divided by 16). Subject to downward attenuation when `source_completeness_pct < 100`. |
| `state` | `StringType` (`STRING`) | 0 | 49 unique states/territories | U.S. state or territory name (e.g., `Alabama`, `Texas`, `California`). |
| `county` | `StringType` (`STRING`) | 0 | 1,760 unique county names | County name (note: county names repeat across states; always pair with `state` or use `fips_code` for uniqueness). |
| `median_sum` | `DoubleType` (`DOUBLE`) | 0 | Constant per `fips_code` (1 unique value per county) | County-level historical baseline outage metric (static per `fips_code`). Because it is constant per county across all years (2015–2023), use historical training-split county baselines when evaluating strict out-of-time generalization. |
| `new_event_no` | `IntegerType` (`INT`) | 0 | `1` to `2,812,860` (1,374,112 unique `(fips_code, new_event_no)` pairs) | Sequential identifier assigned to contiguous outage events within a county. Identifier only; never use as a numerical feature. |
| `evDur_Hr` | `IntegerType` (`INT`) | 0 | Min: `1`, Median: `7`, Mean: `18.35`, P90: `29`, Max: `3,133` | Total duration (in hours) of the full contiguous outage event `(fips_code, new_event_no)`. Event-level outcome; do not use as a feature to predict hourly `max_rolling_avg` (causes temporal look-ahead leakage). |
| `evDur_day` | `IntegerType` (`INT`) | 0 | `0` to `130` (`FLOOR(evDur_Hr / 24)` or calendar days) | Event duration expressed in days (`evDur_Hr` coarse equivalent). Event-level outcome; never use as a predictor for `evDur_Hr` or hourly outage size. |
| `Max_outage` | `DoubleType` (`DOUBLE`) | 0 | Min: `0.0625`, Median: `11.125`, Mean: `840.24`, P90: `809.8125`, Max: `934,675.0` | Peak `max_rolling_avg` recorded at any point during the entire outage event `(fips_code, new_event_no)`. Event-level peak severity; never use as a feature to predict `max_rolling_avg`. |
| `source_completeness_pct` | `DoubleType` (`DOUBLE`) | 0 | 16 discrete values: `6.25, 12.5, ..., 100.0` (Mean: `62.01%`) | Percentage of expected 15-minute telemetry intervals observed within the 16-interval (4-hour) rolling window ($\frac{k}{16} \times 100\%$ for $k \in \{1,\dots,16\}$). Exactly `1,091,082` rows (30.54%) have `100.0%` completeness. |
| `event_mean_completeness_pct` | `DoubleType` (`DOUBLE`) | 0 | `6.25` to `100.0` (Mean: `62.24%`) | Mean of `source_completeness_pct` across all hours of the entire outage event `(fips_code, new_event_no)`. |
| `event_min_completeness_pct` | `DoubleType` (`DOUBLE`) | 0 | `6.25` to `100.0` | Minimum `source_completeness_pct` observed across all hours of the outage event `(fips_code, new_event_no)`. |
| `WFO` | `StringType` (`STRING`) | 0 | 115 unique 3-letter codes (e.g., `BMX`, `FWD`, `HGX`) | National Weather Service Weather Forecast Office code responsible for the county. |
| `Matched_Events` | `StringType` (`STRING`) | 0 | Semicolon-delimited VTEC phenomenon codes (e.g., `SV`, `HT`, `WI`, `SV; TO`) | Active NWS VTEC weather phenomenon codes matched to that county and hour. Top values: `SV` (Severe Thunderstorm, 1,476,827 rows), `HT` (Heat, 409,974), `WI` (Wind, 344,684), `WW` (Winter Weather, 268,955), `SV; TO` (Severe Thunderstorm + Tornado, 200,934). |
| `Matched_Count` | `IntegerType` (`INT`) | 0 | `1` to `5` (Mean: `1.15`) | Number of distinct active NWS VTEC phenomenon types matched to the county-hour (matches the number of semicolon-separated tokens in `Matched_Events`). |

---

## 3. Dataset 2: `EAGLEI_Source_Record_Availability.csv`

### 3.1 Description & Observational Unit
- **Primary Key / Analytical Grain:** `(fips_code, Date)` — 0 duplicate keys across 1,048,575 rows.
- **Coverage & Truncation Limitation:** Contains daily 15-minute telemetry availability counts for **288 counties** (`fips_code` `1001` in Alabama through `12033` Escambia County, Florida) across 3,653 days (`1/1/2015` to `9/9/2024`).
- **CRITICAL LIMITATION:** The file has exactly **1,048,575 data rows** ($2^{20} - 1$, plus 1 header row = $1,048,576$ lines), which is the Microsoft Excel `.xlsx` worksheet row limit. Consequently, counties with `fips_code > 12033` (approx. 90% of U.S. counties) were truncated when this availability table was exported upstream. Any join between `Eagle_I_US_2024_with_VTEC_Updated.csv` and `EAGLEI_Source_Record_Availability.csv` must treat this file as a **subset availability audit** (`fips_code <= 12033`), whereas `source_completeness_pct` inside `Eagle_I_US_2024_with_VTEC_Updated.csv` is available for 100% of outage rows nationwide.

### 3.2 Column Schema

| Column Name | Spark Data Type | Null Count | Empirical Range | Meaning |
| :--- | :--- | ---: | :--- | :--- |
| `fips_code` | `IntegerType` | 0 | `1001` to `12033` (288 counties) | County FIPS code (Alabama through partial Florida). |
| `Date` | `StringType` (`M/d/yyyy`) | 0 | `1/1/2015` to `9/9/2024` (3,653 dates) | Calendar date formatted as non-zero-padded `M/d/yyyy`. Parse with `to_date(col("Date"), "M/d/yyyy")`. |
| `expected_15min_records` | `IntegerType` | 0 | Constant `96` | Expected 15-minute intervals per 24-hour day ($24 \times 4 = 96$). |
| `observed_15min_records` | `IntegerType` | 0 | `0` to `96` | Number of 15-minute telemetry snapshots actually received on that date. Note: `408,021` county-days (38.9%) have `0` observed records (`0%` availability), and only `51,702` county-days (4.93%) have `96` observed records (`100%` availability). **Zero observed records means missing telemetry or no reported snapshots, NOT necessarily zero physical outages.** |
| `missing_15min_records` | `IntegerType` | 0 | `0` to `96` | `expected_15min_records - observed_15min_records`. |
| `source_record_availability_pct` | `DoubleType` | 0 | `0.0` to `100.0` (Mean: `23.45%`) | `(observed_15min_records / 96.0) * 100`. |

---

## 4. Dataset 3: `NWS_WARNINGS_COMBINED_data_Updated.csv`

### 4.1 Description & Observational Unit
- **Observational Unit:** Individual National Weather Service (NWS) VTEC warning/watch/advisory bulletin record (4,152,437 rows across 125 WFOs).
- **Mixed Timestamp Format Limitation:** Timestamp columns (`ISSUED`, `EXPIRED`, `INIT_ISS`, `INIT_EXP`, `UPDATED`, `POLYBEGIN`, `POLYEND`) use **two distinct string formats**:
  1. ISO-like `yyyy-MM-dd HH:mm` for 2015–2022 records (3,217,551 rows, 77.49%)
  2. Slash-delimited `M/d/yyyy H:mm` for 2023–2024 records (934,886 rows, 22.51%)
  - Always parse in PySpark using `coalesce(to_timestamp(col, "yyyy-MM-dd HH:mm"), to_timestamp(col, "M/d/yyyy H:mm"))`.

### 4.2 Column Schema

| Column Name | Spark Data Type | Null / Sentinel Count | Empirical Range / Top Values | Meaning |
| :--- | :--- | ---: | :--- | :--- |
| `WFO` | `StringType` | 0 | 125 unique 3-letter codes | Issuing NWS Weather Forecast Office (3-letter code; matches `WFO` in outage dataset after stripping any leading `K` if present). |
| `ISSUED` | `StringType` | 0 | `2015-01-01` to `2024-09-09` | Bulletin issuance UTC timestamp (`yyyy-MM-dd HH:mm` or `M/d/yyyy H:mm`). |
| `EXPIRED` | `StringType` | 0 | `2015-01-01` to `2024-09-15` | Bulletin expiration UTC timestamp. |
| `INIT_ISS` | `StringType` | 0 | `2015-01-01` to `2024-09-09` | Initial event issuance timestamp. |
| `INIT_EXP` | `StringType` | 0 | `2015-01-01` to `2024-09-15` | Initial event expiration timestamp. |
| `PHENOM` | `StringType` | 0 | 59 unique 2-letter VTEC codes | VTEC Phenomenon code (`SV`=Severe Thunderstorm, `FA`=Areal Flood, `SC`=Small Craft, `FG`=Dense Fog, `WI`=Wind, `HT`=Heat, `WS`=Winter Storm, `TO`=Tornado, etc.). |
| `GTYPE` | `StringType` | 0 | `C` (3,682,148), `P` (470,289) | Geometry type: `C` = County/Zone UGC polygon, `P` = Storm-based warning polygon. |
| `SIG` | `StringType` | 0 | `W` (1.74M), `Y` (1.68M), `A` (681K), `S` (46.8K), `O` (43) | VTEC Significance: `W`=Warning, `Y`=Advisory, `A`=Watch, `S`=Statement, `O`=Outlook. |
| `ETN` | `IntegerType` | 0 | `1` to `9999` | Event Tracking Number (resets annually per WFO/PHENOM/SIG). |
| `STATUS` | `StringType` | 0 | `CAN`, `EXP`, `NEW`, `CON`, `UPG`, `EXT`, `EXA`, `EXB`, `COR` | VTEC Action Status code (`NEW`=New, `CON`=Continue, `EXT`=Extend time, `EXP`=Expired, `CAN`=Cancelled). |
| `NWS_UGC` | `StringType` | 100,752 nulls + 369,537 empty `""` | 6-character UGC code (e.g., `ALC001`, `TXZ100`) | Universal Geographic Code (empty/null on all `GTYPE == 'P'` storm-based polygon rows). |
| `AREA_KM2` | `DoubleType` | 0 | `0.43` to `380,356.09` (Median: `1,544.74`) | Geographic area of the warning polygon or zone in square kilometers. |
| `UPDATED` | `StringType` | 0 | Timestamp string | Last update timestamp of the bulletin segment. |
| `HVTEC_NWSLI` | `StringType` | 3,342,844 `"None"` | 5-char station ID or `"None"` | Hydrologic VTEC NWS Location Identifier (string literal `"None"` when not applicable). |
| `HVTEC_SEVERITY` | `StringType` | 3,342,844 `"None"` | `N`, `0`, `1`, `2`, `3`, `U`, `"None"` | Hydrologic flood severity code (`1`=Minor, `2`=Moderate, `3`=Major). |
| `HVTEC_CAUSE` | `StringType` | 3,342,844 `"None"` | `ER`, `SM`, `RS`, etc., or `"None"` | Hydrologic flood cause (`ER`=Excessive Rain, `SM`=Snowmelt). |
| `HVTEC_RECORD` | `StringType` | 3,342,844 `"None"` | `NO`, `NR`, `OO`, `UU`, `"None"` | Hydrologic record status. |
| `IS_EMERGENCY` | `BooleanType` | 0 | `False` / `True` | Whether the warning was declared a Tornado/Flash Flood Emergency. |
| `POLYBEGIN` / `POLYEND` | `StringType` | 834,134 nulls + `"None"` | Timestamp string or null/`"None"` | Polygon active begin/end timestamps (populated only for storm-based polygons `GTYPE == 'P'`). |
| `WINDTAG` / `HAILTAG` / `TORNADOTAG` / `DAMAGETAG` | `StringType` | >3.92M `"None"` | Numeric/text tag or string literal `"None"` | IBW (Impact-Based Warning) threat tags attached to severe convective warnings (`SV`, `TO`, `MA`). |

---

## 5. Dataset 4: `Missing_Data_Sensitivity_Summary.csv`

### 5.1 Description & Observational Unit
- **Observational Unit:** Completeness tier across 91,522,025 raw EAGLE-I rolling-window observations.
- **Analytical Meaning:** Quantifies the systematic attenuation bias introduced into `max_rolling_avg` when fewer than 16 fifteen-minute telemetry snapshots are observed inside a 4-hour rolling window:

| `completeness_tier` | `Total_Observations` | `Median_Abs_Difference` | `Median_Relative_Difference` (%) |
| :--- | ---: | ---: | ---: |
| `100% Complete` | 27,010,031 | 0.000000 | 0.00 |
| `75% - 99% Complete` | 11,776,430 | 1.133929 | 18.75 |
| `50% - 74% Complete` | 14,711,002 | 2.000000 | 43.75 |
| `< 50% Complete` | 38,024,562 | 2.250000 | 75.00 |
