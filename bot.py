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
API_ID = int(os.environ.get("API_ID", "123456"))
API_HASH = os.environ.get("API_HASH", "your_api_hash")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "your_bot_token")

ADMIN_ID = 8306853454 
SUPPORT_ID = "@SANATANI_GOJO"
DATA_FILE = "bot_data.json"

# --- FAKE WEB SERVICE FOR RENDER ---
app_web = Flask(__name__)
@app_web.route('/')
def home(): return "Security Bot 10000% Online & Secure!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app_web.run(host="0.0.0.0", port=port)

# --- DATABASE ---
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f: return json.load(f)
        except: return {"licenses": {}, "active_groups": {}, "settings": {}}
    return {"licenses": {}, "active_groups": {}, "settings": {}}

def save_data(data):
    with open(DATA_FILE, "w") as f: json.dump(data, f, indent=4)

db = load_data()
tracked_messages = []

# --- BOT SETUP ---
app = Client("SecurityBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# --- COMMANDS ---

@app.on_message(filters.command("start"))
async def start_cmd(client, message):
    await message.reply_text(f"🛡️ **Group Security Bot**\n\nOwner: {SUPPORT_ID}\nUse /help for setup.")

@app.on_message(filters.command("help"))
async def help_cmd(client, message):
    await message.reply_text("1. Add me as Admin.\n2. /redeem [code]\n3. /settime [min]\n\nI will delete A to Z messages (User, Admin, Owner, & Bots).")

@app.on_message(filters.command("gen") & filters.user(ADMIN_ID))
async def gen_code(client, message):
    try:
        days = int(message.command[1])
        code = str(random.randint(100000, 999999))
        db["licenses"][code] = days
        save_data(db)
        await message.reply_text(f"✅ Code: `{code}` ({days} Days)")
    except: await message.reply_text("Usage: `/gen 30`")

@app.on_message(filters.command("redeem") & filters.group)
async def redeem_code(client, message):
    chat_id = str(message.chat.id)
    try:
        user = await client.get_chat_member(message.chat.id, message.from_user.id)
        if user.status not in [enums.ChatMemberStatus.OWNER, enums.ChatMemberStatus.ADMINISTRATOR]:
            return await message.reply_text("❌ Only Admins can redeem.")
        
        code = message.command[1]
        if code in db["licenses"]:
            days = db["licenses"].pop(code)
            db["active_groups"][chat_id] = time.time() + (days * 86400)
            if chat_id not in db["settings"]: db["settings"][chat_id] = {"delete_time": 60}
            save_data(db)
            await message.reply_text("🔥 Premium Activated! A to Z cleaning started.")
        else: await message.reply_text("❌ Invalid Code.")
    except: await message.reply_text("❌ Use: `/redeem [code]`")

@app.on_message(filters.command("settime") & filters.group)
async def set_time(client, message):
    chat_id = str(message.chat.id)
    try:
        user = await client.get_chat_member(message.chat.id, message.from_user.id)
        if user.status not in [enums.ChatMemberStatus.OWNER, enums.ChatMemberStatus.ADMINISTRATOR]: return
        mins = int(message.command[1])
        db["settings"][chat_id]["delete_time"] = mins * 60
        save_data(db)
        await message.reply_text(f"⏱️ Delete time: {mins} min.")
    except: await message.reply_text("Usage: `/settime 1`")

# --- A TO Z DELETE ENGINE ---
# Isme filters.all use kiya h taaki Bots aur Admins sab cover ho jayein
@app.on_message(filters.group & ~filters.service, group=1)
async def track_all(client, message):
    chat_id = str(message.chat.id)
    # Check if group is premium
    if chat_id in db["active_groups"] and db["active_groups"][chat_id] > time.time():
        # Skip commands taaki admin control kar sake (optional)
        if message.text and message.text.startswith("/"):
            return
            
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
        to_del = [m for m in tracked_messages if now >= m['at']]
        tracked_messages = [m for m in tracked_messages if now < m['at']]

        for m in to_del:
            try:
                await app.delete_messages(m['cid'], m['mid'])
            except FloodWait as e: await asyncio.sleep(e.value)
            except: pass
        await asyncio.sleep(1)

# --- STARTUP ---
async def start_services():
    threading.Thread(target=run_web, daemon=True).start()
    await app.start()
    asyncio.create_task(delete_worker())
    from pyrogram.methods.utilities.idle import idle
    await idle()

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(start_services())
