import os
import time
import json
import random
import asyncio
import threading
import requests  # Ye line top pe add karo
from flask import Flask
from pyrogram import Client, filters, enums
from pyrogram.errors import FloodWait

# --- CONFIGURATION ---
API_ID = int(os.environ.get("API_ID", "123456"))
API_HASH = os.environ.get("API_HASH", "your_api_hash")
SESSION_STRING = os.environ.get("SESSION_STRING", "")
RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL", "") # Render auto provide karta hai

ADMIN_ID = 8306853454 
SUPPORT_ID = "@SANATANI_GOJO"
DATA_FILE = "userbot_data.json"

# --- RENDER WEB SERVICE & ANTI-SLEEP ---
app_web = Flask(__name__)

@app_web.route('/')
def home():
    return "Userbot 10000% Secure & Always Awake!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app_web.run(host="0.0.0.0", port=port)

# Naya logic: Bot khud ko ping karega har 10 minute me
def keep_alive():
    if not RENDER_URL:
        print("⚠️ RENDER_EXTERNAL_URL is missing, self-ping disabled.")
        return
    while True:
        try:
            requests.get(RENDER_URL)
            print("Pinged self to stay awake!")
        except:
            pass
        time.sleep(600) # 10 minute ka delay

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
    session_string=SESSION_STRING,
    in_memory=True
)

# ... (Purane Commands: Start, Gen, Redeem wahi rahenge) ...

# --- DELETE ENGINE (Same as before) ---
@app.on_message(filters.group & ~filters.me, group=1)
async def track_everything(client, message):
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

# --- UPDATED STARTUP ---
async def start_services():
    # Start web server
    threading.Thread(target=run_web, daemon=True).start()
    
    # Start self-ping (Anti-Sleep)
    threading.Thread(target=keep_alive, daemon=True).start()
    
    await app.start()
    print(">>> USERBOT IS ONLINE & ANTI-SLEEP ACTIVE!")
    asyncio.create_task(delete_worker())
    from pyrogram.methods.utilities.idle import idle
    await idle()

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(start_services())
                
