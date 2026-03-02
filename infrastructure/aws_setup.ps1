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

# 1. S3 Bucket (Audio Storage)
Write-Host "Creating S3 Bucket: $BucketName..."
aws s3 mb "s3://$BucketName" --region $Region
Write-Host "S3 Bucket Created" -ForegroundColor Green

# 2. DynamoDB Table (Metadata Cache)
Write-Host "Creating DynamoDB Table: $TableName..."
aws dynamodb create-table `
    --table-name $TableName `
    --attribute-definitions AttributeName=ArticleID,AttributeType=S
    --key-schema AttributeName=ArticleID,KeyType=HASH `
    --billing-mode PAY_PER_REQUEST `
    --region $Region
Write-Host "DynamoDB Table Created" -ForegroundColor Green

# 3. Cognito User Pool (Authentication)
Write-Host "Creating Cognito User Pool..."
$UserPoolResponse = aws cognito-idp create-user-pool --pool-name "$ProjectName-Users" --auto-verified-attributes email --region $Region | ConvertFrom-Json
$UserPoolId = $UserPoolResponse.UserPool.Id

Write-Host "Creating App Client..."
$ClientResponse = aws cognito-idp create-user-pool-client --user-pool-id $UserPoolId --client-name "$ProjectName-Web-App" --no-generate-secret --explicit-auth-flows ALLOW_USER_PASSWORD_AUTH ALLOW_REFRESH_TOKEN_AUTH ALLOW_USER_SRP_AUTH ALLOW_ADMIN_USER_PASSWORD_AUTH --region $Region | ConvertFrom-Json
$ClientId = $ClientResponse.UserPoolClient.ClientId

Write-Host "Creating admins Group..."
aws cognito-idp create-group --group-name "admins" --user-pool-id $UserPoolId --description "Administrative users for Papercast" --region $Region
Write-Host "Cognito Resources Created: Pool($UserPoolId), Client($ClientId)" -ForegroundColor Green

# Summary
Write-Host "`n--- Setup Complete ---" -ForegroundColor Cyan
Write-Host "S3 Bucket: $BucketName"
Write-Host "DynamoDB Table: $TableName"
Write-Host "User Pool ID: $UserPoolId"
Write-Host "Cognito Client ID: $ClientId"

# Save to JSON for reference
$Config = @{
    s3_bucket = $BucketName
    dynamodb_table = $TableName
    user_pool_id = $UserPoolId
    client_id = $ClientId
    region = $Region
}
$Config | ConvertTo-Json | Out-File "infrastructure/aws_config_manual.json"
Write-Host "Configuration saved to infrastructure/aws_config_manual.json"
