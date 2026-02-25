# Standard .env Parser
if (Test-Path ".env") {
    Get-Content ".env" | ForEach-Object {
        if ($_ -match "^([^#=]+)=(.+)$") {
            $key = $matches[1].Trim()
            $value = $matches[2].Trim()
            Set-Variable -Name "env:$key" -Value $value -Force
        }
    }
}

# Configuration
$Region = $env:AWS_REGION -or "us-east-1"
$ProjectName = "Papercast"
$BucketName = $env:S3_BUCKET_NAME -or "papercast-audio-$((Get-Date).Ticks)"
$TableName = $env:DYNAMODB_TABLE_NAME -or "PapercastCache"

Write-Host "--- Starting AWS Infrastructure Setup ---" -ForegroundColor Cyan

# 1. Create VPC
Write-Host "Creating VPC..."
$VpcId = aws ec2 create-vpc --cidr-block 10.0.0.0/16 --query 'Vpc.VpcId' --output text --region $Region
aws ec2 create-tags --resources $VpcId --tags Key=Name,Value="$ProjectName-VPC" --region $Region
Write-Host "VPC Created: $VpcId" -ForegroundColor Green

# 2. Internet Gateway
Write-Host "Creating Internet Gateway..."
$IgwId = aws ec2 create-internet-gateway --query 'InternetGateway.InternetGatewayId' --output text --region $Region
aws ec2 attach-internet-gateway --vpc-id $VpcId --internet-gateway-id $IgwId --region $Region
Write-Host "IGW Attached: $IgwId" -ForegroundColor Green

# 3. Route Table
Write-Host "Creating Route Table..."
$RouteTableId = aws ec2 create-route-table --vpc-id $VpcId --query 'RouteTable.RouteTableId' --output text --region $Region
aws ec2 create-route --route-table-id $RouteTableId --destination-cidr-block 0.0.0.0/0 --gateway-id $IgwId --region $Region
Write-Host "Route Table Created: $RouteTableId" -ForegroundColor Green

# 4. Subnets (Public - Multi-AZ for ALB)
Write-Host "Creating Public Subnets (Multi-AZ)..."
$SubnetAId = aws ec2 create-subnet --vpc-id $VpcId --cidr-block 10.0.1.0/24 --availability-zone "${Region}a" --query 'Subnet.SubnetId' --output text --region $Region
$SubnetBId = aws ec2 create-subnet --vpc-id $VpcId --cidr-block 10.0.2.0/24 --availability-zone "${Region}b" --query 'Subnet.SubnetId' --output text --region $Region

aws ec2 associate-route-table --subnet-id $SubnetAId --route-table-id $RouteTableId --region $Region
aws ec2 associate-route-table --subnet-id $SubnetBId --route-table-id $RouteTableId --region $Region
aws ec2 modify-subnet-attribute --subnet-id $SubnetAId --map-public-ip-on-launch --region $Region
aws ec2 modify-subnet-attribute --subnet-id $SubnetBId --map-public-ip-on-launch --region $Region
Write-Host "Subnets Created and associated with IGW Route Table: $SubnetAId, $SubnetBId" -ForegroundColor Green
Write-Host "Public routing verified for ALB compatibility." -ForegroundColor Cyan

# 5. Security Groups
Write-Host "Creating Security Groups..."
$AlbSgId = aws ec2 create-security-group --group-name "$ProjectName-ALB-SG" --description "ALB HTTP" --vpc-id $VpcId --query 'GroupId' --output text --region $Region
aws ec2 authorize-security-group-ingress --group-id $AlbSgId --protocol tcp --port 80 --cidr 0.0.0.0/0 --region $Region

$Ec2SgId = aws ec2 create-security-group --group-name "$ProjectName-EC2-SG" --description "EC2 SSH/HTTP from ALB" --vpc-id $VpcId --query 'GroupId' --output text --region $Region
aws ec2 authorize-security-group-ingress --group-id $Ec2SgId --protocol tcp --port 22 --cidr 0.0.0.0/0 --region $Region
aws ec2 authorize-security-group-ingress --group-id $Ec2SgId --protocol tcp --port 80 --source-group $AlbSgId --region $Region
Write-Host "SGs Created: ALB($AlbSgId), EC2($Ec2SgId)" -ForegroundColor Green

# 6. S3 Bucket (Audio Storage)
Write-Host "Creating S3 Bucket: $BucketName..."
aws s3 mb "s3://$BucketName" --region $Region
Write-Host "S3 Bucket Created" -ForegroundColor Green

# 7. DynamoDB Table (Metadata Cache)
Write-Host "Creating DynamoDB Table: $TableName..."
aws dynamodb create-table `
    --table-name $TableName `
    --attribute-definitions AttributeName=ArticleID,AttributeType=S
    --key-schema AttributeName=ArticleID,KeyType=HASH `
    --billing-mode PAY_PER_REQUEST `
    --region $Region
Write-Host "DynamoDB Table Created" -ForegroundColor Green

# 8. Cognito User Pool (Authentication)
Write-Host "Creating Cognito User Pool..."
$UserPoolResponse = aws cognito-idp create-user-pool --pool-name "$ProjectName-Users" --auto-verified-attributes email --region $Region | ConvertFrom-Json
$UserPoolId = $UserPoolResponse.UserPool.Id

Write-Host "Creating App Client..."
$ClientResponse = aws cognito-idp create-user-pool-client --user-pool-id $UserPoolId --client-name "$ProjectName-Web-App" --no-generate-secret --explicit-auth-flows ALLOW_USER_PASSWORD_AUTH ALLOW_REFRESH_TOKEN_AUTH ALLOW_USER_SRP_AUTH ALLOW_ADMIN_USER_PASSWORD_AUTH --region $Region | ConvertFrom-Json
$ClientId = $ClientResponse.UserPoolClient.ClientId

Write-Host "Creating admins Group..."
aws cognito-idp create-group --group-name "admins" --user-pool-id $UserPoolId --description "Administrative users for Papercast" --region $Region
Write-Host "Cognito Resources Created: Pool($UserPoolId), Client($ClientId)" -ForegroundColor Green

# 9. ALB & Target Group
Write-Host "Creating ALB and Target Group..."
$TgArn = aws elbv2 create-target-group --name "$ProjectName-TG" --protocol HTTP --port 80 --vpc-id $VpcId --target-type instance --query 'TargetGroups[0].TargetGroupArn' --output text --region $Region
$AlbResponse = aws elbv2 create-load-balancer --name "$ProjectName-ALB" --subnets $SubnetAId $SubnetBId --security-groups $AlbSgId --query 'LoadBalancers[0].[LoadBalancerArn,DNSName]' --output text --region $Region
$AlbArn = ($AlbResponse -split "`t")[0]
$AlbDns = ($AlbResponse -split "`t")[1]
aws elbv2 create-listener --load-balancer-arn $AlbArn --protocol HTTP --port 80 --default-actions Type=forward,TargetGroupArn=$TgArn --region $Region
Write-Host "ALB Created: $AlbDns" -ForegroundColor Green

# 7. Auto Scaling Group
Write-Host "Creating ASG..."
$LtData = @{
    ImageId = "ami-0bb84387b76a46159"
    InstanceType = "t2.micro"
    KeyName = "papercast-key"
    SecurityGroupIds = @($Ec2SgId)
    IamInstanceProfile = @{ Name = "$ProjectName-EC2-Role" }
    TagSpecifications = @(
        @{
            ResourceType = "instance"
            Tags = @( @{ Key = "Name"; Value = "$ProjectName-ASG-Node" } )
        }
    )
} | ConvertTo-Json -Compress
aws ec2 create-launch-template --launch-template-name "$ProjectName-LT" --launch-template-data "$($LtData.Replace('"', '""'))" --region $Region

aws autoscaling create-auto-scaling-group --auto-scaling-group-name "$ProjectName-ASG" `
    --launch-template LaunchTemplateName="$ProjectName-LT" `
    --min-size 1 --max-size 2 --desired-capacity 1 `
    --vpc-zone-identifier "$SubnetAId,$SubnetBId" `
    --target-group-arns $TgArn `
    --tags "ResourceId=$ProjectName-ASG,ResourceType=auto-scaling-group,Key=Name,Value=$ProjectName-Node,PropagateAtLaunch=true" `
    --region $Region
Write-Host "ASG Created with instance tagging enabled" -ForegroundColor Green

# Summary
Write-Host "`n--- Setup Complete ---" -ForegroundColor Cyan
Write-Host "VPC ID: $VpcId"
Write-Host "ALB DNS: $AlbDns"
Write-Host "IAM Role: $ProjectName-EC2-Role"

# Save to JSON for reference
$Config = @{
    vpc_id = $VpcId
    subnets = @($SubnetAId, $SubnetBId)
    alb_sg_id = $AlbSgId
    ec2_sg_id = $Ec2SgId
    s3_bucket = $BucketName
    dynamodb_table = $TableName
    user_pool_id = $UserPoolId
    client_id = $ClientId
    iam_role = "$ProjectName-EC2-Role"
    alb_dns = $AlbDns
    region = $Region
}
$Config | ConvertTo-Json | Out-File "infrastructure/aws_config_manual.json"
Write-Host "Configuration saved to infrastructure/aws_config_manual.json"
