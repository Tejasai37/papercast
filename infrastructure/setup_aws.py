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

def create_vpc(ec2):
    print(f"Creating VPC for {PROJECT_NAME}...")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    vpc.create_tags(Tags=[{"Key": "Name", "Value": f"{PROJECT_NAME}-VPC"}])
    vpc.wait_until_available()
    print(f"VPC Created: {vpc.id}")

    # Internet Gateway
    igw = ec2.create_internet_gateway()
    vpc.attach_internet_gateway(InternetGatewayId=igw.id)
    print(f"Internet Gateway Attached: {igw.id}")

    # Route Table
    route_table = vpc.create_route_table()
    route_table.create_route(DestinationCidrBlock="0.0.0.0/0", GatewayId=igw.id)
    print(f"Route Table Created: {route_table.id}")

    # Subnets (Public - Multi-AZ needed for ALB)
    subnets = []
    az_suffixes = ["a", "b"]
    for i, suffix in enumerate(az_suffixes):
        cidrs = [f"10.0.{i+1}.0/24"]
        subnet = vpc.create_subnet(CidrBlock=cidrs[0], AvailabilityZone=f"{REGION}{suffix}")
        subnet.create_tags(Tags=[{"Key": "Name", "Value": f"{PROJECT_NAME}-Public-Subnet-{suffix.upper()}"}])
        route_table.associate_with_subnet(SubnetId=subnet.id)
        subnets.append(subnet)
        print(f"Public Subnet {suffix.upper()} Created: {subnet.id}")

    return vpc, subnets

def create_security_group(ec2, vpc_id):
    print("Creating Security Groups...")
    # 1. ALB Security Group
    alb_sg = ec2.create_security_group(
        GroupName=f"{PROJECT_NAME}-ALB-SG",
        Description="Allow HTTP/HTTPS traffic to ALB",
        VpcId=vpc_id
    )
    alb_sg.authorize_ingress(
        IpPermissions=[
            {'IpProtocol': 'tcp', 'FromPort': 80, 'ToPort': 80, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
            {'IpProtocol': 'tcp', 'FromPort': 443, 'ToPort': 443, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}
        ]
    )
    
    # 2. EC2 Security Group
    ec2_sg = ec2.create_security_group(
        GroupName=f"{PROJECT_NAME}-EC2-SG",
        Description="Allow SSH and traffic from ALB",
        VpcId=vpc_id
    )
    ec2_sg.authorize_ingress(
        IpPermissions=[
            {'IpProtocol': 'tcp', 'FromPort': 22, 'ToPort': 22, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
            {'IpProtocol': 'tcp', 'FromPort': 80, 'ToPort': 80, 'UserIdGroupPairs': [{'GroupId': alb_sg.id}]}, # Traffic from ALB
            {'IpProtocol': 'tcp', 'FromPort': 8000, 'ToPort': 8000, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]} # Debugging
        ]
    )
    print(f"Security Groups Created: ALB({alb_sg.id}), EC2({ec2_sg.id})")
    return alb_sg.id, ec2_sg.id

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
            "arn:aws:iam::aws:policy/AmazonCognitoPowerUser",
            "arn:aws:iam::aws:policy/CloudWatchLogsFullAccess"
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

def create_alb(elbv2, subnets, sg_id, vpc_id):
    print("Creating Application Load Balancer...")
    try:
        # 1. Target Group
        tg_response = elbv2.create_target_group(
            Name=f"{PROJECT_NAME}-TG",
            Protocol='HTTP',
            Port=80,
            VpcId=vpc_id,
            HealthCheckPath='/',
            TargetType='instance'
        )
        tg_arn = tg_response['TargetGroups'][0]['TargetGroupArn']
        print(f"Target Group Created: {tg_arn}")

        # 2. ALB
        subnet_ids = [s.id for s in subnets]
        alb_response = elbv2.create_load_balancer(
            Name=f"{PROJECT_NAME}-ALB",
            Subnets=subnet_ids,
            SecurityGroups=[sg_id],
            Scheme='internet-facing',
            Type='application',
            IpAddressType='ipv4'
        )
        alb_arn = alb_response['LoadBalancers'][0]['LoadBalancerArn']
        alb_dns = alb_response['LoadBalancers'][0]['DNSName']
        print(f"ALB Created: {alb_dns}")

        # 3. Listener
        elbv2.create_listener(
            LoadBalancerArn=alb_arn,
            Protocol='HTTP',
            Port=80,
            DefaultActions=[{'Type': 'forward', 'TargetGroupArn': tg_arn}]
        )
        return alb_arn, alb_dns, tg_arn
    except ClientError as e:
        print(f"Error creating ALB: {e}")
        return None, None, None

def create_asg(asg_client, tg_arn, subnets, role_name, sg_id):
    print("Creating Auto Scaling Group...")
    lt_name = f"{PROJECT_NAME}-LT"
    asg_name = f"{PROJECT_NAME}-ASG"
    try:
        # 1. Launch Template
        asg_client.create_launch_template(
            LaunchTemplateName=lt_name,
            LaunchTemplateData={
                'ImageId': 'ami-0bb84387b76a46159', # Amazon Linux 2023
                'InstanceType': 't2.micro',
                'KeyName': 'papercast-key',
                'SecurityGroupIds': [sg_id],
                'IamInstanceProfile': {'Name': role_name},
                'TagSpecifications': [{
                    'ResourceType': 'instance',
                    'Tags': [{'Key': 'Name', 'Value': f"{PROJECT_NAME}-ASG-Node"}]
                }]
            }
        )
        print(f"Launch Template Created: {lt_name}")

        # 2. Auto Scaling Group
        subnet_ids = ",".join([s.id for s in subnets])
        asg_client.create_auto_scaling_group(
            AutoScalingGroupName=asg_name,
            LaunchTemplate={'LaunchTemplateName': lt_name, 'Version': '$Default'},
            MinSize=1,
            MaxSize=2,
            DesiredCapacity=1,
            VPCZoneIdentifier=subnet_ids,
            TargetGroupARNs=[tg_arn]
        )
        print(f"ASG Created: {asg_name}")
        return asg_name
    except ClientError as e:
        print(f"Error creating ASG: {e}")
        return None

if __name__ == "__main__":
    try:
        ec2_res = boto3.resource("ec2", region_name=REGION)
        ec2_cli = boto3.client("ec2", region_name=REGION)
        s3 = boto3.client("s3", region_name=REGION)
        dynamodb = boto3.resource("dynamodb", region_name=REGION)
        cognito = boto3.client("cognito-idp", region_name=REGION)
        iam = boto3.client("iam", region_name=REGION)
        elbv2 = boto3.client("elbv2", region_name=REGION)
        asg_client = boto3.client("autoscaling", region_name=REGION)

        print("--- Starting AWS Infrastructure Setup ---")
        
        # 1. VPC & Network
        vpc, subnets = create_vpc(ec2_res)
        
        # 2. Security Groups
        alb_sg_id, ec2_sg_id = create_security_group(ec2_res, vpc.id)
        
        # 3. S3 Bucket
        bucket = create_s3_bucket(s3)
        
        # 4. DynamoDB
        table = create_dynamodb_table(dynamodb)

        # 5. Cognito
        user_pool_id, client_id = create_cognito_resources(cognito)

        # 6. IAM & EC2 Base
        role_name = create_iam_role(iam)
        
        # 7. ALB & ASG (Phase 6 High Availability)
        alb_arn, alb_dns, tg_arn = create_alb(elbv2, subnets, alb_sg_id, vpc.id)
        asg_name = create_asg(asg_client, tg_arn, subnets, role_name, ec2_sg_id)

        print("\n--- Setup Complete ---")
        print(f"VPC ID: {vpc.id}")
        print(f"ALB DNS: {alb_dns}")
        print(f"S3 Bucket: {bucket}")
        print(f"User Pool ID: {user_pool_id}")
        
        # Save output to file
        with open("infrastructure/aws_config.json", "w") as f:
            json.dump({
                "vpc_id": vpc.id,
                "subnets": [s.id for s in subnets],
                "alb_sg_id": alb_sg_id,
                "ec2_sg_id": ec2_sg_id,
                "s3_bucket": bucket,
                "dynamodb_table": table,
                "user_pool_id": user_pool_id,
                "client_id": client_id,
                "iam_role": role_name,
                "alb_dns": alb_dns,
                "asg_name": asg_name,
                "region": REGION
            }, f, indent=4)
        print("Configuration saved to infrastructure/aws_config.json")

    except Exception as e:
        print(f"Setup Failed: {e}")

    except Exception as e:
        print(f"Setup Failed: {e}")
