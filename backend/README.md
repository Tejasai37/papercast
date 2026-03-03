# Backend API & AI Integration Layer

This directory houses the core FastAPI application logic and the heavy-lifting Boto3 integrations that power the PaperCast AI pipeline. It acts as the orchestrator between the user interface and the various AWS Generative AI and standard cloud services.

## Core Files

### `main.py`
The primary FastAPI entry point. 
*   **Routing**: Defines all application routes (`/dashboard`, `/library`, `/admin`) and API endpoints (`/api/generate_audio`, `/api/process_link`).
*   **Session Management**: Handles Cognito JWT validation and sets `HttpOnly` secure cookies for user sessions and Role-Based Access Control (RBAC).
*   **Jinja2 Templating**: Mounts the static files and registers custom Python filters (e.g., `format_script`) used by the HTML SSR engine to format the visual dialogue script.

### `real_aws.py`
The unified AWS Services Integration class (`RealAWSService`). This file is the backbone of the application.
*   **Authentication**: Manages `boto3.client('cognito-idp')` for user login and group verification.
*   **AI Pipeline Orchestration**:
    1.  **Comprehend**: Extracts NLP sentiment, entities, and key phrases from the raw article text.
    2.  **Bedrock**: Uses `amazon.nova-micro-v1:0` to dynamically generate the dialogue script and summary.
    3.  **Translate**: Translates the generated Bedrock text into the user's target language (if not English).
    4.  **Polly**: Synthesizes the final script into an MP3 using Neural voices dynamically mapped based on the requested language (e.g., Matthew/Joanna for US English, Kajal/Aditi for Indian English).
*   **Storage & Caching**: Manages `boto3.client('dynamodb')` to store the generated data and uses an `UpdateItem` String Set (`SS`) operation to append users to the `subscribers` list, enabling a highly efficient multi-tenant global cache. Generates S3 presigned URLs for secure frontend streaming.

### `news_service.py`
A modular external integration script.
*   Fetches real-time trending news articles from the GNews API based on search queries and language preferences.
*   Extracts the raw body text from external URLs using regular expressions and basic HTML parsing to feed into the AI pipeline.

## API Documentation
When running the server locally, you can view the auto-generated interactive OpenAPI documentation by visiting:
*   `http://localhost:8080/docs`

## Environment Variables
Ensure the local `.env` file at the root of the project contains the necessary keys (`NEWS_API_KEY`, `S3_BUCKET_NAME`, `DYNAMODB_TABLE_NAME`, `COGNITO_USER_POOL_ID`) for these modules to function. AWS Authentication keys are not required if running on an EC2 instance with an attached IAM Role.
