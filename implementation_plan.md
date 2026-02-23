    # Implementation Plan: Papercast - AI News Podcast Platform

This document outlines the step-by-step roadmap for building **Papercast**, a scalable and secure AI-powered news podcast platform.

## 1. Project Overview
Papercast leverages Generative AI to convert trending news articles into high-quality audio podcasts on demand. The architecture is designed for high availability, security, and enterprise-grade scalability using AWS.

### Tech Stack
- **Frontend**: Vanilla JS, Bootstrap 5, Jinja2 Templates (HTML)
- **Backend**: FastAPI (Python), Boto3
- **AI Services**: Amazon Bedrock (Summarization), Amazon Polly (Neural Text-to-Speech)
- **Database**: Amazon DynamoDB (Metadata & Caching)
- **Storage**: Amazon S3 (Audio artifacts)
- **Auth**: Amazon Cognito (JWT & RBAC)
- **Infrastructure**: AWS VPC, EC2 (ASG/ALB), Route 53

---

## Phase 1: Basic Project Structure & Local Setup
*Goal: Establish the repository and local development environment.*

- [ ] **1.1 Setup Project Directory**: Create folders for `frontend` and `backend`.
- [ ] **1.2 Backend Initialization**: Initialize a FastAPI project with dependencies (`fastapi`, `uvicorn`, `boto3`, `pydantic`).
- [ ] **1.3 Frontend Initialization**: Initialize a React project using Vite.
- [ ] **1.4 Version Control**: Initialize Git and draft `.gitignore` files.

## Phase 2: AWS Infrastructure (Cost-Optimized)
*Goal: Build the network and security layer.*

- [ ] **2.1 Custom VPC**: Create a VPC with **Public Subnets Only** (to avoid NAT Gateway costs).
- [ ] **2.2 Security Groups**: 
    - App SG: Restrict traffic to your IP (for dev) or allow HTTP/HTTPS.
- [ ] **2.3 Amazon S3**: Create a bucket for audio file storage with appropriate lifecycle policies.
- [ ] **2.4 Amazon DynamoDB**: Create a table (`PapercastCache`) with `ArticleID` as Partition Key.

**Note**: We are skipping NAT Gateways and Private Subnets for this phase to save ~$32/month.

## Phase 3: Backend API Development
*Goal: Implement the core AI orchestration logic.*

- [ ] **3.1 News Integration**: Implement a service to fetch news from an external API (e.g., NewsAPI.org).
- [ ] **3.2 Bedrock Integration**: Implement the "Script Generator" module to summarize news content using LLMs.
- [ ] **3.3 Polly Integration**: Implement the "Podcast Producer" module to convert text scripts to MP3.
- [ ] **3.4 Caching Logic**: Implement logic to check DynamoDB/S3 before triggering AI processing.
- [ ] **3.5 API Endpoints**:
    - `GET /news`: Fetch trending articles.
    - `POST /generate`: Trigger podcast creation.
    - `GET /audio/{id}`: Fetch audio playback link.

## Phase 4: Frontend Development (Vanilla JS + Bootstrap)
*Goal: Create a clean UI using Bootstrap and custom JS.*

- [ ] **4.1 Base Setup**: Create `base.html` with Bootstrap 5 CDN and custom `style.css`.
- [ ] **4.2 Dashboard**: Build `index.html` with a responsive news grid.
- [ ] **4.3 Interactions**: Enhance UI with Vanilla JS (e.g., fetch news, play audio).
- [ ] **4.4 Audio Player**: Create a custom HTML5 audio player.

## Phase 5: Authentication & Security
*Goal: Secure the application with Cognito.*

- [ ] **5.1 User Pool**: Setup Amazon Cognito User Pool.
- [ ] **5.2 RBAC**: Create `Admin` and `User` groups.
- [ ] **5.3 JWT Middleware**: Implement backend middleware to validate Cognito tokens for every request.
- [ ] **5.4 Frontend Auth**: Integrate AWS Amplify or a custom Cognito flow in React.
*Goal: Move from local to the cloud.*

- [ ] **6.1 Dockerization**: Dockerize both Frontend and Backend.
- [ ] **6.2 EC2 Launch Templates**: Configure templates for ASG (including IAM roles for S3/DynamoDB/Polly/Bedrock access).
- [ ] **6.3 Load Balancer Setup**: Deploy ALB and configure target groups for the EC2 instances.
- [ ] **6.4 SSL & Route 53**: Connect domain and enable HTTPS via AWS Certificate Manager.


---

## Phase 7: Cost Analysis & Optimization
*Goal: Minimize cloud spend while maintaining functionality.*

### High-Impact Services & Mitigation
| Service | Cost Driver | Mitigation Strategy |
| :--- | :--- | :--- |
| **NAT Gateway** | ~$0.045/hour (~$32/mo) + Data processing | **Development Phase**: Deploy EC2 instances in **Public Subnets** to avoid NAT costs entirely. Secure with strict Security Groups. <br> **Production**: Use VPC Endpoints for S3/DynamoDB (Free) to reduce processed data. |
| **Application Load Balancer (ALB)** | ~$0.0225/hour (~$16/mo) + LCU charges | **Dev/Test**: Stop ALB when not in use. Use direct Public IP for early testing. |
| **Amazon Bedrock** | Per-token (Input/Output) | **Cache Summaries**: Store generated summaries in DynamoDB. Never re-summarize the same article. <br> **Model Selection**: Use `Titan Text Express` or `Claude Instant` for lower cost vs. `Claude 3 Sonnet`. |
| **Amazon Polly** | Per-character | **Cache Audio**: Store MP3s in S3 `Standard-IA` (Infrequent Access). Check cache before generating. |
| **Amazon EC2** | Hourly compute | **Instance Type**: Use `t2.micro` or `t3.micro` (Free Tier eligible: 750 hrs/mo). <br> **Spot Instances**: Use Spot Instances for the backend ASG (upto 90% savings). |

---

## Success Metrics
1. **Low Latency**: AI generation to audio playback takes < 10 seconds.
2. **Scalability**: System handles 100 concurrent users without performance degradation.
3. **Security**: Zero unauthorized API access; all audio files served via pre-signed S3 URLs.
