# Manual AWS Infrastructure Setup Guide

This document provides step-by-step instructions for creating the project infrastructure using the AWS Management Console.

## 1. Create a VPC (Network)
1.  **Navigate to VPC Dashboard**: Search for "VPC" in the top bar.
2.  **Create VPC**:
    -   Click **Create VPC**.
    -   Select **VPC only**.
    -   **Name tag**: `Papercast-VPC`.
    -   **IPv4 CIDR block**: `10.0.0.0/16`.
    -   Leave other settings as default.
    -   Click **Create VPC**.

### 1.1 Create Public Subnets (Multi-AZ)
1.  In the left menu, click **Subnets** > **Create subnet**.
2.  **VPC ID**: Select `Papercast-VPC`.
3.  **Subnet 1**:
    -   **Subnet name**: `Papercast-Public-Subnet-A`.
    -   **Availability Zone**: Select `us-east-1a`.
    -   **IPv4 CIDR block**: `10.0.1.0/24`.
4.  **Add new subnet** (Subnet 2):
    -   **Subnet name**: `Papercast-Public-Subnet-B`.
    -   **Availability Zone**: Select `us-east-1b`.
    -   **IPv4 CIDR block**: `10.0.2.0/24`.
5.  Click **Create subnet**.
6.  **Enable Auto-assign Public IP** for **BOTH** subnets:
    -   Select a subnet > **Actions** > **Edit subnet settings**.
    -   Check **Enable auto-assign public IPv4 address**.
    -   Click **Save**.

### 1.2 Setup Internet Gateway (IGW)
1.  Click **Internet gateways** > **Create internet gateway**.
2.  **Name tag**: `Papercast-IGW`.
3.  Click **Create internet gateway**.
4.  **Attach to VPC**:
    -   Click **Actions** > **Attach to VPC** > select `Papercast-VPC`.

### 1.3 Configure Route Table
1.  Click **Route tables** > Select the **Main** route table for `Papercast-VPC`.
2.  **Edit Routes**: Add `0.0.0.0/0` -> `Internet Gateway` (`Papercast-IGW`).
3.  **Associate Subnets**:
    -   Click **Subnet associations** > **Edit subnet associations**.
    -   Select **BOTH** `Papercast-Public-Subnet-A` and `B`.
    -   Click **Save**.

---

## 2. Create Security Groups
### 2.1 ALB Security Group (Public)
1.  **Name**: `Papercast-ALB-SG`.
2.  **VPC**: `Papercast-VPC`.
3.  **Inbound Rules**:
    -   HTTP (80) | `0.0.0.0/0`.
    -   HTTPS (443) | `0.0.0.0/0`.

### 2.2 EC2 Security Group (Private/Internal)
1.  **Name**: `Papercast-EC2-SG`.
2.  **VPC**: `Papercast-VPC`.
3.  **Inbound Rules**:
    -   SSH (22) | `My IP`.
    -   HTTP (80) | Custom: Type `Papercast-ALB-SG` (Allows only traffic from the Load Balancer).
    -   Custom TCP (8000) | `0.0.0.0/0` (Testing).

---

## 3. Create S3 Bucket (Audio Storage)
1.  Search for "S3" in the top bar.
2.  Click **Create bucket**.
3.  **Bucket name**: `papercast-audio-[your-unique-suffix]` (Must be globally unique!).
4.  **Region**: Ensure it matches your VPC region (e.g., `us-east-1`).
5.  **Block Public Access**: Keep **Block all public access** checked (Recommended).
6.  Click **Create bucket`.

---

## 4. Create DynamoDB Table (Metadata Cache)
1.  Search for "DynamoDB" in the top bar.
2.  Click **Create table`.
3.  **Table name**: `PapercastCache`.
4.  **Partition key**: `ArticleID` (String).
    -   Leave Sort key empty.
5.  **Table settings**: Default settings are fine for now.
6.  Click **Create table`.

---

## 5. Create Amazon Cognito User Pool (Authentication)
1.  Search for "Cognito" > **Create user pool**.
2.  **Step 1: Configure sign-in experience**:
    -   **Authentication providers**: Select **Cognito user pool**.
    -   **Cognito user pool sign-in options**: Check **User name**. 
    -   Click **Next**.
3.  **Step 2: Configure security requirements**:
    -   **Password policy**: Keep **Cognito default**.
    -   **Multi-factor authentication (MFA)**: Select **No MFA** (for development).
    -   **User recovery**: Keep defaults.
    -   Click **Next**.
4.  **Step 3: Configure sign-up experience**:
    -   **Self-service sign-up**: Keep **Enabled**.
    -   **Attribute verification**: Keep defaults.
    -   **Required attributes**: Click **Next**.
5.  **Step 4: Configure message delivery**:
    -   **Email**: Select **Send email with Cognito**.
    -   Click **Next**.
6.  **Step 5: Integrate your app**:
    -   **User pool name**: `Papercast-Users`.
    -   **Initial app client**: 
        -   **App type**: Select **Public client**.
        -   **App client name**: `Papercast-Web-App`.
        -   **Client secret**: Select **Don't generate a client secret**.
    -   Click **Next**.
7.  **Step 6: Review and create**:
    -   Scroll to bottom > **Create user pool**.

---

## 6. Create IAM Role (API Permissions)
1.  Search for "IAM" in the top bar.
2.  Click **Roles** > **Create role`.
3.  **Step 1: Select trusted entity**:
    -   Keep **AWS service**.
    -   Under **Service or use case**, select **EC2**.
    -   Click **Next`.
4.  **Step 2: Add permissions**:
    -   Search and check: `AmazonS3FullAccess`.
    -   Search and check: `AmazonDynamoDBFullAccess`.
    -   Search and check: `AmazonPollyFullAccess`.
    -   Search and check: `AmazonBedrockFullAccess`.
    -   Search and check: `AmazonCognitoPowerUser`.
    -   Search and check: `CloudWatchLogsFullAccess`.
5.  **Step 3: Name, review, and create**:
    -   **Role name**: `Papercast-EC2-Role`.
    -   Click **Create role`.

---

## 7. Create Application Load Balancer (ALB)
1.  Search for "EC2" > **Target Groups** > **Create target group**.
    -   **Choose a target type**: `Instances`.
    -   **Name**: `Papercast-TG`.
    -   **Health check path**: `/`.
    -   Click **Next** > **Create target group** (Wait to register instances later).
2.  **Load Balancers** > **Create load balancer**.
    -   **Type**: `Application Load Balancer`.
    -   **Name**: `Papercast-ALB`.
    -   **Network mapping**: Select `Papercast-VPC` and check **BOTH** subnets (`A` and `B`).
    -   **Security groups**: Remove default and select `Papercast-ALB-SG`.
    -   **Listeners and routing**: HTTP:80 -> Forward to `Papercast-TG`.
    -   Click **Create load balancer**.

---

## 8. Create Auto Scaling Group (ASG)
1.  **Launch Templates** > **Create launch template**.
    -   **Name**: `Papercast-LT`.
    -   **AMI**: Amazon Linux 2023.
    -   **Instance type**: `t2.micro`.
    -   **Key pair**: `papercast-key`.
    -   **Security groups**: `Papercast-EC2-SG`.
    -   **Advanced details** > **IAM instance profile**: `Papercast-EC2-Role`.
    -   Click **Create launch template**.
2.  **Auto Scaling Groups** > **Create Auto Scaling group**.
    -   **Launch template**: `Papercast-LT`.
    -   **VPC**: `Papercast-VPC` > Select **BOTH** subnets.
    -   **Load balancing**: **Attach to an existing load balancer** > `Papercast-TG`.
    -   **Desired/Min/Max**: `1` / `1` / `2`.
    -   Click **Create Auto Scaling group**.

---

## 9. Setup Route 53 & SSL (Optional/Production)
1.  **Route 53**:
    -   Create a **Hosted Zone** for your domain (e.g., `mydomain.com`).
    -   Create an **A Record** (Alias) > Select **Alias to Application Load Balancer`.
2.  **ACM (Certificate Manager)**:
    -   Request a public certificate for your domain.
    -   Follow DNS validation instructions in Route 53.
3.  **ALB HTTPS Listener**:
    -   Go to `Papercast-ALB` > **Listeners** > **Add listener`.
    -   HTTPS:443 -> Forward to `Papercast-TG`.
    -   Select the certificate from ACM.

---

## 10. Local Environment Configuration
After setting up the AWS resources, you must configure your local application to talk to them.

1.  **Create `.env` File**: 
    -   Copy the template: `cp .env.example .env`.
2.  **Fill in Resource Details**:
    -   `NEWS_API_KEY`: Your key from NewsAPI.org.
    -   `USE_REAL_AWS`: Set to `true` to use your cloud setup.
    -   `S3_BUCKET_NAME`: The name of the bucket you created in Section 3.
    -   `DYNAMODB_TABLE_NAME`: `PapercastCache` (Section 4).
    -   `COGNITO_USER_POOL_ID`: The ID from the User Pool (Section 5).
    -   `COGNITO_CLIENT_ID`: The App Client ID (Section 5).
    -   `AWS_REGION`: e.g., `us-east-1`.

---

## 11. Setting up Administrative Access
The application uses **Cognito Groups** to determine who is an admin.

1.  **Create admins Group**:
    -   In your User Pool dashboard, click the **Groups** tab.
    -   Click **Create group**.
    -   **Group name**: `admins` (Must be exact!).
    -   Click **Create group**.
2.  **Promote a User**:
    -   Click the **Users** tab.
    -   Click on your username.
    -   Click **Add user to group**.
    -   Select `admins`.
    -   Click **Add**.

Now, when you log in with that user, the Papercast dashboard will automatically recognize you as an administrator!

---

## Verification Checklist
- [x] VPC created with 2 Public Subnets in different AZs?
- [x] Auto-assign Public IP enabled for both subnets?
- [x] Internet Gateway attached and Route Table configured for both?
- [x] ALB Security Group allows 80/443 from anywhere?
- [x] EC2 Security Group allows 80 only from the ALB SG?
- [x] S3 Bucket & DynamoDB Table `PapercastCache` ready?
- [x] Cognito User Pool and App Client ready?
- [x] IAM Role `Papercast-EC2-Role` with full access attached to Launch Template?
- [x] ALB is "Active" and DNS name is working?
- [x] ASG is successfully launching a node into the Target Group?
- [x] Local `.env` file is populated with all the IDs above?
