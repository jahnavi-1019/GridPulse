# GridPulse — Data Dictionary (Observed Schemas & Derived Variables)

> **Grounded strictly in the actual observed schemas of the four raw CSV datasets and derived Parquet tables.**

---

## 1. Raw Source File 1: `Eagle_I_US_2024_with_VTEC_Updated.csv`
- **File Size:** `366,933,304` bytes (`349.93 MB`)
- **Row Count:** `3,572,394` data rows (`0` nulls, `0` duplicate rows)
- **Observational Unit:** County-Hour (`(fips_code, Hour)`) where a non-zero power outage coincided with $\ge 1$ active NWS VTEC weather warning.
- **Temporal Range:** `2015-01-02T03:00:00Z` to `2023-01-03T01:00:00Z`

| Column Name | Observed Type | Min / Max (or Distinct Count) | Exact Empirical Definition & Semantics |
| :--- | :--- | :--- | :--- |
| `fips_code` | `Int64` | `1001` to `56045` (`3,010` unique) | 5-digit U.S. County FIPS identifier (leading zero omitted for states 01–09). |
| `Hour` | `String` | `55,673` unique ISO-8601 UTC | Hourly timestamp formatted as `YYYY-MM-DDTHH:00:00Z`. |
| `max_rolling_avg` | `Float64` | `0.0625` to `840,141.875` (Median: `4.375`) | Hourly rolling average of customers without power in the county during that hour (multiples of $1/16 = 0.0625$). |
| `state` | `String` | `49` unique states (incl. DC) | Full U.S. state name (or District of Columbia). |
| `county` | `String` | `1,760` unique names | County name corresponding to `fips_code`. |
| `median_sum` | `Float64` | `0.3125` to `2,199.0625` (Median: `8.875`) | **County-level static baseline invariant** (`1` unique value per `fips_code` across all years), representing typical baseline outage burden in that county. |
| `new_event_no` | `Int64` | `2` to `3,195,884` (`923,178` unique; `1,374,112` unique `(fips_code, new_event_no)`) | Contiguous outage episode identifier within a county. **Must be combined with `fips_code` to uniquely identify an episode (`1,374,112` episodes).** |
| `evDur_Hr` | `Int64` | `1` to `3,133` hours (Median: `7.0` hourly, `4.0` episode) | **Episode-level invariant:** Total duration in hours of the contiguous outage episode `(fips_code, new_event_no)`. |
| `evDur_day` | `Int64` | `0` to `131` days | **Episode-level invariant:** Duration of the outage episode expressed in days. |
| `Max_outage` | `Float64` | `0.0625` to `934,675.0` (Median: `11.125` hourly, `3.1875` episode) | **Episode-level invariant:** Peak affected customer count reached across the entire outage episode `(fips_code, new_event_no)`. |
| `source_completeness_pct` | `Float64` | `6.25%` to `100.0%` in steps of `6.25%` (Mean: `62.01%`) | Hourly source telemetry completeness across the 16 sub-intervals of the 4-hour rolling window ($1/16 = 6.25\%$). |
| `event_mean_completeness_pct` | `Float64` | `6.25%` to `100.0%` (Mean: `63.84%`) | **Episode-level invariant:** Mean telemetry completeness percentage across all hours of the outage episode. |
| `event_min_completeness_pct` | `Float64` | `6.25%` to `100.0%` (Mean: `34.02%`) | **Episode-level invariant:** Minimum hourly telemetry completeness percentage observed during the outage episode. |
| `WFO` | `String` | `115` unique 3-letter codes | Primary NWS Weather Forecast Office serving the county (`1` unique WFO per `fips_code`). |
| `Matched_Events` | `String` | `153` unique combinations (`18` base VTEC codes) | Semicolon-delimited (`"; "`) sorted string of active NWS VTEC phenomenon codes overlapping that county-hour (e.g., `"SV"`, `"HZ; WC; WI"`). |
| `Matched_Count` | `Int64` | `1` to `5` (Mean: `1.146`) | Count of distinct active VTEC phenomenon codes in `Matched_Events` for that county-hour (`86.5%` have `1`; `13.5%` have $\ge 2$). |

---

## 2. Raw Source File 2: `EAGLEI_Source_Record_Availability.csv`
- **File Size:** `32,427,674` bytes (`30.93 MB`)
- **Row Count:** `1,048,575` data rows (`0` nulls; **truncated at Microsoft Excel `.xlsx` sheet limit of $2^{20}-1$ data rows**)
- **Observational Unit:** County-Day (`(fips_code, Date)`) for `288` counties (`fips_code` `1001` to `12033`, covering AL, AR, CA, CO, CT, DC, FL).
- **Temporal Range:** `1/1/2015` to `12/31/2024` (`3,653` days per full county).

| Column Name | Observed Type | Min / Max | Exact Empirical Definition & Semantics |
| :--- | :--- | :--- | :--- |
| `fips_code` | `Int64` | `1001` to `12033` (`288` unique) | 5-digit U.S. County FIPS identifier. |
| `Date` | `String` | `1/1/2015` to `12/31/2024` | Calendar date formatted as `M/D/YYYY`. |
| `expected_15min_records` | `Int64` | Constant `96` | Expected number of 15-minute utility telemetry polls per 24-hour day ($24 \times 4 = 96$). |
| `observed_15min_records` | `Int64` | `0` to `96` (Mean: `22.51`, Median: `8.0`) | Actual number of 15-minute records observed in EAGLE-I for that county-day (`38.91%` of rows have `0`). |
| `missing_15min_records` | `Int64` | `0` to `96` (Mean: `73.49`, Median: `88.0`) | Number of missing 15-minute intervals (`96 - observed_15min_records`). |
| `source_record_availability_pct` | `Float64` | `0.0%` to `100.0%` (Mean: `23.45%`, Median: `8.33%`) | Daily telemetry availability percentage (`observed_15min_records / 96 * 100`). |

---

## 3. Raw Source File 3: `Missing_Data_Sensitivity_Summary.csv`
- **File Size:** `232` bytes
- **Row Count:** `4` rows (`91,522,025` total benchmark observations)

| Column Name | Observed Type | Values | Exact Empirical Definition & Semantics |
| :--- | :--- | :--- | :--- |
| `completeness_tier` | `String` | `100% Complete`, `75% - 99% Complete`, `50% - 74% Complete`, `< 50% Complete` | Telemetry completeness stratum. |
| `Total_Observations` | `Int64` | `11,776,430` to `38,024,562` | Number of county-hour observations evaluated in each tier. |
| `Median_Abs_Difference` | `Float64` | `0.0`, `1.1339`, `2.0`, `2.25` | Median absolute error in customer outage count caused by missing 15-minute telemetry intervals. |
| `Median_Relative_Difference` | `Float64` | `0.0%`, `18.75%`, `43.75%`, `75.0%` | Median percentage error in outage magnitude caused by incomplete sub-hourly telemetry. |

---

## 4. Raw Source File 4: `NWS_WARNINGS_COMBINED_data_Updated.csv`
- **File Size:** `832,283,249` bytes (`793.73 MB`)
- **Row Count:** `4,152,437` rows (`24` columns, `2015–2024`)
- **Observational Unit:** Individual NWS VTEC warning issuance/update/continuation/cancellation action record.

| Column Name | Observed Type | Coverage / Nulls | Exact Empirical Definition & Semantics |
| :--- | :--- | :--- | :--- |
| `WFO` | `String` | `125` unique (`0` nulls) | Issuing NWS Weather Forecast Office code. |
| `ISSUED` / `EXPIRED` | `String` | Mixed `YYYY-MM-DD HH:MM` & `M/D/YYYY H:MM` | Timestamp when the warning action took effect / expired. |
| `INIT_ISS` / `INIT_EXP` | `String` | Mixed formats (`0` nulls) | Initial event issuance and initial expiration timestamps. |
| `PHENOM` | `String` | `59` unique VTEC codes (`0` nulls) | 2-letter NWS VTEC phenomenon code (e.g., `SV`, `TO`, `FF`, `FA`, `WI`, `WW`, `HT`). |
| `GTYPE` | `String` | `'C'` (`3,682,148`), `'P'` (`470,289`) | Geometry type: `'C'` = County/Forecast Zone UGC; `'P'` = Storm-based Polygon. |
| `SIG` | `String` | `'W'`, `'Y'`, `'A'`, `'S'`, `'O'` | VTEC significance: `'W'` (Warning), `'Y'` (Advisory), `'A'` (Watch), `'S'` (Statement). |
| `ETN` | `Int64` | `0` to `4,034` | Event Tracking Number (resets annually per WFO and `PHENOM`). |
| `STATUS` | `String` | `9` unique (`CAN`, `EXP`, `NEW`, `CON`, `EXT`, etc.) | VTEC action status code. |
| `NWS_UGC` | `String` | Populated for `GTYPE='C'`; empty/null for `GTYPE='P'` | Universal Geographic Code (e.g., `INC021` county or `ALZ014` forecast zone). |
| `AREA_KM2` | `Float64` | `0.43` to `380,356.09` $\text{km}^2$ | Geographic area of the warning polygon or zone in square kilometers. |
| `IS_EMERGENCY` | `Boolean` | `True` (`2,319`), `False` (`4,150,118`) | Indicates Tornado or Flash Flood Emergency headline. |
| `WINDTAG` / `HAILTAG` / `TORNADOTAG` / `DAMAGETAG` | `String` | Literal string `"None"` when absent | Severe convective IBW (Impact-Based Warning) tags (`WINDTAG` mph, `HAILTAG` inches). |

---

## 5. Derived Feature Tables (`data/features/`)
1. **`event_features.parquet` (`1,374,112` rows $\times$ `42` columns):** Episode-level (`(fips_code, new_event_no)`) dataset containing onset telemetry (`initial_outage_hr1`, `initial_completeness_pct`, `initial_matched_count`), county baseline normalization (`initial_to_baseline_ratio`, `normalized_peak_severity_ratio`), cyclical temporal encodings (`sin_onset_hour`, `cos_onset_hour`, `sin_month`, `cos_month`), strictly causal `shift(1)` historical county lag features (`prior_1_max_outage`, `prior_5_mean_max_outage`, `prior_5_mean_duration_hr`, `prior_10_high_sev_rate`, `hours_since_prior_event`), and target indicators (`target_high_severity_100`, `target_major_severity_500`).
2. **`county_reliability_profiles.parquet` (`3,010` rows $\times$ `31` columns):** County-level reliability profile including observed episode counts, `events_per_observed_year`, `median_max_outage`, `p90_max_outage`, `county_baseline_median_sum`, `median_normalized_severity_ratio`, `high_severity_event_share_pct`, `mean_event_completeness_pct`, `coverage_confidence_tier`, and K-Means `reliability_archetype`.
3. **`state_reliability_profiles.parquet` (`49` rows $\times$ `21` columns):** State-level aggregated profile with USPS codes (`state_abbr`), coordinates (`lat`, `lon`), `events_per_county`, severity shares, and mean telemetry completeness.
