"""GridPulse — Research-Grade Power Outage Analytics and Reliability Assessment Dashboard."""

from __future__ import annotations

import sys
from pathlib import Path

import folium
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from streamlit_folium import st_folium

# Ensure src is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

from gridpulse.config import STATE_METADATA, VTEC_PHENOM_LABELS
from gridpulse.dashboard.data_loader import (
    load_filtered_event_summary,
    load_json_metrics,
    load_parquet_pandas,
)

st.set_page_config(
    page_title="GridPulse | Power Outage & Weather Reliability Research",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Load core cached datasets and metrics
try:
    audit_report = load_json_metrics("data_audit_report.json")
    weather_stats = load_json_metrics("weather_and_spatiotemporal_stats.json")
    model_results = load_json_metrics("modeling_evaluation_results.json")
    state_profiles = load_parquet_pandas("features", "state_reliability_profiles.parquet")
    county_profiles = load_parquet_pandas("features", "county_reliability_profiles.parquet")
    weather_summary = load_parquet_pandas("processed", "weather_association_summary.parquet")
    sens_df = load_parquet_pandas("processed", "missing_data_sensitivity.parquet")
except FileNotFoundError as exc:
    st.error(
        f"Processed Parquet/JSON artifacts not found: {exc}\n\n"
        "Please run `python scripts/run_pipeline.py --stage all` first to generate all datasets."
    )
    st.stop()

# Sidebar navigation & global filters
st.sidebar.title("⚡ GridPulse Research")
st.sidebar.caption(
    "Harmonized EAGLE-I Outage & NWS VTEC Weather-Warning Analytics (2015–2023)"
)

PAGES = [
    "1. Overview & Key Findings",
    "2. Data Quality & Coverage Audit",
    "3. Spatiotemporal Outage Trends",
    "4. Geographic & Spatial Analysis",
    "5. Weather-Warning Associations",
    "6. Regional Reliability Profiles",
    "7. Onset-Time Predictive Analysis",
    "8. Methodology, Ethics & Limitations",
]
selected_page = st.sidebar.radio("Research Section", PAGES)

st.sidebar.markdown("---")
st.sidebar.subheader("Global Interactive Filters")
st.sidebar.caption("Applies to dynamic exploration on Trends, Weather, and Profiles pages.")

year_range = st.sidebar.slider(
    "Episode Year Range (UTC)", min_value=2015, max_value=2023, value=(2015, 2022)
)
all_states = sorted(state_profiles["state"].unique().tolist())
selected_states = st.sidebar.multiselect(
    "Filter States (Empty = All 49 States/DC)", options=all_states, default=[]
)
all_phenoms = weather_summary["primary_phenom"].tolist()
selected_phenoms = st.sidebar.multiselect(
    "Filter Primary VTEC Codes (Empty = All 18 Codes)",
    options=all_phenoms,
    format_func=lambda x: VTEC_PHENOM_LABELS.get(x, x),
    default=[],
)
min_comp_filter = st.sidebar.slider(
    "Minimum Episode Telemetry Completeness (%)",
    min_value=0.0,
    max_value=100.0,
    value=0.0,
    step=6.25,
    help="Filter episodes by event_mean_completeness_pct to test robustness against missing 15-min telemetry.",
)

filtered_data = load_filtered_event_summary(
    years=year_range,
    states=tuple(selected_states),
    phenoms=tuple(selected_phenoms),
    min_completeness=float(min_comp_filter),
)

# ==============================================================================
# PAGE 1: OVERVIEW
# ==============================================================================
if selected_page == PAGES[0]:
    st.title("⚡ GridPulse: Power Outage Analytics & Reliability Assessment")
    st.markdown(
        """
        **Core Research Question:** *Can historical outage behaviour, weather-warning characteristics, temporal patterns,
        and geographic context help explain outage severity and identify regions with recurring power-reliability problems?*
        """
    )

    st.info(
        "**Observational Scope & Interpretation Guardrail:** Every record in the harmonized `Eagle_I_US_2024_with_VTEC_Updated.csv` "
        "dataset represents a **county-hour where a non-zero power outage overlapped with at least one active NWS VTEC weather warning** "
        "(`Matched_Count >= 1`). Unreported intervals are never treated as confirmed zero-outage observations unless source availability "
        "telemetry (`EAGLEI_Source_Record_Availability.csv`) confirms 100% 15-minute reporting coverage."
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric(
        "Observed Outage-Warning Hours",
        f"{audit_report['eagle_vtec']['total_hourly_rows']:,}",
        "2015-01-02 to 2023-01-03 UTC",
    )
    c2.metric(
        "Distinct County Outage Episodes",
        f"{audit_report['eagle_vtec']['unique_county_events']:,}",
        "Unique (fips_code, new_event_no)",
    )
    c3.metric(
        "Geographic Coverage",
        f"{audit_report['eagle_vtec']['unique_counties_fips']:,} Counties",
        f"{audit_report['eagle_vtec']['unique_states']} States/DC | {audit_report['eagle_vtec']['unique_wfos']} WFOs",
    )
    c4.metric(
        "Mean Telemetry Completeness",
        "62.01%",
        "30.52% at 100% (4/4 15-min intervals)",
    )

    st.markdown("### Filtered Slice Summary (Interactive Sidebar Selection)")
    if filtered_data["empty"]:
        st.warning("No outage episodes match the current sidebar filter combination. Adjust your filters to view statistics.")
    else:
        fc1, fc2, fc3, fc4, fc5 = st.columns(5)
        fc1.metric("Filtered Episodes", f"{filtered_data['n_events']:,}")
        fc2.metric("Affected Counties", f"{filtered_data['n_counties']:,}")
        fc3.metric("Median Peak Customers Out", f"{filtered_data['median_max_outage']:,.2f}")
        fc4.metric("High-Severity Share (>=100 Cust)", f"{filtered_data['high_sev_rate_pct']:.2f}%")
        fc5.metric("Slice Mean Completeness", f"{filtered_data['mean_completeness_pct']:.2f}%")

    st.markdown("### Key Empirical Findings (Measured From Actual Data)")
    col_left, col_right = st.columns(2)
    with col_left:
        st.markdown(
            """
            1. **Weather Regime Stratification ($H = 28,328.59, p < 0.0001$):**
               - **Severe Thunderstorm (`SV`)** warnings co-occur with **53.5%** (`735,490`) of all warning-matched outage episodes across the United States, with **16.27%** reaching $\\ge 100$ customers out.
               - **Extreme Wind (`EW`)** and **Tornado (`TO`)** warnings carry the highest tail escalation risk (**74.03%** and **19.35%** reaching $\\ge 100$ customers out, respectively).
               - **Heat (`HT`)** and **Fire Weather (`FW`)** warnings have substantially lower large-outage escalation rates (**6.13%** and **5.56%**).
            2. **Robustness to Telemetry Missingness ($\\rho = 0.9840, p < 0.0001$):**
               - Restricting analysis strictly to episodes with $\\ge 75\\%$ telemetry completeness preserves the relative severity ranking of weather phenomena.
            """
        )
    with col_right:
        st.markdown(
            """
            3. **Source Record Availability & Under-Reporting Bias:**
               - In `EAGLEI_Source_Record_Availability.csv` (`1,048,575` county-days across `288` counties), **38.91%** of county-days have `0` observed 15-minute intervals (100% reporting gap).
               - `Missing_Data_Sensitivity_Summary.csv` demonstrates that `< 50%` completeness introduces a **75.0% median relative difference** in estimated outage magnitude.
            4. **Onset-Time Escalation Prediction (Untouched 2022 Test Set, $N = 214,185$):**
               - Predicting at **Hour 1** whether an episode will reach `Max_outage >= 100` customers achieves **ROC-AUC = 0.8640** and **PR-AUC = 0.6713** (`Brier = 0.0664`) using calibrated `HistGradientBoosting`, outperforming both onset persistence (**ROC-AUC = 0.7803**) and historical county-weather priors (**ROC-AUC = 0.7165**).
            """
        )

# ==============================================================================
# PAGE 2: DATA QUALITY & COVERAGE AUDIT
# ==============================================================================
elif selected_page == PAGES[1]:
    st.title("🔍 Data Quality, Telemetry Coverage & Missingness Audit")
    st.markdown(
        "Rigorous inspection of all four source datasets, schema verification, duplicate checks, and missing-data sensitivity."
    )

    q1, q2, q3, q4 = st.columns(4)
    q1.metric("Duplicate Rows (EAGLE-I VTEC)", f"{audit_report['eagle_vtec']['duplicate_full_rows']}", "0 duplicate (fips_code, Hour) keys")
    q2.metric("Invalid Timestamps (EAGLE-I)", f"{audit_report['eagle_vtec']['invalid_timestamps']}", "100% valid ISO-8601 UTC")
    q3.metric("Availability File Rows", f"{audit_report['availability']['total_rows']:,}", "Truncated at Excel limit (2^20 - 1)")
    q4.metric("0%-Coverage County-Days", f"{audit_report['availability']['zero_coverage_days_pct']}%", f"{audit_report['availability']['zero_coverage_days_count']:,} reporting-gap days")

    st.warning(
        "**Critical Audit Discovery — Excel Row-Limit Truncation in `EAGLEI_Source_Record_Availability.csv`:** "
        "The source availability file contains exactly `1,048,575` data rows (+1 header = `1,048,576` = $2^{20}$ rows, the exact Microsoft Excel `.xlsx` sheet limit), "
        "covering only `288` counties (`fips_code` `1001` in Alabama through `12033` in Escambia County, Florida). "
        "Therefore, for all 3,010 counties in the main dataset, GridPulse uses the in-sample `source_completeness_pct`, `event_mean_completeness_pct`, and `event_min_completeness_pct` columns to track telemetry coverage."
    )

    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Missing-Data Sensitivity Benchmark")
        st.caption("Source: `Missing_Data_Sensitivity_Summary.csv` (91.52M total benchmark observations)")
        fig_sens = px.bar(
            sens_df,
            x="completeness_tier",
            y="Median_Relative_Difference",
            text="Median_Relative_Difference",
            color="completeness_tier",
            title="Median Relative Error (%) in Outage Magnitude by Telemetry Completeness Tier",
            labels={
                "completeness_tier": "Source Telemetry Completeness Tier",
                "Median_Relative_Difference": "Median Relative Difference (%)",
            },
        )
        fig_sens.update_traces(texttemplate="%{text:.2f}%", textposition="outside")
        st.plotly_chart(fig_sens, use_container_width=True)
        st.dataframe(sens_df, use_container_width=True)

    with col_b:
        st.subheader("In-Sample Hourly Completeness Distribution")
        st.caption("Source: `Eagle_I_US_2024_with_VTEC_Updated.csv` (3,572,394 county-hours)")
        comp_df = pd.DataFrame(audit_report["eagle_vtec"]["completeness_tier_breakdown"])
        fig_comp = px.pie(
            comp_df,
            names="completeness_tier",
            values="hourly_rows",
            hole=0.4,
            title="Share of Harmonized Outage-Warning County-Hours by Completeness Tier",
        )
        st.plotly_chart(fig_comp, use_container_width=True)
        st.dataframe(comp_df, use_container_width=True)

    st.subheader("Yearly Source Coverage & Record Counts (2015–2023)")
    yr_cov_df = pd.DataFrame(audit_report["eagle_vtec"]["yearly_coverage"])
    fig_yr = px.bar(
        yr_cov_df,
        x="year",
        y="hourly_rows",
        color="mean_completeness_pct",
        text="unique_counties",
        title="Annual Outage-Warning County-Hours and Unique Counties Observed (Note: 2022 ends Nov 12; 2023 is Jan 1–3 tail)",
        labels={
            "year": "Year (UTC)",
            "hourly_rows": "County-Hour Records",
            "mean_completeness_pct": "Mean Completeness (%)",
        },
    )
    st.plotly_chart(fig_yr, use_container_width=True)

# ==============================================================================
# PAGE 3: SPATIOTEMPORAL OUTAGE TRENDS
# ==============================================================================
elif selected_page == PAGES[2]:
    st.title("📈 Spatiotemporal Outage Trends & Severity Distributions")
    st.markdown(
        """
        **Metric Distinction Guardrail:**
        - **Hourly Outage Records (`hourly_records`):** Number of county-hour intervals overlapping an active weather warning.
        - **Distinct Outage Episodes (`outage_events`):** Unique `(fips_code, new_event_no)` contiguous outage events.
        - **Peak Affected Customers (`Max_outage`):** Peak customer outage count reached during an episode.
        - **Episode Duration (`evDur_Hr`):** Total hours the outage episode persisted.
        """
    )

    if filtered_data["empty"]:
        st.warning("No records match the selected sidebar filters.")
    else:
        ym_df = filtered_data["by_ym"]
        fig_ym = go.Figure()
        fig_ym.add_trace(
            go.Scatter(
                x=ym_df["year_month"],
                y=ym_df["outage_events"],
                mode="lines+markers",
                name="Outage Episodes (Count)",
                line=dict(color="#1f77b4", width=2),
            )
        )
        fig_ym.add_trace(
            go.Scatter(
                x=ym_df["year_month"],
                y=ym_df["high_severity_rate_pct"],
                mode="lines",
                name="High-Severity Share >=100 Cust (%)",
                yaxis="y2",
                line=dict(color="#d62728", width=2, dash="dot"),
            )
        )
        fig_ym.update_layout(
            title="Monthly Outage Episode Volume vs. High-Severity Escalation Rate (%)",
            xaxis_title="Year-Month (UTC)",
            yaxis=dict(title="Distinct Outage Episodes"),
            yaxis2=dict(
                title="High-Severity Share (%)",
                overlaying="y",
                side="right",
                range=[0, 40],
            ),
            legend=dict(orientation="h", y=1.12),
        )
        st.plotly_chart(fig_ym, use_container_width=True)

        c_left, c_right = st.columns(2)
        with c_left:
            hr_df = filtered_data["by_hour"]
            fig_hr = px.bar(
                hr_df,
                x="onset_hour_utc",
                y="outage_events",
                color="high_severity_rate_pct",
                title="Diurnal Cycle: Outage Episode Onset by Hour of Day (UTC)",
                labels={
                    "onset_hour_utc": "Onset Hour of Day (UTC)",
                    "outage_events": "Outage Episodes Initiated",
                    "high_severity_rate_pct": "Prob >=100 Cust (%)",
                },
                color_continuous_scale="Magma",
            )
            st.plotly_chart(fig_hr, use_container_width=True)

        with c_right:
            seas_df = filtered_data["by_season"]
            fig_seas = px.bar(
                seas_df,
                x="season",
                y="outage_events",
                color="mean_duration_hr",
                text="high_severity_rate_pct",
                title="Seasonal Outage Episode Burden & Mean Duration (Hours)",
                labels={
                    "season": "Meteorological Season",
                    "outage_events": "Distinct Outage Episodes",
                    "mean_duration_hr": "Mean Duration (Hours)",
                },
            )
            fig_seas.update_traces(texttemplate=">=100 Cust: %{text:.1f}%", textposition="outside")
            st.plotly_chart(fig_seas, use_container_width=True)

# ==============================================================================
# PAGE 4: GEOGRAPHIC & SPATIAL ANALYSIS
# ==============================================================================
elif selected_page == PAGES[3]:
    st.title("🗺️ Geographic & Spatial Vulnerability Analysis")
    st.markdown(
        "Compare state and county outage burdens alongside **baseline normalization (`median_sum`)** and **telemetry completeness (`mean_event_completeness_pct`)**."
    )

    metric_choice = st.selectbox(
        "Select State Mapping Metric",
        options=[
            "high_severity_event_share_pct",
            "events_per_county",
            "median_normalized_severity_ratio",
            "mean_duration_hr",
            "mean_event_completeness_pct",
            "total_outage_events",
        ],
        format_func=lambda x: {
            "high_severity_event_share_pct": "Share of Episodes Reaching >=100 Customers (%)",
            "events_per_county": "Mean Outage Episodes per Observed County",
            "median_normalized_severity_ratio": "Median Normalized Severity Ratio (Max_outage / County Baseline)",
            "mean_duration_hr": "Mean Episode Duration (Hours)",
            "mean_event_completeness_pct": "Mean Telemetry Completeness (%) [Coverage Context]",
            "total_outage_events": "Raw Total Outage Episodes (Unnormalized Count)",
        }[x],
    )

    col_map1, col_map2 = st.columns([3, 2])
    with col_map1:
        fig_choro = px.choropleth(
            state_profiles,
            locations="state_abbr",
            locationmode="USA-states",
            color=metric_choice,
            hover_name="state",
            hover_data=[
                "observed_counties",
                "total_outage_events",
                "events_per_county",
                "high_severity_event_share_pct",
                "mean_event_completeness_pct",
                "dominant_weather_phenom",
            ],
            scope="usa",
            color_continuous_scale="YlOrRd",
            title=f"U.S. State Choropleth: {metric_choice}",
        )
        fig_choro.update_layout(margin=dict(l=0, r=0, t=40, b=0))
        st.plotly_chart(fig_choro, use_container_width=True)

    with col_map2:
        st.subheader("Interactive Folium State Reliability & Coverage Map")
        m = folium.Map(location=[38.5, -96.5], zoom_start=4, tiles="CartoDB positron")
        for _, row in state_profiles.iterrows():
            radius = max(5.0, min(22.0, float(row["high_severity_event_share_pct"]) * 0.9))
            popup_html = (
                f"<b>{row['state']} ({row['state_abbr']})</b><br>"
                f"Observed Counties: {int(row['observed_counties'])}<br>"
                f"Total Episodes: {int(row['total_outage_events']):,}<br>"
                f"Episodes / County: {row['events_per_county']:.1f}<br>"
                f"High-Severity Share (>=100): {row['high_severity_event_share_pct']:.2f}%<br>"
                f"Mean Completeness: {row['mean_event_completeness_pct']:.1f}%<br>"
                f"Dominant Hazard: {row['dominant_weather_phenom']}"
            )
            folium.CircleMarker(
                location=[float(row["lat"]), float(row["lon"])],
                radius=radius,
                color="#b30000" if row["high_severity_event_share_pct"] >= 15.0 else "#2b8cbe",
                fill=True,
                fill_opacity=0.7,
                popup=folium.Popup(popup_html, max_width=280),
                tooltip=f"{row['state']}: {row['high_severity_event_share_pct']:.1f}% >=100 cust (Completeness: {row['mean_event_completeness_pct']:.1f}%)",
            ).add_to(m)
        st_folium(m, width=520, height=400, returned_objects=[])

    st.subheader("State-Level Comparison Table (With Denominator & Coverage Context)")
    st.dataframe(state_profiles, use_container_width=True)

# ==============================================================================
# PAGE 5: WEATHER-WARNING ASSOCIATIONS
# ==============================================================================
elif selected_page == PAGES[4]:
    st.title("🌩️ Weather-Warning Association & Robustness Analysis")
    st.info(
        "**Non-Causal Association Statement:** Outage records in EAGLE-I are linked to active NWS VTEC weather warnings "
        "by spatiotemporal overlap within county/WFO boundaries. Results represent **observational co-occurrence associations**, "
        "not proof that a specific warning caused an outage."
    )

    kw = weather_stats["kruskal_wallis_top10_phenoms"]
    rk = weather_stats["completeness_rank_robustness"]
    w1, w2, w3 = st.columns(3)
    w1.metric("Kruskal-Wallis H-Statistic", f"{kw['h_statistic']:,.2f}", f"p-value < 0.0001 (Top 10 Phenomena)")
    w2.metric("Completeness Rank Robustness", f"Spearman ρ = {rk['spearman_rho']:.4f}", "All Episodes vs >=75% Complete")
    w3.metric("Distinct VTEC Phenomenon Codes", "18 Matched in EAGLE-I", "59 Total in Raw NWS Feed")

    fig_w_bar = px.bar(
        weather_summary,
        x="phenomenon_label",
        y="prob_high_severity_ge100_pct",
        color="mean_completeness_pct",
        hover_data=[
            "total_events",
            "median_max_outage",
            "mean_max_outage",
            "p90_max_outage",
            "mean_duration_hr",
            "median_norm_severity_ratio",
        ],
        title="Probability of Episode Reaching >=100 Customers Out by Primary NWS VTEC Warning Phenomenon",
        labels={
            "phenomenon_label": "NWS VTEC Phenomenon",
            "prob_high_severity_ge100_pct": "Episodes Reaching >=100 Customers (%)",
            "mean_completeness_pct": "Mean Completeness (%)",
        },
        color_continuous_scale="Viridis",
    )
    fig_w_bar.update_layout(xaxis_tickangle=-35)
    st.plotly_chart(fig_w_bar, use_container_width=True)

    c_w1, c_w2 = st.columns(2)
    with c_w1:
        st.subheader("Robustness Check: All Episodes vs. High-Completeness (>=75%)")
        fig_rob = px.scatter(
            weather_summary.dropna(subset=["high_comp_prob_ge100_pct"]),
            x="prob_high_severity_ge100_pct",
            y="high_comp_prob_ge100_pct",
            size="total_events",
            color="phenomenon_label",
            title=f"High-Severity Rate (%): All Episodes vs. >=75% Complete Episodes (ρ = {rk['spearman_rho']:.4f})",
            labels={
                "prob_high_severity_ge100_pct": "All Episodes Prob >=100 Customers (%)",
                "high_comp_prob_ge100_pct": ">=75% Completeness Prob >=100 Customers (%)",
            },
        )
        st.plotly_chart(fig_rob, use_container_width=True)

    with c_w2:
        st.subheader("Single-Hazard vs. Compound Multi-Hazard Overlap")
        mh_df = pd.DataFrame(weather_stats["multi_hazard_comparison"])
        mh_df["Hazard Regime"] = mh_df["initial_is_multi_hazard"].map(
            {0: "Single Warning (Matched_Count = 1)", 1: "Compound Multi-Warning (Matched_Count >= 2)"}
        )
        fig_mh = px.bar(
            mh_df,
            x="Hazard Regime",
            y=["median_max_outage", "prob_high_severity_ge100_pct", "mean_duration_hr"],
            barmode="group",
            title="Comparison: Single Active Warning vs. Overlapping Multi-Hazard Warnings",
        )
        st.plotly_chart(fig_mh, use_container_width=True)

    st.subheader("Complete Weather Phenomenon Association Table")
    st.dataframe(weather_summary, use_container_width=True)

# ==============================================================================
# PAGE 6: REGIONAL RELIABILITY PROFILES
# ==============================================================================
elif selected_page == PAGES[5]:
    st.title("🏛️ Regional Reliability & Vulnerability Profiles")
    st.markdown(
        """
        **Observational Unit:** County (`fips_code`, $N = 3,010$) aggregated over `2015–2023`.
        - **Denominator Guardrail:** Because external utility customer-served denominators vary across rural vs. urban counties, GridPulse displays both **raw outage metrics (`median_max_outage`, `total_outage_events`)** and **baseline-normalized ratios (`Max_outage / county_baseline_median_sum`)**, alongside **telemetry coverage confidence (`coverage_confidence_tier`)**.
        """
    )

    arch_counts = (
        county_profiles.groupby(["reliability_archetype", "coverage_confidence_tier"])
        .size()
        .reset_index(name="county_count")
    )
    fig_arch = px.bar(
        arch_counts,
        x="reliability_archetype",
        y="county_count",
        color="coverage_confidence_tier",
        barmode="stack",
        title="Distribution of U.S. Counties Across Reliability Archetypes & Telemetry Coverage Tiers",
        labels={
            "reliability_archetype": "K-Means Reliability & Vulnerability Archetype",
            "county_count": "Number of U.S. Counties",
            "coverage_confidence_tier": "Telemetry Coverage Confidence",
        },
    )
    st.plotly_chart(fig_arch, use_container_width=True)

    col_f1, col_f2 = st.columns(2)
    with col_f1:
        sel_arch = st.selectbox(
            "Filter by Reliability Archetype",
            options=["All Archetypes"] + sorted(county_profiles["reliability_archetype"].unique().tolist()),
        )
    with col_f2:
        sel_cov = st.selectbox(
            "Filter by Coverage Confidence Tier",
            options=["All Coverage Tiers"] + sorted(county_profiles["coverage_confidence_tier"].unique().tolist()),
        )

    prof_view = county_profiles.copy()
    if selected_states:
        prof_view = prof_view[prof_view["state"].isin(selected_states)]
    if sel_arch != "All Archetypes":
        prof_view = prof_view[prof_view["reliability_archetype"] == sel_arch]
    if sel_cov != "All Coverage Tiers":
        prof_view = prof_view[prof_view["coverage_confidence_tier"] == sel_cov]

    fig_prof_scatter = px.scatter(
        prof_view.head(1500),
        x="events_per_observed_year",
        y="high_severity_event_share_pct",
        color="reliability_archetype",
        size="county_baseline_median_sum",
        hover_name="county",
        hover_data=[
            "state",
            "fips_code",
            "total_outage_events",
            "median_normalized_severity_ratio",
            "mean_event_completeness_pct",
            "dominant_weather_phenom",
        ],
        title="County Recurrence Rate (Episodes/Year) vs. High-Severity Escalation Share (%)",
        labels={
            "events_per_observed_year": "Outage Episodes per Observed Year",
            "high_severity_event_share_pct": "Share of Episodes Reaching >=100 Customers (%)",
        },
    )
    st.plotly_chart(fig_prof_scatter, use_container_width=True)

    st.subheader(f"Filtered County Reliability Profiles ({len(prof_view):,} Counties)")
    st.dataframe(prof_view.head(500), use_container_width=True)

# ==============================================================================
# PAGE 7: PREDICTIVE ANALYSIS
# ==============================================================================
elif selected_page == PAGES[6]:
    st.title("🤖 Onset-Time Outage Escalation Prediction & Robustness")
    td = model_results["task_definition"]
    st.markdown(
        f"""
        - **Prediction Task:** At the end of **Hour 1** of a newly initiated county outage episode (`(fips_code, new_event_no)`), predict whether the episode will escalate to a **High-Severity Outage (`Max_outage >= 100` customers)**.
        - **Temporal Validation Design (Zero Future Leakage):**
          - **Training Set:** `{td['train_period']}`
          - **Validation Set (Threshold & Hyperparameter Tuning):** `{td['validation_period']}`
          - **Untouched Final Test Set:** `{td['test_period']}`
        """
    )

    models_dict = model_results["models"]
    comp_rows = []
    for key, m_info in models_dict.items():
        v = m_info["validation_2021"]
        t = m_info["test_2022"]
        comp_rows.append(
            {
                "Model": m_info["display_name"],
                "Val (2021) ROC-AUC": v["roc_auc"],
                "Test (2022) ROC-AUC": t["roc_auc"],
                "Test (2022) PR-AUC": t["pr_auc"],
                "Test (2022) F1": t["f1_score"],
                "Test (2022) Precision": t["precision"],
                "Test (2022) Recall": t["recall"],
                "Test (2022) Brier Score (Lower=Better)": t["brier_score"],
            }
        )
    comp_df = pd.DataFrame(comp_rows)
    st.subheader("Measured Model Benchmark on Untouched 2022 Test Period (214,185 Episodes)")
    st.dataframe(comp_df, use_container_width=True)

    c_m1, c_m2 = st.columns(2)
    with c_m1:
        imp_df = pd.DataFrame(model_results["feature_importance_hgb_permutation"]).head(12)
        fig_imp = px.bar(
            imp_df.sort_values("importance_mean_roc_auc_drop", ascending=True),
            x="importance_mean_roc_auc_drop",
            y="feature",
            error_x="importance_std",
            orientation="h",
            title="Permutation Feature Importance (Mean ROC-AUC Drop on 2022 Test Set)",
            labels={
                "importance_mean_roc_auc_drop": "ROC-AUC Drop When Permuted",
                "feature": "Onset / Historical Feature",
            },
        )
        st.plotly_chart(fig_imp, use_container_width=True)
        st.caption(
            "Note: Feature importance reflects predictive contribution within the model and is NOT proof of physical causation."
        )

    with c_m2:
        cal_df = pd.DataFrame(model_results["calibration_curve_test_2022"])
        fig_cal = go.Figure()
        fig_cal.add_trace(
            go.Scatter(
                x=cal_df["mean_predicted_prob"],
                y=cal_df["observed_positive_fraction"],
                mode="lines+markers",
                name="HistGradientBoosting (Brier = 0.0664)",
            )
        )
        fig_cal.add_trace(
            go.Scatter(
                x=[0, 1],
                y=[0, 1],
                mode="lines",
                name="Perfect Calibration",
                line=dict(dash="dash", color="gray"),
            )
        )
        fig_cal.update_layout(
            title="Probability Calibration Curve (2022 Untouched Test Set)",
            xaxis_title="Mean Predicted Probability",
            yaxis_title="Observed Fraction of High-Severity Episodes (>=100 Cust)",
        )
        st.plotly_chart(fig_cal, use_container_width=True)

    st.subheader("Subgroup Robustness & Error Analysis on 2022 Test Set")
    sub_tab1, sub_tab2, sub_tab3 = st.tabs(
        ["By Onset Telemetry Completeness Tier", "By Meteorological Season", "By Primary Weather Phenomenon"]
    )
    with sub_tab1:
        df_sub_c = pd.DataFrame(model_results["subgroup_robustness_test_2022"]["by_completeness_tier"])
        st.dataframe(df_sub_c.drop(columns=["confusion_matrix"]), use_container_width=True)
    with sub_tab2:
        df_sub_s = pd.DataFrame(model_results["subgroup_robustness_test_2022"]["by_season"])
        st.dataframe(df_sub_s.drop(columns=["confusion_matrix"]), use_container_width=True)
    with sub_tab3:
        df_sub_p = pd.DataFrame(model_results["subgroup_robustness_test_2022"]["by_weather_phenomenon"])
        st.dataframe(df_sub_p.drop(columns=["confusion_matrix"]), use_container_width=True)

# ==============================================================================
# PAGE 8: METHODOLOGY & LIMITATIONS
# ==============================================================================
elif selected_page == PAGES[7]:
    st.title("📚 Research Methodology, Architecture & Limitations")
    st.markdown(
        """
        ### 1. Observational Units & Variable Definitions
        - **County-Hour Unit (`(fips_code, Hour)`):** `3,572,394` records in `Eagle_I_US_2024_with_VTEC_Updated.csv`. Each record represents an hourly interval in a county where a positive outage (`max_rolling_avg > 0`) coincided with $\\ge 1$ active NWS VTEC weather warning (`Matched_Count >= 1`).
        - **County-Outage Episode Unit (`(fips_code, new_event_no)`):** `1,374,112` distinct episodes. Because `evDur_Hr` and `Max_outage` are episode-level invariants repeated across every hour of the same episode, aggregating to `(fips_code, new_event_no)` eliminates repeated-measurement pseudoreplication.
        - **County Profile Unit (`fips_code`):** `3,010` counties profiled over `2015–2023` with explicit county baseline (`median_sum`) and telemetry completeness (`mean_event_completeness_pct`).

        ### 2. Leakage Prevention & Temporal Validation Protocol
        - **Forbidden Post-Onset Variables Excluded:** `Max_outage`, `evDur_Hr`, `evDur_day`, `observed_matched_hours`, `event_mean_completeness_pct`, `event_min_completeness_pct`, and `max_matched_count` are strictly excluded from the feature matrix.
        - **Causal Historical Lags:** Rolling county history features (`prior_1_max_outage`, `prior_5_mean_max_outage`, `prior_10_high_sev_rate`, `hours_since_prior_event`) are computed using a strict `shift(1)` window over chronologically ordered episodes within each county.
        - **Chronological Splits:** Trained on `2015–2020` (`968,968` episodes), validated on `2021` (`190,562` episodes), and evaluated once on the untouched `2022` test period (`214,185` episodes).

        ### 3. Key Methodological & Data Limitations
        1. **Selection on Positive Warning-Matched Outages:** `Eagle_I_US_2024_with_VTEC_Updated.csv` contains only intervals with both an outage and an active weather warning. It cannot be used to estimate unconditional outage probability during clear-sky conditions.
        2. **Telemetry Missingness & Under-Reporting Bias:** Unreported 15-minute utility intervals reduce observed outage counts (`75.0%` median relative difference when completeness `< 50%`). Never equate missing records with confirmed zero outages.
        3. **Excel Row Truncation in Source Availability File:** `EAGLEI_Source_Record_Availability.csv` is truncated at `1,048,575` rows (`288` counties).
        4. **Lack of Total Customer Denominator:** Without external EIA-861 total customer counts per county, metrics represent observed customer-outage burdens and baseline-normalized ratios (`Max_outage / median_sum`), not formal IEEE 1366 SAIDI/SAIFI rates.
        """
    )
