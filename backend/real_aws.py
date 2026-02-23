
import boto3
import json
import os
from botocore.exceptions import ClientError

class RealAWSService:
    def __init__(self):
        # 1. Start with defaults or environment variables
        self.config = {
            "s3_bucket": os.getenv("S3_BUCKET_NAME"),
            "dynamodb_table": os.getenv("DYNAMODB_TABLE_NAME", "PapercastCache"),
            "user_pool_id": os.getenv("COGNITO_USER_POOL_ID"),
            "client_id": os.getenv("COGNITO_CLIENT_ID"),
            "region": os.getenv("AWS_REGION", "us-east-1")
        }

        # 2. If a local config file exists, use it to fill in blanks (backward compatibility)
        config_path = "infrastructure/aws_config.json"
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                file_config = json.load(f)
                for key, value in file_config.items():
                    if not self.config.get(key): # Only fill if environment variable is NOT set
                        self.config[key] = value

        # 3. Initialize clients
        self.s3 = boto3.client("s3", region_name=self.config["region"])
        self.dynamodb = boto3.resource("dynamodb", region_name=self.config["region"])
        self.table = self.dynamodb.Table(self.config["dynamodb_table"])
        self.cognito = boto3.client("cognito-idp", region_name=self.config["region"])
        
        # Bedrock & Polly
        self.bedrock = boto3.client("bedrock-runtime", region_name=self.config["region"])
        self.polly = boto3.client("polly", region_name=self.config["region"])

    # --- S3 (File Storage) ---
    def upload_audio(self, file_content: bytes, file_name: str) -> str:
        """Uploads audio file to S3 and returns the URL"""
        try:
            self.s3.put_object(
                Bucket=self.config["s3_bucket"],
                Key=file_name,
                Body=file_content,
                ContentType="audio/wav"
            )
            # Generating a pre-signed URL for temporary access (or use public URL if bucket is public)
            url = self.s3.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.config['s3_bucket'], 'Key': file_name},
                ExpiresIn=3600  # 1 hour
            )
            return url
        except ClientError as e:
            print(f"S3 Upload Error: {e}")
            return None

    def get_audio_url(self, file_name: str) -> str:
        """Check if file exists and return a pre-signed URL"""
        try:
            self.s3.head_object(Bucket=self.config["s3_bucket"], Key=file_name)
            url = self.s3.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.config['s3_bucket'], 'Key': file_name},
                ExpiresIn=3600
            )
            return url
        except ClientError:
            return None

    # --- DynamoDB (Metadata Cache) ---
    def get_article_metadata(self, article_id: str):
        """Fetch metadata from DynamoDB"""
        try:
            response = self.table.get_item(Key={'ArticleID': article_id})
            return response.get('Item')
        except ClientError as e:
            print(f"DynamoDB Get Error: {e}")
            return None

    def save_article_metadata(self, article_id: str, data: dict):
        """Save metadata to DynamoDB"""
        try:
            item = {'ArticleID': article_id, **data}
            self.table.put_item(Item=item)
        except ClientError as e:
            print(f"DynamoDB Put Error: {e}")

    # --- Cognito (Authentication) ---
    def authenticate_user(self, username, password):
        """Authenticates user with Cognito and returns tokens"""
        try:
            response = self.cognito.admin_initiate_auth(
                UserPoolId=self.config["user_pool_id"],
                ClientId=self.config["client_id"],
                AuthFlow='ADMIN_NO_SRP_AUTH',
                AuthParameters={
                    'USERNAME': username,
                    'PASSWORD': password
                }
            )
            return response['AuthenticationResult']
        except ClientError as e:
            print(f"Cognito Auth Error: {e}")
            return None

    def sign_up_user(self, username, password, email):
        """Creates a new user in Cognito"""
        try:
            response = self.cognito.admin_create_user(
                UserPoolId=self.config["user_pool_id"],
                Username=username,
                UserAttributes=[
                    {'Name': 'email', 'Value': email},
                    {'Name': 'email_verified', 'Value': 'true'}
                ],
                MessageAction='SUPPRESS' # Don't send welcome email for dev
            )
            # Set password
            self.cognito.admin_set_user_password(
                UserPoolId=self.config["user_pool_id"],
                Username=username,
                Password=password,
                Permanent=True
            )
            return response
        except ClientError as e:
            print(f"Cognito Sign-up Error: {e}")
            return None

# Singleton Instance (Optional: but useful for FastAPI)
# real_aws = RealAWSService()
