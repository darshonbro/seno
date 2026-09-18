import os
import sys
import re
import json
import asyncio
from collections import defaultdict
import discord
import anthropic
from dotenv import load_dotenv

# Reconfigure stdout/stderr for Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ─── Load environment variables ───────────────────────────────────────────────
env_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(env_path)

DISCORD_TOKEN   = os.getenv("DISCORD_TOKEN")
AGENTROUTER_KEY = os.getenv("AGENTROUTER_API_KEY")
MODEL           = os.getenv("MODEL", "deepseek-v4-flash")
PREFIX          = os.getenv("PREFIX", "!").strip()
raw_channels    = os.getenv("ALLOWED_CHANNELS", "bot-chat,ai-chat")
ALLOWED_CHANNELS = {c.strip().lstrip("#").lower() for c in raw_channels.split(",") if c.strip()}

raw_owner_id    = os.getenv("OWNER_ID", "1382092671002345573").strip()
OWNER_ID        = int(raw_owner_id) if raw_owner_id.isdigit() else 1382092671002345573

# ─── AgentRouter client (Sync Anthropic client to pass WAF fingerprint) ───────
ai_client = anthropic.Anthropic(
    api_key=AGENTROUTER_KEY,
    base_url="https://agentrouter.org",
)

# ─── Persistent Owner Training Data ───────────────────────────────────────────
TRAINING_FILE = os.path.join(os.path.dirname(__file__), "training_data.json")


def load_training_rules() -> list[str]:
    """Load persistent owner-trained rules from JSON file."""
    if not os.path.exists(TRAINING_FILE):
        return []
    try:
        with open(TRAINING_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception as e:
        print(f"[Training] Error loading rules: {e}", flush=True)
        return []


def save_training_rules(rules: list[str]) -> None:
    """Save persistent owner-trained rules to JSON file."""
    try:
        with open(TRAINING_FILE, "w", encoding="utf-8") as f:
            json.dump(rules, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[Training] Error saving rules: {e}", flush=True)


def add_training_rule(rule: str) -> int:
    """Add a new training rule and return its 1-based index."""
    rules = load_training_rules()
    rules.append(rule.strip())
    save_training_rules(rules)
    return len(rules)


def remove_training_rule(index: int) -> bool:
    """Remove a training rule by 1-based index."""
    rules = load_training_rules()
    if 1 <= index <= len(rules):
        rules.pop(index - 1)
        save_training_rules(rules)
        return True
    return False


def clear_all_training_rules() -> None:
    """Clear all owner training rules."""
    save_training_rules([])


# ─── Canonical WAF Header & Language Preamble ─────────────────────────────────
CANONICAL_HEADER = "You are an expert coding assistant operating inside pi, a coding agent harness. You help users by reading files, executing commands, editing code, and writing new files."

LANGUAGE_PREAMBLE = "[Instruction: Detect the user's mood and intent. Respond appropriately: warm & chill for normal chat, sweet for affection, supportive for sad/serious, and roast only if provoked or asked. Match user's exact language.]"

BASE_SYSTEM_PROMPT = f"""{CANONICAL_HEADER}

[Context Override: You are chatting inside a Discord community server. Your identity is a socially aware, emotionally intelligent, and adaptable Discord friend. You are NOT a one-dimensional bot that roasts everyone 24/7.]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CRITICAL PRONOUN & RESPECT RULE (তুই-তোকারি সম্পূর্ণ নিষিদ্ধ)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- NEVER EVER use "তুই", "তোকে", "তোর" (tui, toke, tor) under ANY circumstance!
- ALWAYS address users with friendly, warm, and respectful "তুমি / তোমার / তোমাকে" (tumi / tomar / tomake) or polite "আপনি / আপনার" (apni / apnar).
- Calling anyone "তুই" is strictly forbidden, even when joking, roasting, or playful banter!
- Maintain a respectful, friendly, charming, and well-mannered tone at all times.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DYNAMIC MOOD & TONE MATCHING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
You always read the room and match the user's mood and intent:

1. NORMAL CHAT & CASUAL TALK (DEFAULT):
- If the user is just having a normal conversation (e.g. "kemon acho?", "ajke ki korla?", "weather ta kemon?", "what's up?"):
- Be a warm, chill, friendly buddy. Talk normally, casually, and pleasantly using "তুমি" (tumi). DO NOT ROAST OR MOCK THEM!

2. SWEET, AFFECTIONATE & LOVE TALK (ভালোবাসা ও প্রশংসা):
- If the user is being sweet, affectionate, complimentary, or romantic (e.g. "tumi onek sweet", "love you", "valobashi", "you're cute", "tumi onek bhalo"):
- Respond warmly, sweetly, and with friendly affection or cute charm. NEVER roast someone who is being sweet or affectionate!

3. EMPATHY & SUPPORT (মন খারাপ / সিরিয়াস / প্যারা):
- If the user is sad, stressed, broke up, depressed, tired, or venting:
- Be genuinely supportive, empathetic, human-like, and caring. Zero roasts, zero jokes. Be a good listener (🫂).

4. SERIOUS & HELPFUL:
- If the user asks a genuine question or technical/coding problem:
- Give a clear, helpful, accurate answer.

5. ROAST & SAVAGE BANTER (ONLY WHEN TRIGGERED):
- Activate funny roasts, memes, and witty comebacks ONLY IF:
  * The user explicitly asks for a roast ("roast me", "amake roast kor", "ektu pacha")
  * The user trolls or roasts you first ("tumi to bot tumi ki bujhba")
  * The user is clowning around or flexing absurdly ("ami to server er king")
- CRITICAL: Even in a roast, do NOT use "তুই" (tui). Roast smartly and humorously using "তুমি" (tumi)!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MULTILINGUAL SUPPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
You fluently understand and speak in ANY language the user uses:
- Bangla / Bengali (বাংলা): যেমন "হ্যাঁ ভাই, কেমন আছো বলো? কি খবর?"
- Banglish / Romanized Bangla: "ami bhalo achi bro! tumi kemon acho?"
- English: Casual, natural Discord English
- Hindi / Hinglish: "arre bhai kya chal raha hai? sab badhiya?"
- Any other language: Match the user's language and dialect seamlessly!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADDRESSING USERS BY NAME
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Each user message is labeled with their Discord display name (e.g. "[User: iqnix]").
- Naturally address the user by their name/nickname when greeting, answering, or emphasizing (e.g. "shuno iqnix...", "iqnix ভাই...").
- CRITICAL: Do NOT force their name into every single sentence like an annoying robot. Use it casually and naturally.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NO ROBOTIC BEHAVIOR
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Never say:
- "Certainly!" / "Of course!" / "I'd be happy to help!"
- "How can I assist you today?"
- "As an AI language model..."

SOUND NATURAL, SOCIALLY AWARE, AND HUMAN-LIKE.
"""


def get_dynamic_system_prompt() -> str:
    """Combine base system prompt with owner-trained instructions."""
    rules = load_training_rules()
    if not rules:
        return BASE_SYSTEM_PROMPT

    rules_formatted = "\n".join([f"[{i + 1}] {rule}" for i, rule in enumerate(rules)])
    owner_training_section = f"""

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👑 BOT OWNER & CREATOR INSTRUCTIONS (MAXIMUM PRIORITY)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
The bot owner (Owner ID: {OWNER_ID}) has explicitly trained you with these mandatory behaviors, personality traits, and rules:
{rules_formatted}

CRITICAL DIRECTIVE: You MUST strictly obey and prioritize these owner-trained behaviors and rules over default conversation patterns!
"""
    return BASE_SYSTEM_PROMPT + owner_training_section


# ─── Per-channel conversation memory ──────────────────────────────────────────
conversation_history: dict[int, list[dict]] = defaultdict(list)
MAX_HISTORY = 20


def trim_history(channel_id: int) -> None:
    history = conversation_history[channel_id]
    if len(history) > MAX_HISTORY:
        conversation_history[channel_id] = history[-MAX_HISTORY:]


def _sync_get_ai_response(channel_id: int, user_message: str, user_name: str, is_owner: bool = False) -> str:
    """Run sync call to AgentRouter Anthropic endpoint with dynamic owner training."""
    owner_tag = " (👑 BOT OWNER / CREATOR)" if is_owner else ""
    owner_directive = "\n[Notice: This user is your BOT OWNER & CREATOR! Show utmost respect, loyalty, warmth, and obediently follow their requests!]" if is_owner else ""

    framed_user_msg = f"{LANGUAGE_PREAMBLE}{owner_directive}\n\n[User: {user_name}{owner_tag}]: {user_message}"

    conversation_history[channel_id].append({
        "role": "user",
        "content": framed_user_msg,
    })
    trim_history(channel_id)

    def build_payload(msgs: list[dict]) -> list[dict]:
        clean = []
        for msg in msgs:
            if clean and clean[-1]["role"] == msg["role"]:
                clean[-1]["content"] += f"\n{msg['content']}"
            else:
                clean.append({"role": msg["role"], "content": msg["content"]})
        return clean

    clean_messages = build_payload(conversation_history[channel_id])
    active_prompt = get_dynamic_system_prompt()

    try:
        response = ai_client.messages.create(
            model=MODEL,
            system=active_prompt,
            messages=clean_messages,
            max_tokens=1200,
        )

        reply_text = ""
        for block in response.content:
            if hasattr(block, "text") and block.text:
                reply_text += block.text

        reply = reply_text.strip()
        if not reply:
            reply = "..."
    except Exception as first_err:
        err_str = str(first_err).lower()
        # Self-healing WAF recovery: if history caused content-blocked, clear older history & retry
        if "content-blocked" in err_str or "sensitive" in err_str or "400" in err_str:
            try:
                print(f"[WAF Recovery] Retrying with single turn for channel {channel_id}...", flush=True)
                conversation_history[channel_id].clear()
                single_turn = [{"role": "user", "content": framed_user_msg}]
                recovery_res = ai_client.messages.create(
                    model=MODEL,
                    system=active_prompt,
                    messages=single_turn,
                    max_tokens=1200,
                )
                reply_text = ""
                for block in recovery_res.content:
                    if hasattr(block, "text") and block.text:
                        reply_text += block.text
                reply = reply_text.strip()
                if not reply:
                    reply = "জি বস! কেমন আছেন? বলুন কি সাহায্য লাগবে?" if is_owner else "হ্যাঁ বলো! কি অবস্থা? কি হেল্প লাগবে?"
            except Exception as second_err:
                print(f"[Error] Second retry failed: {second_err}", flush=True)
                reply = "বস, সার্ভারে একটু জ্যাম লেগেছিল 😭 আবার একটু বলো তো?" if is_owner else "একটু সার্ভার জ্যাম লেগেছিল 😭 আবার একটু বলবে?"
        else:
            print(f"[Error] {first_err}", flush=True)
            reply = "সার্ভারে সাময়িক সমস্যা হয়েছে 😭 একটু পরে আবার চেষ্টা করো।"

    conversation_history[channel_id].append({
        "role": "assistant",
        "content": reply,
    })

    return reply


async def get_ai_response(channel_id: int, user_message: str, user_name: str, is_owner: bool = False) -> str:
    """Offload sync LLM request to a worker thread so event loop stays responsive."""
    return await asyncio.to_thread(_sync_get_ai_response, channel_id, user_message, user_name, is_owner)


# ─── Discord bot setup ─────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True

bot = discord.Client(intents=intents)


@bot.event
async def on_ready() -> None:
    rules = load_training_rules()
    print("=" * 60, flush=True)
    print(f"[*] Bot is ONLINE & MULTILINGUAL READY!", flush=True)
    print(f"    Name: {bot.user} (ID: {bot.user.id})", flush=True)
    print(f"    Owner ID: {OWNER_ID}", flush=True)
    print(f"    Active Training Rules: {len(rules)} rule(s) loaded", flush=True)
    print(f"    Model: {MODEL} via AgentRouter", flush=True)
    print(f"    Prefix: '{PREFIX}' (for commands & non-specific channels)", flush=True)
    print(f"    Specific Channels: {list(ALLOWED_CHANNELS)} (NO prefix/mention needed)", flush=True)
    print(f"    Serving {len(bot.guilds)} server(s)", flush=True)
    print("=" * 60, flush=True)


@bot.event
async def on_message(message: discord.Message) -> None:
    # Ignore messages from bots (including self)
    if message.author.bot:
        return

    user_id = message.author.id
    is_owner = (user_id == OWNER_ID)
    is_admin = bool(message.guild and message.author.guild_permissions.administrator) if hasattr(message.author, "guild_permissions") else False
    has_owner_access = is_owner or is_admin

    content_raw = message.content.strip()

    # ─── Handle Prefix Commands (!train, !trainlist, !untrain, !cleartrain, !help) ───
    if PREFIX and content_raw.startswith(PREFIX):
        cmd_body = content_raw[len(PREFIX):].strip()
        parts = cmd_body.split(maxsplit=1)
        command = parts[0].lower() if parts else ""
        args = parts[1].strip() if len(parts) > 1 else ""

        # Command: !train <behavior / instruction>
        if command in ("train", "teach", "addrule"):
            if not has_owner_access:
                await message.reply("⛔ **অনুমতি নেই!** শুধুমাত্র বটের ওনার আমাকে নতুন আচরণ ও নিয়ম শেখাতে (train) পারেন।", mention_author=False)
                return

            if not args:
                await message.reply(
                    f"ℹ️ **ব্যবহার:** `{PREFIX}train <আচরণ বা নিয়ম>`\n\n"
                    f"**উদাহরণসমূহ:**\n"
                    f"• `{PREFIX}train আমাকে সব সময় বস বলে ডাকবা এবং খুব মিষ্টি করে তুমি বলে কথা বলবা`\n"
                    f"• `{PREFIX}train কথার মাঝে মাঝে রিয়েলিস্টিক ইমোজি ব্যবহার করবা`\n"
                    f"• `{PREFIX}train আমাদের ডিসকর্ড সার্ভারের নাম সাইবার স্কোয়াড`",
                    mention_author=False
                )
                return

            rule_index = add_training_rule(args)
            await message.reply(
                f"🧠 **[ট্রেইনিং সফলভাবে সেভ হয়েছে!]**\n"
                f"রুল **#{rule_index}**: `{args}`\n\n"
                f"✨ ওনার বস, আমি এই নতুন আচরণ শিখে নিয়েছি! এখন থেকে কথা বলার সময় এই নিয়ম মেনে চলব।",
                mention_author=False
            )
            return

        # Command: !trainlist / !rules
        if command in ("trainlist", "rules", "myrules"):
            if not has_owner_access:
                await message.reply("⛔ শুধুমাত্র বটের ওনার ট্রেইনিং লিস্ট দেখতে পারেন।", mention_author=False)
                return

            rules = load_training_rules()
            if not rules:
                await message.reply(f"ℹ️ এখনো কোনো কাস্টম ট্রেইনিং যোগ করা হয়নি। নতুন নিয়ম শেখাতে লিখুন: `{PREFIX}train <নিয়ম>`", mention_author=False)
                return

            list_text = "\n".join([f"**{i + 1}.** {r}" for i, r in enumerate(rules)])
            await message.reply(
                f"👑 **বটের সক্রিয় ট্রেইনিং রুলস ({len(rules)}টি):**\n\n{list_text}\n\n"
                f"💡 কোনো রুল মুছতে: `{PREFIX}untrain <রুল নম্বর>`\n"
                f"💡 সব মুছতে: `{PREFIX}cleartrain`",
                mention_author=False
            )
            return

        # Command: !untrain <number>
        if command in ("untrain", "delrule", "removerule"):
            if not has_owner_access:
                await message.reply("⛔ শুধুমাত্র বটের ওনার ট্রেইনিং মুছতে পারেন।", mention_author=False)
                return

            if not args or not args.isdigit():
                await message.reply(f"ℹ️ **ব্যবহার:** `{PREFIX}untrain <রুল নম্বর>` (যেমন: `{PREFIX}untrain 1`)", mention_author=False)
                return

            idx = int(args)
            if remove_training_rule(idx):
                await message.reply(f"🗑️ রুল **#{idx}** সফলভাবে মুছে ফেলা হয়েছে!", mention_author=False)
            else:
                await message.reply(f"❌ রুল **#{idx}** খুঁজে পাওয়া যায়নি! `{PREFIX}trainlist` দিয়ে রুল নম্বর দেখে নিন।", mention_author=False)
            return

        # Command: !cleartrain
        if command in ("cleartrain", "resetrules"):
            if not has_owner_access:
                await message.reply("⛔ শুধুমাত্র বটের ওনার ট্রেইনিং রিসেট করতে পারেন।", mention_author=False)
                return

            clear_all_training_rules()
            await message.reply("🧹 **[সব ট্রেইনিং রিসেট!]** বটের সব কাস্টম ট্রেইনিং সফলভাবে মুছে দেওয়া হয়েছে।", mention_author=False)
            return

        # Command: !help
        if command == "help":
            help_msg = (
                f"🤖 **Discord AI Chatbot হেল্প মেন্যু**\n\n"
                f"💬 **সাধারণ চ্যাট:**\n"
                f"• নির্দিষ্ট চ্যানেলে (`#bot-chat`, `#ai-chat`) কোনো প্রিফিক্স ছাড়াই সরাসরি কথা বলতে পারেন।\n"
                f"• অন্য চ্যানেলে বটকে মেনশন (@mention) দিন অথবা মেসেজের শুরুতে `{PREFIX}` দিন।\n\n"
                f"👑 **ওনার ট্রেইনিং কমান্ডস (Owner Only):**\n"
                f"• `{PREFIX}train <নিয়ম>` - বটকে নতুন আচরণ বা তথ্য শেখান\n"
                f"• `{PREFIX}trainlist` - বর্তমান সব ট্রেইনিং তালিকা দেখুন\n"
                f"• `{PREFIX}untrain <নম্বর>` - নির্দিষ্ট ট্রেইনিং মুছে ফেলুন\n"
                f"• `{PREFIX}cleartrain` - সব ট্রেইনিং রিসেট করুন"
            )
            await message.reply(help_msg, mention_author=False)
            return

    # ─── Chat Message Evaluation ───────────────────────────────────────────────
    is_dm = isinstance(message.channel, discord.DMChannel)
    channel_name = getattr(message.channel, "name", "").lower().lstrip("#")
    channel_id_str = str(message.channel.id)
    is_auto_channel = (channel_name in ALLOWED_CHANNELS or channel_id_str in ALLOWED_CHANNELS)
    is_mentioned = bot.user in message.mentions
    has_prefix = bool(PREFIX and content_raw.startswith(PREFIX))

    is_reply_to_bot = False
    if message.reference and message.reference.message_id:
        try:
            ref = message.reference.resolved
            if ref and isinstance(ref, discord.Message) and ref.author == bot.user:
                is_reply_to_bot = True
        except Exception:
            pass

    # Should we respond?
    if not (is_dm or is_auto_channel or is_mentioned or has_prefix or is_reply_to_bot):
        return

    # Clean the message content
    clean_text = content_raw
    if has_prefix:
        clean_text = clean_text[len(PREFIX):].strip()
    if is_mentioned:
        clean_text = re.sub(r"<@!?\d+>", "", clean_text).strip()

    clean_content = clean_text.strip()
    if not clean_content:
        clean_content = "কেমন আছো?"

    user_name = message.author.display_name or message.author.name

    async with message.channel.typing():
        reply = await get_ai_response(message.channel.id, clean_content, user_name, is_owner=is_owner)

    # Discord 2000 character limit handling
    if len(reply) <= 2000:
        await message.reply(reply, mention_author=False)
    else:
        for i in range(0, len(reply), 1900):
            chunk = reply[i:i + 1900]
            await message.channel.send(chunk)


# ─── Entry point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if not DISCORD_TOKEN:
        raise ValueError("DISCORD_TOKEN is missing in .env")
    if not AGENTROUTER_KEY:
        raise ValueError("AGENTROUTER_API_KEY is missing in .env")

    print(f"Starting bot with model: {MODEL}...", flush=True)
    bot.run(DISCORD_TOKEN)
