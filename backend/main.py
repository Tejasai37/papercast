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

from backend.news_service import news_service
from backend.news_service import news_service

@app.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


# Validates user and sets cookie
@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    aws_service = RealAWSService()
    
    # Real Cognito Auth
    auth_result = aws_service.authenticate_user(username, password)
    if auth_result:
        groups = aws_service.get_user_groups(username)
        is_admin = "admins" in groups
        
        response = RedirectResponse(url="/admin" if is_admin else "/", status_code=303)
        response.set_cookie(key="session", value=username)
        response.set_cookie(key="id_token", value=auth_result['IdToken'])
        response.set_cookie(key="is_admin", value="true" if is_admin else "false")
        return response
    else:
        return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid Cognito credentials"})

@app.get("/logout")
def logout(response: Response):
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie("session")
    response.delete_cookie("id_token")
    response.delete_cookie("is_admin")
    return response

@app.get("/signup")
def signup_page(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})

@app.post("/signup")
async def signup(request: Request, username: str = Form(...), password: str = Form(...), email: str = Form(...)):
    aws_service = RealAWSService()
    success = aws_service.sign_up_user(username, password, email)
    if success:
        return RedirectResponse(url="/login?msg=Signup+successful", status_code=303)
    else:
        return templates.TemplateResponse("signup.html", {"request": request, "error": "Cognito signup failed"})

@app.get("/")
def landing_page(request: Request):
    user = request.cookies.get("session")
    if user:
        return RedirectResponse(url="/dashboard")
    return templates.TemplateResponse("landing.html", {"request": request})

@app.get("/dashboard")
def dashboard(request: Request, category: str = "general", q: str = None, language: str = "en", sort_by: str = "relevancy"):
    user = request.cookies.get("session")
    if not user:
        return RedirectResponse(url="/login")
        
    if q:
        # Keyword Search Mode
        news_articles = news_service.search_news(query=q, language=language, sort_by=sort_by)
        display_title = f'Results for "{q}"'
    else:
        # Category/Headline Mode
        news_articles = news_service.get_top_headlines(category=category)
        display_title = category.capitalize()
    
    # Fallback to empty list if API fails
    if not news_articles:
        news_articles = []
    
    # User specifically requested TOP FIVE
    top_five = news_articles[:5]
        
    return templates.TemplateResponse("dashboard.html", {
        "request": request, 
        "user": user,
        "news": top_five,
        "current_category": display_title,
        "search_query": q or ""
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
    is_admin = request.cookies.get("is_admin") == "true"
    
    if not is_admin:
        return RedirectResponse(url="/")
    
    aws_service = RealAWSService()
    stats = aws_service.get_admin_metrics()
    
    # Add a pseudo-metric for active sessions if needed, or just let it be
    stats["active_sessions"] = "Local Dev" # Or some other indicator
    
    return templates.TemplateResponse("admin.html", {
        "request": request, 
        "user": user,
        "stats": stats
    })


from backend.real_aws import RealAWSService

@app.post("/api/generate_audio/{article_id}")
async def generate_audio(request: Request, article_id: str):
    """
    Endpoint to generate audio with Bedrock Summarization and Polly TTS.
    """
    user = request.cookies.get("session", "anonymous")
    aws_service = RealAWSService()
    
    # 1. Check Cache (S3/DynamoDB)
    cached_data = aws_service.get_article_metadata(article_id)
    if cached_data and cached_data.get("audio_url"):
        return {"audio_url": cached_data["audio_url"], "status": "cached"}

    # 2. Get Article Content
    article = news_service.get_article_by_id(article_id)
    
    if not article:
        return {"error": "Article not found", "status": "failed"}

    content = article.get("content", "No content available.")
    
    # 3. Perform Generation
    # A. Summarize with Bedrock (Returns dict: script, summary, key_points, tldr)
    insights = aws_service.summarize_article(content)
    
    # B. Convert to Speech with Polly (Using the radio script)
    audio_bytes = aws_service.generate_speech(insights['script'])
    if not audio_bytes:
        return {"error": "Polly generation failed", "status": "failed"}
    
    # C. Upload to S3
    file_name = f"{article_id}.mp3"
    audio_url = aws_service.upload_audio(audio_bytes, file_name)
    
    # 4. Update Cache (DynamoDB) with Expanded Metadata
    aws_service.save_article_metadata(article_id, {
        "audio_url": audio_url,
        "status": "completed",
        "title": article.get("title"),
        "source": article.get("source"),
        "time": article.get("time"),
        "summary": insights.get("summary", ""),
        "key_points": insights.get("key_points", []),
        "tldr": insights.get("tldr", "")
    }, user_id=user)
    
    return {
        "audio_url": audio_url, 
        "status": "generated",
        "summary": insights.get("summary"),
        "key_points": insights.get("key_points"),
        "tldr": insights.get("tldr")
    }

@app.get("/library")
def library_page(request: Request):
    user = request.cookies.get("session")
    if not user:
        return RedirectResponse(url="/login")
    
    aws_service = RealAWSService()
    podcasts = aws_service.get_user_library(user)
    
    return templates.TemplateResponse("library.html", {
        "request": request,
        "user": user,
        "podcasts": podcasts
    })
