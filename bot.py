import os
import time
import json
import random
import asyncio
import threading
from flask import Flask
from pyrogram import Client, filters
from pyrogram.errors import FloodWait

# --- CONFIGURATION ---
# Ye variables Render dashboard me Environment Variables me dalne hain
API_ID = int(os.environ.get("API_ID", "123456")) # Apna API ID dalein
API_HASH = os.environ.get("API_HASH", "your_api_hash") # Apna API Hash dalein
BOT_TOKEN = os.environ.get("BOT_TOKEN", "your_bot_token")

ADMIN_ID = 8306853454
SUPPORT_ID = "@SANATANI_GOJO"
DATA_FILE = "bot_data.json"

# --- FAKE WEB SERVICE FOR RENDER ---
app_web = Flask(__name__)

@app_web.route('/')
def home():
    return "Bot is running securely 10000%!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app_web.run(host="0.0.0.0", port=port)

# Start Fake Port in background
threading.Thread(target=run_web, daemon=True).start()

# --- BOT SETUP ---
app = Client("SecurityBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# --- DATABASE HANDLING (JSON) ---
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"licenses": {}, "active_groups": {}, "settings": {}}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

db = load_data()
tracked_messages = []

# --- COMMANDS ---

@app.on_message(filters.command("start") & filters.private)
async def start_cmd(client, message):
    await message.reply_text(
        f"**Hello!** I am an Advanced Group Security Bot.\n\n"
        f"To use me in your group, you need a premium license.\n"
        f"Contact Support: {SUPPORT_ID}"
    )

@app.on_message(filters.command("gen") & filters.user(ADMIN_ID))
async def gen_code(client, message):
    try:
        days = int(message.command[1])
    except IndexError:
        await message.reply_text("Usage: `/gen [days]` (e.g., `/gen 30`)")
        return
    
    # Generate 6 digit code
    code = str(random.randint(100000, 999999))
    db["licenses"][code] = days
    save_data(db)
    
    await message.reply_text(f"**License Generated!**\n\nCode: `{code}`\nValidity: {days} Days\nShare this code with the user.")

@app.on_message(filters.command("redeem") & filters.group)
async def redeem_code(client, message):
    chat_id = str(message.chat.id)
    try:
        code = message.command[1]
    except IndexError:
        await message.reply_text("Usage: `/redeem [6-digit-code]`")
        return
    
    # Check admin rights
    member = await client.get_chat_member(message.chat.id, message.from_user.id)
    if member.status not in ["creator", "administrator"]:
        await message.reply_text("Only Group Admins can redeem the code.")
        return

    if code in db["licenses"]:
        days = db["licenses"].pop(code)
        expiry_time = time.time() + (days * 86400) # Convert days to seconds
        
        db["active_groups"][chat_id] = expiry_time
        if chat_id not in db["settings"]:
            db["settings"][chat_id] = {"delete_time": 60} # Default 1 min
            
        save_data(db)
        await message.reply_text(f"✅ **Premium Activated!**\n\nThis group is now fully secured. Valid for {days} days.")
    else:
        await message.reply_text("❌ Invalid or Expired Code.")

@app.on_message(filters.command("settime") & filters.group)
async def set_time(client, message):
    chat_id = str(message.chat.id)
    
    # Check if premium
    if chat_id not in db["active_groups"] or db["active_groups"][chat_id] < time.time():
        await message.reply_text(f"This group does not have an active premium plan. Contact {SUPPORT_ID}")
        return
        
    member = await client.get_chat_member(message.chat.id, message.from_user.id)
    if member.status not in ["creator", "administrator"]:
        return

    try:
        minutes = int(message.command[1])
        db["settings"][chat_id]["delete_time"] = minutes * 60
        save_data(db)
        await message.reply_text(f"✅ Auto-delete time set to {minutes} minutes.")
    except (IndexError, ValueError):
        await message.reply_text("Usage: `/settime [minutes]` (e.g., `/settime 1`)")

# --- MESSAGE TRACKING & AUTO-DELETE SYSTEM ---

@app.on_message(filters.group & ~filters.service)
async def track_all_messages(client, message):
    chat_id = str(message.chat.id)
    
    # Ignore if not premium or expired
    if chat_id not in db["active_groups"] or db["active_groups"][chat_id] < time.time():
        return
        
    delete_delay = db["settings"].get(chat_id, {}).get("delete_time", 60)
    
    tracked_messages.append({
        'chat_id': message.chat.id,
        'msg_id': message.id,
        'delete_at': time.time() + delete_delay
    })

async def auto_delete_worker():
    while True:
        now = time.time()
        to_delete = {}
        global tracked_messages
        remaining_messages = []

        # Find messages that need to be deleted
        for msg in tracked_messages:
            if now >= msg['delete_at']:
                if msg['chat_id'] not in to_delete:
                    to_delete[msg['chat_id']] = []
                to_delete[msg['chat_id']].append(msg['msg_id'])
            else:
                remaining_messages.append(msg)

        tracked_messages = remaining_messages

        # Delete messages in chunks of 100 to avoid API limits
        for chat_id, msg_ids in to_delete.items():
            try:
                for i in range(0, len(msg_ids), 100):
                    await app.delete_messages(chat_id, msg_ids[i:i+100])
            except FloodWait as e:
                # If Telegram rate limits us, wait and try again
                await asyncio.sleep(e.value)
            except Exception:
                # Ignore errors like 'Message already deleted'
                pass
                
        await asyncio.sleep(5) # Check every 5 seconds

# --- RUN BOT ---
async def main():
    await app.start()
    print("Bot Started Successfully!")
    asyncio.create_task(auto_delete_worker())
    
    # Keep running
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    app.run(main())
  
