package gridpulse.features

import org.apache.spark.sql.DataFrame
import org.apache.spark.sql.expressions.Window
import org.apache.spark.sql.functions._
import gridpulse.config.SparkConfig

object EpisodeFeatureEngine {

  def aggregateEpisodesAndBuildFeatures(rawDf: DataFrame): DataFrame = {
    println("\n" + "=" * 80)
    println("⚙️ STAGE 2: DISTRIBUTED EPISODE AGGREGATION & CAUSAL LAG FEATURE ENGINE")
    println("=" * 80)

    // 1. Timestamp and date parsing
    val parsedDf = rawDf
      .withColumn("ts", to_timestamp(col("Hour"), "yyyy-MM-dd'T'HH:mm:ss'Z'"))
      .withColumn("primary_phenom", trim(split(col("Matched_Events"), ";").getItem(0)))
      .withColumn("year", year(col("ts")))
      .withColumn("month", month(col("ts")))
      .withColumn("onset_hour_utc", hour(col("ts")))
      .withColumn("season", when(col("month").isin(12, 1, 2), "Winter")
        .when(col("month").isin(3, 4, 5), "Spring")
        .when(col("month").isin(6, 7, 8), "Summer")
        .otherwise("Fall"))

    // 2. Window across each episode (fips_code, new_event_no) ordered by timestamp to isolate Hour 1 onset telemetry
    val epOrderWin = Window.partitionBy("fips_code", "new_event_no").orderBy("ts")

    val withOnset = parsedDf
      .withColumn("onset_rank", row_number().over(epOrderWin))
      .filter(col("onset_rank") === 1) // strictly onset hour
      .select(
        col("fips_code"),
        col("new_event_no"),
        col("state"),
        col("county"),
        col("WFO"),
        col("primary_phenom"),
        col("Matched_Events").alias("matched_events"),
        col("ts").alias("onset_ts"),
        col("year"),
        col("month"),
        col("onset_hour_utc"),
        col("season"),
        col("max_rolling_avg").alias("initial_outage_hr1"),
        col("source_completeness_pct").alias("initial_completeness_pct"),
        col("Matched_Count").alias("initial_matched_count"),
        col("median_sum").alias("county_baseline_median_sum"),
        (col("max_rolling_avg") / (col("median_sum") + 0.001)).alias("initial_to_baseline_ratio"),
        col("evDur_Hr"),
        col("Max_outage"),
        col("event_mean_completeness_pct"),
        col("event_min_completeness_pct"),
        when(col("Max_outage") >= SparkConfig.HighSeverityThreshold, 1.0).otherwise(0.0).alias("label")
      )

    println(s"✅ Aggregated Contiguous Episodes (fips_code, new_event_no): ${withOnset.count()}")

    // 3. Strictly causal historical county lags (zero future leakage!)
    val countyHistoryWin = Window.partitionBy("fips_code").orderBy("onset_ts")

    val episodesWithLags = withOnset
      .withColumn("prior_1_max_outage", coalesce(lag("Max_outage", 1).over(countyHistoryWin), lit(0.0)))
      .withColumn("prior_5_mean_max_outage", coalesce(avg("Max_outage").over(countyHistoryWin.rowsBetween(-5, -1)), lit(0.0)))
      .withColumn("prior_5_mean_duration_hr", coalesce(avg("evDur_Hr").over(countyHistoryWin.rowsBetween(-5, -1)), lit(0.0)))
      .withColumn("prior_10_high_sev_rate", coalesce(avg("label").over(countyHistoryWin.rowsBetween(-10, -1)), lit(0.0)))
      .withColumn("hours_since_prior_event", coalesce(
        (unix_timestamp(col("onset_ts")) - lag(unix_timestamp(col("onset_ts")), 1).over(countyHistoryWin)) / 3600.0,
        lit(720.0) // 30-day default when no prior event exists
      ))
      // Cyclical temporal encodings
      .withColumn("sin_onset_hour", sin(col("onset_hour_utc") * (2.0 * math.Pi / 24.0)))
      .withColumn("cos_onset_hour", cos(col("onset_hour_utc") * (2.0 * math.Pi / 24.0)))
      .withColumn("sin_month", sin(col("month") * (2.0 * math.Pi / 12.0)))
      .withColumn("cos_month", cos(col("month") * (2.0 * math.Pi / 12.0)))

    episodesWithLags
  }
}
