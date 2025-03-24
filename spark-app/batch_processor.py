import time
import sys
import json
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json, expr, count, avg

def main():
    # Initialize Spark session in LOCAL mode
    print("Initializing Spark session in LOCAL mode...")
    spark = SparkSession.builder \
        .appName("BatchProcessor") \
        .master("local[*]") \
        .config("spark.hadoop.fs.s3a.endpoint", "http://minio:9000") \
        .config("spark.hadoop.fs.s3a.access.key", "minio") \
        .config("spark.hadoop.fs.s3a.secret.key", "minio123") \
        .config("spark.hadoop.fs.s3a.path.style.access", "true") \
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
        .config("spark.sql.shuffle.partitions", "10") \
        .config("spark.sql.parquet.binaryAsString", "true") \
        .getOrCreate()
    
    print("Starting batch processing of raw Kafka data...")
    
    try:
        # Test that we can reach MinIO
        print("Testing MinIO connection...")
        test_df = spark.createDataFrame([("test",)], ["value"])
        test_path = "s3a://processed-data/test-local-batch"
        test_df.write.mode("overwrite").parquet(test_path)
        print(f"Successfully wrote test data to {test_path}")
        
        # Read the raw data from MinIO
        print("Reading raw data from MinIO...")
        raw_data = spark.read \
            .option("recursiveFileLookup", "true") \
            .option("pathGlobFilter", "*.parquet") \
            .parquet("s3a://processed-data/raw-kafka-data")
        
        # Check if data was loaded
        count = raw_data.count()
        print(f"Found {count} raw records")
        
        if count == 0:
            print("No data found in raw-kafka-data")
            return
        
        # Show sample data for debugging
        print("Sample of raw data:")
        raw_data.show(5, truncate=False)
        print("Raw data schema:")
        raw_data.printSchema()
        
        # Process klienci (customers) data - group by country
        process_klienci_by_country(spark, raw_data)
        
        # Process pracownicy (employees) data - avg age by position
        process_avg_age_by_position(spark, raw_data)
        
        print("Batch processing completed successfully!")
    
    except Exception as e:
        print(f"Error in batch processing: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

def process_klienci_by_country(spark, raw_data):
    """Process customer data to group by country"""
    print("Processing klienci (customers) data...")
    
    # Filter for klienci data
    klienci_raw = raw_data.filter("topic = 'dbserver1.public.klienci'")
    
    if klienci_raw.count() == 0:
        print("No klienci data found")
        return
    
    print(f"Processing {klienci_raw.count()} klienci records")
    
    try:
        # Extract the JSON value
        klienci_parsed = klienci_raw.selectExpr("CAST(value AS STRING) as json_value")
        
        # Show sample for debugging
        print("Sample of klienci JSON data:")
        klienci_parsed.select("json_value").show(2, truncate=False)
        
        # Get a sample to understand the structure
        sample = klienci_parsed.limit(1).collect()
        if not sample:
            print("No sample data available to inspect")
            return
        
        sample_json = sample[0]["json_value"]
        print(f"Sample JSON: {sample_json[:200]}...")  # Print first 200 chars
        
        try:
            # Try to parse as JSON to understand structure
            json_obj = json.loads(sample_json)
            print("Successfully parsed JSON")
            
            # Print structure for debugging
            if "payload" in json_obj and "after" in json_obj["payload"]:
                print("Found Debezium envelope structure with after field")
                
                # Using SQL expressions to navigate the JSON structure
                print("Extracting country field from JSON...")
                result = klienci_parsed.selectExpr(
                    "get_json_object(json_value, '$.payload.after.kraj') as kraj"
                )
                
                # Show sample for debugging
                print("Sample of extracted country data:")
                result.show(5)
                
                # Group by country and count
                country_counts = result \
                    .filter("kraj IS NOT NULL") \
                    .groupBy("kraj") \
                    .count()
                
                # Show results for debugging
                print("Country counts:")
                country_counts.show()
                
                # Write to MinIO
                print("Writing klienci-by-country to MinIO...")
                country_counts.write.mode("overwrite").parquet("s3a://processed-data/klienci-by-country")
                
                # Also write to local project folder
                country_counts.write.mode("overwrite").parquet("/app/klienci-by-country")
                
                print("Successfully processed klienci by country")
            else:
                print("Unexpected JSON structure in klienci data, trying flat JSON")
                # Try flat JSON fallback method
                result = klienci_parsed.selectExpr(
                    "get_json_object(json_value, '$.kraj') as kraj"
                )
                
                # Group by country and count
                country_counts = result \
                    .filter("kraj IS NOT NULL") \
                    .groupBy("kraj") \
                    .count()
                
                # Write to MinIO
                country_counts.write.mode("overwrite").parquet("s3a://processed-data/klienci-by-country")
                
                # Also write to local project folder
                country_counts.write.mode("overwrite").parquet("/app/klienci-by-country")
        except json.JSONDecodeError as e:
            print(f"Could not parse JSON: {str(e)}. Using raw SQL extraction.")
            
            # Fallback method using SQL expressions directly
            result = klienci_parsed.selectExpr(
                "get_json_object(json_value, '$.payload.after.kraj') as kraj"
            )
            
            # Group by country and count
            country_counts = result \
                .filter("kraj IS NOT NULL") \
                .groupBy("kraj") \
                .count()
            
            # Write to MinIO
            country_counts.write.mode("overwrite").parquet("s3a://processed-data/klienci-by-country")
            
            # Also write to local project folder
            country_counts.write.mode("overwrite").parquet("/app/klienci-by-country")
            
            print("Successfully processed klienci by country using fallback method")
    
    except Exception as e:
        print(f"Error processing klienci data: {e}")
        print(f"Exception details: {str(e)}")
        import traceback
        traceback.print_exc()

def process_avg_age_by_position(spark, raw_data):
    """Process employee data to calculate average age by position"""
    print("Processing pracownicy (employees) data...")
    
    # Filter for pracownicy data
    pracownicy_raw = raw_data.filter("topic = 'dbserver1.public.pracownicy'")
    
    if pracownicy_raw.count() == 0:
        print("No pracownicy data found")
        return
    
    print(f"Processing {pracownicy_raw.count()} pracownicy records")
    
    try:
        # Extract the JSON value
        pracownicy_parsed = pracownicy_raw.selectExpr("CAST(value AS STRING) as json_value")
        
        # Show sample for debugging
        print("Sample of pracownicy JSON data:")
        pracownicy_parsed.select("json_value").show(2, truncate=False)
        
        # Get a sample to understand the structure
        sample = pracownicy_parsed.limit(1).collect()
        if not sample:
            print("No sample data available to inspect")
            return
        
        sample_json = sample[0]["json_value"]
        print(f"Sample JSON: {sample_json[:200]}...")  # Print first 200 chars
        
        try:
            # Try to parse as JSON to understand structure
            json_obj = json.loads(sample_json)
            print("Successfully parsed JSON")
            
            # Print structure for debugging
            if "payload" in json_obj and "after" in json_obj["payload"]:
                print("Found Debezium envelope structure with after field")
                
                # Using SQL expressions to navigate the JSON structure
                print("Extracting position and age fields from JSON...")
                result = pracownicy_parsed.selectExpr(
                    "get_json_object(json_value, '$.payload.after.stanowisko') as stanowisko",
                    "CAST(get_json_object(json_value, '$.payload.after.wiek') AS INT) as wiek"
                )
                
                # Show sample for debugging
                print("Sample of extracted position and age data:")
                result.show(5)
                
                # Calculate average age by position
                avg_age = result \
                    .filter("stanowisko IS NOT NULL AND wiek IS NOT NULL") \
                    .groupBy("stanowisko") \
                    .agg(avg("wiek").alias("avg_age"))
                
                # Show results for debugging
                print("Average age by position:")
                avg_age.show()
                
                # Write to MinIO
                print("Writing avg-age-by-position to MinIO...")
                avg_age.write.mode("overwrite").parquet("s3a://processed-data/avg-age-by-position")
                
                # Also write to local project folder
                avg_age.write.mode("overwrite").parquet("/app/avg-age-by-position")
                
                print("Successfully processed average age by position")
            else:
                print("Unexpected JSON structure in pracownicy data, trying flat JSON")
                # Try flat JSON fallback method
                result = pracownicy_parsed.selectExpr(
                    "get_json_object(json_value, '$.stanowisko') as stanowisko",
                    "CAST(get_json_object(json_value, '$.wiek') AS INT) as wiek"
                )
                
                # Calculate average age by position
                avg_age = result \
                    .filter("stanowisko IS NOT NULL AND wiek IS NOT NULL") \
                    .groupBy("stanowisko") \
                    .agg(avg("wiek").alias("avg_age"))
                
                # Write to MinIO
                avg_age.write.mode("overwrite").parquet("s3a://processed-data/avg-age-by-position")
                
                # Also write to local project folder
                avg_age.write.mode("overwrite").parquet("/app/avg-age-by-position")
        except json.JSONDecodeError as e:
            print(f"Could not parse JSON: {str(e)}. Using raw SQL extraction.")
            
            # Fallback method using SQL expressions directly
            result = pracownicy_parsed.selectExpr(
                "get_json_object(json_value, '$.payload.after.stanowisko') as stanowisko",
                "CAST(get_json_object(json_value, '$.payload.after.wiek') AS INT) as wiek"
            )
            
            # Calculate average age by position
            avg_age = result \
                .filter("stanowisko IS NOT NULL AND wiek IS NOT NULL") \
                .groupBy("stanowisko") \
                .agg(avg("wiek").alias("avg_age"))
            
            # Write to MinIO
            avg_age.write.mode("overwrite").parquet("s3a://processed-data/avg-age-by-position")
            
            # Also write to local project folder
            avg_age.write.mode("overwrite").parquet("/app/avg-age-by-position")
            
            print("Successfully processed average age by position using fallback method")
    
    except Exception as e:
        print(f"Error processing pracownicy data: {e}")
        print(f"Exception details: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()