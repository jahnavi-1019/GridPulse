package gridpulse.config

import java.io.File
import org.apache.spark.sql.SparkSession

object SparkConfig {

  val TrainEndYear: Int = 2020
  val ValYear: Int = 2021
  val TestYear: Int = 2022
  val HighSeverityThreshold: Double = 100.0

  def resolveDataFile(filename: String): File = {
    // Check possible locations
    val candidates = Seq(
      new File("data/raw", filename),
      new File(".", filename),
      new File("D:/bda_project", filename),
      new File("D:/bda_project/data/raw", filename)
    )
    candidates.find(_.exists()).getOrElse(
      throw new java.io.FileNotFoundException(s"Source file '$filename' not found in candidate paths: ${candidates.map(_.getAbsolutePath).mkString(", ")}")
    )
  }

  def getOrCreateSparkSession(appName: String = "GridPulse-Scala-Spark"): SparkSession = {
    SparkSession.builder()
      .appName(appName)
      .master(sys.env.getOrElse("GRIDPULSE_SPARK_MASTER", "local[*]"))
      .config("spark.driver.memory", sys.env.getOrElse("GRIDPULSE_SPARK_MEMORY", "4g"))
      .config("spark.sql.shuffle.partitions", "16")
      .config("spark.sql.session.timeZone", "UTC")
      .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer")
      .config("spark.ui.enabled", "false")
      .getOrCreate()
  }
}
