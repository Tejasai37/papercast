import boto3
import time
import json
import os
from botocore.exceptions import ClientError
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Configuration
REGION = os.getenv("AWS_REGION", "us-east-1")
PROJECT_NAME = "Papercast"
BUCKET_NAME = os.getenv("S3_BUCKET_NAME", f"papercast-audio-{int(time.time())}")
TABLE_NAME = os.getenv("DYNAMODB_TABLE_NAME", "PapercastCache")

def create_s3_bucket(s3):
    print(f"Creating S3 Bucket: {BUCKET_NAME}...")
    try:
        if REGION == "us-east-1":
            s3.create_bucket(Bucket=BUCKET_NAME)
        else:
            s3.create_bucket(
                Bucket=BUCKET_NAME,
                CreateBucketConfiguration={'LocationConstraint': REGION}
            )
        print("S3 Bucket Created successfully.")
        return BUCKET_NAME
    except ClientError as e:
        print(f"Error creating bucket: {e}")
        return None

def create_dynamodb_table(dynamodb):
    print(f"Creating DynamoDB Table: {TABLE_NAME}...")
    try:
        table = dynamodb.create_table(
            TableName=TABLE_NAME,
            KeySchema=[{'AttributeName': 'ArticleID', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'ArticleID', 'AttributeType': 'S'}],
            ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
        )
        print("Waiting for table to be active...")
        table.wait_until_exists()
        print("DynamoDB Table Created successfully.")
        return table.name
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceInUseException':
            print("Table already exists.")
            return TABLE_NAME
        else:
            print(f"Error creating table: {e}")
            return None

def create_cognito_resources(cognito):
    print("Creating Cognito User Pool...")
    try:
        pool_response = cognito.create_user_pool(
            PoolName=f"{PROJECT_NAME}-Users",
            Policies={
                'PasswordPolicy': {
                    'MinimumLength': 8,
                    'RequireUppercase': True,
                    'RequireLowercase': True,
                    'RequireNumbers': True,
                    'RequireSymbols': False
                }
            },
            AutoVerifiedAttributes=['email']
        )
        user_pool_id = pool_response['UserPool']['Id']
        print(f"User Pool Created: {user_pool_id}")

        # Create Client
        print("Creating App Client...")
        client_response = cognito.create_user_pool_client(
            UserPoolId=user_pool_id,
            ClientName=f"{PROJECT_NAME}-Web-App",
            GenerateSecret=False,
            ExplicitAuthFlows=[
                'ALLOW_USER_PASSWORD_AUTH', 
                'ALLOW_REFRESH_TOKEN_AUTH', 
                'ALLOW_USER_SRP_AUTH',
                'ALLOW_ADMIN_USER_PASSWORD_AUTH'
            ]
        )
        client_id = client_response['UserPoolClient']['ClientId']
        print(f"App Client Created: {client_id}")

        # Create admins Group
        print("Creating admins Group...")
        try:
            cognito.create_group(
                GroupName='admins',
                UserPoolId=user_pool_id,
                Description='Administrative users for Papercast'
            )
            print("admins Group Created.")
        except ClientError as e:
            if e.response['Error']['Code'] == 'GroupExistsException':
                print("Admins Group already exists.")
            else:
                print(f"Error creating Admins group: {e}")

        return user_pool_id, client_id
    except ClientError as e:
        print(f"Error creating Cognito resources: {e}")
        return None, None

def create_iam_role(iam):
    print("Creating IAM Role for EC2...")
    role_name = f"{PROJECT_NAME}-EC2-Role"
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [{"Effect": "Allow", "Principal": {"Service": "ec2.amazonaws.com"}, "Action": "sts:AssumeRole"}]
    }
    try:
        iam.create_role(RoleName=role_name, AssumeRolePolicyDocument=json.dumps(trust_policy))
        policies = [
            "arn:aws:iam::aws:policy/AmazonS3FullAccess",
            "arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess",
            "arn:aws:iam::aws:policy/AmazonPollyFullAccess",
            "arn:aws:iam::aws:policy/AmazonBedrockFullAccess",
            "arn:aws:iam::aws:policy/ComprehendFullAccess",
            "arn:aws:iam::aws:policy/TranslateFullAccess",
            "arn:aws:iam::aws:policy/AmazonCognitoPowerUser"
        ]
        for policy in policies:
            iam.attach_role_policy(RoleName=role_name, PolicyArn=policy)
        
        # Create Instance Profile
        iam.create_instance_profile(InstanceProfileName=role_name)
        iam.add_role_to_instance_profile(InstanceProfileName=role_name, RoleName=role_name)
        print(f"IAM Role and Instance Profile Created: {role_name}")
        return role_name
    except ClientError as e:
        if e.response['Error']['Code'] == 'EntityAlreadyExists':
            print("IAM Role already exists.")
            return role_name
        print(f"Error creating IAM role: {e}")
        return None

if __name__ == "__main__":
    try:
        s3 = boto3.client("s3", region_name=REGION)
        dynamodb = boto3.resource("dynamodb", region_name=REGION)
        cognito = boto3.client("cognito-idp", region_name=REGION)
        iam = boto3.client("iam", region_name=REGION)

        print("--- Starting AWS Infrastructure Setup ---")
        
        # 1. S3 Bucket
        bucket = create_s3_bucket(s3)
        
        # 2. DynamoDB
        table = create_dynamodb_table(dynamodb)

        # 3. Cognito
        user_pool_id, client_id = create_cognito_resources(cognito)

        # 4. IAM & EC2 Base
        role_name = create_iam_role(iam)

        print("\n--- Setup Complete ---")
        print(f"S3 Bucket: {bucket}")
        print(f"DynamoDB Table: {table}")
        print(f"User Pool ID: {user_pool_id}")
        print(f"Cognito Client ID: {client_id}")
        print(f"IAM Role: {role_name}")
        
        # Save output to file
        with open("infrastructure/aws_config.json", "w") as f:
            json.dump({
                "s3_bucket": bucket,
                "dynamodb_table": table,
                "user_pool_id": user_pool_id,
                "client_id": client_id,
                "iam_role": role_name,
                "region": REGION
            }, f, indent=4)
        print("Configuration saved to infrastructure/aws_config.json")

    except Exception as e:
        print(f"Setup Failed: {e}")
