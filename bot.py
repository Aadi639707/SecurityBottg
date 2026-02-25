import os
import time
import json
import random
import asyncio
import threading
from flask import Flask
from pyrogram import Client, filters, enums
from pyrogram.errors import FloodWait

# --- CONFIGURATION ---
# Render Environment Variables se data uthayega
API_ID = int(os.environ.get("API_ID", "123456"))
API_HASH = os.environ.get("API_HASH", "your_api_hash")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "your_bot_token")

ADMIN_ID = 8306853454  # Aapki Admin ID
SUPPORT_ID = "@SANATANI_GOJO"
DATA_FILE = "bot_data.json"

# --- FAKE WEB SERVICE FOR RENDER ---
app_web = Flask(__name__)

@app_web.route('/')
def home():
    return "Security Bot 10000% Online & Secure!"

def run_web():
    # Render default port 8080 use karta hai
    port = int(os.environ.get("PORT", 8080))
    app_web.run(host="0.0.0.0", port=port)

# --- DATABASE HANDLING ---
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except:
            return {"licenses": {}, "active_groups": {}, "settings": {}}
    return {"licenses": {}, "active_groups": {}, "settings": {}}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

db = load_data()
tracked_messages = []

# --- BOT SETUP ---
app = Client("SecurityBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# --- COMMANDS ---

@app.on_message(filters.command("start"))
async def start_cmd(client, message):
    await message.reply_text(
        f"🛡️ **Advanced Group Security Bot**\n\n"
        f"I am designed to keep your group 10000% secure with auto-chat cleaning.\n\n"
        f"👤 **Support:** {SUPPORT_ID}\n"
        f"💳 **Owner ID:** `{ADMIN_ID}`\n\n"
        f"Use /help to see setup instructions."
    )

@app.on_message(filters.command("help"))
async def help_cmd(client, message):
    help_text = (
        "📖 **Setup Guide:**\n\n"
        "1. Add me to group & make me **Admin**.\n"
        "2. Buy license from: @SANATANI_GOJO\n"
        "3. Use `/redeem [code]` (Only for Group Owner/Admins).\n"
        "4. Set speed: `/settime [minutes]`.\n\n"
        "**Admin Commands:**\n"
        "• `/status` - Check plan expiry\n"
        "• `/settime` - Change message delete delay"
    )
    await message.reply_text(help_text)

@app.on_message(filters.command("gen") & filters.user(ADMIN_ID))
async def gen_code(client, message):
    try:
        days = int(message.command[1])
        code = str(random.randint(100000, 999999))
        db["licenses"][code] = days
        save_data(db)
        await message.reply_text(f"✅ **License Created!**\n\nCode: `{code}`\nDays: {days}\n\nGive this to the user.")
    except:
        await message.reply_text("Usage: `/gen 30` (for 30 days)")

@app.on_message(filters.command("redeem") & filters.group)
async def redeem_code(client, message):
    chat_id = str(message.chat.id)
    try:
        # Permission Check: Owner or Admin
        check = await client.get_chat_member(message.chat.id, message.from_user.id)
        if check.status not in [enums.ChatMemberStatus.OWNER, enums.ChatMemberStatus.ADMINISTRATOR]:
            return await message.reply_text("❌ Only Group Owner or Admins can use this.")

        if len(message.command) < 2:
            return await message.reply_text("Usage: `/redeem 123456`")

        code = message.command[1]
        if code in db["licenses"]:
            days = db["licenses"].pop(code)
            expiry = time.time() + (days * 86400)
            db["active_groups"][chat_id] = expiry
            if chat_id not in db["settings"]:
                db["settings"][chat_id] = {"delete_time": 60} # Default 1 min
            save_data(db)
            await message.reply_text(f"🔥 **Premium Activated!**\n\nGroup is now secure.\nExpires on: {time.ctime(expiry)}")
        else:
            await message.reply_text("❌ Invalid or used code.")
    except Exception as e:
        await message.reply_text("❌ Make sure I am Admin in this group!")

@app.on_message(filters.command("settime") & filters.group)
async def set_time(client, message):
    chat_id = str(message.chat.id)
    if chat_id not in db["active_groups"] or db["active_groups"][chat_id] < time.time():
        return await message.reply_text("❌ This group doesn't have an active plan.")

    try:
        check = await client.get_chat_member(message.chat.id, message.from_user.id)
        if check.status not in [enums.ChatMemberStatus.OWNER, enums.ChatMemberStatus.ADMINISTRATOR]:
            return
            
        mins = int(message.command[1])
        db["settings"][chat_id]["delete_time"] = mins * 60
        save_data(db)
        await message.reply_text(f"⏱️ **Auto-delete interval set to {mins} minute(s).**")
    except:
        await message.reply_text("Usage: `/settime 1` (for 1 minute)")

@app.on_message(filters.command("status") & filters.group)
async def status_cmd(client, message):
    chat_id = str(message.chat.id)
    if chat_id in db["active_groups"]:
        rem = db["active_groups"][chat_id] - time.time()
        if rem > 0:
            days = int(rem // 86400)
            await message.reply_text(f"✅ **Premium: ACTIVE**\n⏳ Remaining: {days} days")
        else:
            await message.reply_text("❌ **Premium: EXPIRED**")
    else:
        await message.reply_text("❌ **Premium: NOT ACTIVE**")

# --- AUTO DELETE ENGINE ---
@app.on_message(filters.group & ~filters.service)
async def track_messages(client, message):
    chat_id = str(message.chat.id)
    # Only track if premium is active
    if chat_id in db["active_groups"] and db["active_groups"][chat_id] > time.time():
        delay = db["settings"].get(chat_id, {}).get("delete_time", 60)
        tracked_messages.append({
            'cid': message.chat.id,
            'mid': message.id,
            'at': time.time() + delay
        })

async def delete_worker():
    while True:
        now = time.time()
        global tracked_messages
        # Messages to delete
        to_del = [m for m in tracked_messages if now >= m['at']]
        # Messages to keep for later
        tracked_messages = [m for m in tracked_messages if now < m['at']]

        for m in to_del:
            try:
                await app.delete_messages(m['cid'], m['mid'])
            except FloodWait as e:
                await asyncio.sleep(e.value)
            except:
                pass
        await asyncio.sleep(2) # Check every 2 seconds

# --- ASYNC STARTUP ---
async def start_services():
    # Start Web Server in Thread
    threading.Thread(target=run_web, daemon=True).start()
    
    # Start Bot
    await app.start()
    print(">>> Bot is Online (10000% Secure Mode)")
    
    # Start Background Delete Worker
    asyncio.create_task(delete_worker())
    
    # Keep running
    from pyrogram.methods.utilities.idle import idle
    await idle()
    await app.stop()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(start_services())
        
