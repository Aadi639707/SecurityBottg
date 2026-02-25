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
# Userbot ke liye API_ID aur API_HASH bahut zaroori hain
API_ID = int(os.environ.get("API_ID", "123456"))
API_HASH = os.environ.get("API_HASH", "your_api_hash")
# Isme BOT_TOKEN nahi lagega, balki STRING_SESSION lagega ya login karna hoga
# Sabse simple hai login session use karna
SESSION_STRING = os.environ.get("SESSION_STRING", "") 

ADMIN_ID = 8306853454 
SUPPORT_ID = "@SANATANI_GOJO"
DATA_FILE = "userbot_data.json"

app_web = Flask(__name__)
@app_web.route('/')
def home(): return "Userbot Security 10000% Online!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app_web.run(host="0.0.0.0", port=port)

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

# Yahan hum Client mein session string use kar rahe hain
app = Client("SecurityUserbot", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)

# --- COMMANDS (Only for Admin ID) ---

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
        code = message.command[1]
        if code in db["licenses"]:
            days = db["licenses"].pop(code)
            db["active_groups"][chat_id] = time.time() + (days * 86400)
            if chat_id not in db["settings"]: db["settings"][chat_id] = {"delete_time": 60}
            save_data(db)
            await message.edit(f"🔥 **Premium Activated!** A to Z (including Bots) will be deleted.")
        else: await message.edit("❌ Invalid Code.")
    except: await message.edit("Usage: `.redeem [code]`")

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
        # ID commands ko skip karegi taaki control chalta rahe
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
                # Userbot har message (bot/user/admin) delete kar sakta hai
                await app.delete_messages(m['cid'], m['mid'])
            except FloodWait as e: await asyncio.sleep(e.value)
            except: pass
        await asyncio.sleep(1)

async def start_services():
    threading.Thread(target=run_web, daemon=True).start()
    await app.start()
    print(">>> USERBOT IS ONLINE (MissRose is now target!)")
    asyncio.create_task(delete_worker())
    from pyrogram.methods.utilities.idle import idle
    await idle()

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(start_services())
