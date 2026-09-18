# Discord AI Chatbot & Web Panel

An emotionally intelligent, multilingual AI chatbot built for Discord communities using DeepSeek / Claude via AgentRouter, accompanied by a modern Web Management Panel, Terms of Service, and Privacy Policy.

---

## 🌟 Key Features

- **Multilingual Fluency**: Seamless conversation in English, Bangla (বাংলা), Banglish, and Hindi.
- **Dynamic Mood & Tone Matching**: Automatically adapts between friendly casual talk, warm affection, supportive listening for sad/venting users, and sharp roasters when challenged.
- **Self-Healing WAF Recovery**: Automatic single-turn recovery if upstream filters block context.
- **Transient Memory**: Context is held strictly in RAM (rolling window of 20 turns) with zero persistent logging to disk.
- **Web Management Panel & Playground**: Browser-based telemetry, interactive chat simulator, and Discord invite link generator.
- **Discord Developer Ready**: Pre-built, legally compliant Terms of Service and Privacy Policy pages.

---

## 🚀 Quick Start

### 1. Configure Environment
Make sure your `.env` file contains:
```env
DISCORD_TOKEN=your_discord_bot_token_here
AGENTROUTER_API_KEY=your_agentrouter_api_key_here
MODEL=deepseek-v4-flash
PREFIX=!
ALLOWED_CHANNELS=bot-chat,ai-chat
PORT=5000
```

### 2. Run the Discord Bot
```bash
python bot.py
```

### 3. Run the Web Panel & Legal Portal
```bash
python web_panel.py
```
Open your browser at:
- **Dashboard**: [http://localhost:5000/](http://localhost:5000/)
- **Terms of Service**: [http://localhost:5000/terms.html](http://localhost:5000/terms.html)
- **Privacy Policy**: [http://localhost:5000/privacy.html](http://localhost:5000/privacy.html)

---

## 📋 Setting URLs in Discord Developer Portal

Discord Developer Portal requires public HTTPS URLs:

### Option 1: GitHub Pages (Free & Permanent)
1. Push this project to a GitHub repository.
2. Open **Settings → Pages** in your repo.
3. Select `main` branch and folder `/web`.
4. Enter these URLs in Discord Developer Portal:
   - **Terms of Service URL**: `https://<username>.github.io/<repo>/terms.html`
   - **Privacy Policy URL**: `https://<username>.github.io/<repo>/privacy.html`

### Option 2: Cloudflare Pages / Vercel
Drag and drop the `web/` folder to [Cloudflare Pages](https://pages.cloudflare.com/) or [Vercel](https://vercel.com/) for an instant public domain.

### Option 3: Cloudflare Tunnel (For Local Server)
```bash
npx cloudflared tunnel --url http://localhost:5000
```
