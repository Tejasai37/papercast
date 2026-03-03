# AWS Cloud Architecture

This diagram provides a structural view of how the PaperCast application is deployed within the Amazon Web Services (AWS) ecosystem.

It highlights the network boundaries, security perimeters (IAM & Cognito), and the serverless AI and Storage services utilized by the core compute instance.

## Infrastructure Diagram

```mermaid
flowchart TB
    %% External Actors
    User(( Web Browser ))
    GNews(("GNews API<br>(External)"))

    subgraph AWS["AWS Cloud (us-east-1)"]
        direction TB
        
        %% Identity and Access Management
        subgraph Security["Identity & Security"]
            IAM["IAM Role<br>(Papercast-EC2-Role)"]
            Cognito["Amazon Cognito<br>(User Pool)"]
        end

        %% Virtual Private Cloud
        subgraph VPC["Default VPC"]
            IGW["Internet Gateway"]
            subgraph Subnet["Public Subnet"]
                SG["Security Group<br>(Ports: 80, 22)"]
                
                subgraph Compute["Compute"]
                    EC2["Amazon EC2 Instance<br>(Amazon Linux 2023)<br>• Nginx Proxy<br>• Gunicorn<br>• FastAPI"]
                end
                
                %% Connections inside Subnet
                SG --- EC2
            end
            
            IGW --> SG
        end

        %% Serverless Storage
        subgraph Storage["Serverless Storage & Database"]
            direction LR
            S3[("Amazon S3<br>(Audio Bucket)")]
            DynamoDB[("Amazon DynamoDB<br>(PapercastCache)")]
        end

        %% Generative AI & Machine Learning Services
        subgraph AIServices["Serverless AI & ML Pipeline"]
            direction LR
            Comprehend["Amazon Comprehend<br>(NLP Insights)"]
            Bedrock["Amazon Bedrock<br>(Nova Micro)"]
            Translate["Amazon Translate<br>(Localization)"]
            Polly["Amazon Polly<br>(Neural TTS)"]
        end
    end

    %% Flow Dynamics
    User -- "HTTP (Port 80)" --> IGW
    
    %% Application Logic out to AWS Services
    EC2 .-> IAM
    IAM -. "Grants programmatic access to" .-> Storage
    IAM -. "Grants programmatic access to" .-> AIServices

    EC2 <-->|Validates JWT Sessions| Cognito
    EC2 <-->|Fetches Live Articles| GNews

    %% EC2 to Storage Actions
    EC2 -->|Writes Metadata| DynamoDB
    EC2 -->|Uploads MP3| S3

    %% EC2 to AI Actions
    EC2 -->|1. Analyzes Text| Comprehend
    EC2 -->|2. Prompts Radio Host| Bedrock
    EC2 -->|3. Translates Script| Translate
    EC2 -->|4. Synthesizes Audio| Polly
```

## AWS Services Used

*   **Amazon EC2 (Elastic Compute Cloud)**: The primary host for the Python web application. Sits in a public subnet to receive web traffic.
*   **Amazon VPC (Virtual Private Cloud)**: The overarching network structure providing the Internet Gateway to field incoming browser requests.
*   **AWS IAM (Identity and Access Management)**: An Instance Profile Role attached to the EC2 server, completely removing the need to manage secret API keys on the machine itself.
*   **Amazon Cognito**: A managed User Directory handling frontend sign-up schemas, email verifications, password hashing, and yielding secure JWT tokens to the backend.
*   **Amazon DynamoDB**: A fully managed NoSQL database operating as an ultra-fast global cache, tracking which users have listened to which articles.
*   **Amazon S3 (Simple Storage Service)**: Object storage acting as an audio sandbox, dispensing rapid short-lived streaming URLs back to the frontend dynamically.
*   **AWS AI Services (Bedrock, Polly, Comprehend, Translate)**: A suite of independently managed NLP and Foundational Models orchestrated by the EC2 server using the Boto3 SDK.
