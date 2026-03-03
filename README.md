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

## Security
*   **Private S3 Buckets**: Audio files cannot be accessed directly; the backend generates a short-lived pre-signed URL for streaming.
*   **API Protection**: All generation endpoints (`/api/generate_audio`) require a valid Cognito session cookie to restrict unauthorized AWS SDK calls.

## License
This project is proprietary and built for demonstration purposes as a comprehensive, end-to-end AWS Cloud and AI integration platform.
