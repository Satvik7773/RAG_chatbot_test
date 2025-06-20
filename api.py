import os
import shutil
import asyncio
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from starlette.responses import JSONResponse
import time
from contextlib import asynccontextmanager

# Import your optimized ChatBot
from main import OptimizedChatBot as ChatBot

# Global session management with cleanup
_sessions: dict[str, ChatBot] = {}
_session_timestamps: dict[str, float] = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Starting up...")
    # Start cleanup task
    cleanup_task = asyncio.create_task(periodic_cleanup())
    
    yield
    
    # Shutdown
    print("Shutting down...")
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass

app = FastAPI(lifespan=lifespan)

# CORS middleware

# Request models
class TrainRequest(BaseModel):
    user: str

class ChatRequest(BaseModel):
    user: str
    question: str

async def periodic_cleanup():
    """Periodically clean up old sessions and cache"""
    while True:
        try:
            await asyncio.sleep(300)  # Run every 5 minutes
            current_time = time.time()
            
            # Remove sessions older than 30 minutes
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
            
            # Clean up vectorstore cache
            ChatBot.cleanup_cache(max_age_hours=2)
            
            if expired_users:
                print(f"Cleaned up {len(expired_users)} expired sessions")
                
        except Exception as e:
            print(f"Cleanup error: {e}")

@app.post("/upload")
async def upload_documents(
    background_tasks: BackgroundTasks,
    user: str = Form(...),
    files: List[UploadFile] = File(...)
):
    """
    Optimized upload with file size limits and async processing
    """
    try:
        # Validate inputs
        if len(files) > 10:
            raise HTTPException(400, "Maximum 10 files allowed")
        
        # Check total size
        total_size = 0
        for file in files:
            if hasattr(file, 'size') and file.size:
                total_size += file.size
        
        if total_size > 20 * 1024 * 1024:  # 20MB total limit
            raise HTTPException(400, "Total file size exceeds 20MB limit")
        
        # Clean up old user data
        tmpdir = f"/tmp/{user}"
        if os.path.exists(tmpdir):
            shutil.rmtree(tmpdir)
        os.makedirs(tmpdir, exist_ok=True)
        
        file_paths = []
        for upload in files:
            # Validate file type
            allowed_extensions = {'.txt', '.pdf', '.docx', '.doc'}
            file_ext = os.path.splitext(upload.filename)[1].lower()
            
            if file_ext not in allowed_extensions:
                continue
            
            dest = os.path.join(tmpdir, upload.filename)
            
            # Read file content
            content = await upload.read()
            
            # Check individual file size
            if len(content) > 10 * 1024 * 1024:  # 10MB per file
                continue
            
            with open(dest, "wb") as out:
                out.write(content)
            file_paths.append(dest)
        
        if not file_paths:
            raise HTTPException(400, "No valid files to process")
        
        # Create ChatBot instance (this might take time)
        try:
            bot = ChatBot(file_paths=file_paths, user_id=user)
            _sessions[user] = bot
            _session_timestamps[user] = time.time()
            
            # Schedule cleanup of old files in background
            background_tasks.add_task(cleanup_old_files, tmpdir, delay=3600)  # 1 hour
            
            return {
                "status": "uploaded", 
                "count": len(file_paths),
                "message": "Documents processed successfully"
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

async def cleanup_old_files(tmpdir: str, delay: int):
    """Background task to clean up files after delay"""
    await asyncio.sleep(delay)
    if os.path.exists(tmpdir):
        shutil.rmtree(tmpdir, ignore_errors=True)

@app.post("/train")
def train(req: TrainRequest):
    """
    Optional training endpoint (currently just returns success)
    """
    if req.user not in _sessions:
        raise HTTPException(400, "No session found. Please upload documents first.")
    
    # Update timestamp
    _session_timestamps[req.user] = time.time()
    
    return {"status": "trained", "message": "Training completed"}

@app.post("/chat")
async def chat(req: ChatRequest):
    """
    Async chat endpoint with optimized response
    """
    try:
        user = req.user
        
        if user not in _sessions:
            raise HTTPException(400, "Session expired or no documents uploaded. Please upload documents first.")
        
        bot = _sessions[user]
        
        # Update session timestamp
        _session_timestamps[user] = time.time()
        
        # Use async method if available, otherwise fallback to sync
        if hasattr(bot, 'ask_async'):
            answer = await bot.ask_async(req.question)
        else:
            answer = bot.ask(req.question)
        
        return {"answer": answer, "timestamp": time.time()}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Chat processing failed: {str(e)}")

@app.post("/logout")
def logout(user: str = Form(...)):
    """
    Clean logout with proper resource cleanup
    """
    try:
        # Remove from sessions
        _sessions.pop(user, None)
        _session_timestamps.pop(user, None)
        
        # Clean up user files
        tmpdir = f"/tmp/{user}"
        if os.path.exists(tmpdir):
            shutil.rmtree(tmpdir, ignore_errors=True)
        
        return JSONResponse(content={"status": "logged_out", "message": "Session cleaned up"})
        
    except Exception as e:
        return JSONResponse(
            content={"status": "error", "message": f"Logout failed: {str(e)}"},
            status_code=500
        )

@app.get("/")
async def root():
    return {
        "message": "Optimized Backend is up and running!",
        "active_sessions": len(_sessions),
        "timestamp": time.time()
    }

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "active_sessions": len(_sessions),
        "memory_usage": f"{len(_sessions)} sessions active"
    }

@app.post("/cleanup")
async def manual_cleanup(user: str = Form(...)):
    """Manual cleanup endpoint for specific user"""
    try:
        _sessions.pop(user, None)
        _session_timestamps.pop(user, None)
        
        tmpdir = f"/tmp/{user}"
        if os.path.exists(tmpdir):
            shutil.rmtree(tmpdir, ignore_errors=True)
        
        return {"status": "cleaned", "user": user}
        
    except Exception as e:
        raise HTTPException(500, f"Cleanup failed: {str(e)}")

# Add error handler for better debugging
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
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
