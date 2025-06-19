# api.py
import os
import shutil
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from starlette.responses import JSONResponse

# import your ChatBot from wherever you defined it
from main import ChatBot  

app = FastAPI()

# CORS: adjust origin(s) as needed
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # or ["*"] for dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# in‑memory user→ChatBot sessions
_sessions: dict[str, ChatBot] = {}

# —— Request models for JSON endpoints —— #
class TrainRequest(BaseModel):
    user: str

class ChatRequest(BaseModel):
    user: str
    question: str


@app.post("/upload")
async def upload_documents(
    user: str = Form(...),
    files: List[UploadFile] = File(...)
):
    """
    Receive files via multipart/form-data,
    save them under /tmp/<user>/, and
    create a new ChatBot instance.
    """
    tmpdir = f"/tmp/{user}"
    if os.path.exists(tmpdir):
        shutil.rmtree(tmpdir)
    os.makedirs(tmpdir, exist_ok=True)

    file_paths = []
    for upload in files:
        dest = os.path.join(tmpdir, upload.filename)
        with open(dest, "wb") as out:
            out.write(await upload.read())
        file_paths.append(dest)

    bot = ChatBot(file_paths=file_paths)
    _sessions[user] = bot

    return {"status": "uploaded", "count": len(file_paths)}


@app.post("/train")
def train(req: TrainRequest):
    # Optional: _sessions[user].retrain()
    return {"status": "trained"}


@app.post("/chat")
def chat(req: ChatRequest):
    """
    JSON POST { "user": "...", "question": "..." } → { "answer": "..." }
    """
    print(req.user)
    print(req.question)
    user = req.user
    if user not in _sessions:
        raise HTTPException(400, "Session expired or no docs uploaded.")
    bot = _sessions[user]
    print(req.question)
    answer = bot.ask(req.question)
    return {"answer": answer}


@app.post("/logout")
def logout(user: str = Form(...)):
    """
    multipart/form-data POST { user: "alice" } → clear session.
    """
    _sessions.pop(user, None)
    return JSONResponse(content={"status": "logged_out"})
