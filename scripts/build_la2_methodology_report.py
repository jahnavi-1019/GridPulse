import os
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT

out_dir = r"c:\Users\jsm10\OneDrive\Desktop\bda_project\GridPulse_Part1_Team_Evaluation"
img_dir = os.path.join(out_dir, "outputs")
doc_path = os.path.join(out_dir, "GridPulse_LA2_Methodology_Report.docx")

doc = Document()

# Page setup
for section in doc.sections:
    section.top_margin = Inches(1.0)
    section.bottom_margin = Inches(1.0)
    section.left_margin = Inches(1.0)
    section.right_margin = Inches(1.0)

style = doc.styles["Normal"]
style.font.name = "Times New Roman"
style.font.size = Pt(12)

def add_title_line(text, size=16, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=8):
    p = doc.add_paragraph()
    p.alignment = align
    p.paragraph_format.space_after = Pt(space_after)
    r = p.add_run(text)
    r.font.name = "Times New Roman"
    r.font.size = Pt(size)
    r.bold = bold
    return p

def add_heading_custom(text, level=1):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(14 if level == 1 else 10)
    p.paragraph_format.space_after = Pt(6)
    r = p.add_run(text)
    r.font.name = "Times New Roman"
    r.font.size = Pt(14 if level == 1 else 12)
    r.bold = True
    return p

def add_para(text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.space_after = Pt(8)
    p.paragraph_format.line_spacing = 1.15
    r = p.add_run(text)
    r.font.name = "Times New Roman"
    r.font.size = Pt(12)
    return p

def add_table_custom(title, headers, rows):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(4)
    r = p.add_run(title)
    r.font.name = "Times New Roman"
    r.font.size = Pt(11)
    r.bold = True

    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr_cells = table.rows[0].cells
    for i, h in enumerate(headers):
        hdr_cells[i].text = h
        for p_cell in hdr_cells[i].paragraphs:
            for run in p_cell.runs:
                run.font.name = "Times New Roman"
                run.font.size = Pt(10)
                run.bold = True
    for row in rows:
        row_cells = table.add_row().cells
        for i, val in enumerate(row):
            row_cells[i].text = str(val)
            for p_cell in row_cells[i].paragraphs:
                for run in p_cell.runs:
                    run.font.name = "Times New Roman"
                    run.font.size = Pt(10)
    doc.add_paragraph()

def add_figure_if_exists(filename, caption):
    fpath = os.path.join(img_dir, filename)
    if os.path.exists(fpath):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run()
        r.add_picture(fpath, width=Inches(6.0))
        cap = doc.add_paragraph()
        cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        cap.paragraph_format.space_after = Pt(10)
        rc = cap.add_run(caption)
        rc.font.name = "Times New Roman"
        rc.font.size = Pt(10)
        rc.italic = True

# FRONT PAGE (Matching user's Literature Survey front page format with METHODOLOGY heading)
add_title_line("METHODOLOGY", size=18, bold=True, space_after=14)
add_title_line("GridPulse: Independent Electricity Reliability Sensing from Internet Telemetry", size=14, bold=True, space_after=24)
add_title_line("Submitted By", size=12, bold=True, space_after=10)
add_title_line("1. MUTYALA JAHNAVI SAI   BL.AI.U4AID24047", size=12, bold=False, space_after=6)
add_title_line("2. AEJAZ AHMAD ANSARI   BL.AI.U4AID24078", size=12, bold=False, space_after=6)
add_title_line("3. DIVYESH PERUMAL SHANMUGARAJAH   BL.AI.U4AID24083", size=12, bold=False, space_after=24)

add_title_line("Project Methodology", size=14, bold=True, space_after=14)
add_title_line("Project Title: GridPulse: Independent Electricity Reliability Sensing from Internet Telemetry", size=12, bold=True, align=WD_ALIGN_PARAGRAPH.LEFT, space_after=6)
add_title_line("Subject: Big Data Analytics", size=12, bold=True, align=WD_ALIGN_PARAGRAPH.LEFT, space_after=6)
add_title_line("Course code : 23AID302", size=12, bold=True, align=WD_ALIGN_PARAGRAPH.LEFT, space_after=6)
add_title_line("Mentor : B. Uma Maheshwari", size=12, bold=True, align=WD_ALIGN_PARAGRAPH.LEFT, space_after=18)

doc.add_page_break()

# SECTION 1: INTRODUCTION AND PROBLEM STATEMENT
add_heading_custom("1. Introduction and Problem Statement", level=1)
add_para("Reliable electrical power infrastructure forms the operational backbone of modern residential, industrial, healthcare, and digital communication systems. When severe weather events or distribution-grid failures occur, utilities and emergency response coordinators must assess three distinct dimensions of grid reliability simultaneously: how many customers will lose power in the coming hour, whether an active local disruption will escalate into a critical distribution-feeder outage, and which geographic regions exhibit chronic structural vulnerability versus incomplete telemetry reporting.")
add_para("Conventional outage analysis struggles with two major operational bottlenecks. First, raw utility outage records arrive at high temporal frequency across thousands of counties and millions of event hours, making single-threaded in-memory tools inefficient for multi-year feature engineering and model training. Second, recorded outage datasets suffer from telemetry coverage gaps: an absence of recorded outages in a county during a specific year can reflect either genuine grid stability or incomplete data collection from local utilities. Treating unverified county-hours as true zero-outage periods introduces severe downward bias into predictive models.")
add_para("To address this problem at big-data scale, the GridPulse experimental framework is implemented end-to-end in Apache Spark (PySpark 4.2.0 and Spark MLlib). The methodology divides the outage analytics pipeline into three complementary analytical tracks spanning nine distributed statistical, machine learning, and deep learning models:")
add_para("The first analytical track addresses continuous outage magnitude forecasting through distributed regression. Given an active outage event in county i at hour t, the objective is to forecast the one-hour-ahead log-transformed customer outage demand y_{i,t} = log(1 + max_rolling_avg_{i,t}) using Linear Regression with ElasticNet regularization, Random Forest Regression, and Gradient-Boosted Tree (GBT) Regression.")
add_para("The second analytical track addresses operational alarm disambiguation through binary classification. Using the same verified county-hour feature panel, the objective is to predict whether the following hour will breach the utility distribution-feeder threshold of 100 or more customers without power (label_high_severity_100 = 1) using Regularized Logistic Regression, Decision Tree Classification, and a Feedforward Neural Network implemented via the Spark Multilayer Perceptron Classifier (MLP).")
add_para("The third analytical track addresses nationwide spatial vulnerability profiling and telemetry auditing through unsupervised learning. Aggregating nine years of outage duration, intensity, weather coupling, and coverage records across 3,010 U.S. counties, this track discovers latent vulnerability tiers and separates genuine grid resilience from telemetry missingness using K-Means Clustering, Gaussian Mixture Models (GMM) via Expectation-Maximization, and Principal Component Analysis (PCA).")

# SECTION 2: DATASET SOURCE AND PREPROCESSING DETAILS
add_heading_custom("2. Dataset Source and Preprocessing Details", level=1)
add_para("The experimental dataset integrates four complementary multi-source CSV tables located in the GridPulse repository (~1.23 GB on disk), derived from the Oak Ridge National Laboratory (ORNL) EAGLE-I utility outage monitoring system and the National Weather Service (NWS) Valid Time Event Code (VTEC) storm warning archives covering the United States from 2014 through 2023.")

add_heading_custom("2.1 Multi-Source Data Inventory", level=2)
add_para("The primary event-hour table, Eagle_I_US_2024_with_VTEC_Updated.csv (366.93 MB, 3,574,278 county-hour rows, 18 columns), records hourly customer outage counts (sum, mean, max, and 3-hour rolling averages), outage event identifiers, cumulative elapsed outage hours (event_hour), and binary flags indicating co-occurring NWS weather warnings across 15 hazard categories. The second table, EAGLEI_Source_Record_Availability.csv (32.43 MB, 969,050 rows), provides annual county-by-year telemetry coverage ratios (ratio in [0, 1]) measuring the fraction of expected 15-minute utility reports actually received. The third table, NWS_WARNINGS_COMBINED_data_Updated.csv (832.28 MB, 650,919 polygon records), provides raw meteorological warning polygons and storm phenomena codes. The fourth table, Missing_Data_Sensitivity_Summary.csv (5 rows), supplies empirical coverage sensitivity thresholds across completeness tiers (70%, 80%, 90%, 99%, and 100%).")

add_table_custom(
    "Summary Table 1 – GridPulse Multi-Source Dataset Inventory",
    ["Dataset File", "Size on Disk", "Records / Granularity", "Primary Variables", "Role in GridPulse Pipeline"],
    [
        ["Eagle_I_US_2024_with_VTEC_Updated.csv", "366.93 MB", "3,574,278 county-hours (2014–2023)", "fips, start_time, max_rolling_avg, event_hour, 15 VTEC storm flags", "Core spatiotemporal outage and weather feature panel"],
        ["EAGLEI_Source_Record_Availability.csv", "32.43 MB", "969,050 county-year records", "fips, year, ratio (0.0 to 1.0)", "Telemetry completeness filter and observability profiling"],
        ["NWS_WARNINGS_COMBINED_data_Updated.csv", "832.28 MB", "650,919 warning polygons", "WFO, phenomena, sig, issue/expire timestamps", "Meteorological hazard context and VTEC cross-reference"],
        ["Missing_Data_Sensitivity_Summary.csv", "0.23 KB", "5 coverage thresholds", "70%, 80%, 90%, 99%, 100% completeness benchmarks", "Threshold justification for 100%-complete filtering"]
    ]
)

add_heading_custom("2.2 Distributed Preprocessing and Leakage-Free Feature Engineering in PySpark", level=2)
add_para("All data ingestion and preprocessing steps execute inside a unified PySpark pipeline configured with Adaptive Query Execution (spark.sql.adaptive.enabled = true) and Snappy Parquet compression. Initially, county FIPS identifiers are standardized to zero-padded 5-character strings (LPAD(CAST(fips AS STRING), 5, '0')), and hourly timestamps are parsed into UTC format to extract cyclical calendar indicators (hour_of_day, month, day_of_week, and event year).")
add_para("To prevent incomplete utility reporting from corrupting supervised model training, the 3,574,278 county-hour outage records are inner-joined against deduplicated county-year availability records filtered strictly to 100% telemetry completeness (ratio >= 1.0). Next, distributed window functions partitioned by (fips, event_id) and ordered chronologically by event_hour construct strictly causal autoregressive lag predictors: lag1_log_outage (outage magnitude at t - 1), lag2_log_outage (outage magnitude at t - 2), lag1_delta_log_outage (first-order outage growth velocity between t - 2 and t - 1), and lag1_any_vtec (weather alert state at t - 1). Initial onset hours (event_hour = 0), where prior-hour lags do not exist, are excluded so that no synthetic zero imputation or future information leaks into the feature vector.")
add_para("This preprocessing pipeline yields N = 843,512 verified, 100%-complete continuation county-hours containing 22 leak-free predictors. Rather than applying a random train-test split that would place adjacent hours of the same multi-day storm into both training and test sets, the panel is partitioned strictly along chronological boundaries: Training Set (2015–2020: 560,572 rows, 66.46%), Validation Set (2021: 146,995 rows, 17.43%), and Out-of-Time Test Set (2022–2023: 135,945 rows, 16.12%). For the Unsupervised Learning track, the full 3,574,278 county-hour telemetry dataset is aggregated by county FIPS alongside the complete county-year availability table to construct a nationwide structural profile of N = 3,010 U.S. counties across seven standardized vulnerability and telemetry completeness features.")

# SECTION 3: METHODOLOGY AND IMPLEMENTATION OF MODELS
add_heading_custom("3. Methodology and Implementation of Statistical, ML, and DL Models", level=1)
add_para("To satisfy rigorous comparative evaluation across paradigms, three distinct models are implemented per analytical track (nine models in total) using Spark MLlib Pipelines. All preprocessing transformers (VectorAssembler and StandardScaler) are fitted exclusively on the training partition before transforming validation and test partitions.")

add_heading_custom("3.1 Track 1: Outage Magnitude Forecasting (Regression Models)", level=2)
add_para("The regression track predicts continuous one-hour-ahead log customer outage demand y_{i,t} = log(1 + max_rolling_avg_{i,t}). Because raw customer outage counts exhibit extreme right-skewness spanning five orders of magnitude, the natural log transformation stabilizes variance while allowing direct interpretation of prediction errors in log-customer units.")
add_para("Model 1 (Regularized Linear Regression – ElasticNet): Implemented via pyspark.ml.regression.LinearRegression over standardized features (StandardScaler withMean=True, withStd=True). The model minimizes penalized squared error with regularization parameter regParam in {0.0001, 0.01} and ElasticNet mixing parameter elasticNetParam in {0.0, 0.5}. Validation tuning selected L2 ridge penalty regParam = 0.0001 and elasticNetParam = 0.0. This model provides a fast, closed-form linear baseline that quantifies the additive contribution of autoregressive outage persistence.")
add_para("Model 2 (Random Forest Regressor – Bagging Ensemble): Implemented via pyspark.ml.regression.RandomForestRegressor with numTrees = 30, featureSubsetStrategy = 'sqrt', and maxDepth tuned over {6, 10} (selecting maxDepth = 10 on the 2021 validation split). By training 30 independent variance-reducing regression trees in parallel across bootstrapped subsamples, Random Forest captures non-linear interactions between elapsed duration and compound weather warnings without overfitting.")
add_para("Model 3 (Gradient-Boosted Tree Regressor – Boosting Ensemble): Implemented via pyspark.ml.regression.GBTRegressor with maxIter = 25, maxDepth = 5, and stepSize = 0.1. Unlike parallel bagging, GBT builds shallow trees sequentially, where each new tree fits the negative gradient of the squared-error loss of the preceding ensemble. This sequential residual correction targets sharp outage restoration drops and rapid storm escalation spikes.")

add_table_custom(
    "Summary Table 2 – Regression Track Models (Outage Magnitude Forecasting)",
    ["Model", "Paradigm", "Spark MLlib Implementation & Key Hyperparameters", "Architectural Role"],
    [
        ["Linear Regression (ElasticNet)", "Statistical Parametric Baseline", "LinearRegression(regParam=0.0001, elasticNetParam=0.0) + StandardScaler", "Captures linear first-order Markov persistence"],
        ["Random Forest Regressor", "Parallel Bagging Tree Ensemble", "RandomForestRegressor(numTrees=30, maxDepth=10, featureSubsetStrategy='sqrt')", "Reduces variance via parallel decorrelated trees"],
        ["GBT Regressor", "Sequential Gradient Boosting", "GBTRegressor(maxIter=25, maxDepth=5, stepSize=0.1)", "Minimizes non-linear bias during storm transitions"]
    ]
)

add_heading_custom("3.2 Track 2: High-Severity Outage Alarm Prediction (Classification Models)", level=2)
add_para("The classification track formulates an operational utility dispatch alarm: predicting whether a county's active outage will reach or exceed 100 affected customers in the next hour (label_high_severity_100 in {0, 1}). Across the 843,512 county-hours, 37.90% represent high-severity feeder events (39.11% on the 2022–2023 test set).")
add_para("Model 1 (Regularized Logistic Regression): Implemented via pyspark.ml.classification.LogisticRegression with standardized inputs, tuning regParam in {0.001, 0.01} and elasticNetParam in {0.0, 0.5}. Logistic Regression estimates log-odds linearly and optimizes log-loss via distributed L-BFGS, serving as a calibrated probabilistic baseline.")
add_para("Model 2 (Decision Tree Classifier): Implemented via pyspark.ml.classification.DecisionTreeClassifier tuned across maxDepth in {5, 8} and impurity criteria in {'gini', 'entropy'} (selecting maxDepth = 8 and information-gain entropy on validation). The tree recursively partitions the 22-dimensional feature space into interpretable axis-aligned threshold rules suitable for human dispatchers.")
add_para("Model 3 (Multilayer Perceptron Classifier – Deep Feedforward Neural Network): Implemented via pyspark.ml.classification.MultilayerPerceptronClassifier with architecture layers = [22, 24, 12, 2], two hidden layers of 24 and 12 sigmoid neurons, a 2-unit softmax output layer, blockSize = 128, and distributed L-BFGS backpropagation (maxIter = 50). The deep neural architecture learns smooth non-linear decision boundaries across multi-hazard weather indicators and temporal lag trajectories.")

add_table_custom(
    "Summary Table 3 – Classification Track Models (High-Severity Outage Disambiguation)",
    ["Model", "Paradigm", "Spark MLlib Implementation & Key Hyperparameters", "Architectural Role"],
    [
        ["Logistic Regression", "Statistical Generalized Linear Model", "LogisticRegression(regParam=0.001, elasticNetParam=0.0) + StandardScaler", "Linear log-odds baseline with calibrated probabilities"],
        ["Decision Tree Classifier", "Non-Parametric Recursive Partitioning", "DecisionTreeClassifier(maxDepth=8, impurity='entropy')", "Rule-based hierarchical feature splitting"],
        ["Multilayer Perceptron (MLP)", "Deep Feedforward Neural Network", "MultilayerPerceptronClassifier(layers=[22, 24, 12, 2], maxIter=50)", "Smooth non-linear representation learning & ranking"]
    ]
)

add_heading_custom("3.3 Track 3: County Vulnerability & Telemetry Regime Discovery (Unsupervised Models)", level=2)
add_para("The unsupervised track analyzes all N = 3,010 U.S. counties across seven county-level features standardized via StandardScaler(withMean=True, withStd=True): log_total_customer_hours, log_mean_cust_out, log_max_cust_out, log_outage_hours, pct_high_sev_100, vtec_Freeze_rate, and mean_availability_ratio.")
add_para("Model 1 (K-Means Clustering – Centroid Partitioning): Implemented via pyspark.ml.clustering.KMeans(initMode='k-means||', maxIter=50) swept across k in {2, 3, 4, 5, 6, 7, 8}. K-Means minimizes Within-Set Sum of Squared Errors (WSSSE) to produce hard spherical partitions of county vulnerability.")
add_para("Model 2 (Gaussian Mixture Model – Probabilistic EM Soft Clustering): Implemented via pyspark.ml.clustering.GaussianMixture(maxIter=50) swept across k in {2, 3, 4, 5, 6, 7, 8}. Unlike K-Means, GMM models each cluster as a multivariate Gaussian distribution N(mu_c, Sigma_c) with a full 7x7 covariance matrix fitted via distributed Expectation-Maximization (EM). It outputs continuous posterior membership probabilities gamma_{i,c} for counties straddling transitional vulnerability boundaries.")
add_para("Model 3 (Principal Component Analysis – Orthogonal Manifold Projection): Implemented via pyspark.ml.feature.PCA(k=7) via Singular Value Decomposition (SVD) of the standardized county feature covariance matrix. PCA quantifies intrinsic dimensionality and projects the 7-dimensional county profiles onto orthogonal axes for visual verification of the K-Means and GMM cluster boundaries.")

add_table_custom(
    "Summary Table 4 – Unsupervised Learning Track Models (County Regime Discovery)",
    ["Model", "Paradigm", "Spark MLlib Implementation & Key Hyperparameters", "Architectural Role"],
    [
        ["K-Means Clustering", "Hard Centroid Partitioning", "KMeans(k=2..8, initMode='k-means||', maxIter=50)", "Assigns discrete county vulnerability tiers"],
        ["Gaussian Mixture Model (GMM)", "Probabilistic EM Density Estimation", "GaussianMixture(k=2..8, maxIter=50, full covariance)", "Captures elliptical clusters and soft posterior risk"],
        ["Principal Component Analysis", "Linear Spectral Dimensionality Reduction", "PCA(k=7) on z-scored county feature matrix", "Extracts orthogonal variance axes (PC1–PC4)"]
    ]
)

# SECTION 4: EVALUATION METRICS AND COMPARATIVE ANALYSIS
add_heading_custom("4. Evaluation Metrics and Comparative Analysis", level=1)
add_para("Each track is evaluated using domain-appropriate statistical metrics on held-out data to compare model paradigms objectively.")

add_heading_custom("4.1 Regression Comparative Analysis (2022–2023 Out-of-Time Test Set)", level=2)
add_para("Regression performance is evaluated using Mean Absolute Error (MAE), Root Mean Squared Error (RMSE), and the Coefficient of Determination (R2) across the 135,945 out-of-time test county-hours, alongside a naive persistence baseline (y_hat_t = y_{t-1}). All three machine learning models significantly outperform naive persistence (RMSE = 0.6254, R2 = 0.9078). Linear Regression achieves Test RMSE = 0.5575 and R2 = 0.9267 (92.67%), confirming strong autoregressive continuity. Random Forest improves Test RMSE to 0.5474 and R2 to 0.9293 (92.93%). The GBT Regressor achieves the best overall performance across every metric, reducing Test MAE to 0.2947, Test RMSE to 0.5324, and reaching Test R2 = 0.9332 (93.32%). Furthermore, evaluating GBT across outage progression phases reveals R2 = 0.8891 during volatile early propagation hours (1 <= event_hour <= 3) and R2 = 0.9515 during sustained outages (event_hour >= 4).")

add_table_custom(
    "Summary Table 5 – Regression Track Comparative Performance (2021 Validation vs. 2022–2023 Test)",
    ["Model", "Val MAE", "Val RMSE", "Val R2", "Test MAE", "Test RMSE", "Test R2"],
    [
        ["Naive Persistence Baseline (y_{t-1})", "0.3358", "0.6062", "0.9163", "0.3547", "0.6254", "0.9078"],
        ["Model 1: Linear Regression (ElasticNet)", "0.3054", "0.5396", "0.9337", "0.3212", "0.5575", "0.9267"],
        ["Model 2: Random Forest Regressor", "0.3029", "0.5313", "0.9357", "0.3176", "0.5474", "0.9293"],
        ["Model 3: GBT Regressor (Best)", "0.2815", "0.5174", "0.9390", "0.2947", "0.5324", "0.9332"]
    ]
)

add_figure_if_exists("regression_eda_overview.png", "Figure 1: Regression Track – Outage Target Distribution and Autoregressive Lag Correlation")
add_figure_if_exists("regression_evaluation_diagnostics.png", "Figure 2: Regression Track – Out-of-Time Test Set (2022–2023) Comparative Error & Feature Importance Diagnostics")

add_heading_custom("4.2 Classification Comparative Analysis (2022–2023 Out-of-Time Test Set)", level=2)
add_para("Classification models are evaluated using Accuracy, Precision, Recall, F1-Score, Area Under the Precision-Recall Curve (PR-AUC), and Area Under the ROC Curve (ROC-AUC). On the 2022–2023 test set (135,945 county-hours), Logistic Regression achieves 92.80% Accuracy, F1 = 0.9099, and ROC-AUC = 0.9728, generating 6,047 false alarms. The Decision Tree Classifier improves Accuracy to 94.92% and F1-Score to 0.9344 by capturing sharp threshold splits, but its piecewise-constant leaf probabilities yield a lower PR-AUC (0.9167) and ROC-AUC (0.9033). The deep Multilayer Perceptron Classifier (MLP [22, 24, 12, 2]) delivers the strongest overall performance across five of six metrics: Test Accuracy = 94.96% (Validation Accuracy = 95.25%), Precision = 94.87%, F1-Score = 0.9346, PR-AUC = 0.9764, and ROC-AUC = 0.9814. Crucially, the MLP cuts false-positive feeder dispatches by 56.2% compared to Logistic Regression (2,646 vs. 6,047 false positives).")

add_table_custom(
    "Summary Table 6 – Classification Track Comparative Performance on Out-of-Time Test Set (2022–2023)",
    ["Model", "Accuracy", "Precision", "Recall", "F1-Score", "PR-AUC", "ROC-AUC", "Confusion Matrix (TP / FP / TN / FN)"],
    [
        ["Model 1: Logistic Regression", "92.80%", "89.10%", "92.97%", "0.9099", "0.9636", "0.9728", "49,423 / 6,047 / 76,736 / 3,739"],
        ["Model 2: Decision Tree (depth=8)", "94.92%", "94.34%", "92.56%", "0.9344", "0.9167", "0.9033", "49,208 / 2,953 / 79,830 / 3,954"],
        ["Model 3: MLP Neural Net [22,24,12,2]", "94.96%", "94.87%", "92.08%", "0.9346", "0.9764", "0.9814", "48,954 / 2,646 / 80,137 / 4,208"]
    ]
)

add_figure_if_exists("classification_eda_overview.png", "Figure 3: Classification Track – High-Severity Outage Class Balance and VTEC Hazard Lift")
add_figure_if_exists("classification_evaluation_diagnostics.png", "Figure 4: Classification Track – Confusion Matrices and Metric Comparison Across Models")

add_heading_custom("4.3 Unsupervised Learning Comparative Analysis (3,010 U.S. Counties)", level=2)
add_para("Unsupervised models are evaluated across k in {2..8} using Euclidean Silhouette Score, K-Means WSSSE, GMM Log-Likelihood, and PCA Explained Variance Ratio. Both K-Means and GMM identify k = 2 as the primary structural division (K-Means Silhouette = 0.5518, WSSSE = 13,300.43; GMM Silhouette = 0.4354, Log-Likelihood = -16,146.99), separating 2,105 well-instrumented high-exposure counties from 905 rural/incomplete-telemetry counties. At k = 3, K-Means achieves Silhouette = 0.4178 (WSSSE = 10,492.16) and subdivides the nation into three actionable operational regimes: Cluster 0 (1,132 Moderate-Exposure Regional Grid Counties, mean availability 80.5%), Cluster 1 (1,461 High-Exposure Metropolitan/Coastal Vulnerability Hotspots, mean availability 94.3%, averaging 2,262 outage hours and 49.4% high-severity rate), and Cluster 2 (417 Sparse/Low-Telemetry Rural Counties, mean availability 33.4%, confirming that low recorded outage counts in these counties stem from sensor blind spots rather than grid immunity). PCA confirms that the first two orthogonal components capture 76.40% of total nationwide variance (PC1 = 61.88%, PC2 = 14.52%), and the top four components capture 95.26% (PC3 = 10.65%, PC4 = 8.21%).")

add_table_custom(
    "Summary Table 7 – Unsupervised Track K-Means vs. Gaussian Mixture Model Sweep (N = 3,010 Counties)",
    ["Clusters (k)", "K-Means WSSSE", "K-Means Silhouette", "K-Means Sizes", "GMM Log-Likelihood", "GMM Silhouette", "GMM Sizes"],
    [
        ["k = 2", "13,300.43", "0.5518", "[905, 2105]", "-16,146.99", "0.4354", "[2137, 873]"],
        ["k = 3", "10,492.16", "0.4178", "[1132, 1461, 417]", "-15,663.99", "0.3870", "[533, 451, 2026]"],
        ["k = 4", "8,998.08", "0.3910", "[498, 1277, 355, 880]", "-15,076.19", "0.2147", "[761, 1445, 360, 444]"],
        ["k = 5", "7,869.62", "0.3598", "[785, 353, 818, 608, 446]", "-14,257.42", "0.1753", "[647, 361, 200, 1344, 458]"],
        ["k = 6", "7,041.00", "0.3511", "[382, 738, 608, 307, 745, 230]", "-14,265.24", "0.1816", "[363, 453, 405, 293, 987, 509]"]
    ]
)

add_figure_if_exists("unsupervised_eda_county_correlations.png", "Figure 5: Unsupervised Track – County Vulnerability Feature Distributions and Correlation Matrix")
add_figure_if_exists("unsupervised_evaluation_diagnostics.png", "Figure 6: Unsupervised Track – K-Means vs. GMM Model Selection, PCA Biplot, and Cluster Profiles")

# SECTION 5: EXPERIMENTAL RESULTS FOR EXECUTION-TIME AND SCALABILITY ANALYSIS
add_heading_custom("5. Experimental Results for Execution-Time and Scalability Analysis", level=1)
add_para("A core requirement of Big Data Analytics is evaluating how distributed algorithms scale with respect to dataset volume (weak/strong data scaling) and cluster partition parallelism (spark.sql.shuffle.partitions / RDD partitioning). Two systematic benchmark suites were executed across all nine models.")

add_heading_custom("5.1 Data-Size Scalability Analysis (25%, 50%, 75%, and 100% Volume)", level=2)
add_para("In the supervised tracks (Regression and Classification), training subsets of 25% (140,420 rows), 50% (280,536 rows), 75% (420,420 rows), and 100% (560,572 rows) were benchmarked with 8 Spark partitions. Linear Regression scales with near-constant wall-clock time from 1.05s at 25% volume to 1.48s at 100% volume (a 1.41x time increase for a 4.0x data increase) because Spark computes the 22x22 Gram matrix in a single distributed pass. Random Forest Regressor scales sub-linearly from 4.70s to 10.18s (2.17x increase for 4x data), and GBT Regressor scales from 13.05s to 17.66s (1.35x increase) due to sequential tree construction. In Classification, Decision Tree training scales from 3.39s to 5.86s, MLP Neural Network training scales from 8.38s to 10.87s, and Logistic Regression scales from 13.37s to 14.47s.")
add_para("In the Unsupervised track, scaling is evaluated end-to-end across raw telemetry fractions from 25% (893,569 rows) to 100% (3,574,278 rows). Distributed Spark SQL county aggregation scales sub-linearly from 3.581s at 25% to 5.143s at 100% (only a 1.44x latency increase for a 4x volume increase), while subsequent county-level clustering takes ~1.97s for K-Means, ~3.12s for GMM, and ~0.31s for PCA.")

add_table_custom(
    "Summary Table 8 – Data-Volume Scalability Benchmark Across All 9 Models (25% to 100% Data Scale)",
    ["Track / Model", "25% Data Time (s)", "50% Data Time (s)", "75% Data Time (s)", "100% Data Time (s)", "Scaling Factor (100% / 25%)"],
    [
        ["Regression: Linear Regression", "1.05 s", "1.39 s", "1.59 s", "1.48 s", "1.41x (4x rows)"],
        ["Regression: Random Forest Regressor", "4.70 s", "6.02 s", "8.33 s", "10.18 s", "2.17x (4x rows)"],
        ["Regression: GBT Regressor", "13.05 s", "14.44 s", "15.86 s", "17.66 s", "1.35x (4x rows)"],
        ["Classification: Decision Tree", "3.39 s", "4.36 s", "5.37 s", "5.86 s", "1.73x (4x rows)"],
        ["Classification: MLP Neural Network", "8.38 s", "9.64 s", "10.35 s", "10.87 s", "1.30x (4x rows)"],
        ["Classification: Logistic Regression", "13.37 s", "13.70 s", "14.21 s", "14.47 s", "1.08x (4x rows)"],
        ["Unsupervised: Spark 3.57M Aggregation", "3.58 s", "3.94 s", "4.82 s", "5.14 s", "1.44x (4x rows)"],
        ["Unsupervised: K-Means (k=3) / GMM / PCA", "2.39s / 3.45s / 0.44s", "2.12s / 3.16s / 0.28s", "1.87s / 2.81s / 0.28s", "1.97s / 3.12s / 0.31s", "O(N_counties) invariant"]
    ]
)

add_heading_custom("5.2 Partition Parallelism Benchmark (4, 8, and 16 Spark Partitions)", level=2)
add_para("To evaluate horizontal task parallelism, the full training dataset was repartitioned across 4, 8, and 16 Spark partitions. On the large 560,572-row supervised dataset, increasing parallelism from 4 to 16 partitions yields substantial speedups for compute-bound algorithms: Random Forest Regressor training drops by 38.2% (from 21.09s at 4 partitions to 13.03s at 16 partitions), Decision Tree Classifier drops by 36.8% (from 9.44s to 5.97s), and MLP Neural Network training drops by 25.4% (from 11.12s to 8.30s). Sequential GBT Regression reaches its optimal trade-off at 8 partitions (20.67s vs. 23.81s at 4 partitions), slightly increasing to 21.44s at 16 partitions due to tree-level synchronization barriers.")
add_para("Conversely, on the compact 3,010-row county matrix in the Unsupervised track, increasing partitions from 4 to 16 slows execution down: K-Means rises from 1.217s (4 partitions) to 3.149s (16 partitions), GMM rises from 3.220s to 8.018s, and PCA rises from 0.157s to 0.281s. This demonstrates a fundamental Big Data systems law: when per-partition data volume is very small (~188 rows per partition at 16 partitions), Spark task serialization and barrier coordination overhead across 50 EM/Lloyd iterations exceed parallel compute gains.")

add_table_custom(
    "Summary Table 9 – Partition Parallelism Benchmark (4, 8, and 16 Spark Partitions at 100% Data Volume)",
    ["Track / Model", "4 Partitions (s)", "8 Partitions (s)", "16 Partitions (s)", "Optimal Partitioning & Systems Behavior"],
    [
        ["Regression: Linear Regression", "1.62 s", "1.73 s", "1.32 s", "16 Partitions (-18.5% latency)"],
        ["Regression: Random Forest Regressor", "21.09 s", "15.14 s", "13.03 s", "16 Partitions (-38.2% parallel speedup)"],
        ["Regression: GBT Regressor", "23.81 s", "20.67 s", "21.44 s", "8 Partitions (optimal compute vs. shuffle balance)"],
        ["Classification: Logistic Regression", "13.25 s", "13.38 s", "12.71 s", "16 Partitions (-4.1% latency)"],
        ["Classification: Decision Tree", "9.44 s", "7.38 s", "5.97 s", "16 Partitions (-36.8% parallel speedup)"],
        ["Classification: MLP Neural Network", "11.12 s", "10.02 s", "8.30 s", "16 Partitions (-25.4% L-BFGS gradient speedup)"],
        ["Unsupervised: K-Means (3,010 counties)", "1.22 s", "1.75 s", "3.15 s", "4 Partitions (avoids small-task scheduling overhead)"],
        ["Unsupervised: GMM (3,010 counties)", "3.22 s", "4.83 s", "8.02 s", "4 Partitions (minimizes EM barrier synchronization)"],
        ["Unsupervised: PCA (3,010 counties)", "0.16 s", "0.21 s", "0.28 s", "4 Partitions (single-pass Gram SVD)"]
    ]
)

add_figure_if_exists("regression_scalability_analysis.png", "Figure 7: Regression Track – Data-Volume and Spark Partition Scalability Curves")
add_figure_if_exists("classification_scalability_analysis.png", "Figure 8: Classification Track – Data-Volume and Spark Partition Scalability Curves")
add_figure_if_exists("unsupervised_scalability_analysis.png", "Figure 9: Unsupervised Track – End-to-End 3.57M Row Aggregation and Partition Scalability")

# SECTION 6: CONCLUSION
add_heading_custom("6. Conclusion", level=1)
add_para("This methodology and experimental evaluation demonstrated an end-to-end distributed PySpark analytics pipeline for electricity outage reliability sensing across 3.57 million county-hour records and 3,010 U.S. counties. By enforcing strict 100% telemetry completeness filtering (N = 843,512 verified continuation county-hours) and chronological train/validation/test partitioning, the framework eliminated missing-data bias and temporal leakage.")
add_para("Across the nine implemented models, three central findings emerge. First, in continuous one-hour-ahead outage magnitude regression, sequential Gradient-Boosted Trees (GBTRegressor) achieved the highest accuracy (Test RMSE = 0.5324, MAE = 0.2947, R2 = 0.9332), outperforming both Linear Regression (R2 = 0.9267) and Random Forest (R2 = 0.9293) by correcting non-linear storm escalation residuals. Second, in binary high-severity feeder outage classification (>= 100 customers), the deep Multilayer Perceptron Classifier (layers = [22, 24, 12, 2]) achieved superior discrimination (Test Accuracy = 94.96%, F1 = 0.9346, PR-AUC = 0.9764, ROC-AUC = 0.9814) while cutting false-positive dispatch alarms by 56.2% relative to Logistic Regression. Third, in nationwide unsupervised regime discovery, K-Means (Silhouette = 0.5518 at k = 2; 0.4178 at k = 3), Gaussian Mixture Models, and PCA (76.40% variance in 2 components; 95.26% in 4 components) successfully separated 1,461 genuine high-vulnerability metropolitan/coastal counties from 417 rural counties suffering from severe telemetry reporting blind spots (33.4% mean availability). Finally, scalability benchmarks verified sub-linear execution-time growth across a 4x data expansion and up to 38.2% parallel speedup at 16 partitions for large-volume supervised training, while empirically demonstrating scheduler overhead on compact county-level tables.")

# SECTION 7: REFERENCES
add_heading_custom("7. References", level=1)
refs = [
    "1. Brelsford, C., Tennille, S., Myers, A., Chinthavali, S., Tansakul, V., Denman, M., Coletti, M., Grant, J., Lee, S., Allen, K., & Bhaduri, B. (2024). A dataset of recorded electricity outages by United States county 2014–2022. Scientific Data, 11(1), 271. Oak Ridge National Laboratory (ORNL) EAGLE-I.",
    "2. Ma, J., Li, B., Omitaomu, O. A., & Mostafavi, A. (2025). Establishing nationwide power system vulnerability index across US counties using interpretable machine learning. Applied Energy, 397, 126360.",
    "3. Kabir, E., Guikema, S. D., & Quiring, S. M. (2024). Power outage prediction using data streams: An adaptive ensemble learning approach with a feature- and performance-based weighting mechanism. Risk Analysis, 44(3), 686–704.",
    "4. Meier, A. K., Ueno, T., & Pritoni, M. (2019). Using data from connected thermostats to track large power outages in the United States. Applied Energy, 256, 113940.",
    "5. Bayat, N., Mahajan, K., Denton, S., Misra, V., & Rubenstein, D. (2021). Down for failure: Active power status monitoring. Future Generation Computer Systems, 125, 629–640.",
    "6. National Weather Service (NWS) & Iowa Environmental Mesonet (IEM). (2024). Valid Time Event Code (VTEC) Watch, Warning, and Advisory Archives (2014–2023).",
    "7. Zaharia, M., Xin, R. S., Wendell, P., Das, T., Armbrust, M., Dave, A., Meng, X., Rosen, J., Venkataraman, S., Franklin, M. J., Ghodsi, A., Gonzalez, J., Shenker, S., & Stoica, I. (2016). Apache Spark: A unified engine for big data processing. Communications of the ACM, 59(11), 56–65.",
    "8. Meng, X., Bradley, J., Yavuz, B., Sparks, E., Venkataraman, S., Liu, D., Freeman, J., Tsai, D., Amde, M., Owen, S., Xin, D., Xin, R., Franklin, M. J., Zadeh, R., Zaharia, M., & Talwalkar, A. (2016). MLlib: Machine learning in Apache Spark. Journal of Machine Learning Research, 17(34), 1–7."
]
for ref in refs:
    add_para(ref)

doc.save(doc_path)
print("Saved:", doc_path, "Size:", os.path.getsize(doc_path))
