import time
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json, window
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

# Define schema for klienci table
klienci_schema = StructType([
    StructField("id", IntegerType(), True),
    StructField("nazwa", StringType(), True),
    StructField("email", StringType(), True),
    StructField("kraj", StringType(), True),
    StructField("telefon", StringType(), True)
])

# Define schema for pracownicy table
pracownicy_schema = StructType([
    StructField("id", IntegerType(), True),
    StructField("imie", StringType(), True),
    StructField("nazwisko", StringType(), True),
    StructField("email", StringType(), True),
    StructField("wiek", IntegerType(), True),
    StructField("stanowisko", StringType(), True)
])

# Define schema for projekty table
projekty_schema = StructType([
    StructField("id", IntegerType(), True),
    StructField("nazwa", StringType(), True),
    StructField("opis", StringType(), True),
    StructField("data_rozpoczecia", StringType(), True),
    StructField("data_zakonczenia", StringType(), True)
])

# Define Kafka CDC message schema
kafka_schema = StructType([
    StructField("schema", StructType([]), True),
    StructField("payload", StringType(), True)
])

# Read stream for "klienci" topic with startingOffsets and failOnDataLoss
df_klienci = spark \
    .readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "kafka:9092") \
    .option("subscribe", "dbserver1.public.klienci") \
    .option("startingOffsets", "earliest") \
    .option("failOnDataLoss", "false") \
    .load() \
    .selectExpr("CAST(value AS STRING)", "timestamp") \
    .select(from_json("value", kafka_schema).alias("data"), "timestamp") \
    .select("data.payload", "timestamp") \
    .select(from_json(col("payload"), klienci_schema).alias("klienci"), "timestamp") \
    .select("klienci.*", "timestamp")

# Add watermark on "timestamp"
df_klienci_with_watermark = df_klienci.withWatermark("timestamp", "1 minute")

# Read stream for "pracownicy" topic
df_pracownicy = spark \
    .readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "kafka:9092") \
    .option("subscribe", "dbserver1.public.pracownicy") \
    .option("startingOffsets", "earliest") \
    .option("failOnDataLoss", "false") \
    .load() \
    .selectExpr("CAST(value AS STRING)", "timestamp") \
    .select(from_json("value", kafka_schema).alias("data"), "timestamp") \
    .select("data.payload", "timestamp") \
    .select(from_json(col("payload"), pracownicy_schema).alias("pracownicy"), "timestamp") \
    .select("pracownicy.*", "timestamp")

df_pracownicy_with_watermark = df_pracownicy.withWatermark("timestamp", "1 minute")

# Read stream for "projekty" topic
df_projekty = spark \
    .readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "kafka:9092") \
    .option("subscribe", "dbserver1.public.projekty") \
    .option("startingOffsets", "earliest") \
    .option("failOnDataLoss", "false") \
    .load() \
    .select(from_json(col("value").cast("string"), kafka_schema).alias("data")) \
    .select("data.payload") \
    .select(from_json(col("payload"), projekty_schema).alias("projekty")) \
    .select("projekty.*")

# Process data - Count clients by country (grouped by time window and "kraj")
df_klienci_by_country = df_klienci_with_watermark \
    .groupBy(window("timestamp", "1 minute"), "kraj") \
    .count()

# Process data - Average age by position (grouped by time window and "stanowisko")
df_avg_age_by_position = df_pracownicy_with_watermark \
    .groupBy(window("timestamp", "1 minute"), "stanowisko") \
    .avg("wiek") \
    .withColumnRenamed("avg(wiek)", "sredni_wiek")

# Opóźnienie startu, aby dać czas na utworzenie tematów w Kafka (zwiększone do 60 sekund)
time.sleep(60)

# Write stream results to MinIO (S3)
query1 = df_klienci_by_country \
    .writeStream \
    .outputMode("append") \
    .format("parquet") \
    .option("checkpointLocation", "/tmp/checkpoint1") \
    .option("path", "s3a://processed-data/klienci-by-country") \
    .start()

query2 = df_avg_age_by_position \
    .writeStream \
    .outputMode("append") \
    .format("parquet") \
    .option("checkpointLocation", "/tmp/checkpoint2") \
    .option("path", "s3a://processed-data/avg-age-by-position") \
    .start()

# Await termination of streams
spark.streams.awaitAnyTermination()
