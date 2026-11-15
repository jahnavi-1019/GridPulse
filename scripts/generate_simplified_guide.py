#!/usr/bin/env python
"""Generate a simplified, student-friendly Word (.docx) guide for GridPulse."""

from __future__ import annotations
import os
from pathlib import Path
from docx import Document
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls
from docx.shared import Inches, Pt, RGBColor

PROJECT_ROOT = Path(__file__).resolve().parents[1]

def set_cell_background(cell, fill_hex: str) -> None:
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tcPr.append(shd)

def add_styled_table(doc: Document, headers, rows, col_widths=None):
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    hdr_cells = table.rows[0].cells
    for i, header_text in enumerate(headers):
        hdr_cells[i].text = ""
        p = hdr_cells[i].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(str(header_text))
        run.bold = True
        run.font.size = Pt(10)
        run.font.name = "Calibri"
        run.font.color.rgb = RGBColor(255, 255, 255)
        set_cell_background(hdr_cells[i], "1B365D")
        hdr_cells[i].vertical_alignment = WD_ALIGN_VERTICAL.CENTER

    for r_idx, row_values in enumerate(rows):
        row_cells = table.add_row().cells
        bg_color = "F4F7FA" if r_idx % 2 == 1 else "FFFFFF"
        for c_idx, val in enumerate(row_values):
            row_cells[c_idx].text = ""
            p = row_cells[c_idx].paragraphs[0]
            run = p.add_run(str(val))
            run.font.size = Pt(9.5)
            run.font.name = "Calibri"
            set_cell_background(row_cells[c_idx], bg_color)
            if c_idx > 1 and any(ch.isdigit() for ch in str(val)) and len(str(val)) < 15:
                p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            else:
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            row_cells[c_idx].vertical_alignment = WD_ALIGN_VERTICAL.CENTER

    if col_widths and len(col_widths) == len(headers):
        for row in table.rows:
            for idx, width in enumerate(col_widths):
                row.cells[idx].width = Inches(width)

def build_simplified_guide():
    doc = Document()

    # Page Margins
    for sec in doc.sections:
        sec.top_margin = Inches(1.0)
        sec.bottom_margin = Inches(1.0)
        sec.left_margin = Inches(1.0)
        sec.right_margin = Inches(1.0)

    # Document Title
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_title = p_title.add_run("⚡ GridPulse: Simplified Student & Viva Guide")
    r_title.bold = True
    r_title.font.size = Pt(24)
    r_title.font.color.rgb = RGBColor(27, 54, 93)

    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_sub = p_sub.add_run("A Plain-English, Step-by-Step Explanation of the Project, the Datasets, Apache Spark & Scala Architecture, ML/DL Models, and Top Viva Q&A")
    r_sub.font.size = Pt(12)
    r_sub.font.italic = True
    r_sub.font.color.rgb = RGBColor(90, 105, 120)

    p_meta = doc.add_paragraph()
    p_meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_meta = p_meta.add_run("Course: B.Tech Big Data Analytics | Technologies: Apache Spark (v3.5.3), Scala (v2.12.18), PySpark, Spark MLlib, Streamlit")
    r_meta.font.size = Pt(10)
    r_meta.bold = True

    doc.add_paragraph("―" * 55)

    # SECTION 1: THE BIG PICTURE
    h1 = doc.add_heading("1. The Big Picture: What is GridPulse Doing in Simple Words?", level=1)
    h1.runs[0].font.color.rgb = RGBColor(27, 54, 93)

    doc.add_paragraph(
        "Imagine a severe thunderstorm or a tornado hits a county. Within the first hour, power lines trip and customers start losing electricity. "
        "The electric utility company faces a critical life-or-death decision: Is this just a minor local fuse that one trouble-truck can fix, or is it about "
        "to blow up into a massive multi-feeder power outage leaving thousands of homes and hospitals in the dark for days?"
    )
    doc.add_paragraph(
        "GridPulse is a Big Data Analytics project built using Apache Spark and Scala that solves two major problems:\n"
        "1. Real-Time Outage Prediction: At the very start of a storm (Hour 1 of an outage), can we accurately predict if it will escalate into a severe power failure (>= 100 customers out)?\n"
        "2. Long-Term Grid Reliability Profiling: Looking at 8 years of historical data across all 3,010 counties in the United States, which counties have chronically fragile power grids that fail repeatedly, and which ones are resilient?"
    )

    # SECTION 2: THE DATASETS EXPLAINED
    h2 = doc.add_heading("2. What are the Datasets? (Where Did the Data Come From?)", level=1)
    h2.runs[0].font.color.rgb = RGBColor(27, 54, 93)

    doc.add_paragraph(
        "Our project combines four complementary datasets (~1.23 GB total raw data) from two major U.S. federal agencies: "
        "the U.S. Department of Energy (DOE EAGLE-I) and the National Oceanic and Atmospheric Administration (NOAA National Weather Service)."
    )

    ds_rows = [
        ["1. Eagle_I_US_2024_with_VTEC_Updated.csv", "3.57 Million Rows (350 MB)", "County-Hour (Every hour a county had an outage & active storm warning)", "DOE EAGLE-I + NOAA NWS", "Contains the core hourly customer outages (max_rolling_avg), duration (evDur_Hr), peak outage (Max_outage), and weather warning codes (SV, TO, WS)."],
        ["2. NWS_WARNINGS_COMBINED_data_Updated.csv", "4.15 Million Rows (794 MB)", "Severe weather warning bulletin issuances/updates", "NOAA National Weather Service (IEM Archive)", "Contains storm warning polygons, start/end times, phenomenon codes (59 types), and severity tags (wind speed, hail size, tornado emergencies)."],
        ["3. EAGLEI_Source_Record_Availability.csv", "1.05 Million Rows (31 MB)", "County-Day telemetry availability", "DOE / ORNL EAGLE-I Monitoring", "Tracks whether utility web-scrapers successfully collected 15-minute polling data. Reveals that 38.9% of county-days had zero records due to internet/scraper failures."],
        ["4. Missing_Data_Sensitivity_Summary.csv", "4 Benchmark Tiers (91.5M Obs)", "Completeness stratum sensitivity", "DOE Benchmark Study", "Proves that when telemetry is < 50% complete, reported outage counts have a 75.0% error rate. Explains why missing data cannot be treated as zero outages!"],
    ]
    add_styled_table(
        doc,
        headers=["Dataset File Name", "Size & Rows", "Observational Unit", "Source Agency", "What It Contains in Simple Terms"],
        rows=ds_rows,
        col_widths=[1.8, 1.1, 1.2, 1.1, 1.8]
    )

    doc.add_paragraph(
        "\nKey Columns You Must Know for Viva:\n"
        "• fips_code: The official 5-digit ID for each U.S. county (e.g., 12086 = Miami-Dade, Florida).\n"
        "• max_rolling_avg: The number of customers without power during that hour.\n"
        "• median_sum: The typical baseline outage in that county (allows fair comparison between large and small counties).\n"
        "• new_event_no: The unique ID of the storm/outage episode.\n"
        "• evDur_Hr: The total length of the outage in hours.\n"
        "• Max_outage: The highest number of customers who lost power during the entire storm.\n"
        "• Matched_Events: The weather warning codes active at that time (e.g., 'SV' = Severe Thunderstorm, 'TO' = Tornado, 'WS' = Winter Storm)."
    )

    # SECTION 3: HOW WE ARE DOING IT (PIPELINE EXPLAINED)
    h3 = doc.add_heading("3. How We Did It: The Step-by-Step Pipeline", level=1)
    h3.runs[0].font.color.rgb = RGBColor(27, 54, 93)

    steps_rows = [
        ["Step 1: Ingestion & Quality Audit", "Apache Spark & Scala (DataIngestionAudit.scala)", "Reads raw CSVs with strict schemas. Verifies 0 duplicate rows and checks for missing values. Analyzes the 38.9% telemetry reporting gap so missing intervals are not faked as zero outages."],
        ["Step 2: Episode Aggregation", "Spark Window Functions (EpisodeFeatureEngine.scala)", "The raw dataset has 3.57 million hourly rows, but contiguous storm hours belong to the SAME event! Using Window.partitionBy(fips_code, new_event_no), we combine them into 1.37 million distinct storm episodes."],
        ["Step 3: Leakage-Free Feature Engineering", "Spark SQL & Window Lag Functions", "To predict the future at Hour 1, we CANNOT use future columns like final duration or peak outage! We only use Hour 1 telemetry + past history (lag(1), lag(5)) within that county."],
        ["Step 4: Machine Learning & Deep Learning", "Spark MLlib (OutageMLSuite.scala)", "Trains 4 models: Logistic Regression, Random Forest, Gradient-Boosted Trees (GBT), and a Deep Multilayer Perceptron Neural Network (MLPC) on 2015–2020, tuned on 2021, and tested on 2022."],
        ["Step 5: County Reliability Profiling", "Distributed K-Means (RegionalReliabilityClustering.scala)", "Uses Spark MLlib KMeans (k=4) to cluster all 3,010 counties into 4 distinct grid vulnerability archetypes."],
        ["Step 6: Interactive Dashboard & Simulator", "Streamlit, Plotly & Folium (app.py)", "Builds a 9-page web dashboard with interactive maps, charts, and a real-time 'What-If' Risk Simulator where you can pick a county and weather threat to see live escalation probabilities."],
    ]
    add_styled_table(
        doc,
        headers=["Pipeline Stage", "Module / Tool", "What Happens Under the Hood"],
        rows=steps_rows,
        col_widths=[1.5, 1.7, 3.8]
    )

    # SECTION 4: THE MODELS EXPLAINED SIMPLY
    h4 = doc.add_heading("4. The Machine Learning & Deep Learning Models (Explained Simply)", level=1)
    h4.runs[0].font.color.rgb = RGBColor(27, 54, 93)

    doc.add_paragraph(
        "We tested four models in Apache Spark MLlib on an untouched test set of 214,185 storm episodes from the year 2022. "
        "Here is how each model works and how it performed:"
    )

    ml_rows = [
        ["1. Logistic Regression", "Linear Baseline", "0.8378", "86.12%", "Draws a mathematical boundary line between minor and severe outages using log-odds. Fast, but misses complex storm interactions."],
        ["2. Random Forest", "Bagging Ensemble", "0.8524", "87.45%", "Builds 50 different decision trees in parallel on random data subsets and takes a democratic vote. Very stable against noisy utility spikes."],
        ["3. Gradient-Boosted Trees (GBT)", "Boosting Ensemble (Winner)", "0.8640", "88.94%", "Trees are built sequentially, where each new tree specifically focuses on correcting the mistakes of the previous trees. Achieved the highest ROC-AUC (0.864) and PR-AUC (0.671)."],
        ["4. Deep Multilayer Perceptron (MLPC)", "Deep Learning (Neural Net)", "0.8510", "87.10%", "Spark's native Deep Neural Network with 4 layers: Input (24 features) -> Hidden 1 (64 neurons) -> Hidden 2 (32 neurons) -> Hidden 3 (16 neurons) -> Output (2 classes). Runs natively on the JVM!"],
    ]
    add_styled_table(
        doc,
        headers=["Model Name", "Category", "Test ROC-AUC", "Accuracy", "How It Works in Simple Terms"],
        rows=ml_rows,
        col_widths=[1.8, 1.2, 1.0, 0.9, 2.1]
    )

    doc.add_paragraph(
        "\nWhat is K-Means Clustering Doing?\n"
        "It groups all 3,010 U.S. counties into 4 distinct reliability tiers based on outage recurrence, severity, and telemetry coverage:\n"
        "• Tier 1: Chronic High-Severity & High-Recurrence (Severe storm corridors, frequent multi-hour blackouts).\n"
        "• Tier 2: Elevated Weather-Driven Vulnerability (Generally okay, but vulnerable to severe tropical/winter storms).\n"
        "• Tier 3: Moderate / Intermittent Outage Burden (Typical suburban/rural counties with average grid reliability).\n"
        "• Tier 4: Low Observed Burden or Sparse Telemetry (Counties with few reported storms or low utility reporting)."
    )

    # SECTION 5: LIVE WHAT-IF SIMULATOR
    h5 = doc.add_heading("5. The Interactive 'What-If' Outage Risk Simulator (Page 8)", level=1)
    h5.runs[0].font.color.rgb = RGBColor(27, 54, 93)

    doc.add_paragraph(
        "In Page 8 of the Streamlit dashboard (`app.py`), we built an interactive control-room decision simulator:\n"
        "1. You select any U.S. county (e.g., Miami-Dade, Florida). The system instantly looks up its baseline outage level and past history.\n"
        "2. You select the active weather warning (e.g., Tornado 'TO', Severe Thunderstorm 'SV', or Winter Storm 'WS').\n"
        "3. You slide the Hour-1 telemetry slider (e.g., 35 customers out in the first hour).\n"
        "4. The system runs real-time inference through the trained GBT pipeline and displays:\n"
        "   - A live color-coded gauge (Green for Low Risk, Amber for Moderate, Red for Critical Escalation).\n"
        "   - Automated operational dispatch advice: Tells control rooms whether to send 1 trouble-truck or pre-stage multi-crew mutual aid and initiate automated SCADA feeder switching."
    )

    # SECTION 6: TOP 10 VIVA QUESTIONS AND SIMPLE ANSWERS
    h6 = doc.add_heading("6. Top 10 Viva Questions & Winning Answers", level=1)
    h6.runs[0].font.color.rgb = RGBColor(27, 54, 93)

    qa = [
        ("Q1: What is the main objective of project GridPulse?",
         "Answer: GridPulse investigates whether historical outage behavior, severe weather warnings, and geographic context can explain power outage severity and identify regions with recurring power grid reliability problems across 3.57 million county-hour observations."),

        ("Q2: Why did you use Apache Spark and Scala?",
         "Answer: Apache Spark is the industry standard for distributed Big Data processing. Since Spark is natively written in Scala, building the pipeline in Scala allows native execution on the JVM with zero Py4J serialization overhead, high-speed Window aggregations over 3.57 million rows, and native distributed Deep Learning via Spark MLlib's MultilayerPerceptronClassifier."),

        ("Q3: Why can't we treat absent outage records as zero outages?",
         "Answer: Our source availability audit of 1.05 million county-days revealed that 38.91% of days had zero 15-minute telemetry records because utility web scrapers failed or internet went down during storms. A missing record means we have no telemetry, NOT that zero customers lost power! In our benchmark, incomplete telemetry caused a 75% error in outage counts."),

        ("Q4: What is pseudoreplication and how did you fix it?",
         "Answer: In the raw dataset, an outage event lasting 10 hours was repeated as 10 separate rows, each showing the SAME total event duration and peak customer count. If treated as 10 independent samples, models would overfit. We fixed this by using Spark Window functions to aggregate the 3.57 million hourly rows into 1.37 million distinct contiguous episodes (fips_code, new_event_no)."),

        ("Q5: What is data leakage and how did you prevent it in your prediction task?",
         "Answer: Data leakage happens when a model uses future information to predict the future. We strictly evaluated our model at Hour 1 of a newly started outage. We eliminated all post-onset columns (like final duration, peak outage, and mean completeness) and used only past historical lags computed with strict shift(1) windows. Furthermore, we used chronological splits: Train on 2015–2020, validate on 2021, and test on the untouched 2022 dataset."),

        ("Q6: Which model performed the best and why?",
         "Answer: Gradient-Boosted Trees (GBT) performed best with a Test ROC-AUC of 0.8640 and PR-AUC of 0.6713. Tree boosting excels on non-linear tabular grid data because it sequentially builds decision trees that correct the residuals of prior trees, capturing the sharp escalation caused by severe weather warnings."),

        ("Q7: How did you implement Deep Learning in Apache Spark?",
         "Answer: We used Spark MLlib's native MultilayerPerceptronClassifier (MLPC), configuring a 4-layer deep feedforward neural network: [Input (24 features) -> Hidden 1 (64 neurons) -> Hidden 2 (32 neurons) -> Hidden 3 (16 neurons) -> Output (2 classes)]. It trains natively across Spark workers using the L-BFGS optimizer on the JVM."),

        ("Q8: How did you evaluate the scalability of Apache Spark?",
         "Answer: We benchmarked Spark throughput across partition scaling (4, 8, and 16 partitions). Runtimes decreased from 14.82s (4 partitions) to 9.15s (8 partitions, 1.62x speedup) to 5.48s (16 partitions, 2.70x speedup), confirming high parallel CPU efficiency and sub-linear execution time growth."),

        ("Q9: Is the Streamlit dashboard live or dataset-based?",
         "Answer: It is dataset-based on the historical 2015–2023 dataset, meaning it does not connect to live streaming NOAA APIs. However, it performs real-time interactive query computation: whenever a user adjusts filters or tests the What-If Risk Simulator, it dynamically queries the Parquet lake via Polars lazy pushdown and runs real-time ML inference in milliseconds."),

        ("Q10: What are the 4 county reliability archetypes?",
         "Answer: Using Spark MLlib KMeans (k=4), we grouped all 3,010 counties into: Tier 1 (Chronic High-Severity & High Recurrence), Tier 2 (Elevated Weather-Driven Vulnerability), Tier 3 (Moderate / Intermittent Burden), and Tier 4 (Low Observed Burden or Sparse Telemetry). This prevents ranking bias by evaluating outage burden alongside telemetry coverage."),
    ]

    for q, a in qa:
        p_q = doc.add_paragraph()
        r_q = p_q.add_run(q)
        r_q.bold = True
        r_q.font.color.rgb = RGBColor(27, 54, 93)
        r_q.font.size = Pt(10.5)

        p_a = doc.add_paragraph()
        r_a = p_a.add_run(a)
        r_a.font.size = Pt(10)
        p_a.paragraph_format.left_indent = Inches(0.2)

    # Save
    out_file = PROJECT_ROOT / "GridPulse_Simplified_Student_Guide.docx"
    doc.save(str(out_file))
    print(f"✅ Generated Simplified Student & Viva Guide: {out_file} (Size: {os.path.getsize(out_file)} bytes)")
    return out_file

if __name__ == "__main__":
    build_simplified_guide()
