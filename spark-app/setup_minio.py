import boto3
from botocore.client import Config
import time

def setup_minio():
    # Wait for MinIO to be ready
    max_retries = 30
    retries = 0
    
    while retries < max_retries:
        try:
            # Configure MinIO client
            s3_client = boto3.client(
                's3',
                endpoint_url='http://minio:9000',
                aws_access_key_id='minio',
                aws_secret_access_key='minio123',
                config=Config(signature_version='s3v4'),
                region_name='us-east-1'
            )
            
            # Test connection
            s3_client.list_buckets()
            print("MinIO is ready")
            break
        except Exception as e:
            print(f"Waiting for MinIO to be ready... Retry {retries+1}/{max_retries}")
            print(f"Error: {str(e)}")
            retries += 1
            time.sleep(5)
    
    if retries == max_retries:
        print("Failed to connect to MinIO")
        return
    
    # Create buckets
    try:
        s3_client.create_bucket(Bucket='processed-data')
        print("Successfully created bucket: processed-data")
    except Exception as e:
        if 'BucketAlreadyOwnedByYou' in str(e):
            print("Bucket 'processed-data' already exists")
        else:
            print(f"Error creating bucket: {str(e)}")

if __name__ == "__main__":
    setup_minio()