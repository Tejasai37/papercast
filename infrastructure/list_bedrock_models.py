import boto3
import os
from dotenv import load_dotenv

load_dotenv()

def list_models():
    region = os.getenv("AWS_REGION", "us-east-1")
    session_kwargs = {
        "region_name": region,
        "aws_access_key_id": os.getenv("AWS_ACCESS_KEY_ID"),
        "aws_secret_access_key": os.getenv("AWS_SECRET_ACCESS_KEY")
    }
    
    bedrock = boto3.client("bedrock", **session_kwargs)
    
    try:
        # 1. Try a direct lookup for Titan Text Lite
        lite_id = "amazon.titan-text-lite-v1"
        print(f"Checking specific Model ID: {lite_id}...")
        try:
            m = bedrock.get_foundation_model(modelIdentifier=lite_id)
            details = m.get('modelDetails', {})
            print(f"FOUND: {details.get('modelName')}")
            print(f"Status: {details.get('modelLifecycle', {}).get('status')}")
            print(f"Modalities: {details.get('inputModalities')} -> {details.get('outputModalities')}")
        except Exception as e:
            print(f"Direct Lookup Failed: {e}")

        # 2. List all Amazon models for comparison
        print("\nListing all 'Amazon' provider models:")
        print("-" * 60)
        response = bedrock.list_foundation_models(byProvider='Amazon')
        for m in response['modelSummaries']:
            print(f" - {m['modelName']:<30} | {m['modelId']}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    list_models()
