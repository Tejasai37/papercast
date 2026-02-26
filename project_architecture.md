flowchart TD
    subgraph External [External / User Layer]
        User((End User\nBrowser))
        Cognito[Amazon Cognito\nAuth / Sign Up]
    end

    User -->|1. Authenticates| Cognito

    subgraph AWS [AWS Cloud]
        subgraph VPC [VPC - Virtual Private Cloud]
            IGW([Internet Gateway])
            
            subgraph Subnets [Public Subnets - Multi-AZ]
                ALB[[Application Load Balancer]]
                EC2(EC2 Instances - ASG\nPython/Gunicorn\nIAM Role Attached)
            end
            
            IGW -->|Routes inbound traffic| ALB
            ALB -->|Forwards HTTP traffic| EC2
        end

        subgraph Backend [Data and AI Services Layer]
            Bedrock{Amazon Bedrock\nNova Micro}
            Polly{Amazon Polly\nAudio Synthesis}
            S3[(Amazon S3\nAudio Storage)]
            DB[(Amazon DynamoDB\nMetadata)]
        end

        EC2 -->|3. Sends raw article & gets dialogue script| Bedrock
        EC2 -->|4. Sends script & gets .mp3 audio| Polly
        EC2 -->|5. Saves .mp3 audio file| S3
        EC2 -->|6. Saves Metadata: Summary, Keys, URL| DB
    end

    User -->|2. HTTP Request via ALB DNS| IGW
    S3 -.->|7. Streams audio securely\nvia Pre-signed URL| User