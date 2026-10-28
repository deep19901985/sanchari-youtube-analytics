# Databricks notebook source
# Day 1: READ-ONLY diagnostics. Runs in the Databricks notebook serverless environment.
# No credentials, tokens or workspace URLs are printed.

# COMMAND ----------
print("Spark version:", spark.version)
print("PySpark runtime: PASS")

# COMMAND ----------
for statement in ["SELECT current_catalog() AS catalog", "SELECT current_schema() AS schema", "SHOW CATALOGS"]:
    print("QUERY:", statement)
    try:
        display(spark.sql(statement))
    except Exception as exc:
        print(f"CHECK FAILED ({type(exc).__name__}). Review workspace permissions.")

# COMMAND ----------
# A tiny in-memory PySpark transformation validates DataFrame capability.
from pyspark.sql import functions as F
rows = [("sample-video-A", 12), ("sample-video-B", 21)]
sample = spark.createDataFrame(rows, ["video_id", "sample_views"])
result = sample.withColumn("double_views", F.col("sample_views") * 2)
display(result)
print("Spark DataFrame smoke test:", "PASS" if result.count() == 2 else "FAIL")

# COMMAND ----------
# No permanent catalogs, schemas, volumes or tables are created by this notebook.
print("Next manual UI checks: Catalog Explorer / SQL Warehouse / Jobs / Pipelines.")
