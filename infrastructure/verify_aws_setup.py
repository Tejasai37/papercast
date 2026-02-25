import boto3
import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

def verify_aws_connectivity():
    print("--- 🛰️ Papercast AWS Smoke Test ---")
    
    region = os.getenv("AWS_REGION", "us-east-1")
    s3_bucket = os.getenv("S3_BUCKET_NAME")
    table_name = os.getenv("DYNAMODB_TABLE_NAME")
    pool_id = os.getenv("COGNITO_USER_POOL_ID")
    
    print(f"Region: {region}")
    
    # 1. Verify S3
    try:
        s3 = boto3.client('s3', region_name=region)
        s3.head_bucket(Bucket=s3_bucket)
        print(f"✅ S3 Bucket '{s3_bucket}': REACHABLE")
    except Exception as e:
        print(f"❌ S3 Bucket Verification Failed: {e}")

    # 2. Verify DynamoDB
    try:
        db = boto3.client('dynamodb', region_name=region)
        db.describe_table(TableName=table_name)
        print(f"✅ DynamoDB Table '{table_name}': REACHABLE")
    except Exception as e:
        print(f"❌ DynamoDB Verification Failed: {e}")

    # 3. Verify Cognito
    try:
        cognito = boto3.client('cognito-idp', region_name=region)
        cognito.describe_user_pool(UserPoolId=pool_id)
        print(f"✅ Cognito User Pool '{pool_id}': REACHABLE")
    except Exception as e:
        print(f"❌ Cognito Verification Failed: {e}")

    # 4. Verify Bedrock (Nova Micro)
    try:
        bedrock = boto3.client('bedrock-runtime', region_name=region)
        # Simple test call
        body = '{"messages": [{"role": "user", "content": [{"text": "hi"}]}]}'
        bedrock.invoke_model(
            modelId='amazon.nova-micro-v1:0',
            body=body
        )
        print(f"✅ Amazon Bedrock (Nova Micro): PERMISSION GRANTED")
    except Exception as e:
        print(f"❌ Bedrock Verification Failed: {e}")

    # 5. Verify Polly
    try:
        polly = boto3.client('polly', region_name=region)
        polly.describe_voices(Engine='neural', LanguageCode='en-US')
        print(f"✅ Amazon Polly (Neural Voices): ACCESSIBLE")
    except Exception as e:
        print(f"❌ Polly Verification Failed: {e}")

    print("\n--- Smoke Test Complete ---")
    print("If all 5 checkmarks are green, your .env is correct and your IAM keys have the right permissions!")

if __name__ == "__main__":
    verify_aws_connectivity()
