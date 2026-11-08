# GridPulse — Research Methodology & Analytical Design

## 1. Research Questions

**Primary Research Objective:**
> *Can historical outage behaviour, weather-warning characteristics, temporal patterns, and geographic context help explain outage severity and identify regions with recurring power-reliability problems?*

To answer this question rigorously without overclaiming or introducing statistical leakage, GridPulse decomposes the investigation into four testable sub-questions:

1. **Data Coverage & Telemetry Bias (RQ1):** How does sub-hourly 15-minute source telemetry availability vary across space and time, and how sensitive are inferred outage severity metrics to incomplete telemetry?
2. **Weather-Warning Severity Stratification (RQ2):** How do outage episode duration (`evDur_Hr`), peak customer impact (`Max_outage`), and baseline-normalized severity (`Max_outage / median_sum`) differ across the 18 matched NWS VTEC weather phenomenon regimes and single-vs-multi-hazard overlaps?
3. **Regional Reliability & Vulnerability Profiling (RQ3):** How can U.S. counties be profiled across recurrence (`events_per_observed_year`), normalized severity, and tail escalation risk while accounting for baseline differences (`median_sum`) and telemetry coverage (`mean_event_completeness_pct`)?
4. **Onset-Time Escalation Forecasting (RQ4):** Given only the information observable at **Hour 1** of a newly initiated outage episode and the county's strictly prior episode history, how accurately can we predict whether the episode will escalate to a **High-Severity Outage (`Max_outage >= 100` customers)** on an untouched future year (`2022`)?

---

## 2. Observational Units & Why Episode Aggregation Is Mandatory

A critical finding of our initial data inspection is that `Eagle_I_US_2024_with_VTEC_Updated.csv` (`3,572,394` rows) contains **repeated hourly measurements** of contiguous outage episodes identified by `(fips_code, new_event_no)` (`1,374,112` distinct episodes).

- Specifically, `evDur_Hr`, `evDur_day`, `Max_outage`, `event_mean_completeness_pct`, and `event_min_completeness_pct` are **episode-level invariants** that take the exact same value on every hourly row belonging to `(fips_code, new_event_no)`.
- **Methodological Consequence:** Analyzing `Max_outage` or training a classifier directly on the `3,572,394` hourly rows would commit severe **pseudoreplication** (weighting a 20-hour outage episode 20 times more heavily than a 1-hour episode) and **target/feature leakage** (if Hour 2 and Hour 5 of the same episode are split across train and test or used to predict their shared `Max_outage`).
- **GridPulse Solution:** We explicitly separate three observational units:
  1. **Hourly Warning-Matched Unit `(fips_code, Hour)` ($N = 3,572,394$):** Used for diurnal (`hour_of_day`), day-of-week, and hourly rolling-average (`max_rolling_avg`) analyses.
  2. **County-Outage Episode Unit `(fips_code, new_event_no)` ($N = 1,374,112$):** Used for episode duration, peak outage severity (`Max_outage`), weather-warning association tests, and onset-time predictive modeling.
  3. **County Profile Unit `fips_code` ($N = 3,010$) & State Profile Unit `state` ($N = 49$):** Used for multi-year regional reliability profiling and vulnerability clustering.

---

## 3. Normalization & Denominator Discipline

Ranking counties or states by raw outage counts or raw customer-hours alone is scientifically invalid when population, customer base, weather exposure, and reporting completeness vary.

- Because external utility customer-served denominators (e.g., EIA Form 861 total customers per county) are not bundled in the raw files, GridPulse uses the dataset's built-in county baseline invariant **`median_sum`** (`county_baseline_median_sum`) to compute the **Normalized Peak Severity Ratio**:
  $$\text{Normalized Peak Severity Ratio}_{c, e} = \frac{\text{Max\_outage}_{c, e}}{\text{median\_sum}_{c}}$$
- Every regional profile table and dashboard visualization displays:
  1. **Raw burden metrics** (`total_outage_events`, `median_max_outage`, `p90_max_outage`),
  2. **Normalized severity metrics** (`median_normalized_severity_ratio`, `high_severity_event_share_pct`), and
  3. **Coverage context** (`mean_event_completeness_pct`, `coverage_confidence_tier`).

---

## 4. Weather-Warning Linkage & Robustness Testing

- **Spatial and Temporal Matching:** In `Eagle_I_US_2024_with_VTEC_Updated.csv`, each county-hour `(fips_code, Hour)` was pre-linked to active NWS VTEC warnings (`Matched_Events`, `Matched_Count`) issued by the county's primary Weather Forecast Office (`WFO`).
- **Statistical Testing:** Because outage distributions are heavily right-skewed (`skewness > 50`), we use non-parametric **medians**, **90th percentiles (`p90`)**, **tail probabilities (`P(Max_outage >= 100)`)**, and the **Kruskal-Wallis $H$-test** across weather phenomena.
- **Missing-Data Sensitivity Check:** To verify that weather-warning severity rankings are not artifacts of differential telemetry dropouts during severe storms, we recompute phenomenon escalation rates on the subset of episodes with **$\ge 75\%$ mean telemetry completeness** (`high_comp_prob_ge100_pct`) and measure rank consistency via **Spearman's $\rho$** ($\rho = 0.9840, p < 0.0001$).

---

## 5. Predictive Modeling Design & Leakage Prevention

### 5.1 Task Formulation
- **Observational Unit:** County-Outage Episode `(fips_code, new_event_no)`.
- **Prediction Horizon / Decision Point:** End of **Hour 1** of the outage episode (onset).
- **Target Variable (`target_high_severity_100`):** Binary indicator equal to `1` if the episode's eventual peak outage reaches $\ge 100$ customers (`Max_outage >= 100.0`), and `0` otherwise (`12.89%` positive base rate across all `1,374,112` episodes).

### 5.2 Strict Feature Eligibility & Causal Lag Construction
- **Onset Features:** `initial_outage_hr1` (customers out in Hour 1), `county_baseline_median_sum`, `initial_to_baseline_ratio`, `initial_completeness_pct`, `initial_matched_count`, `initial_is_multi_hazard`, `primary_phenom`, `season`, `sin_onset_hour`, `cos_onset_hour`, `sin_month`, `cos_month`.
- **Causal Historical County Features (`shift(1)` over prior episodes $k < i$ in county $c$):**
  - `county_prior_event_count`
  - `prior_1_max_outage`
  - `prior_5_mean_max_outage`
  - `prior_5_mean_duration_hr`
  - `prior_10_high_sev_rate`
  - `hours_since_prior_event`
- **Automated Leakage Guard (`verify_no_leakage`):** Explicitly blocks post-onset variables (`Max_outage`, `evDur_Hr`, `evDur_day`, `observed_matched_hours`, `event_mean_completeness_pct`, `event_min_completeness_pct`, `max_matched_count`, `event_end_utc`) and verifies chronological ordering across splits.

### 5.3 Chronological Validation Protocol
- **Training Period (`2015–2020`):** `968,968` episodes (`12.80%` positive). Used to fit scalers, encoders, Empirical Bayes priors, and model parameters.
- **Validation Period (`2021`):** `190,562` episodes (`13.24%` positive). Used to select optimal F1 decision thresholds and compare model families.
- **Untouched Final Test Period (`2022`):** `214,185` episodes (`12.82%` positive). Evaluated once at the end of the pipeline for final reporting, calibration diagnostics, and subgroup error analysis.
