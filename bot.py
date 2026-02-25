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
# Ye variables Render Dashboard me hona zaroori hai
API_ID = int(os.environ.get("API_ID", "123456"))
API_HASH = os.environ.get("API_HASH", "your_api_hash")
SESSION_STRING = os.environ.get("SESSION_STRING", "") # StringFatherBot se lein

ADMIN_ID = 8306853454  # Aapki Admin ID
SUPPORT_ID = "@SANATANI_GOJO"
DATA_FILE = "userbot_data.json"

# --- RENDER FAKE PORT ---
app_web = Flask(__name__)
@app_web.route('/')
def home(): return "Userbot Security 10000% Online!"

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

# --- USERBOT CLIENT ---
app = Client(
    "SecurityUserbot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

# --- COMMANDS (Prefix '.') ---

@app.on_message(filters.command("start", prefixes=".") & filters.me)
async def start_cmd(client, message):
    await message.edit("🛡️ **Userbot Security Active**\n\nMain ab active hoon aur A to Z (including Rose) messages delete karunga.")

@app.on_message(filters.command("gen", prefixes=".") & filters.user(ADMIN_ID))
async def gen_code(client, message):
    try:
        days = int(message.command[1])
        code = str(random.randint(100000, 999999))
        db["licenses"][code] = days
        save_data(db)
        await message.edit(f"✅ **License Created!**\nCode: `{code}`\nDays: {days}")
    except: await message.edit("Usage: `.gen 30`")

@app.on_message(filters.command("redeem", prefixes=".") & filters.group)
async def redeem_code(client, message):
    chat_id = str(message.chat.id)
    try:
        # Userbot check karega ki redeem karne wala admin hai ya nahi
        user = await client.get_chat_member(message.chat.id, message.from_user.id)
        if user.status not in [enums.ChatMemberStatus.OWNER, enums.ChatMemberStatus.ADMINISTRATOR]:
            return await message.edit("❌ Only Group Admins can redeem.")
        
        code = message.command[1]
        if code in db["licenses"]:
            days = db["licenses"].pop(code)
            db["active_groups"][chat_id] = time.time() + (days * 86400)
            if chat_id not in db["settings"]: db["settings"][chat_id] = {"delete_time": 60}
            save_data(db)
            await message.edit(f"🔥 **Premium Activated!**\nAb ye ID har message delete karegi.")
        else: await message.edit("❌ Invalid Code.")
    except Exception as e:
        await message.edit(f"Error: {e}")

@app.on_message(filters.command("settime", prefixes=".") & filters.group)
async def set_time(client, message):
    chat_id = str(message.chat.id)
    try:
        mins = int(message.command[1])
        db["settings"][chat_id]["delete_time"] = mins * 60
        save_data(db)
        await message.edit(f"⏱️ Delete time set to {mins} min.")
    except: await message.edit("Usage: `.settime 1`")

# --- 🔥 A TO Z DELETE ENGINE (USERBOT POWER) 🔥 ---

@app.on_message(filters.group & ~filters.me, group=1)
async def track_everything(client, message):
    chat_id = str(message.chat.id)
    
    # Check if group is premium
    if chat_id in db["active_groups"] and db["active_groups"][chat_id] > time.time():
        # Commands ko skip karein taaki loop na bane
        if message.text and message.text.startswith("."): return
        
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
                # Userbot har message (bot/user/admin) delete karega
                await app.delete_messages(m['cid'], m['mid'])
            except FloodWait as e: await asyncio.sleep(e.value)
            except: pass
        await asyncio.sleep(1)

# --- STARTUP ---
async def start_services():
    threading.Thread(target=run_web, daemon=True).start()
    await app.start()
    print(">>> USERBOT IS ONLINE!")
    asyncio.create_task(delete_worker())
    from pyrogram.methods.utilities.idle import idle
    await idle()

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(start_services())
