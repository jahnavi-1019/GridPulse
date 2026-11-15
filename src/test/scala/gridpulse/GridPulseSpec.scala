package gridpulse

import org.apache.spark.sql.SparkSession
import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers
import gridpulse.ingestion.DataIngestionAudit

class GridPulseSpec extends AnyFlatSpec with Matchers {

  "SparkConfig" should "initialize SparkSession properly" in {
    val spark = SparkSession.builder()
      .appName("GridPulse-UnitTest")
      .master("local[2]")
      .config("spark.ui.enabled", "false")
      .getOrCreate()

    spark.version should startWith("3.")
    spark.stop()
  }

  "DataIngestionAudit" should "define 16 fields in EagleVtecSchema" in {
    DataIngestionAudit.EagleVtecSchema.fields.length shouldBe 16
    DataIngestionAudit.EagleVtecSchema.fieldNames should contain ("fips_code")
    DataIngestionAudit.EagleVtecSchema.fieldNames should contain ("Max_outage")
    DataIngestionAudit.EagleVtecSchema.fieldNames should contain ("Matched_Events")
  }
}
