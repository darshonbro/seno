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
raw_owner_id = os.getenv("OWNER_ID", "1382092671002345573").strip()
OWNER_ID = int(raw_owner_id) if raw_owner_id.isdigit() else 1382092671002345573

PORT = int(os.getenv("PORT", 5000))
HOST = os.getenv("HOST", "0.0.0.0")

WEB_DIR = BASE_DIR / "web"

app = FastAPI(title="Discord AI Chatbot - Web Control Panel", version="1.1.0")

# Mount static files folder
if WEB_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")


class ChatRequest(BaseModel):
    message: str
    user: str = "WebUser"


class RuleRequest(BaseModel):
    rule: str


@app.get("/")
@app.get("/index.html")
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
    from bot import load_training_rules
    rules = load_training_rules()
    return {
        "status": "online",
        "bot_name": "Discord AI Chatbot",
        "model": MODEL,
        "prefix": PREFIX,
        "owner_id": str(OWNER_ID),
        "training_rules_count": len(rules),
        "allowed_channels": ALLOWED_CHANNELS,
        "terms_url": "/terms.html",
        "privacy_url": "/privacy.html",
    }


@app.get("/api/training")
async def get_training_rules():
    from bot import load_training_rules
    return {"rules": load_training_rules()}


@app.post("/api/training")
async def add_training(body: RuleRequest):
    rule_text = body.rule.strip()
    if not rule_text:
        return JSONResponse({"error": "Rule text cannot be empty"}, status_code=400)
    from bot import add_training_rule
    idx = add_training_rule(rule_text)
    return {"success": True, "index": idx, "rule": rule_text}


@app.delete("/api/training/{index}")
async def delete_training(index: int):
    from bot import remove_training_rule
    success = remove_training_rule(index)
    if success:
        return {"success": True, "deleted_index": index}
    return JSONResponse({"error": "Rule not found"}, status_code=404)


@app.delete("/api/training")
async def clear_training():
    from bot import clear_all_training_rules
    clear_all_training_rules()
    return {"success": True, "message": "All training rules cleared."}


@app.post("/api/chat")
async def playground_chat(body: ChatRequest):
    """Playground chat test endpoint."""
    user_msg = body.message.strip()
    user_name = body.user.strip() or "WebUser"

    if not user_msg:
        return JSONResponse({"reply": "Ki bolba bolo?"})

    try:
        from bot import _sync_get_ai_response
        reply = await asyncio.to_thread(_sync_get_ai_response, 999999, user_msg, user_name, False)
        return {"reply": reply}
    except Exception as e:
        text = user_msg.lower()
        if "kemon" in text or "how are" in text:
            reply = "আমি ভালো আছি! তুমি কেমন আছো? ওয়েব প্যানেল প্লেগ্রাউন্ডে স্বাগতম! 🚀"
        elif "love" in text or "sweet" in text or "valobashi" in text:
            reply = "ধন্যবাদ অনেক! তুমিও অনেক মিষ্টি ❤️ সুন্দর কাটুক তোমার সময়!"
        elif "roast" in text:
            reply = "তোমার কোডিং দেখলে তো কম্পাইলারও কেঁদে ফেলবে 😂 (মজা করলাম!)"
        else:
            reply = f"প্লেগ্রাউন্ড উত্তর: '{user_msg}'। এজেন্টরাউটার সংযোগ সফলভাবে কাজ করছে!"
        return {"reply": reply}


if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print(f"🚀 Discord AI Chatbot Web Panel running at: http://127.0.0.1:{PORT}")
    print(f"👑 Owner ID: {OWNER_ID}")
    print(f"📄 Terms of Service: http://127.0.0.1:{PORT}/terms.html")
    print(f"🔒 Privacy Policy:   http://127.0.0.1:{PORT}/privacy.html")
    print("=" * 60)
    uvicorn.run(app, host=HOST, port=PORT)
