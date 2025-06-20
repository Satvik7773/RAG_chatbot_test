import os
import shutil
import time
import asyncio
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from starlette.responses import JSONResponse

# Import the API-based ChatBot
from main import APIBasedChatBot as ChatBot

app = FastAPI()

# Lightweight session management
_sessions: dict[str, ChatBot] = {}
_session_timestamps: dict[str, float] = {}

# CORS

# Request models
class ChatRequest(BaseModel):
    user: str
    question: str

class TrainRequest(BaseModel):
    user: str

async def cleanup_expired_sessions():
    """Background task to cleanup old sessions"""
    while True:
        try:
            current_time = time.time()
            expired_users = [
                user for user, timestamp in _session_timestamps.items()
                if current_time - timestamp > 1800  # 30 minutes
            ]
            
            for user in expired_users:
                _sessions.pop(user, None)
                _session_timestamps.pop(user, None)
                
                # Clean up user files
                tmpdir = f"/tmp/{user}"
                if os.path.exists(tmpdir):
                    shutil.rmtree(tmpdir, ignore_errors=True)
            
            if expired_users:
                print(f"Cleaned up {len(expired_users)} expired sessions")
            
            await asyncio.sleep(600)  # Check every 10 minutes
            
        except Exception as e:
            print(f"Cleanup error: {e}")
            await asyncio.sleep(600)

@app.on_event("startup")
async def startup_event():
    """Start background cleanup task"""
    asyncio.create_task(cleanup_expired_sessions())

@app.post("/upload")
async def upload_documents(
    background_tasks: BackgroundTasks,
    user: str = Form(...),
    files: List[UploadFile] = File(...)
):
    """
    Upload documents with strict memory limits for Render free tier
    """
    try:
        # Strict limits for free tier
        if len(files) > 5:
            raise HTTPException(400, "Maximum 5 files allowed on free tier")
        
        # Check total size before processing
        total_size = 0
        for file in files:
            if hasattr(file, 'size') and file.size:
                total_size += file.size
        
        if total_size > 10 * 1024 * 1024:  # 10MB total limit
            raise HTTPException(400, "Total file size exceeds 10MB limit")
        
        # Clean up old session data
        if user in _sessions:
            del _sessions[user]
        
        tmpdir = f"/tmp/{user}"
        if os.path.exists(tmpdir):
            shutil.rmtree(tmpdir)
        os.makedirs(tmpdir, exist_ok=True)
        
        file_paths = []
        processed_size = 0
        
        for upload in files:
            # Validate file type
            allowed_extensions = {'.txt', '.pdf', '.docx', '.doc'}
            file_ext = os.path.splitext(upload.filename)[1].lower()
            
            if file_ext not in allowed_extensions:
                continue
            
            # Read file content
            content = await upload.read()
            
            # Skip if file is too large
            if len(content) > 3 * 1024 * 1024:  # 3MB per file
                continue
            
            # Check cumulative size
            processed_size += len(content)
            if processed_size > 10 * 1024 * 1024:  # Stop if total exceeds 10MB
                break
            
            dest = os.path.join(tmpdir, upload.filename)
            with open(dest, "wb") as out:
                out.write(content)
            file_paths.append(dest)
        
        if not file_paths:
            raise HTTPException(400, "No valid files to process")
        
        # Create ChatBot instance (this uses minimal memory with API approach)
        try:
            bot = ChatBot(file_paths=file_paths)
            
            # Check if any API is configured
            stats = bot.get_stats()
            if not any(stats['apis_configured'].values()):
                raise HTTPException(500, "No AI API configured. Please set GROQ_API_KEY, TOGETHER_API_KEY, or OPENAI_API_KEY")
            
            _sessions[user] = bot
            _session_timestamps[user] = time.time()
            
            # Schedule file cleanup
            background_tasks.add_task(cleanup_user_files, tmpdir, delay=3600)
            
            return {
                "status": "success",
                "message": "Documents uploaded and processed successfully",
                "stats": stats
            }
            
        except Exception as e:
            # Clean up on failure
            if os.path.exists(tmpdir):
                shutil.rmtree(tmpdir, ignore_errors=True)
            raise HTTPException(500, f"Failed to process documents: {str(e)}")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Upload failed: {str(e)}")

async def cleanup_user_files(tmpdir: str, delay: int):
    """Background task to clean up user files"""
    await asyncio.sleep(delay)
    if os.path.exists(tmpdir):
        shutil.rmtree(tmpdir, ignore_errors=True)

@app.post("/chat")
async def chat(req: ChatRequest):
    """
    Chat endpoint using API-based models (minimal server memory usage)
    """
    try:
        user = req.user
        
        if user not in _sessions:
            raise HTTPException(400, "Session not found. Please upload documents first.")
        
        bot = _sessions[user]
        
        # Update session timestamp
        _session_timestamps[user] = time.time()
        
        # Get answer using API-based models
        # This runs in a thread to avoid blocking
        answer = await asyncio.get_event_loop().run_in_executor(
            None, bot.ask, req.question
        )
        
        return {
            "answer": answer,
            "timestamp": time.time(),
            "status": "success"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Chat processing failed: {str(e)}")

@app.post("/train")
def train(req: TrainRequest):
    """
    Training endpoint (not needed for API-based approach)
    """
    if req.user not in _sessions:
        raise HTTPException(400, "Session not found. Please upload documents first.")
    
    # Update timestamp
    _session_timestamps[req.user] = time.time()
    
    return {"status": "success", "message": "Training not required for API-based models"}

@app.post("/logout")
def logout(user: str = Form(...)):
    """
    Logout and cleanup user session
    """
    try:
        # Remove from sessions
        _sessions.pop(user, None)
        _session_timestamps.pop(user, None)
        
        # Clean up user files
        tmpdir = f"/tmp/{user}"
        if os.path.exists(tmpdir):
            shutil.rmtree(tmpdir, ignore_errors=True)
        
        return {"status": "success", "message": "Logged out successfully"}
        
    except Exception as e:
        return JSONResponse(
            content={"status": "error", "message": f"Logout failed: {str(e)}"},
            status_code=500
        )

@app.get("/")
async def root():
    return {
        "message": "RAG ChatBot API with API-based models",
        "active_sessions": len(_sessions),
        "memory_usage": "Minimal (using API models)",
        "timestamp": time.time()
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "active_sessions": len(_sessions),
        "memory_approach": "API-based (minimal server memory)",
        "apis_supported": ["Groq (free)", "Together AI (free)", "OpenAI (paid)"]
    }

@app.get("/user/{user}/stats")
async def get_user_stats(user: str):
    """Get statistics for a specific user session"""
    if user not in _sessions:
        raise HTTPException(404, "User session not found")
    
    bot = _sessions[user]
    stats = bot.get_stats()
    
    return {
        "user": user,
        "session_age": time.time() - _session_timestamps.get(user, 0),
        **stats
    }

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    print(f"Global exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc),
            "type": type(exc).__name__
        }
    )
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
