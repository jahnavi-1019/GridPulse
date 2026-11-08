# GridPulse — Limitations, Reporting Bias, Ethics & Limits of Inference

## 1. Reporting Bias & Telemetry Missingness

1. **Absence of Evidence $\neq$ Evidence of Zero Outages:**
   - EAGLE-I collects outage counts by scraping public utility outage web maps at 15-minute intervals (`96` expected polls per day). When a utility web server goes down during a severe storm or a scraper parser breaks, no record is logged.
   - Our audit of `EAGLEI_Source_Record_Availability.csv` (`1,048,575` county-days) reveals that **`38.91%` of county-days have `0` observed 15-minute records**, and the median daily availability across those 288 counties is only `8.33%` (`mean = 23.45%`).
   - Consequently, GridPulse never treats an unrecorded county-hour as a confirmed zero-outage interval unless source availability explicitly confirms 100% reporting coverage.

2. **Under-Estimation Bias Under Low Telemetry Completeness:**
   - `Missing_Data_Sensitivity_Summary.csv` demonstrates that when sub-hourly completeness falls below `50%`, observed outage metrics suffer a **`75.0%` median relative difference** (`2.25` customers median absolute difference) relative to complete telemetry.
   - Even in the `2022` test set, episodes with `100%` onset completeness exhibit a `24.60%` positive rate for `Max_outage >= 100` (`ROC-AUC = 0.8901`), whereas episodes with `< 50%` onset completeness exhibit only a `9.63%` positive rate (`ROC-AUC = 0.8357`), reflecting censoring of peak outage trajectories when telemetry is sparse.

3. **Microsoft Excel Row-Limit Truncation in Source Availability File:**
   - `EAGLEI_Source_Record_Availability.csv` terminates at row `1,048,575` (+1 header = $1,048,576 = 2^{20}$ rows), omitting counties with `fips_code > 12033`. Analyses across all `3,010` counties must therefore rely on the episode-level completeness columns (`source_completeness_pct`, `event_mean_completeness_pct`, `event_min_completeness_pct`) embedded inside `Eagle_I_US_2024_with_VTEC_Updated.csv`.

---

## 2. Selection Bias & Interpretation of Weather-Warning Associations

1. **Conditioning on Positive Outage + Active Warning Co-Occurrence:**
   - Every row in `Eagle_I_US_2024_with_VTEC_Updated.csv` (`3,572,394` county-hours) has both `max_rolling_avg > 0` and `Matched_Count >= 1`.
   - Therefore, this dataset **cannot** be used to estimate:
     - The probability that a weather warning causes an outage (since warnings that produced *zero* outages are not in the harmonized table), or
     - The baseline rate of equipment/wildlife/planned outages during clear-sky (non-warning) hours.
   - Instead, all weather findings represent **conditional severity distributions given that an outage and a warning co-occurred**.

2. **Association vs. Physical Causation:**
   - Temporal and spatial overlap between an NWS warning (`Matched_Events`) and a county power outage does not prove that the warning phenomenon physically damaged the grid. For example, during a `Heat Advisory (HT)`, outages may be triggered by air-conditioning load transformer trips or unrelated routine feeder faults.
   - Similarly, permutation feature importance (`initial_outage_hr1`, `primary_phenom`, `county_baseline_median_sum`) measures how much a feature improves out-of-sample predictive ranking—not causal effect if intervened upon.

---

## 3. Geographic Comparability & Ethical Considerations

1. **Population & Customer-Base Heterogeneity:**
   - A `100-customer` outage in Los Angeles County, California (millions of utility meters) represents a negligible fraction of customers served, whereas a `100-customer` outage in a rural frontier county may represent a substantial fraction of the local community.
   - Because total customer-served denominators are absent from the source files, ranking counties solely on raw customer counts (`Max_outage`) systematically biases attention toward populous urban centers.
   - GridPulse mitigates this by always presenting **baseline-normalized ratios (`Max_outage / median_sum`)** alongside raw counts and telemetry completeness tiers.

2. **Responsible Infrastructure & Equity Interpretation:**
   - Rural, tribal, and lower-income counties are often served by smaller municipal utilities or electric cooperatives whose outage web maps had lower scraping coverage in early years (`2015–2017`) of EAGLE-I.
   - Labelling a county as "highly reliable" when it actually has `< 50%` telemetry completeness ("Low Observed Burden or Sparse Telemetry") could misdirect grid-hardening investments away from under-monitored vulnerable communities. For this reason, GridPulse explicitly displays **`coverage_confidence_tier`** next to every regional reliability profile.
