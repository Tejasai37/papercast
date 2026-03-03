# PaperCast Data Workflow

This flowchart illustrates the step-by-step human-readable data flow as a user interacts with the PaperCast platform to generate an AI podcast.

## User Journey

```mermaid
flowchart LR
    %% User Entry
    Start(["User visits<br>PaperCast"]) --> Login{"Logged<br>In?"}
    
    %% Auth
    Login -- No --> Cognito["Amazon Cognito<br>Secure Login"]
    Cognito --> Dashboard
    Login -- Yes --> Dashboard(["User opens<br>Dashboard"])
    
    %% Live Feed
    Dashboard <--> GNews(("GNews API<br>fetches live articles"))
    
    %% Input
    GNews --> Request["User selects / pastes<br>News Article URL"]
    
    %% Cache Check
    Request --> Cache{"Check<br>DynamoDB<br>Cache"}
    
    %% Cache Hit
    Cache -- "Audio Already Exists" --> Deliver["Deliver existing<br>S3 Audio Link"]
    
    %% Cache Miss Flow (AI Pipeline)
    Cache -- "New Article" --> Comprehend["Amazon Comprehend<br>analyzes sentiment"]
    Comprehend --> Bedrock["Amazon Bedrock<br>writes Radio Script"]
    Bedrock --> Translate{"Translate<br>Language?"}
    Translate -- Yes --> AmazonTranslate["Amazon Translate<br>converts script"]
    Translate -- No --> Polly
    AmazonTranslate --> Polly
    Polly["Amazon Polly<br>synthesizes MP3"]
    
    %% Storage
    Polly --> SaveDb["Save details<br>to DynamoDB"]
    SaveDb --> SaveS3["Save MP3<br>to Amazon S3"]
    SaveS3 --> Deliver
    
    %% Output
    Deliver --> Player(["User listens<br>to Podcast!"])
```

## Key Workflow Features

1. **Secure Sessions**: The entire AI pipeline is protected. Only users with a valid Cognito Session Cookie issued during Login can trigger the expensive AI generation phase.
2. **Global Caching**: The system checks DynamoDB *before* running any AI models. If another user has previously generated a podcast for that exact News Article URL, the system completely bypasses the AI Factory, appending the current user to the subscriber list and immediately returning the existing audio.
3. **Dynamic Translation**: The translation step is completely bypassed if the user requests English, saving time and compute resources.
4. **Short-Lived URLs**: The EC2 server never passes the permanent S3 bucket link to the browser. It generates a temporary pre-signed URL to ensure the audio files remain protected from public scraping.
