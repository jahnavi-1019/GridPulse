# GridPulse — Final Research Results & Empirical Findings Report

> **Generated automatically from actual pipeline execution outputs.**

## 1. Research Objective & Empirical Scope

**Research Question:** *Can historical outage behaviour, weather-warning characteristics, temporal patterns, and geographic context help explain outage severity and identify regions with recurring power-reliability problems?*

- **Harmonized Outage-Warning Records Analyzed:** `3,572,394` county-hour observations across `3,010` U.S. counties (`49` states + DC, `115` NWS Weather Forecast Offices).
- **Distinct County-Outage Episodes (`(fips_code, new_event_no)`):** `1,374,112` episodes spanning `2015-01-02T03:00:00Z` to `2023-01-03T01:00:00Z`.
- **NWS VTEC Warning Records Audited:** `4,152,437` warning action records across `125` WFOs and `59` phenomenon codes.
- **Source Availability Audit:** `1,048,575` county-day records (`288` counties, truncated at Excel row limit $2^{20}-1 = 1,048,575$).

---

## 2. Measured Findings (Backed by Pipeline Outputs)

### A. Data Coverage & Telemetry Missingness Sensitivity
1. **Absence of Record $\neq$ Confirmed Zero Outage:** In `EAGLEI_Source_Record_Availability.csv`, `38.91%` (`408,021` county-days) have `0` observed 15-minute telemetry records (100% reporting gap), while only `4.93%` have complete 96/96 daily intervals.
2. **Quantified Under-Reporting Bias:** From `Missing_Data_Sensitivity_Summary.csv`, county-hours with `< 50%` telemetry completeness exhibit a **75.0% median relative difference** (`2.25` customers median absolute difference) compared to complete telemetry, whereas `75%–99%` completeness exhibits an **18.75% median relative difference**.
3. **In-Sample Completeness Distribution:** Among the 3,572,394 harmonized outage-warning county-hours, mean hourly completeness is **62.01%** (median **62.5%**), with **30.52%** (`1,090,322` county-hours) achieving 100% telemetry completeness.

### B. Weather-Warning Associations (Observational, Non-Causal)
1. **Significant Heterogeneity Across Warning Types:** A non-parametric Kruskal-Wallis test across the top 10 VTEC warning phenomena yields $H = 28328.59$ ($p < 0.0001$), confirming strong distributional differences in peak outage severity across weather regimes.
2. **Severe Convective & Cyclonic Regimes Drive Tail Risk:**
   - **Extreme Wind (`EW`):** 74.03% of episodes reach $\ge 100$ customers out (median peak `3,355.4` customers, mean duration `176.4` hours).
   - **Tornado (`TO`):** 19.35% of episodes reach $\ge 100$ customers out (mean peak `559.1` customers, mean duration `9.80` hours).
   - **Severe Thunderstorm (`SV`):** Accounts for `735,490` episodes (53.5% of all warning-matched episodes), with 16.27% reaching $\ge 100$ customers out (mean peak `171.5` customers).
   - **Ice Storm (`IS`) & Wind Advisory (`WI`):** 16.20% and 14.59% of episodes reach $\ge 100$ customers out, respectively.
   - **Heat Advisory (`HT`) & Fire Weather (`FW`):** Lower tail escalation probabilities (6.13% and 5.56% reaching $\ge 100$ customers, respectively).
3. **Robustness to Telemetry Completeness:** Restricting the analysis strictly to high-coverage episodes (`event_mean_completeness_pct >= 75%`) preserves the phenomenon severity ranking with Spearman rank correlation $\rho = 0.984$ ($p < 0.0001$).

### C. Regional Reliability Profiling
- **Four Interpretable County Archetypes Identified:** Using standardized K-Means clustering ($k=4$) over annual episode frequency, baseline-normalized severity ratio (`Max_outage / median_sum`), high-severity share, duration, and telemetry completeness, all 3,010 counties are profiled alongside their explicit coverage tier.
- **Why Raw Counts Alone Are Misleading:** States like Texas (`432,851` county-hours) and Georgia (`270,468` county-hours) lead in raw records due to large county counts (252 and 159 counties) and frequent convective warnings, whereas normalizing peak outage by each county's historical baseline (`median_sum`) highlights localized vulnerability in coastal, mountain, and rural grid corridors.

### D. Onset-Time Predictive Modeling Results (Untouched 2022 Test Set: 214,185 Episodes)
 predicting whether a newly initiated outage episode (`Hour 1`) will escalate to a **High-Severity Outage (`Max_outage >= 100` customers)** using strictly onset-available and prior-episode causal features:

| Model | Validation (2021) ROC-AUC | Test (2022) ROC-AUC | Test (2022) PR-AUC | Test (2022) F1-Score | Test (2022) Brier Score |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Baseline 1: Onset Persistence Heuristic** | 0.7767 | 0.7803 | 0.5989 | 0.5433 | 0.0774 |
| **Baseline 2: County x Weather Empirical Bayes Prior** | 0.7170 | 0.7165 | 0.3397 | 0.3472 | 0.1000 |
| **Model 1: L2 Logistic Regression (Balanced)** | 0.8290 | 0.8378 | 0.6322 | 0.5633 | 0.1517 |
| **Model 2: HistGradientBoosting Classifier (Calibrated)** | 0.8577 | **0.8640** | **0.6713** | **0.5934** | **0.0664** |

---

## 3. Hypotheses & Directions for Future Work (Separated from Measured Evidence)

1. **Integration of Total Utility Customer Denominators (EIA-861 / Census Housing Units):** Incorporating external county customer-served counts would permit formal IEEE 1366 SAIDI, SAIFI, and CAIDI reliability indices across all counties.
2. **Polygon-Level Spatial Intersection:** Matching 15-minute utility service-area polygons directly with NWS polygon warning boundaries (`GTYPE='P'`) rather than county-level WFO/FIPS zones could reduce spatial attribution noise in large western counties.
3. **Physical Grid Topology & Vegetation Covariates:** Adding overhead-vs-underground distribution line ratios and tree-canopy density could help explain why counties facing identical wind speeds experience divergent outage durations.
