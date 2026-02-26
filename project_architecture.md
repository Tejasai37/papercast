flowchart LR
    %% Colors and Styles
    classDef aws fill:#FF9900,stroke:#232F3E,stroke-width:2px,color:white;
    classDef ai fill:#00A4A6,stroke:#232F3E,stroke-width:2px,color:white;
    classDef db fill:#3B48CC,stroke:#232F3E,stroke-width:2px,color:white;
    classDef default fill:#fff,stroke:#333,stroke-width:2px;

    %% External
    User((End User))
    
    %% AWS Cloud
    subgraph AWS [AWS Cloud]
        Cognito[Amazon Cognito<br/>Auth] ::: aws
        
        subgraph VPC [VPC - Public Subnets]
            IGW[Internet Gateway]
            ALB[Application Load<br/>Balancer] ::: aws
            
            subgraph ASG [Auto Scaling Group]
                EC2[EC2 Instance<br/>Python Web App] ::: aws
            end
        end

        subgraph AI_Services [AI Processing]
            Bedrock[Amazon Bedrock<br/>Script Gen] ::: ai
            Polly[Amazon Polly<br/>Audio Gen] ::: ai
        end

        subgraph Storage [Data Storage]
            DynamoDB[(Amazon DynamoDB<br/>Metadata)] ::: db
            S3[(Amazon S3<br/>Audio Files)] ::: db
        end
    end

    %% Flows
    User <-->|1. Auth| Cognito
    User -->|2. HTTP Request| IGW
    IGW --> ALB
    ALB --> EC2
    
    EC2 -->|3. Send Text| Bedrock
    Bedrock -->|Returns Script| EC2
    
    EC2 -->|4. Send Script| Polly
    Polly -->|Returns Audio| EC2
    
    EC2 -->|5. Save Meta| DynamoDB
    EC2 -->|6. Save .mp3| S3
    
    User <..>|7. Stream Audio<br/>(Pre-signed URL)| S3