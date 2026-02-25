import os
import time
import json
import random
import asyncio
import threading
import requests
from flask import Flask
from pyrogram import Client, filters, enums
from pyrogram.errors import FloodWait

# --- CONFIGURATION ---
API_ID = int(os.environ.get("API_ID", "123456"))
API_HASH = os.environ.get("API_HASH", "your_api_hash")
SESSION_STRING = os.environ.get("SESSION_STRING", "")
RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL", "") # Apna Render URL yahan bhi manually daal sakte ho

ADMIN_ID = 8306853454 
SUPPORT_ID = "@SANATANI_GOJO"
DATA_FILE = "userbot_data.json"

# --- ANTI-SLEEP WEB SERVICE ---
app_web = Flask(__name__)

@app_web.route('/')
def home():
    return "Userbot Status: 10000% Awake & Secure!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app_web.run(host="0.0.0.0", port=port)

def keep_alive():
    """Bot ko soney se rokne ke liye self-ping logic"""
    if not RENDER_URL:
        return
    while True:
        try:
            requests.get(RENDER_URL)
            print(">>> Anti-Sleep: Pinged successfully!")
        except Exception as e:
            print(f">>> Anti-Sleep Error: {e}")
        time.sleep(600) # Har 10 minute me ping karega

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

# --- CLIENT SETUP ---
if not SESSION_STRING:
    print("❌ SESSION_STRING Missing!")
    exit(1)

app = Client(
    "SecurityUserbot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING,
    in_memory=True
)

# --- COMMANDS ---

@app.on_message(filters.command("start", prefixes=".") & (filters.user(ADMIN_ID) | filters.me))
async def start_cmd(client, message):
    await message.edit("🛡️ **Userbot Security: ONLINE**\n\nMain ab jag gaya hoon. Rose Bot ki chutti confirm hai!")

@app.on_message(filters.command("gen", prefixes=".") & (filters.user(ADMIN_ID) | filters.me))
async def gen_code(client, message):
    try:
        days = int(message.command[1])
        code = str(random.randint(100000, 999999))
        db["licenses"][code] = days
        save_data(db)
        await message.edit(f"✅ **License Created!**\nCode: `{code}`\nValidity: {days} Days")
    except: await message.edit("Usage: `.gen 30`")

@app.on_message(filters.command("redeem", prefixes=".") & filters.group)
async def redeem_code(client, message):
    chat_id = str(message.chat.id)
    try:
        user_status = await client.get_chat_member(message.chat.id, message.from_user.id)
        if user_status.status not in [enums.ChatMemberStatus.OWNER, enums.ChatMemberStatus.ADMINISTRATOR] and message.from_user.id != ADMIN_ID:
            return await message.edit("❌ Only Admins can redeem.")
        
        code = message.command[1]
        if code in db["licenses"]:
            days = db["licenses"].pop(code)
            db["active_groups"][chat_id] = time.time() + (days * 86400)
            if chat_id not in db["settings"]: db["settings"][chat_id] = {"delete_time": 60}
            save_data(db)
            await message.edit("🔥 **Premium Activated!** A to Z Delete mode is ON.")
        else: await message.edit("❌ Invalid Code.")
    except: await message.edit("Usage: `.redeem [code]`")

# --- DELETE ENGINE ---
@app.on_message(filters.group & ~filters.me, group=1)
async def track_msg(client, message):
    chat_id = str(message.chat.id)
    if chat_id in db["active_groups"] and db["active_groups"][chat_id] > time.time():
        if message.text and message.text.startswith("."): return
        delay = db["settings"].get(chat_id, {}).get("delete_time", 60)
        tracked_messages.append({'cid': message.chat.id, 'mid': message.id, 'at': time.time() + delay})

async def delete_worker():
    while True:
        now = time.time()
        global tracked_messages
        to_del = [m for m in tracked_messages if now >= m['at']]
        tracked_messages = [m for m in tracked_messages if now < m['at']]
        for m in to_del:
            try: await app.delete_messages(m['cid'], m['mid'])
            except FloodWait as e: await asyncio.sleep(e.value)
            except: pass
        await asyncio.sleep(1)

# --- STARTUP ---
async def start_services():
    threading.Thread(target=run_web, daemon=True).start()
    threading.Thread(target=keep_alive, daemon=True).start()
    await app.start()
    asyncio.create_task(delete_worker())
    from pyrogram.methods.utilities.idle import idle
    await idle()

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(start_services())
    
