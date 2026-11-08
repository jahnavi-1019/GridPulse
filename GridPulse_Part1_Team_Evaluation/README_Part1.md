# GridPulse Part 1 — Three-Team PySpark Algorithm Evaluation

**Course:** B.Tech 5th Semester - Big Data Analytics  
**Framework:** Apache Spark (PySpark 4.2.0 & Spark MLlib)

---

## 1. Directory Structure & Deliverables

```text
GridPulse_Part1_Team_Evaluation/
├── Regression.ipynb                     # Linear Regression vs. Random Forest Regressor
├── Classification.ipynb                 # Logistic Regression vs. Decision Tree Classifier
├── Unsupervised_Learning.ipynb          # K-Means Clustering vs. Principal Component Analysis (PCA)
├── README_Part1.md                            # Complete setup, execution, results, and troubleshooting guide
├── data_dictionary.md                         # Empirical schema, coverage, and limitation documentation
├── requirements.txt                           # Python & PySpark package dependencies
├── .gitignore                                 # Excludes raw CSVs and heavy Parquet/Spark scratch artifacts
└── outputs/                                   # Genuine executed metrics (CSV), figures (PNG), and Parquet tables
    ├── regression_eda_overview.png
    ├── regression_evaluation_diagnostics.png
    ├── regression_metrics_comparison.csv
    ├── regression_regime_error_breakdown.csv
    ├── regression_rf_feature_importances.csv
    ├── regression_processed_features.parquet
    ├── classification_eda_overview.png
    ├── classification_evaluation_diagnostics.png
    ├── classification_metrics_comparison.csv
    ├── classification_dt_feature_importances.csv
    ├── classification_processed_features.parquet
    ├── unsupervised_eda_county_correlations.png
    ├── unsupervised_evaluation_diagnostics.png
    ├── unsupervised_kmeans_k_selection_metrics.csv
    ├── unsupervised_kmeans_cluster_profiles_raw.csv
    ├── unsupervised_kmeans_cluster_centroids_zscore.csv
    ├── unsupervised_pca_explained_variance.csv
    ├── unsupervised_pca_loadings_top3.csv
    └── unsupervised_county_profiles.parquet
```

---

## 2. Actual Datasets Inspected and Used

All three notebooks read the four original datasets directly from the parent workspace directory (`../`) without moving, renaming, overwriting, or duplicating the raw files:

| Dataset Filename | Size | Rows | Primary Grain & Coverage | Key Analytical Role & Limitations |
| :--- | ---: | ---: | :--- | :--- |
| `Eagle_I_US_2024_with_VTEC_Updated.csv` | 366.9 MB | 3,572,394 | County-hour `(fips_code, Hour)` during active VTEC alerts (`2015-01-02` to `2023-01-03`; 3,010 counties; 1,374,112 events) | Core outage telemetry (`max_rolling_avg`, `median_sum`, `source_completeness_pct`, `Matched_Events`). Event-summary columns (`Max_outage`, `evDur_Hr`, `evDur_day`, `event_mean_completeness_pct`, `event_min_completeness_pct`) summarize full events and must be isolated to prevent look-ahead leakage. |
| `NWS_WARNINGS_COMBINED_data_Updated.csv` | 832.3 MB | 4,152,437 | Individual NWS VTEC bulletin segment (`2015`–`2024`; 125 WFOs) | Provides WFO-level spatial warning area (`AREA_KM2`), significance (`SIG`), and polygon share (`GTYPE`). Uses mixed timestamp formats (`yyyy-MM-dd HH:mm` for 2015–2022; `M/d/yyyy H:mm` for 2023–2024). |
| `EAGLEI_Source_Record_Availability.csv` | 32.4 MB | 1,048,575 | County-day `(fips_code, Date)` (`1/1/2015` to `9/9/2024`; 288 counties) | Daily 15-minute telemetry availability (`expected_15min_records = 96`). Truncated upstream at $2^{20}-1$ rows (`fips_code <= 12033`). Zero observed records (`38.9%` of county-days) indicate missing telemetry, **not** zero outages. |
| `Missing_Data_Sensitivity_Summary.csv` | 232 B | 4 | National completeness tiers across 91.52M observations | Quantifies downward relative bias in `max_rolling_avg` when `source_completeness_pct < 100%` (`0%` bias at `100% Complete` vs. `18.75%`, `43.75%`, and `75.0%` downward bias in lower tiers). |

See [`data_dictionary.md`](./data_dictionary.md) for the complete column-by-column schema and empirical statistics.

---

## 3. Environment & Spark Compatibility

| Component | Verified Version | Compatibility Notes |
| :--- | :--- | :--- |
| **Operating System** | Windows 10/11 64-bit (also Linux/macOS compatible) | Tested on Windows AMD64 |
| **Python** | `3.12.10` (`>= 3.10` supported) | `PYSPARK_PYTHON` and `PYSPARK_DRIVER_PYTHON` are automatically bound to `sys.executable` inside each notebook |
| **Java (JDK)** | `Java 17.0.12 LTS` (`JAVA_HOME = C:\Program Files\Java\jdk-17`) | Spark 4.x requires Java 17 or Java 21 |
| **Apache Spark / PySpark** | `4.2.0` | Configured with `spark.sql.ansi.enabled=false` and `spark.driver.memory=6g` |
| **PyArrow** | `26.0.0` | Used for columnar memory transfers and Windows Hadoop-less (`winutils.exe`-free) Parquet persistence fallback |

### Setup Instructions

```powershell
# 1. Verify Python and Java 17+
python --version
java -version

# 2. Install required dependencies
pip install -r GridPulse_Part1_Team_Evaluation/requirements.txt
```

### Configuring Data Paths
By default, each notebook automatically searches for the four raw CSV files in:
1. The directory specified by the environment variable `GRIDPULSE_DATA_DIR` (if set),
2. The parent workspace directory (`..`), and
3. The current working directory (`.`).

To override the dataset location explicitly:
```powershell
$env:GRIDPULSE_DATA_DIR = "C:\path\to\folder\containing\csvs"
```

---

## 4. Execution Order and Exact Commands

Each notebook is **100% independent** and can be executed in **any order** (or in parallel on separate machines). None of the notebooks depend on another team's notebook having been run first.

### Option A: Headless CLI Execution via `jupyter nbconvert` (Recommended for Reproducibility)

Run from the project root directory (`c:\Users\jsm10\OneDrive\Desktop\bda_project`):

```powershell
# Execute Regression
python -m jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=1200 "GridPulse_Part1_Team_Evaluation/Regression.ipynb"

# Execute Classification
python -m jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=1200 "GridPulse_Part1_Team_Evaluation/Classification.ipynb"

# Execute Unsupervised Learning
python -m jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=1200 "GridPulse_Part1_Team_Evaluation/Unsupervised_Learning.ipynb"
```

### Option B: Interactive Execution in JupyterLab / Jupyter Notebook / VS Code
```powershell
cd GridPulse_Part1_Team_Evaluation
python -m jupyter notebook
```
Open any of the three `.ipynb` files and select **Kernel -> Restart & Run All**.

---

## 5. Summary of Implemented Algorithms & Measured Results

### 5.1 Regression (`Regression.ipynb`)
- **Observational Unit:** Verified $100\%$-complete active continuation county-hours `(fips_code, Hour)` ($h \ge 1$, $N = 843,512$ county-hours; chronologically split into **Train [2015–2020]: 560,572**, **Validation [2021]: 146,995**, and **Test [2022–2023]: 135,945**).
- **Continuous Target:** $y_{i,t} = \log(1 + \text{max\_rolling\_avg}_{i,t})$.
- **Leakage Controls:** Event-outcome columns (`Max_outage`, `evDur_Hr`, `evDur_day`, `event_mean_completeness_pct`, `event_min_completeness_pct`) are strictly dropped. Predictors use only causal preceding-hour states ($t-1$ and $t-2$), event onset state ($t_0 < t$), historical training baselines (`2015–2020`), and concurrent weather hazard features.

| Model | Evaluation Split | MAE | RMSE | $R^2$ |
| :--- | :--- | ---: | ---: | ---: |
| **Linear Regression** (`regParam=0.0001, elasticNet=0.0`) | Train (2015–2020) | 0.3311 | 0.5762 | 0.9283 |
| **Linear Regression** | Validation (2021) | 0.3299 | 0.5552 | 0.9507 |
| **Linear Regression** | **Test (2022–2023)** | **0.3212** | **0.5575** | **0.9267** |
| **Random Forest Regressor** (`numTrees=30, maxDepth=10`) | Train (2015–2020) | 0.3238 | 0.5573 | 0.9329 |
| **Random Forest Regressor** | Validation (2021) | 0.3685 | 0.6243 | 0.9377 |
| **Random Forest Regressor** | **Test (2022–2023)** | **0.3176** | **0.5474** | **0.9293** |

- **Propagation Regime Breakdown on Test Set (2022–2023):**
  - **Early Propagation ($1 \le h \le 3$, $53,818$ rows):** Random Forest (`MAE = 0.3778`, `RMSE = 0.6377`, $R^2 = 0.8854$) outperforms Linear Regression (`MAE = 0.3936`, `RMSE = 0.6667`, $R^2 = 0.8748$).
  - **Sustained Event ($h \ge 4$, $82,127$ rows):** Both models achieve **$R^2 \approx 0.948$** (`MAE = 0.2737–0.2781`, `RMSE = 0.4725–0.4790`).

---

### 5.2 Classification (`Classification.ipynb`)
- **Observational Unit:** Verified $100\%$-complete active continuation county-hours `(fips_code, Hour)` ($h \ge 1$, $N = 843,512$ county-hours; chronologically split into **Train [2015–2020]: 560,572**, **Validation [2021]: 146,995**, and **Test [2022–2023]: 135,945**).
- **Binary Target (`label_cls`):** 1-Hour-Ahead **High-Severity Feeder-Scale Outage Classification** ($\text{max\_rolling\_avg}_{i,t} \ge 100\text{ customers}$, $42.44\%$ positive class rate), representing outages at or above the utility primary-feeder lockout threshold.
- **Imbalance & Leakage Controls:** Inverse class-frequency weights (`w_neg = 0.8609`, `w_pos = 1.1926`) are learned strictly from the 2015–2020 training split. Current-hour `max_rolling_avg` and all post-onset event summary columns (`evDur_Hr`, `evDur_day`, `Max_outage`, `event_mean_completeness_pct`, `event_min_completeness_pct`) are strictly excluded from the feature matrix.

| Model | Split | Accuracy | Precision (Pos) | Recall (Pos) | F1-Score (Pos) | PR-AUC | ROC-AUC | TP | FP | TN | FN |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **Logistic Regression** | Train (2015–2020) | 0.9284 | 0.8947 | 0.9399 | 0.9167 | 0.9684 | 0.9742 | 220,890 | 26,001 | 299,557 | 14,124 |
| **Logistic Regression** | Validation (2021) | 0.9322 | 0.9141 | 0.9462 | 0.9299 | 0.9790 | 0.9785 | 66,076 | 6,211 | 70,952 | 3,756 |
| **Logistic Regression** | **Test (2022–2023)** | **0.9280** | **0.8910** | **0.9297** | **0.9099** | **0.9636** | **0.9728** | **49,423** | **6,047** | **76,736** | **3,739** |
| **Decision Tree Classifier** | Train (2015–2020) | 0.9484 | 0.9412 | 0.9352 | 0.9382 | 0.9211 | 0.8983 | 219,787 | 13,719 | 311,839 | 15,227 |
| **Decision Tree Classifier** | Validation (2021) | 0.9520 | 0.9532 | 0.9455 | 0.9493 | 0.9422 | 0.9160 | 66,026 | 3,244 | 73,919 | 3,806 |
| **Decision Tree Classifier** | **Test (2022–2023)** | **0.9487** | **0.9385** | **0.9297** | **0.9341** | **0.9129** | **0.8911** | **49,424** | **3,236** | **79,547** | **3,738** |

- **Trade-off Interpretation:** **Decision Tree Classifier** achieves **`94.87%` Overall Test Accuracy**, **`93.85%` Precision**, and **`0.9341` F1-Score**, cutting False Positives nearly in half (`3,236` vs. `6,047`) while matching Logistic Regression's Recall (`92.97%`). Meanwhile, **Logistic Regression** achieves **`92.80%` Overall Test Accuracy** with superior continuous probability ranking (**ROC-AUC = `0.9728`**, **PR-AUC = `0.9636`**).

---

### 5.3 Unsupervised Learning (`Unsupervised_Learning.ipynb`)
- **Analytical Unit:** U.S. County Profile ($N = 3,010$ unique `fips_code` counties) aggregated in PySpark across $3,572,394$ outage hours using **7 core standardized continuous features** (`StandardScaler(withMean=True, withStd=True)`): `log_median_baseline`, `log_mean_hourly_outage`, `log_p90_peak_outage`, `log_mean_event_dur_hr`, `log_total_events`, `mean_completeness_pct`, and `full_completeness_share`—strictly excluding administrative identifiers (`fips_code`, `new_event_no`) and arbitrary string indices.
- **K-Means Evaluation (`seed=42`):**
  - Across $k \in \{2, 3, 4, 5, 6, 7, 8\}$, **$k = 2$** achieves a **Silhouette Score of `0.5518`** (squared Euclidean, cluster sizes `[905, 2105]`), **$k = 5$** achieves **`0.4331`**, and **$k = 3$** achieves **`0.4178`** (`WSSSE = 10,492.16`, cluster sizes `[417, 1132, 1461]` separating high-scale/high-completeness counties, moderate-scale counties, and low-completeness rural counties).
- **PCA Variance Decomposition ($7$ Core Standardized Features):**
  - **PC1:** `61.88%` (Outage Scale & Telemetry Completeness Axis)
  - **PC2:** `14.52%` (Cumulative: **`76.40%`** — Event Frequency vs. Duration Axis)
  - **PC3:** `10.65%` (Cumulative: **`87.05%`** — Baseline Threshold vs. Peak Surge Axis)
  - **PC4:** `8.21%` (Cumulative: **`95.26%`**)

---

## 6. Troubleshooting Guide

1. **`FileNotFoundError: Could not locate 'Eagle_I_US_2024_with_VTEC_Updated.csv'`:**
   - Ensure the four raw CSV files are located in the parent directory (`c:\Users\jsm10\OneDrive\Desktop\bda_project\`) or set `$env:GRIDPULSE_DATA_DIR` to their folder path before launching Jupyter.
2. **Windows `HADOOP_HOME and hadoop.home.dir are unset` / `winutils.exe` Warning:**
   - On Windows without a local Hadoop binary installation (`winutils.exe`), Spark logs a benign startup warning and native `df.write.parquet()` can fail. All three notebooks include a built-in `save_and_verify_parquet()` helper that automatically falls back to `pyarrow.parquet.write_table()` when `winutils.exe` is absent and then verifies the saved file by reading it back via `spark.read.parquet()`.
3. **Spark 4.x `SparkDateTimeException` on Mixed Timestamp Formats:**
   - Spark 4.0+ enables ANSI SQL mode by default. All three notebooks explicitly set `.config("spark.sql.ansi.enabled", "false")` and use regex/multi-format parsing so mixed timestamp formats in `NWS_WARNINGS_COMBINED_data_Updated.csv` (`yyyy-MM-dd HH:mm` and `M/d/yyyy H:mm`) parse cleanly.
4. **Java OutOfMemoryError (OOM):**
   - Each notebook configures `.config("spark.driver.memory", "6g")` and `.config("spark.sql.shuffle.partitions", "16")`, and explicitly calls `.unpersist()` on cached DataFrames once modeling finishes. Close one notebook's kernel before running the next if your machine has $\le 8\text{ GB}$ of physical RAM.
