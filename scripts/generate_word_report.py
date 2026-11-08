#!/usr/bin/env python
"""Generate a comprehensive, publication-grade Microsoft Word (.docx) report for GridPulse."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Sequence

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import polars as pl
from docx import Document
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn
from docx.shared import Inches, Pt, RGBColor

PROJECT_ROOT = Path(__file__).resolve().parents[1]
METRICS_DIR = PROJECT_ROOT / "outputs" / "metrics"
FIGURES_DIR = PROJECT_ROOT / "outputs" / "figures"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
FEATURES_DIR = PROJECT_ROOT / "data" / "features"


def set_cell_background(cell, fill_hex: str) -> None:
    """Set background color of a Word table cell."""
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tcPr.append(shd)


def add_formatted_table(
    doc: Document,
    headers: Sequence[str],
    rows: Sequence[Sequence[str]],
    col_widths: Sequence[float] | None = None,
) -> None:
    """Add a styled academic table with navy header, alternating row shading, and crisp borders."""
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
        run.font.size = Pt(9.5)
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
            # Right-align numeric-looking columns (except first column)
            val_str = str(val)
            if c_idx > 0 and any(ch.isdigit() for ch in val_str) and len(val_str) < 22:
                p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            else:
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            run = p.add_run(val_str)
            run.font.size = Pt(9)
            run.font.name = "Calibri"
            set_cell_background(row_cells[c_idx], bg_color)
            row_cells[c_idx].vertical_alignment = WD_ALIGN_VERTICAL.CENTER

    if col_widths:
        for row in table.rows:
            for idx, width in enumerate(col_widths):
                row.cells[idx].width = Inches(width)

    doc.add_paragraph()


def generate_report_charts() -> dict[str, Path]:
    """Generate high-resolution (300 DPI) matplotlib charts from actual processed Parquet & JSON outputs."""
    plt.style.use("seaborn-v0_8-whitegrid")
    chart_paths: dict[str, Path] = {}

    # 1. Missing-Data Sensitivity & In-Sample Completeness Chart
    sens_df = pl.read_parquet(PROCESSED_DIR / "missing_data_sensitivity.parquet").to_pandas()
    with open(METRICS_DIR / "data_audit_report.json", "r", encoding="utf-8") as f:
        audit = json.load(f)
    comp_df = pd.DataFrame(audit["eagle_vtec"]["completeness_tier_breakdown"])

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.2), dpi=300)
    colors1 = ["#2b8cbe", "#7bccc4", "#fdae61", "#d73027"]
    bars1 = ax1.bar(
        sens_df["completeness_tier"],
        sens_df["Median_Relative_Difference"],
        color=colors1,
        edgecolor="#1B365D",
    )
    ax1.set_title("Benchmark Median Relative Error (%) by Completeness Tier", fontsize=10.5, fontweight="bold")
    ax1.set_ylabel("Median Relative Difference (%)", fontsize=9.5)
    ax1.set_ylim(0, 88)
    ax1.tick_params(axis="x", rotation=20, labelsize=8.5)
    for b in bars1:
        h = b.get_height()
        ax1.text(b.get_x() + b.get_width() / 2, h + 1.8, f"{h:.2f}%", ha="center", fontsize=8.5, fontweight="bold")

    bars2 = ax2.bar(
        comp_df["completeness_tier"],
        comp_df["share_pct"],
        color=["#d73027", "#2b8cbe", "#fdae61", "#7bccc4"],
        edgecolor="#1B365D",
    )
    ax2.set_title("Share of 3.57M Harmonized Outage-Warning Hours (%)", fontsize=10.5, fontweight="bold")
    ax2.set_ylabel("Share of Total County-Hours (%)", fontsize=9.5)
    ax2.set_ylim(0, 42)
    ax2.tick_params(axis="x", rotation=20, labelsize=8.5)
    for b in bars2:
        h = b.get_height()
        ax2.text(b.get_x() + b.get_width() / 2, h + 0.9, f"{h:.2f}%", ha="center", fontsize=8.5, fontweight="bold")

    plt.tight_layout()
    p1 = FIGURES_DIR / "docx_fig1_completeness_sensitivity.png"
    fig.savefig(p1, dpi=300)
    plt.close(fig)
    chart_paths["completeness"] = p1

    # 2. Spatiotemporal Monthly Trend & Diurnal Cycle
    ym_df = pl.read_parquet(PROCESSED_DIR / "temporal_by_year_month.parquet").to_pandas()
    ym_df = ym_df[ym_df["year"] <= 2022].copy()
    ym_df["ym_label"] = ym_df["year"].astype(str) + "-" + ym_df["month"].astype(str).str.zfill(2)
    hr_df = pl.read_parquet(PROCESSED_DIR / "temporal_by_hour.parquet").to_pandas()

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.5, 4.2), dpi=300)
    ax1.plot(range(len(ym_df)), ym_df["outage_events"], color="#1B365D", linewidth=1.8, label="Outage Episodes")
    ax1.set_title("Monthly Outage Episodes Across U.S. Counties (2015–2022)", fontsize=10.5, fontweight="bold")
    ax1.set_ylabel("Distinct County-Outage Episodes", fontsize=9.5)
    tick_idx = list(range(0, len(ym_df), 12))
    ax1.set_xticks(tick_idx)
    ax1.set_xticklabels(ym_df["ym_label"].iloc[tick_idx], rotation=30, fontsize=8.5)

    ax2.bar(hr_df["hour_of_day"], hr_df["hourly_records"], color="#3182bd", edgecolor="#1B365D")
    ax2.set_title("Diurnal Cycle: Warning-Matched Outage Hours by UTC Hour", fontsize=10.5, fontweight="bold")
    ax2.set_xlabel("Hour of Day (UTC)", fontsize=9.5)
    ax2.set_ylabel("Observed County-Hour Records", fontsize=9.5)
    ax2.set_xticks(range(0, 24, 2))

    plt.tight_layout()
    p2 = FIGURES_DIR / "docx_fig2_spatiotemporal_trends.png"
    fig.savefig(p2, dpi=300)
    plt.close(fig)
    chart_paths["spatiotemporal"] = p2

    # 3. Weather-Warning Associations & Robustness Check
    w_df = pl.read_parquet(PROCESSED_DIR / "weather_association_summary.parquet").to_pandas()
    top12_w = w_df.head(12).sort_values("prob_high_severity_ge100_pct", ascending=True)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.5, 4.6), dpi=300)
    bars_w = ax1.barh(
        top12_w["primary_phenom"],
        top12_w["prob_high_severity_ge100_pct"],
        color="#2b8cbe",
        edgecolor="#1B365D",
    )
    ax1.set_title("High-Severity Escalation Rate (>=100 Cust) by Top 12 VTEC Codes", fontsize=10, fontweight="bold")
    ax1.set_xlabel("Episodes Reaching >= 100 Customers Out (%)", fontsize=9)
    ax1.set_xlim(0, 23)
    for b in bars_w:
        w_val = b.get_width()
        ax1.text(w_val + 0.3, b.get_y() + b.get_height() / 2, f"{w_val:.1f}%", va="center", fontsize=8)

    valid_w = w_df.dropna(subset=["high_comp_prob_ge100_pct"])
    ax2.scatter(
        valid_w["prob_high_severity_ge100_pct"],
        valid_w["high_comp_prob_ge100_pct"],
        s=70,
        color="#d73027",
        edgecolor="#1B365D",
        alpha=0.85,
    )
    max_v = max(valid_w["prob_high_severity_ge100_pct"].max(), valid_w["high_comp_prob_ge100_pct"].max()) + 5
    ax2.plot([0, max_v], [0, max_v], linestyle="--", color="gray", label="y = x Reference")
    for _, r in valid_w.head(10).iterrows():
        ax2.annotate(
            r["primary_phenom"],
            (r["prob_high_severity_ge100_pct"], r["high_comp_prob_ge100_pct"]),
            textcoords="offset points",
            xytext=(4, 4),
            fontsize=8,
        )
    ax2.set_title("Completeness Robustness: All vs. >=75% Complete (Spearman ρ = 0.984)", fontsize=10, fontweight="bold")
    ax2.set_xlabel("All Episodes High-Severity Rate (%)", fontsize=9)
    ax2.set_ylabel(">=75% Completeness High-Severity Rate (%)", fontsize=9)
    ax2.legend(fontsize=8.5)

    plt.tight_layout()
    p3 = FIGURES_DIR / "docx_fig3_weather_associations.png"
    fig.savefig(p3, dpi=300)
    plt.close(fig)
    chart_paths["weather"] = p3

    # 4. Predictive Modeling: Permutation Feature Importance & Calibration Curve
    with open(METRICS_DIR / "modeling_evaluation_results.json", "r", encoding="utf-8") as f:
        m_res = json.load(f)
    imp_df = pd.DataFrame(m_res["feature_importance_hgb_permutation"]).head(10).sort_values(
        "importance_mean_roc_auc_drop", ascending=True
    )
    cal_df = pd.DataFrame(m_res["calibration_curve_test_2022"])

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.5, 4.4), dpi=300)
    ax1.barh(
        imp_df["feature"],
        imp_df["importance_mean_roc_auc_drop"],
        xerr=imp_df["importance_std"],
        color="#1B365D",
        ecolor="#d73027",
        capsize=3,
    )
    ax1.set_title("Top 10 Onset Features (Permutation ROC-AUC Drop on 2022 Test Set)", fontsize=10, fontweight="bold")
    ax1.set_xlabel("Mean ROC-AUC Drop When Permuted", fontsize=9)

    ax2.plot(
        cal_df["mean_predicted_prob"],
        cal_df["observed_positive_fraction"],
        marker="o",
        color="#1B365D",
        linewidth=2,
        label="HistGradientBoosting (Brier = 0.0664)",
    )
    ax2.plot([0, 1], [0, 1], linestyle="--", color="#d73027", label="Perfect Calibration (y = x)")
    ax2.set_title("Reliability / Calibration Curve (Untouched 2022 Test Set, N=214,185)", fontsize=10, fontweight="bold")
    ax2.set_xlabel("Mean Predicted Escalation Probability", fontsize=9)
    ax2.set_ylabel("Observed Fraction Reaching >= 100 Customers", fontsize=9)
    ax2.legend(fontsize=8.5)

    plt.tight_layout()
    p4 = FIGURES_DIR / "docx_fig4_model_diagnostics.png"
    fig.savefig(p4, dpi=300)
    plt.close(fig)
    chart_paths["modeling"] = p4

    return chart_paths


def build_word_document() -> Path:
    """Build the complete Word (.docx) report and save it to root and outputs/reports/."""
    with open(METRICS_DIR / "data_audit_report.json", "r", encoding="utf-8") as f:
        audit = json.load(f)
    with open(METRICS_DIR / "weather_and_spatiotemporal_stats.json", "r", encoding="utf-8") as f:
        weather_stats = json.load(f)
    with open(METRICS_DIR / "modeling_evaluation_results.json", "r", encoding="utf-8") as f:
        model_results = json.load(f)

    weather_df = pl.read_parquet(PROCESSED_DIR / "weather_association_summary.parquet").to_pandas()
    state_df = pl.read_parquet(FEATURES_DIR / "state_reliability_profiles.parquet").to_pandas()
    county_df = pl.read_parquet(FEATURES_DIR / "county_reliability_profiles.parquet").to_pandas()
    sens_df = pl.read_parquet(PROCESSED_DIR / "missing_data_sensitivity.parquet").to_pandas()

    chart_paths = generate_report_charts()

    doc = Document()

    # Page margins (1 inch all around)
    for section in doc.sections:
        section.top_margin = Inches(0.9)
        section.bottom_margin = Inches(0.9)
        section.left_margin = Inches(0.9)
        section.right_margin = Inches(0.9)

    # Set default font
    style_normal = doc.styles["Normal"]
    style_normal.font.name = "Calibri"
    style_normal.font.size = Pt(10.5)

    # ==========================================================================
    # TITLE PAGE / HEADER BLOCK
    # ==========================================================================
    title_p = doc.add_paragraph()
    title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_title = title_p.add_run(
        "GRIDPULSE: RESEARCH-GRADE POWER OUTAGE ANALYTICS,\n"
        "WEATHER-WARNING ASSOCIATIONS, AND REGIONAL RELIABILITY ASSESSMENT"
    )
    r_title.bold = True
    r_title.font.size = Pt(16)
    r_title.font.color.rgb = RGBColor(27, 54, 93)

    sub_p = doc.add_paragraph()
    sub_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_sub = sub_p.add_run(
        "B.Tech 5th-Semester Big Data Analytics End-Semester Project — Part 2 Main Research & Application Deliverable\n"
        "Reproducible PySpark + Polars + Scikit-Learn + Streamlit Architecture"
    )
    r_sub.italic = True
    r_sub.font.size = Pt(11)
    r_sub.font.color.rgb = RGBColor(80, 90, 105)

    doc.add_paragraph()

    # Executive Summary Box Table
    exec_rows = [
        [
            "Core Research Question",
            "Can historical outage behaviour, weather-warning characteristics, temporal patterns, and geographic context help explain outage severity and identify regions with recurring power-reliability problems?",
        ],
        [
            "Primary Datasets Audited",
            "1) Eagle_I_US_2024_with_VTEC_Updated.csv (3,572,394 county-hour rows; 349.93 MB)\n"
            "2) NWS_WARNINGS_COMBINED_data_Updated.csv (4,152,437 warning action rows; 793.73 MB)\n"
            "3) EAGLEI_Source_Record_Availability.csv (1,048,575 county-day rows; 30.93 MB)\n"
            "4) Missing_Data_Sensitivity_Summary.csv (4 benchmark tiers across 91.52M observations)",
        ],
        [
            "Observational Units",
            "• County-Hour Unit (fips_code, Hour): 3,572,394 positive outage + active warning hours (2015–2023)\n"
            "• County-Outage Episode Unit (fips_code, new_event_no): 1,374,112 distinct contiguous outage episodes\n"
            "• Regional Units: 3,010 U.S. Counties across 49 States/DC and 115 NWS Weather Forecast Offices (WFOs)",
        ],
        [
            "Headline Empirical Results",
            "• Telemetry Missingness Sensitivity: 38.91% of county-days in the availability audit have 0 observed 15-min records; <50% completeness introduces a 75.0% median relative difference in outage magnitude.\n"
            "• Weather Stratification: Kruskal-Wallis H = 28,328.59 (p < 0.0001); Severe Thunderstorm (SV) accounts for 53.5% of episodes (16.27% >=100 customers), while Extreme Wind (EW, 74.03%) and Tornado (TO, 19.35%) drive peak tail risk. Rank correlation at >=75% completeness is Spearman ρ = 0.9840 (p < 0.0001).\n"
            "• Onset-Time Predictive Modeling (Untouched 2022 Test Set, N = 214,185 episodes): Calibrated HistGradientBoosting achieves ROC-AUC = 0.8640, PR-AUC = 0.6713, F1 = 0.5934, and Brier Score = 0.0664, significantly outperforming persistence (ROC-AUC = 0.7803) and historical priors (ROC-AUC = 0.7165).",
        ],
    ]
    add_formatted_table(
        doc,
        headers=["Project Dimension", "Measured Specification & Summary"],
        rows=exec_rows,
        col_widths=[1.8, 4.7],
    )

    # ==========================================================================
    # SECTION 1: RESEARCH OBJECTIVE & ANALYTICAL SCOPE
    # ==========================================================================
    h1 = doc.add_heading("1. Research Objective & Analytical Scope", level=1)
    h1.runs[0].font.color.rgb = RGBColor(27, 54, 93)

    doc.add_paragraph(
        "GridPulse is the main research and full-stack data application deliverable (Part 2) of the B.Tech 5th-Semester "
        "Big Data Analytics project. Unlike Part 1's pedagogical exercise of implementing eight standalone algorithms, "
        "GridPulse is engineered from the ground up around the actual empirical structure of the harmonized EAGLE-I / NWS VTEC "
        "datasets to answer the central research question:"
    )
    q_p = doc.add_paragraph()
    q_run = q_p.add_run(
        "“Can historical outage behaviour, weather-warning characteristics, temporal patterns, and geographic context "
        "help explain outage severity and identify regions with recurring power-reliability problems?”"
    )
    q_run.bold = True
    q_run.italic = True

    doc.add_paragraph(
        "To investigate this question rigorously without overclaiming or introducing statistical leakage, the research is "
        "structured into four falsifiable sub-questions:"
    )
    bullets_s1 = [
        "RQ1 (Source Coverage & Telemetry Bias): How does 15-minute source telemetry availability vary across counties and days, and how sensitive are inferred outage severity metrics to incomplete sub-hourly reporting?",
        "RQ2 (Weather-Warning Severity Stratification): How do episode duration (evDur_Hr), peak customer impact (Max_outage), and baseline-normalized severity (Max_outage / median_sum) vary across the 18 matched NWS VTEC weather phenomenon regimes and multi-hazard overlaps?",
        "RQ3 (Regional Reliability & Vulnerability Profiling): How can U.S. counties be profiled across recurrence (events_per_observed_year), normalized severity, and tail escalation risk while explicitly accounting for county baseline differences (median_sum) and telemetry completeness?",
        "RQ4 (Onset-Time Escalation Forecasting): Given strictly the telemetry observable at Hour 1 of a newly initiated outage episode and the county's causal prior episode history, how accurately can we predict whether the episode will escalate to a High-Severity Outage (Max_outage >= 100 customers) on an untouched future test year (2022)?",
    ]
    for b in bullets_s1:
        doc.add_paragraph(b, style="List Bullet")

    # ==========================================================================
    # SECTION 2: MANDATORY INITIAL DATA AUDIT & STRUCTURAL DISCOVERIES
    # ==========================================================================
    h2 = doc.add_heading("2. Mandatory Initial Data Audit & Structural Discoveries", level=1)
    h2.runs[0].font.color.rgb = RGBColor(27, 54, 93)

    doc.add_paragraph(
        "All four raw CSV files in the workspace (1.23 GB combined) were audited using PySpark (v4.2.0) and Polars (v1.44.2). "
        "Table 2.1 summarizes the exact verified file inventories, schemas, and date ranges."
    )

    audit_table_rows = [
        [
            "Eagle_I_US_2024_with_VTEC_Updated.csv",
            "349.93 MB",
            "3,572,394",
            "16",
            "County-Hour (fips_code, Hour)",
            "2015-01-02T03:00Z to 2023-01-03T01:00Z",
        ],
        [
            "NWS_WARNINGS_COMBINED_data_Updated.csv",
            "793.73 MB",
            "4,152,437",
            "24",
            "VTEC Warning Action Record",
            "2015-01-01 to 2024-12-31",
        ],
        [
            "EAGLEI_Source_Record_Availability.csv",
            "30.93 MB",
            "1,048,575",
            "6",
            "County-Day (fips_code, Date)",
            "2015-01-01 to 2024-12-31 (288 counties)",
        ],
        [
            "Missing_Data_Sensitivity_Summary.csv",
            "0.0002 MB",
            "4",
            "4",
            "Completeness Tier Benchmark",
            "2015–2024 (91,522,025 total obs)",
        ],
    ]
    add_formatted_table(
        doc,
        headers=["Dataset Filename", "Size", "Exact Rows", "Cols", "Observational Unit", "Observed Temporal Scope"],
        rows=audit_table_rows,
        col_widths=[1.8, 0.75, 0.85, 0.45, 1.35, 1.3],
    )

    doc.add_heading("2.1 Six Critical Empirical Audit Findings", level=2)
    audit_findings = [
        (
            "1. Conditional Positive-Outage & Active-Warning Intersection: ",
            "Every single row in Eagle_I_US_2024_with_VTEC_Updated.csv has max_rolling_avg >= 0.0625 (minimum 1 customer out in one 15-minute poll over a 16-poll / 4-hour rolling window) and Matched_Count >= 1. There are zero null cells, zero duplicate rows, and zero duplicate (fips_code, Hour) keys. Consequently, this dataset represents county-hours where a positive power outage coincided with at least one active NWS VTEC warning.",
        ),
        (
            "2. Episode-Level Invariants & Pseudoreplication Prevention: ",
            "The column new_event_no has 923,178 unique integer IDs globally, but IDs are reused across counties. Combining (fips_code, new_event_no) identifies 1,374,112 distinct contiguous county-outage episodes. Within each episode, evDur_Hr, evDur_day, Max_outage, event_mean_completeness_pct, and event_min_completeness_pct are episode-level constants repeated across every hour of that episode. In 43.81% of episodes, evDur_Hr exceeds the number of rows in the table for that episode because the outage continued into hours before or after the weather warning expired. Aggregating to the episode unit (1,374,112 episodes) is mandatory to avoid weighting long episodes multiple times and to prevent train/test leakage.",
        ),
        (
            "3. Built-in County Baseline Invariant (median_sum) & WFO Mapping: ",
            "Every fips_code (3,010 counties) has exactly 1 unique value of median_sum (ranging from 0.3125 to 2,199.0625 customers) and 1 unique NWS Weather Forecast Office (WFO, 115 offices) across the entire dataset. This provides an internal county-specific baseline denominator (Max_outage / median_sum) for regional comparisons.",
        ),
        (
            "4. Actual Date Range Despite '2024' Filename: ",
            "Although named Eagle_I_US_2024_with_VTEC_Updated.csv, actual records span 2015-01-02T03:00:00Z through 2022-11-12T22:00:00Z, plus a 3-day tail in early 2023 (2023-01-01T00:00:00Z to 2023-01-03T01:00:00Z, 1,644 hourly rows / 397 episodes). No 2024 records exist in the harmonized outage file.",
        ),
        (
            "5. Microsoft Excel Row-Limit Truncation in Source Availability File: ",
            "EAGLEI_Source_Record_Availability.csv contains 1,048,575 data rows (+ 1 header row = 1,048,576 = 2^20 rows, the exact row limit of an Excel .xlsx worksheet). Because it was exported sorted by fips_code ascending, it covers 288 counties (fips_code 1001 in Alabama through 12033 in Escambia County, Florida). Across those 1,048,575 county-days, 38.91% (408,021 county-days) have observed_15min_records == 0 (a 100% reporting gap), proving why an absent outage record must never be treated as a confirmed zero-outage observation.",
        ),
        (
            "6. Mixed Timestamp Formats & Polygon UGC Semantics in NWS Warnings: ",
            "NWS_WARNINGS_COMBINED_data_Updated.csv (4,152,437 rows) mixes 'YYYY-MM-DD HH:MM' and 'M/D/YYYY H:MM' timestamp strings, uses empty/null NWS_UGC exclusively for storm-based polygon warnings (GTYPE='P', 470,289 rows vs. GTYPE='C', 3,682,148 county/zone rows), and encodes absent impact tags (WINDTAG, HAILTAG, TORNADOTAG, DAMAGETAG) as literal 'None' strings.",
        ),
    ]
    for bold_prefix, text_body in audit_findings:
        p = doc.add_paragraph(style="List Bullet")
        r1 = p.add_run(bold_prefix)
        r1.bold = True
        p.add_run(text_body)

    doc.add_heading("2.2 Yearly Coverage & Telemetry Completeness Breakdown", level=2)
    yr_rows = [
        [
            str(r["year"]),
            f"{r['hourly_rows']:,}",
            f"{r['unique_counties']:,}",
            f"{r['unique_event_ids']:,}",
            f"{r['mean_completeness_pct']:.2f}%",
        ]
        for r in audit["eagle_vtec"]["yearly_coverage"]
    ]
    add_formatted_table(
        doc,
        headers=[
            "Year (UTC)",
            "Warning-Matched Hourly Rows",
            "Observed Counties (FIPS)",
            "Unique Event IDs",
            "Mean Hourly Completeness (%)",
        ],
        rows=yr_rows,
        col_widths=[1.0, 1.5, 1.3, 1.3, 1.4],
    )

    doc.add_heading("2.3 Missing-Data Sensitivity Benchmark vs. In-Sample Completeness", level=2)
    sens_table_rows = []
    for _, r in sens_df.iterrows():
        sens_table_rows.append(
            [
                str(r["completeness_tier"]),
                f"{int(r['Total_Observations']):,}",
                f"{float(r['Median_Abs_Difference']):.4f} customers",
                f"{float(r['Median_Relative_Difference']):.2f}%",
            ]
        )
    add_formatted_table(
        doc,
        headers=[
            "Telemetry Completeness Tier",
            "Benchmark Observations",
            "Median Absolute Difference",
            "Median Relative Difference (%)",
        ],
        rows=sens_table_rows,
        col_widths=[1.8, 1.6, 1.6, 1.5],
    )

    doc.add_picture(str(chart_paths["completeness"]), width=Inches(6.4))
    cap1 = doc.add_paragraph(
        "Figure 2.1: Left — Missing-data sensitivity benchmark (Missing_Data_Sensitivity_Summary.csv) showing a 75.0% median relative "
        "error when telemetry completeness falls below 50%. Right — In-sample hourly completeness distribution across the 3,572,394 "
        "county-hours in Eagle_I_US_2024_with_VTEC_Updated.csv."
    )
    cap1.runs[0].italic = True
    cap1.runs[0].font.size = Pt(9)

    # ==========================================================================
    # SECTION 3: SYSTEM ARCHITECTURE & DATA ENGINEERING PIPELINE
    # ==========================================================================
    h3 = doc.add_heading("3. System Architecture, Data Engineering & Data Dictionary", level=1)
    h3.runs[0].font.color.rgb = RGBColor(27, 54, 93)

    doc.add_paragraph(
        "GridPulse implements a modular 6-stage pipeline (executable via `python scripts/run_pipeline.py --stage all` in ~60 seconds) "
        "that separates ingestion, schema validation, cleaning, episode feature engineering, statistical analysis, and predictive modeling:"
    )
    arch_stages = [
        [
            "Stage 1: Ingestion & Schema Audit",
            "src/gridpulse/ingestion/schema_and_audit.py",
            "Validates StructType schemas via PySpark, checks plausible physical bounds, verifies 0 duplicates, and writes outputs/metrics/data_audit_report.json.",
        ],
        [
            "Stage 2: Preprocessing & Parquet Store",
            "src/gridpulse/preprocessing/cleaner.py",
            "Parses UTC timestamps, normalizes mixed NWS date strings, tracks row-count provenance, and writes Zstandard Parquet files in data/processed/.",
        ],
        [
            "Stage 3: Episode Feature Engineering",
            "src/gridpulse/features/builder.py",
            "Aggregates 3.57M hourly rows into 1,374,112 episodes (fips_code, new_event_no), builds shift(1) causal county lags, and creates county (3,010) and state (49) reliability profiles.",
        ],
        [
            "Stage 4: Spatiotemporal & Weather Analytics",
            "src/gridpulse/analysis/spatiotemporal_and_weather.py",
            "Computes hourly/seasonal/monthly trends, runs Kruskal-Wallis H-tests and >=75% completeness Spearman robustness checks, and fits k=4 K-Means county archetypes.",
        ],
        [
            "Stage 5: Predictive Modeling & Evaluation",
            "src/gridpulse/modeling/trainer.py & evaluation/metrics.py",
            "Splits episodes chronologically (2015–2020 Train, 2021 Val, 2022 Untouched Test), enforces verify_no_leakage(), trains 2 baselines + 2 ML models, and computes subgroup error metrics.",
        ],
        [
            "Stage 6: Reporting & Streamlit Dashboard",
            "src/gridpulse/pipeline/orchestrator.py & app.py",
            "Generates standalone HTML figures, markdown/Word research reports, and serves an 8-page Streamlit + Plotly + Folium interactive research application.",
        ],
    ]
    add_formatted_table(
        doc,
        headers=["Pipeline Stage", "Module Path", "Core Engineering & Research Responsibility"],
        rows=arch_stages,
        col_widths=[1.5, 1.8, 3.2],
    )

    doc.add_heading("3.1 Complete Data Dictionary of Core Variables", level=2)
    dict_rows = [
        ["fips_code", "Int64", "1001 to 56045 (3,010 unique)", "5-digit U.S. County FIPS identifier."],
        ["Hour / timestamp_utc", "Datetime (UTC)", "2015-01-02 to 2023-01-03", "Hourly UTC observation timestamp."],
        ["max_rolling_avg", "Float64", "0.0625 to 840,141.88 (Med: 4.375)", "Hourly 4-hour rolling average of customers without power."],
        ["median_sum", "Float64", "0.3125 to 2,199.06 (Med: 8.875)", "Static county-level baseline outage burden (1 unique value per fips_code)."],
        ["(fips_code, new_event_no)", "Composite Key", "1,374,112 unique episodes", "True observational unit for contiguous county outage episodes."],
        ["evDur_Hr", "Int64", "1 to 3,133 hrs (Episode Med: 4.0h)", "Total duration in hours of the outage episode (episode invariant)."],
        ["Max_outage", "Float64", "0.0625 to 934,675 (Episode Med: 3.19)", "Peak affected customers across the outage episode (episode invariant)."],
        ["source_completeness_pct", "Float64", "6.25% to 100.0% (Mean: 62.01%)", "Hourly telemetry completeness in steps of 1/16 (6.25%)."],
        ["event_mean_completeness_pct", "Float64", "6.25% to 100.0% (Mean: 63.84%)", "Mean telemetry completeness across all hours of the episode."],
        ["WFO", "String", "115 unique 3-letter codes", "Issuing NWS Weather Forecast Office assigned to the county."],
        ["Matched_Events / primary_phenom", "String", "153 combos / 18 base VTEC codes", "Active NWS VTEC phenomenon codes overlapping the county-hour."],
        ["Matched_Count", "Int64", "1 to 5 (86.5% = 1, 13.5% >= 2)", "Number of simultaneous active VTEC weather warnings."],
        ["normalized_peak_severity_ratio", "Float64 (Derived)", "Max_outage / median_sum", "County baseline-normalized peak episode severity ratio."],
        ["target_high_severity_100", "Int32 (Target)", "Binary {0, 1} (12.89% positive)", "1 if episode peak reaches Max_outage >= 100 customers, else 0."],
    ]
    add_formatted_table(
        doc,
        headers=["Variable / Key", "Data Type", "Observed Range / Cardinality", "Empirical Definition"],
        rows=dict_rows,
        col_widths=[1.6, 0.9, 1.5, 2.5],
    )

    # ==========================================================================
    # SECTION 4: SPATIOTEMPORAL OUTAGE ANALYSIS
    # ==========================================================================
    h4 = doc.add_heading("4. Spatiotemporal Outage Analysis", level=1)
    h4.runs[0].font.color.rgb = RGBColor(27, 54, 93)

    doc.add_paragraph(
        "GridPulse strictly distinguishes between (1) warning-matched hourly records (3,572,394 county-hours), "
        "(2) distinct contiguous outage episodes (1,374,112 episodes), (3) peak affected customers (Max_outage), "
        "(4) episode duration (evDur_Hr), and (5) county baseline-normalized severity ratios (Max_outage / median_sum). "
        "Figure 4.1 illustrates the monthly episode trajectory (2015–2022) and the diurnal UTC onset cycle."
    )
    doc.add_picture(str(chart_paths["spatiotemporal"]), width=Inches(6.4))
    cap2 = doc.add_paragraph(
        "Figure 4.1: Left — Monthly count of distinct warning-matched county outage episodes (2015–2022), showing pronounced "
        "summer convective peaks (June–August) and winter storm spikes. Right — Diurnal UTC distribution of warning-matched "
        "outage county-hours, peaking between 20:00 and 23:00 UTC (late afternoon/early evening U.S. local time)."
    )
    cap2.runs[0].italic = True
    cap2.runs[0].font.size = Pt(9)

    # ==========================================================================
    # SECTION 5: WEATHER-WARNING ASSOCIATION & ROBUSTNESS ANALYSIS
    # ==========================================================================
    h5 = doc.add_heading("5. Weather-Warning Association & Robustness Analysis", level=1)
    h5.runs[0].font.color.rgb = RGBColor(27, 54, 93)

    doc.add_paragraph(
        "Because outage records in the harmonized dataset are linked to active NWS VTEC warnings by county/WFO spatiotemporal "
        "overlap, all relationships are reported strictly as observational associations rather than physical causation. "
        "A non-parametric Kruskal-Wallis test across the top 10 warning phenomena confirms highly significant variation in peak "
        f"outage severity (H = {weather_stats['kruskal_wallis_top10_phenoms']['h_statistic']:,.2f}, p < 0.0001). "
        "Furthermore, restricting the sample strictly to episodes with >=75% telemetry completeness yields a Spearman rank "
        f"correlation of ρ = {weather_stats['completeness_rank_robustness']['spearman_rho']:.4f} (p < 0.0001), proving that "
        "hazard severity rankings are highly robust to missing sub-hourly telemetry."
    )

    w_rows = []
    for _, r in weather_df.iterrows():
        hc_val = f"{r['high_comp_prob_ge100_pct']:.2f}%" if pd.notna(r["high_comp_prob_ge100_pct"]) else "N/A"
        w_rows.append(
            [
                str(r["phenomenon_label"]),
                f"{int(r['total_events']):,}",
                f"{float(r['median_max_outage']):.2f}",
                f"{float(r['mean_max_outage']):.2f}",
                f"{float(r['p90_max_outage']):.2f}",
                f"{float(r['mean_duration_hr']):.2f}h",
                f"{float(r['prob_high_severity_ge100_pct']):.2f}%",
                hc_val,
            ]
        )
    add_formatted_table(
        doc,
        headers=[
            "NWS VTEC Phenomenon",
            "Episodes",
            "Med Peak Cust",
            "Mean Peak Cust",
            "P90 Peak Cust",
            "Mean Dur",
            "Prob >=100 (All)",
            "Prob >=100 (>=75% Comp)",
        ],
        rows=w_rows,
        col_widths=[1.55, 0.75, 0.65, 0.75, 0.75, 0.65, 0.7, 0.7],
    )

    doc.add_picture(str(chart_paths["weather"]), width=Inches(6.4))
    cap3 = doc.add_paragraph(
        "Figure 5.1: Left — Probability of an outage episode reaching >=100 customers out across the top 12 VTEC phenomenon codes. "
        "Right — Missing-data robustness scatter comparing all episodes against high-completeness (>=75%) episodes (Spearman ρ = 0.9840)."
    )
    cap3.runs[0].italic = True
    cap3.runs[0].font.size = Pt(9)

    # ==========================================================================
    # SECTION 6: REGIONAL RELIABILITY PROFILING & ARCHETYPE CLUSTERING
    # ==========================================================================
    h6 = doc.add_heading("6. Regional Reliability Profiling & Vulnerability Archetypes", level=1)
    h6.runs[0].font.color.rgb = RGBColor(27, 54, 93)

    doc.add_paragraph(
        "Ranking states or counties by raw outage counts alone is misleading when county count, customer population, and telemetry "
        "completeness differ. GridPulse profiles all 3,010 counties and 49 states/DC by pairing raw burden metrics with county "
        "baseline normalization (Max_outage / median_sum) and telemetry completeness tiers. Using standardized K-Means clustering (k=4), "
        "counties are grouped into four interpretable reliability archetypes:"
    )

    arch_summary = (
        county_df.groupby("reliability_archetype")
        .agg(
            counties=("fips_code", "count"),
            mean_events_per_yr=("events_per_observed_year", "mean"),
            med_norm_ratio=("median_normalized_severity_ratio", "median"),
            mean_high_sev_pct=("high_severity_event_share_pct", "mean"),
            mean_dur_hr=("mean_duration_hr", "mean"),
            mean_comp_pct=("mean_event_completeness_pct", "mean"),
        )
        .reset_index()
    )
    arch_rows = [
        [
            str(r["reliability_archetype"]),
            f"{int(r['counties']):,}",
            f"{float(r['mean_events_per_yr']):.1f}",
            f"{float(r['med_norm_ratio']):.3f}x",
            f"{float(r['mean_high_sev_pct']):.2f}%",
            f"{float(r['mean_dur_hr']):.2f}h",
            f"{float(r['mean_comp_pct']):.2f}%",
        ]
        for _, r in arch_summary.iterrows()
    ]
    add_formatted_table(
        doc,
        headers=[
            "County Reliability Archetype (K-Means k=4)",
            "Counties",
            "Mean Episodes/Yr",
            "Med Peak/Base Ratio",
            "Mean Share >=100",
            "Mean Duration",
            "Mean Completeness",
        ],
        rows=arch_rows,
        col_widths=[2.0, 0.7, 0.8, 0.8, 0.75, 0.7, 0.75],
    )

    doc.add_heading("6.1 Top 15 States by Observed Outage Episode Volume (With Normalization & Coverage Context)", level=2)
    st_rows = []
    for _, r in state_df.head(15).iterrows():
        st_rows.append(
            [
                f"{r['state']} ({r['state_abbr']})",
                f"{int(r['observed_counties'])}",
                f"{int(r['total_outage_events']):,}",
                f"{float(r['events_per_county']):.1f}",
                f"{float(r['median_max_outage']):.2f}",
                f"{float(r['median_normalized_severity_ratio']):.3f}x",
                f"{float(r['high_severity_event_share_pct']):.2f}%",
                f"{float(r['mean_event_completeness_pct']):.2f}%",
                str(r["dominant_weather_phenom"]),
            ]
        )
    add_formatted_table(
        doc,
        headers=[
            "State",
            "Counties",
            "Total Episodes",
            "Episodes / County",
            "Med Peak Cust",
            "Med Norm Ratio",
            "Share >=100 (%)",
            "Mean Comp (%)",
            "Top VTEC",
        ],
        rows=st_rows,
        col_widths=[1.15, 0.55, 0.8, 0.75, 0.65, 0.7, 0.7, 0.65, 0.55],
    )

    # ==========================================================================
    # SECTION 7: PREDICTIVE MODELING & RESEARCH ROBUSTNESS
    # ==========================================================================
    h7 = doc.add_heading("7. Onset-Time Predictive Modeling & Research Robustness", level=1)
    h7.runs[0].font.color.rgb = RGBColor(27, 54, 93)

    doc.add_paragraph(
        "To evaluate whether historical outage behaviour, weather-warning characteristics, and temporal context can predict outage "
        "escalation without future leakage, we formulate a strictly causal onset-time classification task:"
    )
    m_bullets = [
        "Observational Unit & Decision Horizon: County-Outage Episode (fips_code, new_event_no) evaluated at the end of Hour 1 of the episode.",
        "Target Variable (target_high_severity_100): Binary indicator equal to 1 if the episode's eventual peak outage reaches Max_outage >= 100 customers (12.89% base rate across all 1,374,112 episodes).",
        "Chronological Validation Split: Training Set = 2015–2020 (968,968 episodes); Validation Set = 2021 (190,562 episodes, used for F1 threshold tuning); Untouched Final Test Set = 2022 (214,185 episodes).",
        "Strict Leakage Guard (verify_no_leakage): Post-onset variables (Max_outage, evDur_Hr, evDur_day, observed_matched_hours, event_mean_completeness_pct, event_min_completeness_pct, max_matched_count) are programmatically blocked from the feature matrix. Historical county lags (prior_1_max_outage, prior_5_mean_max_outage, prior_5_mean_duration_hr, prior_10_high_sev_rate, hours_since_prior_event) are computed using a strict shift(1) window over prior episodes.",
    ]
    for mb in m_bullets:
        doc.add_paragraph(mb, style="List Bullet")

    doc.add_heading("7.1 Model Benchmark on Validation (2021) and Untouched Test (2022) Sets", level=2)
    mod_rows = []
    for k, m_obj in model_results["models"].items():
        v = m_obj["validation_2021"]
        t = m_obj["test_2022"]
        mod_rows.append(
            [
                m_obj["display_name"],
                f"{v['roc_auc']:.4f}",
                f"{t['roc_auc']:.4f}",
                f"{t['pr_auc']:.4f}",
                f"{t['f1_score']:.4f}",
                f"{t['precision']:.4f}",
                f"{t['recall']:.4f}",
                f"{t['brier_score']:.4f}",
            ]
        )
    add_formatted_table(
        doc,
        headers=[
            "Model / Baseline",
            "Val 2021 ROC-AUC",
            "Test 2022 ROC-AUC",
            "Test 2022 PR-AUC",
            "Test 2022 F1",
            "Test 2022 Precision",
            "Test 2022 Recall",
            "Test 2022 Brier",
        ],
        rows=mod_rows,
        col_widths=[1.85, 0.65, 0.68, 0.68, 0.62, 0.68, 0.65, 0.65],
    )

    doc.add_picture(str(chart_paths["modeling"]), width=Inches(6.4))
    cap4 = doc.add_paragraph(
        "Figure 7.1: Left — Permutation feature importance (mean ROC-AUC drop on 2022 test set) for HistGradientBoostingClassifier. "
        "Right — Probability calibration curve on the untouched 2022 test set (N = 214,185 episodes, Brier score = 0.0664). "
        "Note: Feature importance measures predictive contribution within the model and is not proof of physical causation."
    )
    cap4.runs[0].italic = True
    cap4.runs[0].font.size = Pt(9)

    doc.add_heading("7.2 Subgroup Robustness & Error Analysis on 2022 Test Set", level=2)
    sub_rows = []
    for grp_type, grp_list in [
        ("Completeness Tier", model_results["subgroup_robustness_test_2022"]["by_completeness_tier"]),
        ("Season", model_results["subgroup_robustness_test_2022"]["by_season"]),
    ]:
        for s_item in grp_list:
            sub_rows.append(
                [
                    grp_type,
                    str(s_item["subgroup"]),
                    f"{int(s_item['n_samples']):,}",
                    f"{float(s_item['positive_rate'])*100:.2f}%",
                    f"{float(s_item['roc_auc']):.4f}",
                    f"{float(s_item['pr_auc']):.4f}",
                    f"{float(s_item['f1_score']):.4f}",
                    f"{float(s_item['brier_score']):.4f}",
                ]
            )
    add_formatted_table(
        doc,
        headers=[
            "Subgroup Dimension",
            "Stratum",
            "2022 Test Episodes",
            "Base Rate (>=100)",
            "ROC-AUC",
            "PR-AUC",
            "F1-Score",
            "Brier Score",
        ],
        rows=sub_rows,
        col_widths=[1.2, 1.3, 0.9, 0.8, 0.6, 0.6, 0.55, 0.55],
    )

    # ==========================================================================
    # SECTION 8: LIMITATIONS, ETHICS & REPRODUCIBLE EXECUTION GUIDE
    # ==========================================================================
    h8 = doc.add_heading("8. Methodological Limitations, Ethics & Execution Guide", level=1)
    h8.runs[0].font.color.rgb = RGBColor(27, 54, 93)

    lim_bullets = [
        "Selection on Positive Warning-Matched Outages: Eagle_I_US_2024_with_VTEC_Updated.csv includes only county-hours with both a non-zero outage and an active weather warning. It cannot estimate unconditional clear-sky outage probability or the fraction of weather warnings that cause zero outages.",
        "Telemetry Missingness & Under-Reporting Bias: Absent 15-minute utility polls are never treated as confirmed zero outages. Low completeness (<50%) suppresses observed peak outage counts (75.0% median relative difference in the sensitivity benchmark and 9.63% vs. 24.60% positive base rate in the 2022 test set).",
        "Excel Truncation in Availability File: EAGLEI_Source_Record_Availability.csv is truncated at 1,048,575 rows (288 counties). Full-nation coverage context therefore relies on the in-sample source_completeness_pct and event_mean_completeness_pct fields.",
        "Denominator & Equity Guardrail: Because external utility customer-served denominators (e.g., EIA-861 total meters per county) are not bundled, metrics are presented as both raw counts and county baseline-normalized ratios (Max_outage / median_sum) alongside explicit coverage confidence tiers so rural counties with sparse telemetry are never misclassified as 'immune' to grid failures.",
    ]
    for lb in lim_bullets:
        doc.add_paragraph(lb, style="List Bullet")

    doc.add_heading("8.1 Commands to Run Pipeline, Unit Tests, and Streamlit Dashboard", level=2)
    cmd_rows = [
        ["1. Install Dependencies", "pip install -r requirements.txt"],
        ["2. Run Automated Test Suite (9 Pytest Tests)", "pytest tests/ -v"],
        ["3. Run Complete End-to-End Pipeline (~60s)", "python scripts/run_pipeline.py --stage all"],
        ["4. Run Individual Pipeline Stages", "python scripts/run_pipeline.py --stage audit|preprocess|features|analyze|model|report"],
        ["5. Regenerate Word (.docx) Report", "python scripts/generate_word_report.py"],
        ["6. Launch Interactive 8-Page Streamlit App", "streamlit run app.py"],
    ]
    add_formatted_table(
        doc,
        headers=["Workflow Action", "Exact Command"],
        rows=cmd_rows,
        col_widths=[2.5, 4.0],
    )

    out_root = PROJECT_ROOT / "GridPulse_Complete_Research_Report.docx"
    out_reports = PROJECT_ROOT / "outputs" / "reports" / "GridPulse_Complete_Research_Report.docx"
    doc.save(str(out_root))
    doc.save(str(out_reports))
    print(f"Successfully generated Word report at:\n  1) {out_root}\n  2) {out_reports}")
    return out_root


if __name__ == "__main__":
    build_word_document()
