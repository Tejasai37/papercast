### **Project Title: PaperCast AI-Powered News Podcast Platform**

**Abstract**

This project focuses on the development of a secure, cloud-native application that redefines news consumption. Unlike traditional static news feeds, this platform empowers users to discover trending articles and instantly convert them into high-quality, AI-generated audio podcasts on demand. The solution is architected for straightforward deployment, utilizing a **"pull" model** where content is synthesized and enriched in real-time using Generative AI. Built on **AWS**, the platform utilizes an array of AI services for a seamless, multi-lingual, and deeply insightful user experience.

**Objective**

The primary objective is to build a production-ready, full-stack web application that solves information overload through personalization and automation. Key goals include:

* **On-Demand AI Audio:** Enabling users to select articles for instant audio conversion using **Amazon Bedrock** for context-aware summarization and **Amazon Polly** for lifelike neural speech synthesis.  
* **Rich NLP Insights:** Utilizing **Amazon Comprehend** to inherently analyze the source content, extracting key phrases, sentiments, and entities to present alongside the audio.
* **Global Accessibility:** Integrating **Amazon Translate** to allow users to generate podcast audio in their preferred target language.
* **Cost Efficiency & Performance:** Utilizing **Amazon DynamoDB** as a caching layer to prevent redundant AI processing for frequently requested articles, alongside **Amazon S3** for secure audio object storage.
* **Robust Security:** Implementing Role-Based Access Control (RBAC) using **Amazon Cognito** to distinguish between General and Admin users.

**Architecture Overview**

The system adopts a modern 3-tier web architecture designed for security and performance:

* **Frontend & Backend:** The user interface is natively rendered via Server-Side Rendering (SSR) using **Jinja2 Templates** seamlessly integrated with the **FastAPI (Python)** backend orchestrator.  
* **AI Processing Pipeline:** **AWS Boto3** is used to create a unified data pipeline processing content from external News APIs. This pipeline routes data through **Amazon Comprehend**, **Amazon Bedrock**, and **Amazon Translate**, before finally generating audio via **Amazon Polly**.
* **Storage & Caching:** **Amazon S3** stores the generated MP3 files, while **Amazon DynamoDB** manages user profiles, article metadata, NLP insights, and audio caching state.  
* **Authentication:** **Amazon Cognito** secures the application with industry-standard authentication and user group management.

**Workflow and Key Interactions**

1. **User Access:** The user logs in securely via **Cognito**.  
2. **Content Discovery:** The user selects a trending news article via the web dashboard.  
3. **On-Demand Processing:** When the user initiates a podcast generation:  
   * The backend queries **DynamoDB** to check if an audio file already exists for that specific text & language (Cache Check).  
   * *If New:* **Boto3** sends the text to **Amazon Comprehend** for NLP insights, to **Amazon Bedrock** to generate a concise summary script, to **Amazon Translate** for language conversion (if requested), and finally to **Amazon Polly** to synthesize speech.  
   * *Storage:* The resulting MP3 is uploaded to **S3**, and the metadata/insights are saved to **DynamoDB**.  
4. **Playback:** The secure S3 URL is returned to the frontend, allowing the user to stream the audio podcast immediately.  
5. **Admin Management:** Admin users can access restricted endpoints to clear the cache or remove specific items from the database.

**Conclusion**

The Interactive AI-Powered News Podcast Platform demonstrates a comprehensive mastery of modern cloud integration. By combining the reactive capabilities of a full-stack web application with an advanced pipeline of Serverless AI services (Comprehend, Bedrock, Translate, Polly), it delivers a highly capable and intelligent media platform. This project successfully bridges the gap between raw information and personalized, accessible media, offering a sophisticated solution to reading fatigue and information overload.