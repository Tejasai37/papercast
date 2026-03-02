# Manual AWS Infrastructure Setup Guide

This document provides step-by-step instructions for creating the core AI and storage infrastructure using the AWS Management Console. 

> [!NOTE]
> This guide is simplified for a local or single-node EC2 deployment. It relies on the Default VPC already present in your AWS account.

## 1. Create S3 Bucket (Audio & Document Storage)
1.  Search for "S3" in the top bar.
2.  Click **Create bucket**.
3.  **Bucket name**: `papercast-data-[your-unique-suffix]` (Must be globally unique!).
4.  **Region**: Select your preferred region (e.g., `us-east-1`).
5.  **Block Public Access**: Keep **Block all public access** checked (Recommended).
6.  Click **Create bucket**.

---

## 2. Create DynamoDB Table (Metadata Cache)
1.  Search for "DynamoDB" in the top bar.
2.  Click **Create table**.
3.  **Table name**: `PapercastCache`.
4.  **Partition key**: `ArticleID` (String).
    -   Leave Sort key empty.
5.  **Table settings**: Default settings are fine for now.
6.  Click **Create table**.

---

## 3. Create Amazon Cognito User Pool (Authentication)
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

### 3.1 Create admins Group
1.  In your User Pool dashboard, click the **Groups** tab.
2.  Click **Create group**.
3.  **Group name**: `admins` (Must be exact!).
4.  Click **Create group**.

### 3.2 Promote a User
1.  Click the **Users** tab.
2.  Click on your username.
3.  Click **Add user to group**.
4.  Select `admins`.
5.  Click **Add**.

*Now, when you log in with that user, the Papercast dashboard will automatically recognize you as an administrator!*

---

## 4. Create IAM Role (API Permissions)
1.  Search for "IAM" in the top bar.
2.  Click **Roles** > **Create role**.
3.  **Step 1: Select trusted entity**:
    -   Keep **AWS service**.
    -   Under **Service or use case**, select **EC2**.
    -   Click **Next**.
4.  **Step 2: Add permissions**:
    -   Search and check: `AmazonS3FullAccess`.
    -   Search and check: `AmazonDynamoDBFullAccess`.
    -   Search and check: `AmazonPollyFullAccess`.
    -   Search and check: `AmazonBedrockFullAccess`.
    -   Search and check: `ComprehendFullAccess` (For NLP Insights).
    -   Search and check: `TranslateFullAccess` (For language translation).
    -   Search and check: `AmazonCognitoPowerUser`.
5.  **Step 3: Name, review, and create**:
    -   **Role name**: `Papercast-EC2-Role`.
    -   Click **Create role**.

---

## 5. Local Environment Configuration
After setting up the AWS resources, you must configure your local application to talk to them.

1.  **Create `.env` File**: 
    -   Copy the template: `cp .env.example .env`.
2.  **Fill in Resource Details**:
    -   `NEWS_API_KEY`: Your key from NewsAPI.org.
    -   `USE_REAL_AWS`: Set to `true` to use your cloud setup.
    -   `S3_BUCKET_NAME`: The name of the bucket you created in Section 1.
    -   `DYNAMODB_TABLE_NAME`: `PapercastCache` (Section 2).
    -   `COGNITO_USER_POOL_ID`: The ID from the User Pool (Section 3).
    -   `COGNITO_CLIENT_ID`: The App Client ID (Section 3).
    -   `AWS_REGION`: e.g., `us-east-1`.

---

## 6. Manual Server Setup & Deployment (Single Node EC2)
If you wish to deploy this to the cloud rather than running it locally on your laptop, follow these steps to launch a single EC2 instance.

### 6.1 Launch the EC2 Instance
1.  Go to **EC2 Console** > **Instances** > **Launch instances**.
2.  **Name**: `Papercast-Production-Node`.
3.  **AMI**: Amazon Linux 2023.
4.  **Instance type**: `t2.micro` or `t3.micro`.
5.  **Key pair**: Select an existing key pair or create a new one (e.g. `papercast-key`).
6.  **Network Settings**: 
    -   Ensure **Auto-assign public IP** is Enabled.
    -   Create a new Security Group allowing:
        -   **SSH (22)** from `My IP`
        -   **HTTP (80)** from `0.0.0.0/0`
        -   **Custom TCP (8000)** from `0.0.0.0/0` (for testing).
7.  **Advanced Details**:
    -   **IAM instance profile**: Select `Papercast-EC2-Role`.
8.  Click **Launch instance**.

### 6.2 Connect to Instance
Choose one of the two methods below:

#### **Option A: EC2 Instance Connect (Easiest)**
1.  Go to **EC2 Console** > **Instances** > Select `Papercast-Production-Node`.
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

### 6.3 Install System Dependencies
Run these commands in the terminal:
```bash
sudo dnf update -y
sudo dnf install -y python3.11 python3.11-pip git nginx
```

### 6.4 Clone & Setup Application
```bash
# Clone directly from your repo
git clone [YOUR_REPO_URL] papercast
cd papercast

# Setup Virtual Environment
python3.11 -m venv papercast_venv
source papercast_venv/bin/activate
pip install -r requirements.txt
```

### 6.5 Configure Environment
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

### 6.6 Setup Gunicorn (Systemd)
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

### 6.7 Setup Nginx Reverse Proxy
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

## Verification Checklist
- [x] S3 Bucket & DynamoDB Table `PapercastCache` created?
- [x] Cognito User Pool and App Client configured?
- [x] IAM Role `Papercast-EC2-Role` created with Bedrock, Polly, S3, Dynamo, Textract, Comprehend, and Translate permissions attached?
- [ ] EC2 instance launched with Role attached and Security group allowing port 80?
