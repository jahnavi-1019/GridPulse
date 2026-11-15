package gridpulse.model

/** Strongly-typed case class schemas for GridPulse. */
object Schemas {

  case class EagleVtecRaw(
    fips_code: Long,
    Hour: String,
    max_rolling_avg: Double,
    state: String,
    county: String,
    median_sum: Double,
    new_event_no: Long,
    evDur_Hr: Long,
    evDur_day: Long,
    Max_outage: Double,
    source_completeness_pct: Double,
    event_mean_completeness_pct: Double,
    event_min_completeness_pct: Double,
    WFO: String,
    Matched_Events: String,
    Matched_Count: Long
  )

  case class OutageEpisode(
    fips_code: Long,
    new_event_no: Long,
    state: String,
    county: String,
    WFO: String,
    primary_phenom: String,
    matched_events: String,
    year: Int,
    month: Int,
    day: Int,
    onset_hour_utc: Int,
    season: String,
    initial_outage_hr1: Double,
    initial_completeness_pct: Double,
    initial_matched_count: Long,
    county_baseline_median_sum: Double,
    initial_to_baseline_ratio: Double,
    evDur_Hr: Double,
    Max_outage: Double,
    event_mean_completeness_pct: Double,
    event_min_completeness_pct: Double,
    prior_1_max_outage: Double,
    prior_5_mean_max_outage: Double,
    prior_5_mean_duration_hr: Double,
    prior_10_high_sev_rate: Double,
    hours_since_prior_event: Double,
    target_high_severity_100: Int,
    target_major_severity_500: Int
  )

  case class ModelBenchmarkRow(
    modelName: String,
    valRocAuc: Double,
    testRocAuc: Double,
    testPrAuc: Double,
    testAccuracy: Double,
    testF1: Double,
    testPrecision: Double,
    testRecall: Double,
    trainingTimeSec: Double
  )

  case class CountyReliabilityProfile(
    fips_code: Long,
    county: String,
    state: String,
    total_outage_events: Long,
    events_per_observed_year: Double,
    median_max_outage: Double,
    p90_max_outage: Double,
    county_baseline_median_sum: Double,
    median_normalized_severity_ratio: Double,
    high_severity_event_share_pct: Double,
    mean_event_completeness_pct: Double,
    coverage_confidence_tier: String,
    dominant_weather_phenom: String,
    reliability_archetype: String
  )
}
