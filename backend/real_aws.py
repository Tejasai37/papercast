
import boto3
import json
import os
import hmac
import hashlib
import base64
from botocore.exceptions import ClientError

class RealAWSService:
    def __init__(self):
        # 1. Start with defaults or environment variables
        self.config = {
            "s3_bucket": os.getenv("S3_BUCKET_NAME"),
            "dynamodb_table": os.getenv("DYNAMODB_TABLE_NAME", "PapercastCache"),
            "user_pool_id": os.getenv("COGNITO_USER_POOL_ID"),
            "client_id": os.getenv("COGNITO_CLIENT_ID"),
            "client_secret": os.getenv("COGNITO_CLIENT_SECRET"),
            "region": os.getenv("AWS_REGION", "us-east-1"),
            "aws_access_key": os.getenv("AWS_ACCESS_KEY_ID"),
            "aws_secret_key": os.getenv("AWS_SECRET_ACCESS_KEY")
        }

        # 2. If a local config file exists, use it to fill in blanks (backward compatibility)
        config_path = "infrastructure/aws_config.json"
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                file_config = json.load(f)
                for key, value in file_config.items():
                    if not self.config.get(key): # Only fill if environment variable is NOT set
                        self.config[key] = value

        # 3. Initialize clients explicitly with credentials
        session_kwargs = {
            "region_name": self.config["region"]
        }
        if self.config["aws_access_key"] and self.config["aws_secret_key"]:
            session_kwargs["aws_access_key_id"] = self.config["aws_access_key"]
            session_kwargs["aws_secret_access_key"] = self.config["aws_secret_key"]

        self.s3 = boto3.client("s3", **session_kwargs)
        self.dynamodb = boto3.resource("dynamodb", **session_kwargs)
        self.table = self.dynamodb.Table(self.config["dynamodb_table"])
        self.cognito = boto3.client("cognito-idp", **session_kwargs)
        
        self.bedrock = boto3.client("bedrock-runtime", **session_kwargs)
        self.polly = boto3.client("polly", **session_kwargs)

        self.comprehend = boto3.client("comprehend", **session_kwargs)
        self.translate = boto3.client("translate", **session_kwargs)

    def _get_secret_hash(self, username):
        """Calculates the HMAC-SHA256 secret hash for Cognito"""
        if not self.config["client_secret"]:
            return None
            
        msg = username + self.config["client_id"]
        dig = hmac.new(
            str(self.config["client_secret"]).encode('utf-8'),
            msg.encode('utf-8'),
            digestmod=hashlib.sha256
        ).digest()
        return base64.b64encode(dig).decode()

    # --- S3 (File Storage) ---
    def upload_audio(self, file_content: bytes, file_name: str) -> str:
        """Uploads audio file to S3 and returns the URL"""
        try:
            print(f"DEBUG: Uploading {file_name} to S3 bucket {self.config['s3_bucket']}")
            self.s3.put_object(
                Bucket=self.config["s3_bucket"],
                Key=file_name,
                Body=file_content,
                ContentType="audio/mpeg"
            )
            # Generating a pre-signed URL
            url = self.s3.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.config['s3_bucket'], 'Key': file_name},
                ExpiresIn=3600
            )
            print(f"DEBUG: S3 Upload success: {url[:50]}...")
            return url
        except ClientError as e:
            print(f"DEBUG ERROR: S3 Upload Error: {e}")
            return None

    def get_audio_url(self, file_name: str) -> str:
        """Check if file exists and return a pre-signed URL"""
        try:
            self.s3.head_object(Bucket=self.config["s3_bucket"], Key=file_name)
            url = self.s3.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.config['s3_bucket'], 'Key': file_name},
                ExpiresIn=3600
            )
            return url
        except ClientError:
            return None

    # --- DynamoDB (Metadata Cache) ---
    def get_article_metadata(self, article_id: str):
        """Fetch metadata from DynamoDB"""
        try:
            response = self.table.get_item(Key={'ArticleID': article_id})
            return response.get('Item')
        except ClientError as e:
            print(f"DEBUG ERROR: DynamoDB Get Error: {e}")
            return None

    def save_article_metadata(self, article_id: str, data: dict, user_id: str = "system"):
        """Save metadata to DynamoDB, including the UserID"""
        try:
            print(f"DEBUG: Saving metadata for {article_id} to DynamoDB")
            item = {'ArticleID': article_id, 'UserID': user_id, **data}
            self.table.put_item(Item=item)
            print("DEBUG: DynamoDB Save success")
        except ClientError as e:
            print(f"DEBUG ERROR: DynamoDB Put Error: {e}")

    def get_user_library(self, user_id: str):
        """Fetches all podcasts generated by a specific user"""
        try:
            # For personal projects, a scan with filter is fine. 
            # In high-volume production, you would use a GSI on UserID.
            response = self.table.scan(
                FilterExpression=boto3.dynamodb.conditions.Attr('UserID').eq(user_id)
            )
            return response.get('Items', [])
        except Exception as e:
            print(f"DynamoDB Library Error: {e}")
            return []

    # --- AI Services (Comprehend, Bedrock, Polly) ---
    def analyze_text_comprehend(self, text: str) -> dict:
        """Uses Amazon Comprehend to extract sentiment, entities, and key phrases."""
        try:
            # Comprehend has a 5000 byte limit per request. 
            # For simplicity in this demo, we'll truncate the text for analysis if it's too long
            # Production apps should chunk the text and aggregate the results.
            text_to_analyze = text[:4800] 
            
            print("DEBUG: Sending text to Comprehend...")
            
            # 1. Sentiment
            sentiment_resp = self.comprehend.detect_sentiment(Text=text_to_analyze, LanguageCode='en')
            sentiment = sentiment_resp['Sentiment']
            
            # 2. Key Phrases (Top 5)
            phrases_resp = self.comprehend.detect_key_phrases(Text=text_to_analyze, LanguageCode='en')
            key_phrases = [p['Text'] for p in phrases_resp['KeyPhrases'][:5]]
            
            # 3. Entities (Top 5 Unique Persons/Organizations/Locations)
            entities_resp = self.comprehend.detect_entities(Text=text_to_analyze, LanguageCode='en')
            entities = []
            seen = set()
            for e in entities_resp['Entities']:
                if e['Type'] in ['PERSON', 'ORGANIZATION', 'LOCATION'] and e['Text'] not in seen:
                    entities.append(f"{e['Text']} ({e['Type']})")
                    seen.add(e['Text'])
                    if len(entities) >= 5:
                        break
                        
            return {
                "sentiment": sentiment,
                "key_phrases": key_phrases,
                "entities": entities
            }
        except Exception as e:
            print(f"Comprehend Error: {e}")
            return {
                "sentiment": "UNKNOWN",
                "key_phrases": [],
                "entities": []
            }
            
    def translate_text(self, text: str, target_language: str = "en") -> str:
        """Translates text to the target language using Amazon Translate."""
        if target_language == "en" or not text:
            return text
            
        try:
            print(f"DEBUG: Translating text to {target_language}...")
            
            # Translate has a 10,000 byte limit, which is plenty for our scripts/summaries
            response = self.translate.translate_text(
                Text=text,
                SourceLanguageCode="en", # Assuming English source from our Bedrock prompt
                TargetLanguageCode=target_language
            )
            return response.get('TranslatedText', text)
        except Exception as e:
            print(f"Translate Error: {e}")
            return text
            
    def summarize_article(self, text: str) -> dict:
        """Uses Bedrock (Nova Micro) to generate a full suite of AI insights: Script, Summary, Key Points, and TLDR"""
        try:
            model_id = "amazon.nova-micro-v1:0"
            system_prompt = (
                "You are an AI news analyst ensemble. Your task is to extract insights from an article and return them in VALID JSON format.\n"
                "The 'script' part must be a professional dialogue between two people: [HOST] and [EXPERT].\n"
                "- [HOST]: Inquisitive, sets the stage, and asks the expert to clarify.\n"
                "- [EXPERT]: Explains the news in simple, precise, and authoritative terms.\n\n"
                "CRITICAL: Do not include ANY text before or after the JSON. \n"
                "Ensure all quotes inside strings are correctly escaped with a backslash (\\\"). \n"
                "Do not include raw newlines within JSON string values; use '\\n' instead.\n\n"
                "Return a JSON object with exactly these keys:\n"
                "- 'script': A dialogue script using [HOST] and [EXPERT] markers.\n"
                "- 'summary': A 1-2 paragraph professional summary for visual reading.\n"
                "- 'key_points': A list of the most important facts as bullet points.\n"
                "- 'tldr': A single, punchy 'too long didn't read' sentence."
            )
            user_prompt = f"Analyze the following article and provide the insights in the requested JSON format.\n\nArticle: {text}"
            
            response = self.bedrock.converse(
                modelId=model_id,
                messages=[
                    {
                        "role": "user",
                        "content": [{"text": user_prompt}]
                    }
                ],
                system=[{"text": system_prompt}],
                inferenceConfig={
                    "maxTokens": 800,
                    "temperature": 0.5,
                    "topP": 0.9
                }
            )
            
            raw_text = response['output']['message']['content'][0]['text'].strip()
            
            # Robust JSON extraction: Find the first '{' and last '}'
            try:
                # 1. Basic Cleaning
                start_idx = raw_text.find('{')
                end_idx = raw_text.rfind('}')
                if start_idx == -1 or end_idx == -1:
                    raise ValueError("No JSON object found in response")
                
                clean_json = raw_text[start_idx:end_idx + 1]
                
                # 2. Advanced Sanitization for Bedrock hallucinations
                import re
                
                # Fix trailing commas before closing braces/brackets
                sanitized_json = re.sub(r',\s*([\]}])', r'\1', clean_json)
                
                # Fix Invalid JSON Escapes (e.g. \ followed by something not in " \ / b f n r t u)
                # This double-escapes the backslash so the JSON parser accepts it as a literal backslash.
                sanitized_json = re.sub(r'\\(?!["\\/bfnrtu])', r'\\\\', sanitized_json)
                
                data = json.loads(sanitized_json, strict=False)
                
                # Normalize 'script' to string if it's a list
                if 'script' in data and isinstance(data['script'], list):
                    data['script'] = " ".join(data['script'])
                    
                return data
                
            except Exception as e:
                print(f"DEBUG ERROR: JSON Parse failed after deep cleanup. Error: {e}")
                # Last resort: try just raw parsing if cleanup failed
                try:
                    return json.loads(raw_text[raw_text.find('{'):raw_text.rfind('}')+1], strict=False)
                except:
                    raise
                
        except Exception as e:
            print(f"Bedrock Error: {e}. Falling back to simple summary.")
            return {
                "script": text[:200] + "...",
                "summary": text[:500] + "...",
                "key_points": ["Could not extract details."],
                "tldr": "News summary unavailable."
            }

    def generate_speech(self, text: str) -> bytes:
        """Converts text to speech using AWS Polly with Multi-Voice support via separate calls"""
        try:
            # Handle cases where Bedrock returns the script as a list instead of a string
            if isinstance(text, list):
                text = " ".join(text)
            
            # Check if text contains [HOST] or [EXPERT] markers
            if "[HOST]" in text or "[EXPERT]" in text:
                print("DEBUG: Generating Multi-Voice audio via segment concatenation")
                
                # Split text into segments by [HOST] and [EXPERT] markers
                # Using regex to find all segments
                import re
                pattern = r'(\[HOST\]:|\[EXPERT\]:|\[HOST\]|\[EXPERT\])'
                parts = re.split(pattern, text)
                
                combined_audio = b""
                current_voice = "Matthew" # Default
                
                for part in parts:
                    clean_part = part.strip()
                    if not clean_part: continue
                    
                    if "[HOST]" in clean_part:
                        current_voice = "Matthew"
                        continue
                    elif "[EXPERT]" in clean_part:
                        current_voice = "Joanna"
                        continue
                        
                    # This is the actual text segment
                    try:
                        resp = self.polly.synthesize_speech(
                            Text=clean_part,
                            OutputFormat="mp3",
                            VoiceId=current_voice,
                            Engine="neural"
                        )
                        combined_audio += resp['AudioStream'].read()
                    except Exception as e:
                        print(f"DEBUG: Segment synthesis failed for voice {current_voice}: {e}")
                        # Fallback to standard if neural fails
                        resp = self.polly.synthesize_speech(
                            Text=clean_part,
                            OutputFormat="mp3",
                            VoiceId=current_voice,
                            Engine="standard"
                        )
                        combined_audio += resp['AudioStream'].read()
                
                return combined_audio
            else:
                # Legacy / Single Voice
                response = self.polly.synthesize_speech(
                    Text=text,
                    OutputFormat="mp3",
                    VoiceId="Matthew",
                    Engine="neural"
                )
                return response['AudioStream'].read()
                
        except Exception as e:
            print(f"Polly Global Error: {e}")
            return None

    # --- Cognito (Authentication) ---
    def authenticate_user(self, username, password):
        """Authenticates user with Cognito and returns tokens"""
        try:
            auth_params = {
                'USERNAME': username,
                'PASSWORD': password
            }
            
            secret_hash = self._get_secret_hash(username)
            if secret_hash:
                auth_params['SECRET_HASH'] = secret_hash

            response = self.cognito.admin_initiate_auth(
                UserPoolId=self.config["user_pool_id"],
                ClientId=self.config["client_id"],
                AuthFlow='ADMIN_NO_SRP_AUTH',
                AuthParameters=auth_params
            )
            return response['AuthenticationResult']
        except ClientError as e:
            print(f"Cognito Auth Error: {e}")
            return None

    def sign_up_user(self, username, password, email):
        """Creates a new user in Cognito"""
        try:
            response = self.cognito.admin_create_user(
                UserPoolId=self.config["user_pool_id"],
                Username=username,
                UserAttributes=[
                    {'Name': 'email', 'Value': email},
                    {'Name': 'email_verified', 'Value': 'true'}
                ],
                MessageAction='SUPPRESS' # Don't send welcome email for dev
            )
            # Set password
            self.cognito.admin_set_user_password(
                UserPoolId=self.config["user_pool_id"],
                Username=username,
                Password=password,
                Permanent=True
            )
            return response
        except ClientError as e:
            print(f"Cognito Sign-up Error: {e}")
            return None

    def get_user_groups(self, username):
        """Fetches the groups a user belongs to in Cognito"""
        try:
            response = self.cognito.admin_list_groups_for_user(
                UserPoolId=self.config["user_pool_id"],
                Username=username
            )
            return [group['GroupName'] for group in response.get('Groups', [])]
        except ClientError as e:
            print(f"Cognito Groups Error: {e}")
            return []

    def get_admin_metrics(self):
        """Fetches real metrics from Cognito and DynamoDB for the Admin Dashboard"""
        metrics = {
            "total_users": 0,
            "articles_generated": 0,
            "api_cost": "Calculated..."
        }
        try:
            # 1. Total Users from Cognito (Estimated but very fast)
            cognito_res = self.cognito.describe_user_pool(UserPoolId=self.config["user_pool_id"])
            metrics["total_users"] = cognito_res['UserPool'].get('EstimatedNumberOfUsers', 0)
            
            # 2. Total Articles from DynamoDB (Live Scan Count)
            # While 'item_count' is fast but delayed (6h), scan(Select='COUNT') is live.
            # For smaller tables, this is the most reliable way to get an exact live count.
            dynamo_res = self.table.scan(Select='COUNT')
            metrics["articles_generated"] = dynamo_res.get('Count', 0)
            
        except Exception as e:
            print(f"Admin Metrics Error: {e}")
            
        return metrics

    # --- Admin Advanced Management ---
    def list_all_users(self):
        """Fetches all users from the Cognito User Pool with pagination support"""
        try:
            users = []
            paginator = self.cognito.get_paginator('list_users')
            for page in paginator.paginate(UserPoolId=self.config["user_pool_id"]):
                for user in page.get('Users', []):
                    attrs = {attr['Name']: attr['Value'] for attr in user.get('Attributes', [])}
                    users.append({
                        "username": user['Username'],
                        "email": attrs.get('email', 'N/A'),
                        "enabled": user['Enabled'],
                        "status": user['UserStatus'],
                        "created": user['UserCreateDate'].strftime('%Y-%m-%d %H:%M')
                    })
            return users
        except ClientError as e:
            print(f"Cognito List Users Error: {e}")
            return []

    def toggle_user_status(self, username, enabled: bool):
        """Enables or Disables a user in Cognito"""
        try:
            if enabled:
                self.cognito.admin_enable_user(
                    UserPoolId=self.config["user_pool_id"],
                    Username=username
                )
            else:
                self.cognito.admin_disable_user(
                    UserPoolId=self.config["user_pool_id"],
                    Username=username
                )
            return True
        except ClientError as e:
            print(f"Cognito Toggle Error: {e}")
            return False

    def get_all_podcasts(self):
        """Fetches all records from the DynamoDB table with pagination support"""
        try:
            results = []
            response = self.table.scan(
                FilterExpression=boto3.dynamodb.conditions.Attr('audio_url').exists()
            )
            results.extend(response.get('Items', []))

            # Handle pagination
            while 'LastEvaluatedKey' in response:
                response = self.table.scan(
                    FilterExpression=boto3.dynamodb.conditions.Attr('audio_url').exists(),
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
                results.extend(response.get('Items', []))

            return results
        except Exception as e:
            print(f"DynamoDB Global Scan Error: {e}")
            return []

    def delete_podcast(self, article_id: str):
        """Deletes podcast metadata from DynamoDB and the .mp3 file from S3"""
        try:
            # 1. Delete from S3
            file_name = f"{article_id}.mp3"
            self.s3.delete_object(Bucket=self.config["s3_bucket"], Key=file_name)
            
            # 2. Delete from DynamoDB
            self.table.delete_item(Key={'ArticleID': article_id})
            return True
        except Exception as e:
            print(f"Podcast Deletion Error: {e}")
            return False

    def purge_all_podcasts(self):
        """Wipes ALL generated podcasts from S3 and DynamoDB"""
        try:
            # 1. Get all podcast records
            podcasts = self.get_all_podcasts()
            if not podcasts:
                return True
            
            # 2. Delete from S3 (Bulk)
            delete_objects = [{'Key': f"{p['ArticleID']}.mp3"} for p in podcasts]
            self.s3.delete_objects(
                Bucket=self.config["s3_bucket"],
                Delete={'Objects': delete_objects}
            )
            
            # 3. Delete from DynamoDB (Batch)
            with self.table.batch_writer() as batch:
                for podcast in podcasts:
                    batch.delete_item(Key={'ArticleID': podcast['ArticleID']})
            
            return True
        except Exception as e:
            print(f"Global Purge Error: {e}")
            return False

# Singleton Instance (Optional: but useful for FastAPI)
# real_aws = RealAWSService()
