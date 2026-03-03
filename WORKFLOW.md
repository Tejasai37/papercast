# PaperCast Data Workflow

This sequence diagram illustrates the step-by-step journey of data as a user interacts with the PaperCast platform to generate an AI podcast.

## User Journey Sequence

```mermaid
sequenceDiagram
    autonumber
    
    actor User as Web Browser
    participant EC2 as EC2 (FastAPI)
    participant Cognito as Amazon Cognito
    
    %% AI Pipeline
    box rgb(40, 40, 40) The AI Factory
        participant Comprehend as Amazon Comprehend
        participant Bedrock as Amazon Bedrock
        participant Translate as Amazon Translate
        participant Polly as Amazon Polly
    end
    
    %% Storage layer
    participant Dynamo as Amazon DynamoDB
    participant S3 as Amazon S3

    %% 1. Authentication
    User->>EC2: POST /login (Username & Password)
    EC2->>Cognito: Validate Credentials
    Cognito-->>EC2: Returns JWT ID Token
    EC2-->>User: Sets HttpOnly Session Cookie

    %% 2. User Input
    User->>EC2: POST /api/generate_audio (Article URL, Target Language)
    
    %% 3. Cache Check
    EC2->>Dynamo: Check if ArticleID exists
    alt Cache Hit (Audio already exists)
        Dynamo-->>EC2: Returns Podcast Metadata
        EC2->>Dynamo: Append User to 'Subscribers' List
    else Cache Miss (New Article)
        %% 4. AI Processing Pipeline
        EC2->>EC2: Scrape Article Text from URL
        
        EC2->>Comprehend: Analyze Text (Sentiment, Entities)
        Comprehend-->>EC2: Returns NLP Insights
        
        EC2->>Bedrock: Generate Radio Script (Nova Micro)
        Bedrock-->>EC2: Returns English Dialogue
        
        opt If Target Language != English
            EC2->>Translate: Translate Dialogue
            Translate-->>EC2: Returns Localized Text
        end
        
        EC2->>Polly: Synthesize Speech (Neural Voice mapping)
        Polly-->>EC2: Returns raw MP3 Audio Stream
        
        %% 5. Storage
        EC2->>S3: Upload MP3 Audio File
        S3-->>EC2: Upload Confirmed
        
        EC2->>Dynamo: Store Podcast Metadata & NLP Insights
        Dynamo-->>EC2: Save Confirmed
    end
    
    %% 6. Playback
    EC2->>S3: Request Pre-signed URL (Valid for 1 Hour)
    S3-->>EC2: Returns Secure URL
    EC2-->>User: Returns JSON (Audio URL + Comprehend Tags)
    User->>User: Renders Custom Radio Dashboard UI
```

## Key Workflow Features

1. **Secure Sessions**: The entire AI pipeline is protected. Only users with a valid Cognito Session Cookie issued during Login can trigger the expensive AI generation phase.
2. **Global Caching**: The system checks DynamoDB *before* running any AI models. If another user has previously generated a podcast for that exact News Article URL, the system completely bypasses the AI Factory, appending the current user to the subscriber list and immediately returning the existing audio.
3. **Dynamic Translation**: The translation step is completely bypassed if the user requests English, saving time and compute resources.
4. **Short-Lived URLs**: The EC2 server never passes the permanent S3 bucket link to the browser. It generates a temporary pre-signed URL to ensure the audio files remain protected from public scraping.
