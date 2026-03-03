# PaperCast Architecture

This document provides a simple, high-level overview of the systems required to run the application, as outlined in our `infrastructure/manual_setup.md` deployment guide.

## System Flow

```mermaid
flowchart TD
    %% Define Styles
    classDef client fill:#f9f9f9,stroke:#333,stroke-width:2px;
    classDef server fill:#d5e8d4,stroke:#82b366,stroke-width:2px;
    classDef awsAuth fill:#fff2cc,stroke:#d6b656,stroke-width:2px;
    classDef awsAI fill:#dae8fc,stroke:#6c8ebf,stroke-width:2px;
    classDef awsStorage fill:#ffe6cc,stroke:#d79b00,stroke-width:2px;

    %% Nodes
    Browser["Web Browser (User)"]:::client
    EC2["Amazon EC2 Server<br>(Nginx + FastAPI)"]:::server
    
    Cognito["Amazon Cognito<br>(Login & Roles)"]:::awsAuth
    
    Bedrock["Amazon Bedrock<br>(Generates Script)"]:::awsAI
    Polly["Amazon Polly<br>(Creates Audio)"]:::awsAI
    Translate["Amazon Translate<br>(Language Localization)"]:::awsAI
    Comprehend["Amazon Comprehend<br>(Text Analysis)"]:::awsAI
    
    DynamoDB["Amazon DynamoDB<br>(Database Cache)"]:::awsStorage
    S3["Amazon S3<br>(Audio Files Sandbox)"]:::awsStorage

    %% Core Flow
    Browser -->|1. Visits Website| EC2
    
    EC2 <-->|2. Authenticates| Cognito
    
    EC2 -->|3. Analyzes Text| Comprehend
    EC2 -->|4. Writes Podcast| Bedrock
    EC2 -->|5. Translates Text| Translate
    EC2 -->|6. Generates MP3| Polly
    
    EC2 -->|7. Saves Podcast Details| DynamoDB
    EC2 -->|8. Saves MP3 File| S3
    
    EC2 -->|9. Returns Audio Player| Browser
```

## How It Works (Step-by-Step)

The flow is designed to be straightforward, functioning exactly as built during the manual AWS setup:

1.  **The User Interface**: A user visits your application in their browser.
2.  **The Engine (EC2)**: All traffic goes straight to your Amazon EC2 server running your Python code (FastAPI).
3.  **Security (Cognito)**: Before generating any audio, the EC2 server requires the user to log in via Amazon Cognito.
4.  **The AI Factory**: When a user inputs a news article:
    *   **Comprehend** extracts the main themes and entities.
    *   **Bedrock** acts as the radio host, writing the dialogue.
    *   **Translate** converts the script if a different language is chosen.
    *   **Polly** takes that text and reads it aloud, generating an MP3 audio file.
5.  **Storage**: The EC2 server saves the raw MP3 to an **S3 Bucket** and logs the podcast details (like the URL and target language) into the **DynamoDB** table.
6.  **Playback**: The user receives a secure link to the audio file and can play their podcast!
