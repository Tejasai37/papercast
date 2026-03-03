# PaperCast Architecture

This document provides a simple, high-level overview of the systems required to run the application, as outlined in our `infrastructure/manual_setup.md` deployment guide.

## System Flow

```mermaid
flowchart TD
    %% User Entry
    Start([User visits PaperCast]) --> Login{Logged In?}
    
    %% Auth
    Login -- No --> Cognito[Amazon Cognito handles Secure Login]
    Cognito --> Dashboard
    Login -- Yes --> Dashboard([User opens Dashboard])
    
    %% Input
    Dashboard --> Request[User pastes a News Article URL]
    
    %% Cache Check
    Request --> Cache{Check DynamoDB Cache}
    
    %% Cache Hit
    Cache -- Audio Already Exists --> Deliver[Deliver existing S3 Audio Link]
    
    %% Cache Miss Flow (AI Pipeline)
    Cache -- New Article --> Comprehend[Amazon Comprehend analyzes themes & sentiment]
    Comprehend --> Bedrock[Amazon Bedrock writes the Radio Script]
    Bedrock --> Translate{Translate?}
    Translate -- Yes --> AmazonTranslate[Amazon Translate converts script to local language]
    Translate -- No --> Polly
    AmazonTranslate --> Polly
    Polly[Amazon Polly synthesizes text into Neural Speech MP3]
    
    %% Storage
    Polly --> SaveDb[Save Podcast details to DynamoDB]
    SaveDb --> SaveS3[Save MP3 file to Amazon S3]
    SaveS3 --> Deliver
    
    %% Output
    Deliver --> Player([User listens to Podcast!])
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
