# GridPulse — Initial Data Audit & Data Quality Report

> **All counts, ranges, and findings in this report are verified directly against the four raw files in the workspace (`outputs/metrics/data_audit_report.json`).**

---

## 1. Executive Summary of Source Files

| Dataset Filename | Size (MB) | Exact Row Count | Columns | Primary Granularity | Date Range Observed |
| :--- | :---: | :---: | :---: | :--- | :--- |
| `Eagle_I_US_2024_with_VTEC_Updated.csv` | `349.93 MB` | `3,572,394` | `16` | County-Hour `(fips_code, Hour)` | `2015-01-02T03:00:00Z` to `2023-01-03T01:00:00Z` |
| `NWS_WARNINGS_COMBINED_data_Updated.csv` | `793.73 MB` | `4,152,437` | `24` | VTEC Warning Action Record | `2015-01-01` to `2024-12-31` |
| `EAGLEI_Source_Record_Availability.csv` | `30.93 MB` | `1,048,575` | `6` | County-Day `(fips_code, Date)` | `2015-01-01` to `2024-12-31` |
| `Missing_Data_Sensitivity_Summary.csv` | `0.0002 MB` | `4` | `4` | Completeness Tier Summary | `2015–2024` Benchmark (`91.52M` obs) |

---

## 2. Detailed Audit of `Eagle_I_US_2024_with_VTEC_Updated.csv`

### 2.1 Schema, Completeness, and Integrity Checks
- **Null / Missing Values:** `0` across all 16 columns.
- **Duplicate Full Rows:** `0`.
- **Duplicate `(fips_code, Hour)` Keys:** `0`. Every row is a unique county-hour observation.
- **Invalid Timestamps:** `0` (`100%` conform to `YYYY-MM-DDTHH:00:00Z`).
- **Plausible Value Violations:** `0` negative outage values, `0` non-positive durations, `0` completeness percentages outside `[6.25%, 100.0%]`.

### 2.2 Critical Structural Findings (Observational Units & Invariants)
1. **Filtered Positive-Outage & Active-Warning Intersection:** Every single row has `max_rolling_avg >= 0.0625` and `Matched_Count >= 1`. That is, this file contains **only county-hours where a positive power outage overlapped with at least one active NWS weather warning** across `18` weather phenomenon codes (`SV`, `HT`, `WI`, `WW`, `TO`, `FW`, `TR`, `EH`, `FZ`, `WS`, `WC`, `HW`, `HZ`, `HU`, `IS`, `ZR`, `BZ`, `EW`).
2. **Repeated Measurements Within Outage Episodes (`new_event_no`):**
   - `new_event_no` has `923,178` unique integer values globally, but `new_event_no` IDs are reused across different counties. The true episode identifier is the composite key **`(fips_code, new_event_no)`**, which yields **`1,374,112` distinct county-outage episodes**.
   - Within each `(fips_code, new_event_no)` episode, the columns `evDur_Hr`, `evDur_day`, `Max_outage`, `event_mean_completeness_pct`, and `event_min_completeness_pct` are **episode-level constants** repeated on every hourly row of that episode.
   - In `43.81%` of episodes, `evDur_Hr` exceeds the number of rows present in the table for that episode because the outage persisted into hours before or after the weather warning was active (and non-warning hours were filtered out of this harmonized file).
3. **County-Level Static Invariants (`median_sum` and `WFO`):**
   - `median_sum` has **exactly 1 unique value per `fips_code`** across the entire dataset (`min = 0.3125`, `median = 8.875`, `max = 2,199.0625`), serving as a county-specific baseline outage denominator.
   - `WFO` has **exactly 1 unique value per `fips_code`**.
4. **Actual Temporal Coverage Despite Filename (`2015–2023`):**
   - Although the filename includes `2024`, actual records span `2015` through `2022-11-12T22:00:00Z`, plus a small 3-day window from `2023-01-01T00:00:00Z` to `2023-01-03T01:00:00Z` (`1,644` hourly rows / `397` episodes). There are no `2024` rows in `Eagle_I_US_2024_with_VTEC_Updated.csv`.

| Year (UTC) | Hourly Records | Unique Counties (`fips_code`) | Unique Episodes `(fips_code, new_event_no)` | Mean Hourly Completeness (%) |
| :---: | :---: | :---: | :---: | :---: |
| **2015** | 290,964 | 2,428 | 118,923 | 55.66% |
| **2016** | 305,078 | 2,340 | 122,621 | 58.65% |
| **2017** | 354,540 | 2,635 | 134,501 | 62.66% |
| **2018** | 470,789 | 2,733 | 188,389 | 64.96% |
| **2019** | 547,431 | 2,878 | 209,484 | 63.36% |
| **2020** | 517,024 | 2,974 | 195,050 | 61.36% |
| **2021** | 524,116 | 2,930 | 190,562 | 64.08% |
| **2022** | 560,808 | 2,956 | 214,185 | 61.60% |
| **2023** | 1,644 | 116 | 397 | 58.68% |

---

## 3. Audit of `EAGLEI_Source_Record_Availability.csv` & `Missing_Data_Sensitivity_Summary.csv`

1. **Microsoft Excel Row-Limit Truncation Discovery:**
   - `EAGLEI_Source_Record_Availability.csv` has **1,048,575 data rows** (+ 1 header row = **1,048,576 rows = $2^{20}$**, the exact row limit of an Excel `.xlsx` worksheet).
   - Because the file was sorted ascending by `fips_code`, it cuts off mid-way through `fips_code = 12033` (Escambia County, Florida), covering `288` counties across `7` state FIPS prefixes (`01` AL, `05` AR, `06` CA, `08` CO, `09` CT, `11` DC, `12` FL) from `2015-01-01` to `2024-12-31`.
2. **Prevalence of Reporting Gaps vs. Confirmed Coverage:**
   - Across those `1,048,575` county-days, **`408,021` county-days (`38.91%`) have `observed_15min_records == 0`** (a 100% telemetry reporting gap).
   - Only **`51,694` county-days (`4.93%`) have all `96` expected 15-minute intervals observed**.
   - This proves why **an absent outage record must never be treated as a confirmed zero-outage observation**.
3. **Sensitivity to Missing Sub-Hourly Telemetry:**
   - `Missing_Data_Sensitivity_Summary.csv` shows that when completeness drops below `50%`, the median relative difference in outage magnitude reaches **`75.0%`** (`2.25` customers median absolute difference), compared to `18.75%` in the `75%–99%` completeness tier and `0.0%` at `100%` completeness.

---

## 4. Audit of `NWS_WARNINGS_COMBINED_data_Updated.csv`

- **Row Count:** `4,152,437` warning action records across `125` WFOs and `59` VTEC phenomenon codes (`2015–2024`).
- **Mixed Timestamp Formats:** Contains both `YYYY-MM-DD HH:MM` (e.g., `2015-03-28 01:43`) and `M/D/YYYY H:MM` (e.g., `1/16/2024 18:00`) in `ISSUED`, `EXPIRED`, `INIT_ISS`, `INIT_EXP`, and `UPDATED`. GridPulse's preprocessing pipeline normalizes these formats safely.
- **Sentinel `"None"` Strings & Polygon UGC Nulls:**
  - `GTYPE = 'C'` (`3,682,148` rows) represents county/zone warnings where `NWS_UGC` is populated (including forecast zones `Z` and marine zones `PZ`/`AM`).
  - `GTYPE = 'P'` (`470,289` rows) represents storm-based polygon warnings where `NWS_UGC` is empty/null (`470,289` combined empty + null rows).
  - Impact tags (`WINDTAG`, `HAILTAG`, `TORNADOTAG`, `DAMAGETAG`) and `HVTEC_*` columns store literal `"None"` strings when not applicable (`>80%` of rows).
