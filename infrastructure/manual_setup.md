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

> [!IMPORTANT]
> **VERIFY PUBLIC ROUTING**: Click the **Routes** tab for this route table. You **MUST** see a destination `0.0.0.0/0` targeting your `Papercast-IGW`. Without this, your Load Balancer will not be accessible from the internet.

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

### 5.1 Create admins Group
1.  In your User Pool dashboard, click the **Groups** tab.
2.  Click **Create group**.
3.  **Group name**: `admins` (Must be exact!).
4.  Click **Create group**.

### 5.2 Promote a User
1.  Click the **Users** tab.
2.  Click on your username.
3.  Click **Add user to group**.
4.  Select `admins`.
5.  Click **Add**.

*Now, when you log in with that user, the Papercast dashboard will automatically recognize you as an administrator!*

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
    -   **Protocol**: `HTTP`.
    -   **Port**: `80`.
    -   **VPC**: Select `Papercast-VPC`.
    -   **Health check path**: `/`.
    -   Click **Next** > **Create target group** (Wait to register instances later).
2.  **Load Balancers** > **Create load balancer**.
    -   **Type**: `Application Load Balancer`.
    -   **Name**: `Papercast-ALB`.
    -   **Network mapping**: Select `Papercast-VPC` and check **BOTH** subnets (`A` and `B`).
    -   **Security groups**: Remove default and select `Papercast-ALB-SG`.
    -   **Listeners and routing**: HTTP:80 -> Forward to `Papercast-TG`.
    -   Click **Create load balancer**.
    
> [!TIP]
> **"No Route to Internet Gateway" Warning?**: If you see this warning, go back to **Section 1.3** and ensure your Route Table has a `0.0.0.0/0` path to the Internet Gateway and that both subnets are explicitly associated.
---

## 8. Create Auto Scaling Group (ASG)
1.  **Launch Templates** > **Create launch template**.
    -   **Name**: `Papercast-LT`.
    -   **AMI**: Amazon Linux 2023 (Select the one with **Kernel 6.1** - it is the standard LTS version).
    -   **Instance type**: `t2.micro`.
    -   **Key pair**: `papercast-key`.
    -   **Security groups**: `Papercast-EC2-SG`.
    -   **Advanced details** > **IAM instance profile**: `Papercast-EC2-Role`.
    -   **Tags**: Add Tag -> Key: `Name` | Value: `Papercast-ASG-Node`. (Check "Instances" and "Volumes").
    -   Click **Create launch template**.
2.  **Auto Scaling Groups** > **Create Auto Scaling group**.
    -   **Auto Scaling group name**: `Papercast-ASG`.
    -   **Launch template**: `Papercast-LT`.
    -   **VPC**: `Papercast-VPC` > Select **BOTH** subnets.
    -   **Load balancing**: **Attach to an existing load balancer** > `Papercast-TG`.
    -   **Target Group Health Checks**: Check **ELB**.
    -   **Desired/Min/Max**: `1` / `1` / `2`.
    -   **Step 6: Add Tags**: 
        -   Add Tag -> Key: `Name` | Value: `Papercast-Node`.
        -   Ensure **Propagate at launch** is checked.
    -   Click **Create Auto Scaling group**.

---

## 9. Setup Route 53 & SSL (Optional/Production)
> [!NOTE]
> **PRICING ALERT**: Route 53 Hosted Zones cost **$0.50 per month** (not prorated). This is one of the few AWS services not covered by the 100% free tier. If you don't want to pay this, you can skip to **Section 11** and just use your ALB's DNS name for testing.

### 9.1 Register/Setup Domain
1.  Search for "Route 53" in the top bar.
2.  Click **Hosted zones** > **Create hosted zone**.
3.  **Domain name**: Enter your domain (e.g., `papercast.live`).
4.  **Type**: Public hosted zone.
5.  Click **Create hosted zone**.
    *   *Note: If you bought your domain elsewhere, you must point your NS records to the 4 name servers listed in Route 53.*

### 9.2 Request SSL Certificate (ACM)
1.  Search for "Certificate Manager" > **Request certificate**.
2.  Select **Request a public certificate**.
3.  **Fully qualified domain name**: `*.yourdomain.com` and `yourdomain.com`.
4.  **Validation method**: DNS validation.
5.  Click **Request**.
6.  Once created, click the certificate ID > **Create records in Route 53** > **Create records**.
    *   *Wait for Status to become "Issued".*

### 9.3 Point Domain to Load Balancer
1.  Go back to **Route 53** > **Hosted zones** > Select your zone.
2.  Click **Create record**.
3.  **Record type**: `A`.
4.  **Alias**: Toggle **ON**.
5.  **Route traffic to**:
    -   Alias to Application and Classic Load Balancer.
    -   Region: (e.g., `us-east-1`).
    -   Select `Papercast-ALB`.
6.  Click **Create records**.

---

## 10. Enable HTTPS on Load Balancer
> [!WARNING]
> **DOMAIN REQUIRED**: You **CANNOT** use AWS Certificate Manager (ACM) for the default ALB DNS name (the one ending in `.elb.amazonaws.com`). To use Section 10, you **MUST** own a custom domain. If you do not have a domain, you cannot enable HTTPS/SSL through ACM.

1.  G0 to **EC2** > **Load Balancers** > `Papercast-ALB`.
2.  Click **Listeners** tab > **Add listener**.
3.  **Protocol**: `HTTPS` (Port 443).
4.  **Default actions**: Forward to `Papercast-TG`.
5.  **Secure listener settings**: Select the certificate you created in ACM.
6.  Click **Add**.
7.  *(Optional)* Update the HTTP:80 listener to "Redirect" to HTTPS:443 for security.

---

## 11. Local Environment Configuration
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

## 12. Manual Server Setup & Deployment
### 12.1 Connect to Instance
Choose one of the two methods below:

#### **Option A: EC2 Instance Connect (Easiest)**
1.  Go to **EC2 Console** > **Instances** > Select `Papercast-Node`.
2.  Click **Connect** > Select **EC2 Instance Connect** > Click **Connect**.
3.  A terminal will open directly in your browser.

#### **Option B: SSH (From Your Local Terminal)**
1.  Open powershell/terminal on your computer and navigate to the folder containing your `.pem` file.
2.  **Set Permissions** (Required on Windows):
    ```powershell
    icacls.exe papercast-key.pem /inheritance:r /grant:r "$($env:username):(R)"
    ```
3.  **Get Public IP**: Copy the "Public IPv4 address" from your instance dashboard.
4.  **Connect**:
    ```bash
    ssh -i "papercast-key.pem" ec2-user@[YOUR_PUBLIC_IP]
    ```

### 12.2 Install System Dependencies
Run these commands in the terminal:
```bash
sudo dnf update -y
sudo dnf install -y python3.11 python3.11-pip git nginx
```

### 12.3 Clone & Setup Application
```bash
# Clone directly from your repo
git clone [YOUR_REPO_URL] papercast
cd papercast

# Setup Virtual Environment
python3.11 -m venv papercast_venv
source papercast_venv/bin/activate
pip install -r requirements.txt
```

### 12.4 Configure Environment
> [!IMPORTANT]
> **SERVER SECURITY**: Since your EC2 instance uses an **IAM Role**, you **DO NOT** need to put `AWS_ACCESS_KEY_ID` or `AWS_SECRET_ACCESS_KEY` in the server's `.env` file. Leave them blank or remove them entirely; the app will automatically use the role!

1. Create the `.env` file:
```bash
nano .env
```
2. Paste your content (keep `SUMMARY`, `S3`, `DYNAMO`, `COGNITO` info, but **remove** the AWS Keys):
```bash
# Example server .env
NEWS_API_KEY=...
USE_REAL_AWS=true
AWS_REGION=us-east-1
S3_BUCKET_NAME=...
# ... (No access keys needed here!)
```

### 12.5 Setup Gunicorn (Systemd)
- Create a service file:
```bash
sudo nano /etc/systemd/system/papercast.service
```
- Paste this content:
```ini
[Unit]
Description=Gunicorn instance to serve Papercast
After=network.target

[Service]
User=ec2-user
Group=ec2-user
WorkingDirectory=/home/ec2-user/papercast
Environment="PATH=/home/ec2-user/papercast/papercast_venv/bin"
ExecStart=/home/ec2-user/papercast/papercast_venv/bin/gunicorn --workers 3 --bind 0.0.0.0:8000 backend.main:app -k uvicorn.workers.UvicornWorker

[Install]
WantedBy=multi-user.target
```
- Start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl start papercast
sudo systemctl enable papercast
```
- Verify the service is running:
```bash
sudo systemctl status papercast
```

### 12.6 Setup Nginx Reverse Proxy
- Create Nginx config:
```bash
sudo nano /etc/nginx/conf.d/papercast.conf
```
- Paste this content:
```nginx
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```
- Restart Nginx:
```bash
sudo systemctl restart nginx
sudo systemctl enable nginx
```
- Verify the service is running:
```bash
sudo systemctl status nginx
```

---

## 14. Pausing the Station (Cost Savings)
If you are not using the app and want to ensure 0% chance of charges, follow these steps to "Hibernate" your setup without losing your manual installation.

### 14.1 To STOP the App
1.  **Suspend ASG**: 
    - Go to **Auto Scaling Groups** > Select `Papercast-ASG`.
    - Go to the **Details** tab > **Advanced configurations** > **Edit**.
    - Find **Suspended processes** and select: `Launch` and `Terminate`.
    - Click **Update**. (This prevents AWS from trying to "fix" the server when you stop it).
2.  **Stop the Instance**:
    - Go to **EC2 Instances** > Select your `Papercast-Node`.
    - **Instance state** > **Stop instance**.

### 14.2 To START the App
1.  **Start the Instance**:
    - Go to **EC2 Instances** > Select your `Papercast-Node`.
    - **Instance state** > **Start instance**.
2.  **Resume ASG**:
    - Go to **Auto Scaling Groups** > Select `Papercast-ASG` > **Details** > **Edit**.
    - **Remove** the `Launch` and `Terminate` from Suspended processes.
    - Click **Update**.
3.  **Check IP**: 
    - **Note**: When you Stop/Start an instance, AWS usually assigns it a **new Public IP Address**.
    - **Action**: If you connect via SSH (Option B), you will need to copy the *new* IP from the EC2 Dashboard.
    - **Action**: For the web app itself, always use the **ALB DNS Name**. It never changes, even when the server restarts!

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
- [ ] ALB is "Active" and DNS name is working?
- [ ] ASG is successfully launching a node into the Target Group?
