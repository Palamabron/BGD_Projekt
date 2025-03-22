from pyspark.sql import SparkSession

# Create spark session with S3 configuration
spark = SparkSession.builder \
    .appName("Simple MinIO Test") \
    .config("spark.hadoop.fs.s3a.endpoint", "http://minio:9000") \
    .config("spark.hadoop.fs.s3a.access.key", "minio") \
    .config("spark.hadoop.fs.s3a.secret.key", "minio123") \
    .config("spark.hadoop.fs.s3a.path.style.access", "true") \
    .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
    .getOrCreate()

# Create a simple test dataframe
data = [("test1", 1), ("test2", 2)]
df = spark.createDataFrame(data, ["name", "value"])

# Write to MinIO in CSV format
print("Writing test data to MinIO...")
df.write.mode("overwrite").format("csv").save("s3a://processed-data/simple-test")

print("Done!")
