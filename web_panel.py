import os
import sys
import asyncio
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

# Reconfigure stdout/stderr for Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Load environment
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

MODEL = os.getenv("MODEL", "deepseek-v4-flash")
PREFIX = os.getenv("PREFIX", "!").strip()
raw_channels = os.getenv("ALLOWED_CHANNELS", "bot-chat,ai-chat")
ALLOWED_CHANNELS = [c.strip().lstrip("#").lower() for c in raw_channels.split(",") if c.strip()]
PORT = int(os.getenv("PORT", 5000))
HOST = os.getenv("HOST", "0.0.0.0")

WEB_DIR = BASE_DIR / "web"

app = FastAPI(title="Discord AI Chatbot - Web Control Panel", version="1.0.0")

# Mount static files folder
if WEB_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")


class ChatRequest(BaseModel):
    message: str
    user: str = "WebUser"


@app.get("/")
async def get_index():
    return FileResponse(WEB_DIR / "index.html")


@app.get("/styles.css")
async def get_css():
    return FileResponse(WEB_DIR / "styles.css", media_type="text/css")


@app.get("/app.js")
async def get_js():
    return FileResponse(WEB_DIR / "app.js", media_type="application/javascript")


@app.get("/terms")
@app.get("/terms.html")
async def get_terms():
    return FileResponse(WEB_DIR / "terms.html")


@app.get("/privacy")
@app.get("/privacy.html")
async def get_privacy():
    return FileResponse(WEB_DIR / "privacy.html")


@app.get("/api/status")
async def get_status():
    return {
        "status": "online",
        "bot_name": "Discord AI Chatbot",
        "model": MODEL,
        "prefix": PREFIX,
        "allowed_channels": ALLOWED_CHANNELS,
        "terms_url": "/terms.html",
        "privacy_url": "/privacy.html",
    }


@app.post("/api/chat")
async def playground_chat(body: ChatRequest):
    """Playground chat test endpoint."""
    user_msg = body.message.strip()
    user_name = body.user.strip() or "WebUser"

    if not user_msg:
        return JSONResponse({"reply": "Ki bolba bolo?"})

    # Try to leverage bot's AI logic if available
    try:
        from bot import _sync_get_ai_response
        reply = await asyncio.to_thread(_sync_get_ai_response, 999999, user_msg, user_name)
        return {"reply": reply}
    except Exception as e:
        # Fallback simulator if bot or API is not ready
        text = user_msg.lower()
        if "kemon" in text or "how are" in text:
            reply = "Ami bhalo achi bro! Tumi kemon acho? Web panel playground e swagotom! 🚀"
        elif "love" in text or "sweet" in text or "valobashi" in text:
            reply = "Aww! You're really sweet ❤️ Shob shomoy evabe chill thako!"
        elif "roast" in text:
            reply = "Bhai tor coding dekhe to compiler o kanna shuru korbe 😂 (Just joking bro!)"
        else:
            reply = f"Playground echo: '{user_msg}'. AgentRouter API connects seamlessly for Discord servers!"
        return {"reply": reply}


if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print(f"🚀 Discord AI Chatbot Web Panel running at: http://127.0.0.1:{PORT}")
    print(f"📄 Terms of Service: http://127.0.0.1:{PORT}/terms.html")
    print(f"🔒 Privacy Policy:   http://127.0.0.1:{PORT}/privacy.html")
    print("=" * 60)
    uvicorn.run(app, host=HOST, port=PORT)
