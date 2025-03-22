import time
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json, window, current_timestamp
from pyspark.sql.types import StructType, StructField, StringType, IntegerType

# Initialize Spark session
spark = SparkSession.builder \
    .appName("CSVProcessing") \
    .config("spark.hadoop.fs.s3a.endpoint", "http://minio:9000") \
    .config("spark.hadoop.fs.s3a.access.key", "minio") \
    .config("spark.hadoop.fs.s3a.secret.key", "minio123") \
    .config("spark.hadoop.fs.s3a.path.style.access", "true") \
    .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
    .getOrCreate()

# Add explicit settings for better error handling
spark.conf.set("spark.sql.streaming.noDataMicroBatches.enabled", "true")
spark.conf.set("spark.sql.streaming.stopTimeout", "10000")

# Print active Kafka topics
print("Creating simple test dataframe first...")

# Create a sample dataframe and write to MinIO to verify access
test_data = [("test1", 1), ("test2", 2)]
test_df = spark.createDataFrame(test_data, ["name", "value"])
test_df.write.mode("overwrite").parquet("s3a://processed-data/test-data")
print("Test data written to MinIO")

print("Waiting 30 seconds before attempting to read from Kafka...")
time.sleep(30)

# Define Kafka options with explicit host:port
kafka_options = {
    "kafka.bootstrap.servers": "kafka:9092",
    "subscribe": "dbserver1.public.klienci,dbserver1.public.pracownicy,dbserver1.public.projekty",
    "startingOffsets": "earliest",
    "failOnDataLoss": "false"
}

print(f"Reading from Kafka with options: {kafka_options}")

# Simplified approach - read from Kafka with minimal processing
try:
    # Read from Kafka without complex parsing
    kafka_df = spark \
        .readStream \
        .format("kafka") \
        .options(**kafka_options) \
        .load()
    
    # Simple processing - just write raw data
    query = kafka_df \
        .selectExpr("CAST(key AS STRING)", "CAST(value AS STRING)", "topic", "partition", "offset", "timestamp") \
        .writeStream \
        .format("parquet") \
        .option("checkpointLocation", "/tmp/checkpoint-all") \
        .option("path", "s3a://processed-data/raw-kafka-data") \
        .trigger(processingTime="10 seconds") \
        .start()
    
    print("Stream processing started")
    query.awaitTermination()
    
except Exception as e:
    print(f"Error processing Kafka stream: {e}")
    raise e
