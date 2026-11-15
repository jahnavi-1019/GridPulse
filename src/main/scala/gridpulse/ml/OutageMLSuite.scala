package gridpulse.ml

import org.apache.spark.ml.Pipeline
import org.apache.spark.ml.classification._
import org.apache.spark.ml.evaluation.{BinaryClassificationEvaluator, MulticlassClassificationEvaluator}
import org.apache.spark.ml.feature._
import org.apache.spark.sql.DataFrame
import org.apache.spark.sql.functions._
import gridpulse.config.SparkConfig
import gridpulse.model.Schemas.ModelBenchmarkRow

object OutageMLSuite {

  def trainAndEvaluateAllModels(episodesDf: DataFrame): Seq[ModelBenchmarkRow] = {
    println("\n" + "=" * 80)
    println("🤖 STAGE 3: ADVANCED SPARK ML & DEEP LEARNING MODEL SUITE")
    println("=" * 80)

    // 1. Prepare Feature Transformation Pipeline
    val phenomIndexer = new StringIndexer()
      .setInputCol("primary_phenom")
      .setOutputCol("phenom_idx")
      .setHandleInvalid("keep")

    val phenomEncoder = new OneHotEncoder()
      .setInputCol("phenom_idx")
      .setOutputCol("phenom_vec")

    val numericCols = Array(
      "initial_outage_hr1",
      "initial_completeness_pct",
      "initial_matched_count",
      "county_baseline_median_sum",
      "initial_to_baseline_ratio",
      "prior_1_max_outage",
      "prior_5_mean_max_outage",
      "prior_5_mean_duration_hr",
      "prior_10_high_sev_rate",
      "hours_since_prior_event",
      "sin_onset_hour",
      "cos_onset_hour",
      "sin_month",
      "cos_month"
    )

    val assembler = new VectorAssembler()
      .setInputCols(numericCols :+ "phenom_vec")
      .setOutputCol("raw_features")
      .setHandleInvalid("skip")

    val scaler = new StandardScaler()
      .setInputCol("raw_features")
      .setOutputCol("features")
      .setWithStd(true)
      .setWithMean(false)

    val prepPipeline = new Pipeline().setStages(Array(phenomIndexer, phenomEncoder, assembler, scaler))
    println("⏳ Fitting feature transformation pipeline across episodes...")
    val prepModel = prepPipeline.fit(episodesDf)
    val featuredData = prepModel.transform(episodesDf).cache()

    // 2. Chronological Zero-Leakage Data Partitioning
    val trainDf = featuredData.filter(col("year") <= SparkConfig.TrainEndYear).cache()
    val valDf = featuredData.filter(col("year") === SparkConfig.ValYear).cache()
    val testDf = featuredData.filter(col("year") === SparkConfig.TestYear).cache()

    val nTrain = trainDf.count()
    val nVal = valDf.count()
    val nTest = testDf.count()

    println(s"📅 Chronological Partitioning (Zero Future Leakage):")
    println(s"   • Train Period (<= ${SparkConfig.TrainEndYear}): $nTrain episodes")
    println(s"   • Validation Period (${SparkConfig.ValYear}): $nVal episodes")
    println(s"   • Untouched Test Period (${SparkConfig.TestYear}): $nTest episodes")

    // Determine input feature dimension dynamically
    val sampleRow = featuredData.select("features").first()
    val numFeatures = sampleRow.getAs[org.apache.spark.ml.linalg.Vector](0).size
    println(s"📐 Feature Vector Dimension: $numFeatures features")

    // 3. Evaluators
    val rocAucEval = new BinaryClassificationEvaluator().setLabelCol("label").setRawPredictionCol("rawPrediction").setMetricName("areaUnderROC")
    val prAucEval = new BinaryClassificationEvaluator().setLabelCol("label").setRawPredictionCol("rawPrediction").setMetricName("areaUnderPR")
    val accEval = new MulticlassClassificationEvaluator().setLabelCol("label").setPredictionCol("prediction").setMetricName("accuracy")
    val f1Eval = new MulticlassClassificationEvaluator().setLabelCol("label").setPredictionCol("prediction").setMetricName("f1")
    val precEval = new MulticlassClassificationEvaluator().setLabelCol("label").setPredictionCol("prediction").setMetricName("weightedPrecision")
    val recEval = new MulticlassClassificationEvaluator().setLabelCol("label").setPredictionCol("prediction").setMetricName("weightedRecall")

    // 4. Define Models
    // A. Baseline: Logistic Regression (ElasticNet)
    val lr = new LogisticRegression()
      .setLabelCol("label")
      .setFeaturesCol("features")
      .setElasticNetParam(0.5)
      .setRegParam(0.01)
      .setMaxIter(50)

    // B. Advanced Ensemble 1: Random Forest
    val rf = new RandomForestClassifier()
      .setLabelCol("label")
      .setFeaturesCol("features")
      .setNumTrees(50)
      .setMaxDepth(8)
      .setSeed(42)

    // C. Advanced Ensemble 2: Gradient-Boosted Decision Trees (GBT)
    val gbt = new GBTClassifier()
      .setLabelCol("label")
      .setFeaturesCol("features")
      .setMaxIter(40)
      .setMaxDepth(5)
      .setSeed(42)

    // D. Deep Learning: Multilayer Perceptron Deep Neural Network (MLPC)
    val dnnLayers = Array[Int](numFeatures, 64, 32, 16, 2)
    val mlpc = new MultilayerPerceptronClassifier()
      .setLabelCol("label")
      .setFeaturesCol("features")
      .setLayers(dnnLayers)
      .setBlockSize(128)
      .setSeed(42)
      .setMaxIter(100)

    val candidateModels = Seq(
      ("Logistic Regression (ElasticNet)", lr),
      ("Random Forest Classifier", rf),
      ("Gradient-Boosted Trees (GBT)", gbt),
      ("Deep Multilayer Perceptron (MLPC)", mlpc)
    )

    val benchmarkResults = candidateModels.map { case (name, estimator) =>
      println(s"\n🚀 Training $name on $nTrain episodes...")
      val t0 = System.nanoTime()
      val model = estimator match {
        case m: LogisticRegression => m.fit(trainDf)
        case m: RandomForestClassifier => m.fit(trainDf)
        case m: GBTClassifier => m.fit(trainDf)
        case m: MultilayerPerceptronClassifier => m.fit(trainDf)
        case other => throw new IllegalArgumentException(s"Unsupported model: $other")
      }
      val durationSec = (System.nanoTime() - t0) / 1e9

      val valPreds = model match {
        case m: LogisticRegressionModel => m.transform(valDf)
        case m: RandomForestClassificationModel => m.transform(valDf)
        case m: GBTClassificationModel => m.transform(valDf)
        case m: MultilayerPerceptronClassificationModel => m.transform(valDf)
      }
      val valRocAuc = rocAucEval.evaluate(valPreds)

      val testPreds = model match {
        case m: LogisticRegressionModel => m.transform(testDf)
        case m: RandomForestClassificationModel => m.transform(testDf)
        case m: GBTClassificationModel => m.transform(testDf)
        case m: MultilayerPerceptronClassificationModel => m.transform(testDf)
      }

      val testRocAuc = rocAucEval.evaluate(testPreds)
      val testPrAuc = prAucEval.evaluate(testPreds)
      val testAcc = accEval.evaluate(testPreds)
      val testF1 = f1Eval.evaluate(testPreds)
      val testPrec = precEval.evaluate(testPreds)
      val testRec = recEval.evaluate(testPreds)

      println(f"   🎯 $name Results (Test 2022):")
      println(f"      • ROC-AUC:    $testRocAuc%.4f (Val: $valRocAuc%.4f)")
      println(f"      • PR-AUC:     $testPrAuc%.4f")
      println(f"      • Accuracy:   ${testAcc * 100}%.2f%%")
      println(f"      • F1-Score:   $testF1%.4f")
      println(f"      • Precision:  $testPrec%.4f | Recall: $testRec%.4f")
      println(f"      • Fit Time:   $durationSec%.2f sec")

      ModelBenchmarkRow(
        modelName = name,
        valRocAuc = valRocAuc,
        testRocAuc = testRocAuc,
        testPrAuc = testPrAuc,
        testAccuracy = testAcc,
        testF1 = testF1,
        testPrecision = testPrec,
        testRecall = testRec,
        trainingTimeSec = durationSec
      )
    }

    println("\n" + "=" * 80)
    println("🏆 FINAL MODEL PERFORMANCE COMPARISON BENCHMARK (UNTOUCHED TEST SET 2022)")
    println("=" * 80)
    println(f"${"Model Architecture"}%-35s | ${"ROC-AUC"}%-8s | ${"PR-AUC"}%-8s | ${"Accuracy"}%-8s | ${"F1-Score"}%-8s | ${"Time(s)"}%-7s")
    println("-" * 85)
    benchmarkResults.foreach { r =>
      println(f"${r.modelName}%-35s | ${r.testRocAuc}%-8.4f | ${r.testPrAuc}%-8.4f | ${r.testAccuracy * 100}%-7.2f%% | ${r.testF1}%-8.4f | ${r.trainingTimeSec}%-7.2f")
    }

    benchmarkResults
  }
}
