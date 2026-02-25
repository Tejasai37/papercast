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
from backend.real_aws import RealAWSService

@app.get("/login")
def login_page(request: Request):
    user = request.cookies.get("session")
    return templates.TemplateResponse("login.html", {"request": request, "user": user})

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
        response.set_cookie(key="session", value=username, httponly=True)
        response.set_cookie(key="id_token", value=auth_result['IdToken'], httponly=True)
        response.set_cookie(key="is_admin", value="true" if is_admin else "false", httponly=True)
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
    user = request.cookies.get("session")
    return templates.TemplateResponse("signup.html", {"request": request, "user": user})

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
    return templates.TemplateResponse("landing.html", {"request": request, "user": user})

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


@app.get("/admin")
def admin_dashboard(request: Request):
    user = request.cookies.get("session")
    is_admin = request.cookies.get("is_admin") == "true"
    
    if not is_admin:
        return RedirectResponse(url="/")
    
    aws_service = RealAWSService()
    stats = aws_service.get_admin_metrics()
    
    stats["active_sessions"] = "Local Dev"
    
    return templates.TemplateResponse("admin.html", {
        "request": request, 
        "user": user,
        "stats": stats
    })

@app.get("/admin/users")
def admin_users(request: Request):
    is_admin = request.cookies.get("is_admin") == "true"
    if not is_admin: return RedirectResponse(url="/")
    
    aws_service = RealAWSService()
    users = aws_service.list_all_users()
    return templates.TemplateResponse("admin_users.html", {"request": request, "users": users})

@app.post("/admin/users/toggle")
async def toggle_user(request: Request, username: str = Form(...), enabled: str = Form(...)):
    is_admin = request.cookies.get("is_admin") == "true"
    if not is_admin: return {"error": "Unauthorized"}
    
    aws_service = RealAWSService()
    # enabled comes as 'true' or 'false' string from form
    success = aws_service.toggle_user_status(username, enabled == "true")
    return RedirectResponse(url="/admin/users?msg=Status+Updated", status_code=303)

@app.get("/admin/podcasts")
def admin_podcasts(request: Request):
    is_admin = request.cookies.get("is_admin") == "true"
    if not is_admin: return RedirectResponse(url="/")
    
    aws_service = RealAWSService()
    podcasts = aws_service.get_all_podcasts()
    return templates.TemplateResponse("admin_podcasts.html", {"request": request, "podcasts": podcasts})

@app.post("/admin/podcasts/delete/{article_id}")
async def delete_podcast(request: Request, article_id: str):
    is_admin = request.cookies.get("is_admin") == "true"
    if not is_admin: return {"error": "Unauthorized"}
    
    aws_service = RealAWSService()
    success = aws_service.delete_podcast(article_id)
    return RedirectResponse(url="/admin/podcasts?msg=Podcast+Deleted", status_code=303)

@app.post("/admin/podcasts/purge")
async def purge_podcasts(request: Request):
    is_admin = request.cookies.get("is_admin") == "true"
    if not is_admin: return {"error": "Unauthorized"}
    
    aws_service = RealAWSService()
    success = aws_service.purge_all_podcasts()
    return RedirectResponse(url="/admin/podcasts?msg=All+Podcasts+Purged", status_code=303)

@app.post("/api/generate_audio/{article_id}")
async def generate_audio(request: Request, article_id: str):
    """
    Endpoint to generate audio with Bedrock Summarization and Polly TTS.
    """
    user = request.cookies.get("session", "anonymous")
    print(f"DEBUG: Audio request for {article_id} by user {user}")
    aws_service = RealAWSService()
    
    # 1. Try to get content from Memory Cache (Fresh Discovery)
    article = news_service.get_article_by_id(article_id)
    
    # 2. If not in memory, check DynamoDB (Already Generated)
    article_data = aws_service.get_article_metadata(article_id)
    
    # Handle already completed podcasts (from DB)
    if article_data and article_data.get("status") == "completed" and article_data.get("audio_url"):
        print(f"DEBUG: Found already completed podcast for {article_id}")
        return {
            "audio_url": article_data["audio_url"], 
            "status": "cached",
            "summary": article_data.get("summary"),
            "key_points": article_data.get("key_points"),
            "tldr": article_data.get("tldr"),
            "script": article_data.get("script")
        }

    # 3. If we have the article in memory, generate it!
    if article:
        content = article.get("content", "No content available.")
        title = article.get("title")
        source = article.get("source")
        time = article.get("time")
    # 4. If memory is gone but DB has 'discovered' content (fallback for older records)
    elif article_data and article_data.get("content"):
        content = article_data.get("content")
        title = article_data.get("title")
        source = article_data.get("source")
        time = article_data.get("time")
    else:
        print(f"DEBUG ERROR: Article {article_id} not found in memory or DB!")
        return {"error": "Article content expired. Please refresh headlines.", "status": "failed"}

    print(f"DEBUG: Generating audio for: {title[:30]}...")
    
    # 3. Perform Generation
    insights = aws_service.summarize_article(content)
    
    audio_bytes = aws_service.generate_speech(insights['script'])
    if not audio_bytes:
        print("DEBUG ERROR: Polly generation failed")
        return {"error": "Polly generation failed", "status": "failed"}
    
    file_name = f"{article_id}.mp3"
    audio_url = aws_service.upload_audio(audio_bytes, file_name)
    if not audio_url:
        print("DEBUG ERROR: S3 upload failed")
        return {"error": "S3 upload failed", "status": "failed"}
    
    # 4. Save to DynamoDB ON-DEMAND (Only on successful generation)
    aws_service.save_article_metadata(article_id, {
        "article_id": article_id,
        "audio_url": audio_url,
        "status": "completed",
        "title": title,
        "source": source,
        "time": time,
        "summary": insights.get("summary", ""),
        "key_points": insights.get("key_points", []),
        "tldr": insights.get("tldr", ""),
        "script": insights.get("script", "")
    }, user_id=user)
    
    print(f"DEBUG: Success! Audio generated and saved for {article_id}")
    return {
        "audio_url": audio_url, 
        "status": "generated",
        "summary": insights.get("summary"),
        "key_points": insights.get("key_points"),
        "tldr": insights.get("tldr"),
        "script": insights.get("script")
    }

@app.post("/api/process_link")
async def process_link(request: Request, url: str = Form(...)):
    user = request.cookies.get("session", "anonymous")
    article = news_service.extract_article(url)
    
    # Also fetch general headlines to fill the rest of the page
    headlines = news_service.get_top_headlines(category="general")
    
    if not article:
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "user": user,
            "news": headlines[:5],
            "current_category": "Error",
            "error": "Failed to extract content from link."
        })
    
    # Prepend custom article to the top of the general headlines
    all_news = [article] + headlines[:4]
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": user,
        "news": all_news,
        "current_category": "Custom Broadcast"
    })

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
