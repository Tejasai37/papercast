# Cloud Infrastructure Setup

This directory contains the architectural diagrams and step-by-step manual deployment guides necessary to orchestrate the AWS cloud environment for PaperCast.

The project utilizes a modern Serverless mindset for its data layer (S3, DynamoDB) and AI processing pipeline (Cognito, Bedrock, Polly, Comprehend, Translate), while hosting the core application logic on a traditional EC2 instance to simplify networking and VPC requirements.

## Files & Guides

### `manual_setup.md`
The most critical file in this directory. This document provides an exhaustive, step-by-step walkthrough for configuring the AWS environment from a completely blank AWS account via the Management Console.

**It covers the creation and configuration of:**
1.  **Amazon S3**: For secure MP3 audio storage.
2.  **Amazon DynamoDB**: Setting up the `PapercastCache` table with the `ArticleID` partition key for global metadata caching.
3.  **Amazon Cognito**: Configuring the User Pool, the Public App Client, and outlining the creation of the `admins` User Group for Role-Based Access Control (RBAC).
4.  **AWS IAM**: Creating the crucial `Papercast-EC2-Role` instance profile, detailing exactly which managed policies must be attached for the Boto3 SDK to securely access the AI services without hardcoded API keys.
5.  **Amazon EC2 Setup**: A comprehensive walkthrough for launching an Amazon Linux 2023 instance, configuring security groups for port `80` (HTTP), and installing dependencies (`dnf install python3.11`).
6.  **Gunicorn & systemd**: Instructions for creating a persistent Linux `systemd` daemon to run the FastAPI application server in the background using Uvicorn workers.
7.  **Nginx Reverse Proxy**: Details the `/etc/nginx/conf.d/` block required to securely forward external port `80` traffic to the internal `localhost:8000` Gunicorn socket.

### `setup_aws.py`
A legacy programmatic infrastructure script. 
*Note: This script may not dynamically provision the full suite of new AI capabilities (Comprehend/Translate) or the Cognito User Pool setup. The `manual_setup.md` guide is the recommended path for production deployments.*
