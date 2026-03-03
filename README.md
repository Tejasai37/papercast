# PaperCast: AI-Powered News Podcast Platform

![PaperCast Banner](https://img.shields.io/badge/Status-Active-brightgreen) ![AWS](https://img.shields.io/badge/AWS-Cloud_Native-FF9900?logo=amazonaws) ![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?logo=fastapi)

PaperCast is a secure, cloud-native web application that solves information overload by instantly converting trending news articles into high-quality, AI-generated, multi-lingual audio podcasts on demand. Built around a 1940s vintage radio aesthetic, PaperCast utilizes bleeding-edge Generative AI to provide synthesized summaries, NLP insights, and localized neural speech.

## Features

*   **On-Demand Neural Audio (AWS Polly)**: Converts any news article into a lifelike, dynamic dialogue between a "[HOST]" and an "[EXPERT]". Supports specialized Neural voices across multiple locales (e.g., US English, Indian English, Hindi, and German).
*   **Generative Summarization (AWS Bedrock)**: Utilizes the `amazon.nova-micro-v1:0` foundational model to intelligently construct a professional radio script, a highly readable summary, and extreme TL;DR bullet points from raw news.
*   **Polyglot Translation (AWS Translate)**: Dynamically translates the generated radio script and insights into the user's selected language (English, Hindi, German, etc.) before audio synthesis.
*   **NLP Insights (AWS Comprehend)**: Automatically scans source articles to extract key emotional Sentiment, critical Entities (Persons, Places, Organizations), and Key Phrases to display alongside the audio.
*   **Smart Caching Architecture**: Employs a multi-tenant DynamoDB global cache. If a user requests a podcast that someone else has already generated, the system instantly delivers the cached S3 audio stream without re-triggering the AI pipeline, saving costs and time.
*   **Secure Role-Based Access (AWS Cognito)**: Industry-standard authentication flow providing distinct `General` and `Admin` user roles, complete with JWT middleware to protect AI endpoints.

## Technical Architecture

The application adopts a modern 3-tier Serverless architecture designed for extreme cost efficiency and scalability on AWS:

1.  **Frontend**: Server-Side Rendered (SSR) HTML5, CSS3, and Vanilla JavaScript delivered via **Jinja2 Templates**.
2.  **Backend**: High-performance **FastAPI (Python)** server handling asynchronous routing and middleware.
3.  **AI Pipeline**: **Boto3** orchestrates data logically from external APIs (GNews) -> Comprehend -> Bedrock -> Translate -> Polly.
4.  **Storage Engine**: **Amazon S3** stores the MP3 audio artifacts safely behind pre-signed URLs. **Amazon DynamoDB** serves as the NoSQL metadata vault and String Set (`SS`) cache repository.

## Local Development Setup

### Prerequisites
*   Python 3.9+
*   An AWS Account with an active IAM User/Role having programmatic access (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`).
*   A GNews API Key for live headlines.

### 1. Environment Variables
Clone the repository and create a `.env` file in the root directory:
```env
# AWS Credentials
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_REGION=us-east-1

# Papercast AWS Secrets
S3_BUCKET_NAME=your_s3_bucket
DYNAMODB_TABLE_NAME=papercast-podcasts
COGNITO_USER_POOL_ID=your_pool_id
COGNITO_CLIENT_ID=your_client_id

# System Config
NEWS_API_KEY=your_gnews_key
SECRET_KEY=generate_a_random_jwt_secret
```

### 2. Installation
Install the required python packages:
```bash
pip install -r requirements.txt
```

### 3. Running the Server
Start the FastAPI application via Uvicorn:
```bash
uvicorn backend.main:app --reload --port 8080
```
Access the application at `http://localhost:8080`.

## Cloud Deployment (AWS EC2)

For production deployment, PaperCast is designed to run on a single Amazon Linux 2023 instance utilizing a systemd-managed Gunicorn application server and an Nginx reverse proxy.

### 1. EC2 Instance Setup
1.  Launch a `t3.micro` or `t2.micro` Amazon Linux 2023 EC2 instance.
2.  Assign an IAM Role to the instance with full access to **S3, DynamoDB, Bedrock, Polly, Comprehend, and Translate**.
3.  Configure the Security Group to allow inbound traffic on ports `22` (SSH) and `80` (HTTP).

### 2. Environment Configuration
SSH into your instance and install the required dependencies:
```bash
sudo dnf update -y
sudo dnf install -y python3.11 python3.11-pip git nginx
```
Clone the repository and set up your virtual environment:
```bash
git clone [YOUR_REPO_URL] papercast
cd papercast
python3.11 -m venv papercast_venv
source papercast_venv/bin/activate
pip install -r requirements.txt
```
Create your `.env` file (Do **not** include AWS access keys, as the attached IAM role provides credentials):
```env
NEWS_API_KEY=your_key
USE_REAL_AWS=true
AWS_REGION=us-east-1
S3_BUCKET_NAME=your_bucket
DYNAMODB_TABLE_NAME=PapercastCache
COGNITO_USER_POOL_ID=your_pool_id
COGNITO_CLIENT_ID=your_client_id
```

### 3. Application Server (Gunicorn)
Create a systemd service file to manage the FastAPI application:
```bash
sudo nano /etc/systemd/system/papercast.service
```
Add the following configuration (adjusting for your specific user/path):
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
Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now papercast
```

### 4. Reverse Proxy (Nginx)
Configure Nginx to route external port 80 traffic to the internal Gunicorn server:
```bash
sudo nano /etc/nginx/conf.d/papercast.conf
```
Add the routing block:
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
Enable and start Nginx:
```bash
sudo systemctl restart nginx
sudo systemctl enable nginx
```
Access your IP address via your browser port 80, and the app will respond!

## Security
*   **Private S3 Buckets**: Audio files cannot be accessed directly; the backend generates a short-lived pre-signed URL for streaming.
*   **API Protection**: All generation endpoints (`/api/generate_audio`) require a valid Cognito session cookie to restrict unauthorized AWS SDK calls.

## License
This project is proprietary and built for demonstration purposes as a comprehensive, end-to-end AWS Cloud and AI integration platform.
