    # Implementation Plan: Papercast - AI News Podcast Platform

This document outlines the step-by-step roadmap for building **Papercast**, a scalable and secure AI-powered news podcast platform.

## 1. Project Overview
Papercast leverages Generative AI to convert trending news articles into high-quality audio podcasts on demand. The architecture is designed for high availability, security, and enterprise-grade scalability using AWS.

### Tech Stack
- **Frontend**: Vanilla JS, Bootstrap 5, Jinja2 Templates (HTML)
- **Backend / Server**: FastAPI (Python), Boto3 (AWS SDK), Gunicorn, Nginx
- **External Data**: GNews API
- **AI Services**: Amazon Bedrock (Nova Micro), Amazon Comprehend (NLP Sentiment & Entities), Amazon Translate (Language Localization), Amazon Polly (Neural Text-to-Speech)
- **Database**: Amazon DynamoDB (Metadata & Caching)
- **Storage**: Amazon S3 (Audio artifacts)
- **Auth**: Amazon Cognito (JWT & RBAC)
- **Infrastructure**: Amazon EC2 (Amazon Linux 2023)

---

## Phase 1: Basic Project Structure & Local Setup
*Goal: Establish the repository and local development environment.*

- [x] **1.1 Setup Project Directory**: Create a `backend` folder containing `templates` and `static` directories for Jinja2 SSR.
- [x] **1.2 Backend Initialization**: Initialize a FastAPI project with dependencies (`fastapi`, `uvicorn`, `boto3`, `pydantic`).
- [x] **1.3 Frontend Templates**: Create Jinja2 templates for the FastAPI backend to render the dashboard.
- [x] **1.4 Version Control**: Initialize Git and draft `.gitignore` files.

## Phase 2: AWS Infrastructure (Cost-Optimized)
*Goal: Build the network and security layer.*

- [x] **2.1 Default VPC**: Utilize the pre-existing Default VPC in the AWS account.
- [x] **2.2 Security Groups**: 
    - App SG: Allow inbound HTTP (80) and SSH (22).
- [x] **2.3 Amazon S3**: Create a bucket for audio file storage.
- [x] **2.4 Amazon DynamoDB**: Create a table (`PapercastCache`) with `ArticleID` as Partition Key.

**Note**: We are utilizing the Default VPC and a single public subnet for this deployment, bypassing NAT Gateway costs to save ~$32/month.

## Phase 3: Backend API Development
*Goal: Implement the core AI orchestration logic.*

- [x] **3.1 News Integration**: Implement a service to fetch news from an external API (e.g., NewsAPI.org).
- [x] **3.2 Bedrock Integration**: Implement the "Script Generator" module to summarize news content using LLMs.
- [x] **3.3 Polly Integration**: Implement the "Podcast Producer" module to convert text scripts to MP3.
- [x] **3.4 Caching Logic**: Implement logic to check DynamoDB/S3 before triggering AI processing.
- [x] **3.5 API Endpoints**:
    - `GET /news`: Fetch trending articles.
    - `POST /generate`: Trigger podcast creation.
    - `GET /audio/{id}`: Fetch audio playback link.

## Phase 4: Frontend Development (Vanilla JS + Bootstrap)
*Goal: Create a clean UI using Bootstrap and custom JS.*

- [x] **4.1 Base Setup**: Create `base.html` with Bootstrap 5 CDN and custom `style.css`.
- [x] **4.2 Dashboard**: Build `dashboard.html` with a responsive news grid.
- [x] **4.3 Interactions**: Enhance UI with Vanilla JS (e.g., fetch news, play audio).
- [x] **4.4 Audio Player**: Create a custom HTML5 audio player.

## Phase 5: Authentication & Security
*Goal: Secure the application with Cognito.*

- [ ] **5.1 User Pool**: Setup Amazon Cognito User Pool.
- [ ] **5.2 RBAC**: Create `Admin` and `User` groups.
- [ ] **5.3 JWT Middleware**: Implement backend middleware to validate Cognito tokens for every request.
- [ ] **5.4 Frontend Auth**: Integrate Cognito flow within the FastAPI endpoints using session cookies.
## Phase 6: Deployment
*Goal: Move from local to the cloud.*

- [x] **6.1 Manual App Deployment**: Setup FastAPI on a single EC2 instance using Gunicorn as an application server and Nginx as a reverse proxy.
- [x] **6.2 EC2 IAM Role**: Attach an IAM Instance Profile to the EC2 server with explicit permissions for S3, DynamoDB, Polly, Bedrock, Translate, and Comprehend access.
- [x] **6.3 Nginx Configuration**: Optimize the Reverse Proxy to serve frontend static files and manage large MP3 buffer timeouts (120 seconds).

---

## Phase 6.5: Multi-Tenant Architecture Refactor
*Goal: Evolve the single-user caching logic to safely support multiple distinct users while maintaining the global audio cache for cost efficiency.*

### Identified Issues
1. **Global Cache vs Personal Library**: Currently, when User A generates an article, DynamoDB sets `UserID = User A`. If User B generates the *exact same* article, the system uses the global cache to save money/time, but the database still points to User A. **Result**: The podcast never shows up in User B's personal library.
2. **Deletion Cascades**: If an Admin deletes a globally cached podcast that 10 users listen to, it breaks the library for all 10 users.

### Implemented Solution: The "Subscribers" Array
Instead of tracking a single `UserID` string per podcast, we will track a mathematical Set of `subscribers`.

#### `backend/real_aws.py`
- [x] Modified `save_article_metadata` to use an `UpdateItem` command rather than `PutItem`. 
- [x] If the `ArticleID` is new, it creates the record and adds the `UserID` to a `subscribers` String Set (`SS`).
- [x] If the `ArticleID` already exists (Global Cache Hit), it simply appends the new `UserID` to the existing `subscribers` set.
- [x] Modified `get_user_library` to use `CONTAINS(subscribers, :user_id)` in the scan filter to accurately fetch any podcast a user has requested, regardless of who generated it first.

#### `backend/main.py`
- [x] Updated the `/api/generate_audio` cache-hit logic to call `save_article_metadata` *before* returning early, ensuring the user is successfully added to the `subscribers` set even on an instant cache hit.

---

## Phase 7: Cost Analysis & Optimization
*Goal: Minimize cloud spend while maintaining functionality.*

### High-Impact Services & Mitigation
| Service | Cost Driver | Mitigation Strategy |
| :--- | :--- | :--- |
| **Amazon Bedrock** | Per-token (Input/Output) | **Cache Summaries**: Store generated podcast metadata in DynamoDB. Never regenerate the same article. <br> **Model Selection**: Use `amazon.nova-micro-v1:0` for massive cost reduction vs. Opus/Sonnet models. |
| **Amazon Polly** | Per-character | **Cache Audio**: Store MP3s in S3. Check cache before generating any text-to-speech. |
| **Amazon Comprehend** | Per-character | **Text Truncation**: Only pass the first ~4800 characters of an article to the API (which establishes sufficient sentiment/entities) rather than the entire massive source text. |
| **Amazon Translate** | Per-character | **Limit Scope**: Only translate the final, concise script and summary arrays rather than translating the entire raw news article. DynamoDB automatically separates cached language varieties by ID suffix (e.g. `1234_hi`). |
| **Amazon EC2** | Hourly compute | **Instance Type**: Utilize a single `t2.micro` or `t3.micro` (Free Tier eligible: 750 hrs/mo) running Nginx/Gunicorn instead of an expensive Auto Scaling Group or Load Balancer. |

---

## Success Metrics
1. **Low Latency**: AI generation to audio playback takes < 10 seconds.
2. **Scalability**: System handles 100 concurrent users without performance degradation.
3. **Security**: Zero unauthorized API access; all audio files served via pre-signed S3 URLs.
