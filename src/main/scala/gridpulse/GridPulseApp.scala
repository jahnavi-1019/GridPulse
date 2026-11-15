package gridpulse

import gridpulse.config.SparkConfig
import gridpulse.ingestion.DataIngestionAudit
import gridpulse.features.EpisodeFeatureEngine
import gridpulse.ml.{OutageMLSuite, RegionalReliabilityClustering}
import gridpulse.benchmark.ScalabilityBenchmark

object GridPulseApp {

  def main(args: Array[String]): Unit = {
    println("=" * 80)
    println("⚡ GRIDPULSE: DISTRIBUTED POWER OUTAGE ANALYTICS & RELIABILITY ASSESSMENT")
    println("   Native Apache Spark (v3.5.3) & Scala (v2.12.18) Big Data Research Pipeline")
    println("=" * 80)

    val spark = SparkConfig.getOrCreateSparkSession("GridPulse-Distributed-Pipeline")

    try {
      // Stage 1: Ingestion & Quality Audit
      val rawDf = DataIngestionAudit.loadAndAuditEagleVtec(spark)
      DataIngestionAudit.auditAvailabilityAndMissingness(spark)

      // Stage 2: Feature Engineering & Window Aggregations
      val episodesDf = EpisodeFeatureEngine.aggregateEpisodesAndBuildFeatures(rawDf).cache()

      // Stage 3: ML & Deep Learning Benchmark Suite
      val benchmarkResults = OutageMLSuite.trainAndEvaluateAllModels(episodesDf)
      println(s"✅ Evaluated ${benchmarkResults.size} models across validation and untouched test sets.")

      // Stage 4: Regional Reliability Profiling & K-Means Clustering
      val countyProfiles = RegionalReliabilityClustering.buildCountyProfilesAndCluster(episodesDf)
      println(s"✅ Regional profiling complete for ${countyProfiles.count()} counties.")

      // Stage 5: Spark Partition Scalability Benchmark
      ScalabilityBenchmark.runPartitionScalability(rawDf)

      println("\n" + "=" * 80)
      println("🎉 GRIDPULSE SCALA SPARK PIPELINE EXECUTED SUCCESSFULLY!")
      println("=" * 80)
    } catch {
      case e: Throwable =>
        System.err.println(s"❌ Pipeline encountered an error: ${e.getMessage}")
        e.printStackTrace()
    } finally {
      spark.stop()
    }
  }
}
