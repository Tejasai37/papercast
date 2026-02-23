import os
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Form, Response
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

# Load environment variables from .env file
load_dotenv()

app = FastAPI()

app.mount("/static", StaticFiles(directory="backend/static"), name="static")
templates = Jinja2Templates(directory="backend/templates")

@app.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


# Validates user and sets cookie
@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    aws_service = get_aws_service()
    
    if USE_REAL_AWS:
        # Real Cognito Auth
        auth_result = aws_service.authenticate_user(username, password)
        if auth_result:
            response = RedirectResponse(url="/admin" if username == "admin" else "/", status_code=303)
            # In real app, we might store JWT in cookie or session
            response.set_cookie(key="session", value=username)
            response.set_cookie(key="id_token", value=auth_result['IdToken'])
            return response
        else:
            return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid Cognito credentials"})
    else:
        # Mock Logic
        if username == "admin" and password == "admin":
            response = RedirectResponse(url="/admin", status_code=303)
            response.set_cookie(key="session", value="admin")
            return response
        elif username == "user" and password == "user":
            response = RedirectResponse(url="/", status_code=303)
            response.set_cookie(key="session", value="user")
            return response
        else:
            return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid mock credentials"})

@app.get("/logout")
def logout(response: Response):
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie("session")
    response.delete_cookie("id_token")
    return response

@app.get("/signup")
def signup_page(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})

@app.post("/signup")
async def signup(request: Request, username: str = Form(...), password: str = Form(...), email: str = Form(...)):
    aws_service = get_aws_service()
    if USE_REAL_AWS:
        success = aws_service.sign_up_user(username, password, email)
        if success:
            return RedirectResponse(url="/login?msg=Signup+successful", status_code=303)
        else:
            return templates.TemplateResponse("signup.html", {"request": request, "error": "Cognito signup failed"})
    else:
        # Mock signup simply redirects
        return RedirectResponse(url="/login?msg=Mock+Signup+successful", status_code=303)

@app.get("/")
def landing_page(request: Request):
    user = request.cookies.get("session")
    if user:
        return RedirectResponse(url="/dashboard")
    return templates.TemplateResponse("landing.html", {"request": request})

@app.get("/dashboard")
def dashboard(request: Request, category: str = "general"):
    user = request.cookies.get("session")
    if not user:
        return RedirectResponse(url="/login")
        
    from backend.news_service import news_service
    from backend.mock_data import MOCK_NEWS_DATA
    
    # Try to fetch real news
    news_articles = news_service.get_top_headlines(category=category)
    
    # Fallback to mock if API key is missing or error occurred
    if not news_articles:
        news_articles = MOCK_NEWS_DATA["articles"]
    
    # User specifically requested TOP FIVE
    top_five = news_articles[:5]
        
    return templates.TemplateResponse("dashboard.html", {
        "request": request, 
        "user": user,
        "news": top_five,
        "current_category": category.capitalize()
    })

@app.post("/api/process_link")
async def process_link(request: Request, url: str = Form(...)):
    """
    Endpoint to process a custom article link.
    """
    user = request.cookies.get("session")
    if not user:
        return {"error": "Unauthorized"}
    
    # In a real app, this would scrape the URL and use Bedrock to summarize
    # For now, we return a mock success message
    return {
        "title": "Custom Article Processed",
        "content": f"We have successfully analyzed the content from: {url}",
        "article_id": "custom-link",
        "status": "ready"
    }

@app.get("/admin")
def admin_dashboard(request: Request):
    user = request.cookies.get("session")
    if user != "admin":
        return RedirectResponse(url="/")
    
    return templates.TemplateResponse("admin.html", {
        "request": request, 
        "user": user,
        "stats": {
            "total_users": 142,
            "active_sessions": 23,
            "articles_generated": 89,
            "api_cost": "$4.20"
        }
    })


# Service Selector logic
USE_REAL_AWS = os.getenv("USE_REAL_AWS", "false").lower() == "true"

def get_aws_service():
    if USE_REAL_AWS:
        from backend.real_aws import RealAWSService
        return RealAWSService()
    else:
        from backend.mock_aws import mock_aws
        return mock_aws

@app.post("/api/generate_audio/{article_id}")
async def generate_audio(article_id: str):
    """
    Endpoint to generate audio with Caching (Mock or Real).
    """
    aws_service = get_aws_service()
    
    # 1. Check Cache (DynamoDB)
    cached_data = aws_service.get_article_metadata(article_id)
    if cached_data:
        return {"audio_url": cached_data["audio_url"], "status": "cached"}

    # 2. Simulate/Perform Generation
    if USE_REAL_AWS:
        # In a real app, this would call Bedrock/Polly
        # For now, we'll still simulate the delay but use real S3/DynamoDB
        import asyncio
        await asyncio.sleep(2)
        
        # Mock file content for testing real S3
        mock_content = b"This is a simulated audio file content."
        file_name = f"{article_id}.wav"
        
        audio_url = aws_service.upload_audio(mock_content, file_name)
    else:
        import asyncio
        await asyncio.sleep(2)  # Simulate processing delay
        audio_url = "/static/mock.wav"
    
    # 3. Update Cache (DynamoDB)
    aws_service.save_article_metadata(article_id, {
        "audio_url": audio_url,
        "status": "completed"
    })
    
    return {"audio_url": audio_url, "status": "generated"}
