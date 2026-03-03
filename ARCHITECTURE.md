# PaperCast Architecture

This document provides a visual representation of how the PaperCast monolithic application communicates with the various AWS services.

## System Architecture Diagram

This flowchart outlines the synchronous request/response cycle when a user requests an AI-generated sports-radio style podcast from an article URL.

```mermaid
graph TD
    %% Define Styles
    classDef client fill:#f9f9f9,stroke:#333,stroke-width:2px;
    classDef server fill:#e2f0d9,stroke:#548235,stroke-width:2px;
    classDef awsAuth fill:#fff2cc,stroke:#d6b656,stroke-width:2px;
    classDef awsAI fill:#dae8fc,stroke:#6c8ebf,stroke-width:2px;
    classDef awsStorage fill:#ffe6cc,stroke:#d79b00,stroke-width:2px;
    classDef external fill:#f8cecc,stroke:#b85450,stroke-width:2px;

    %% Nodes
    User(("fa:fa-user Web Browser")):::client
    Nginx["Nginx Reverse Proxy<br>(Port 80)"]:::server
    Gunicorn["Gunicorn & Uvicorn<br>(Port 8000)"]:::server
    FastAPI["FastAPI Backend<br>(Python)"]:::server
    
    Cognito[("Amazon Cognito<br>(JWT Auth)")]:::awsAuth
    
    GNews(("GNews API<br>(Trending Articles)")):::external
    
    Translate["Amazon Translate<br>(Localization)"]:::awsAI
    Comprehend["Amazon Comprehend<br>(NLP Insights)"]:::awsAI
    Bedrock["Amazon Bedrock<br>(Nova Micro - Script Gen)"]:::awsAI
    Polly["Amazon Polly<br>(Neural TTS synthesis)"]:::awsAI
    
    DynamoDB[("Amazon DynamoDB<br>(Metadata Cache)")]:::awsStorage
    S3[("Amazon S3<br>(Audio Storage)")]:::awsStorage

    %% Flow
    User -- "1. Login (HTTP POST)" --> Nginx
    Nginx --> Gunicorn
    Gunicorn --> FastAPI
    FastAPI -- "2. Authenticate" --> Cognito
    Cognito -- "Returns JWT Cookie" --> FastAPI

    User -- "3. Request Audio (HTTP POST)" --> Nginx
    Nginx -- "Forwards Request" --> FastAPI
    
    %% Backend Business Logic
    FastAPI -- "4. Fetch Article Content" --> GNews
    FastAPI -- "5. Analyze Theme & Sentiment" --> Comprehend
    FastAPI -- "6. Generate Radio Script" --> Bedrock
    FastAPI -- "7. Translate (Optional)" --> Translate
    FastAPI -- "8. Synthesize Voices" --> Polly
    
    %% Storage Logic
    Polly -- "Returns MP3 Stream" --> FastAPI
    FastAPI -- "9. Upload MP3" --> S3
    FastAPI -- "10. Store Metadata<br>& Comprehend Tags" --> DynamoDB
    
    %% Response
    FastAPI -- "11. Return Short-Lived<br>Pre-signed Audio URL" --> User
```

## Component Roles

*   **Nginx (Reverse Proxy)**: Offloads static asset (CSS/JS) processing and handles 120-second AWS API buffering.
*   **Gunicorn**: Python multiprocessor manager ensuring parallel handling of user requests.
*   **FastAPI**: The core backend orchestrator running all logic and enforcing RBAC (Role-Based Access Control) using Cognito cookies.
*   **Amazon Comprehend**: Scrapes the raw article for keywords, entities (people/places), and overall sentiment before processing.
*   **Amazon Bedrock**: Powers the AI host interaction (e.g., Nova Micro models acting as sports radio hosts).
*   **Amazon Translate**: Mutates the Bedrock-generated text script into user-specified target languages.
*   **Amazon Polly**: Maps the targeted language to native-sounding AWS Neural Voices and synthesizes an MP3.
*   **Amazon S3 & DynamoDB**: Acts as the global multi-tenant cache, ensuring consecutive users requesting the same article get an instant `<audio>` playback instead of re-triggering the expensive Bedrock/Polly pipeline.
