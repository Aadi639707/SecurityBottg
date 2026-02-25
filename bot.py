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
SESSION_STRING = os.environ.get("SESSION_STRING", "")

ADMIN_ID = 8306853454  # Aapki Global Admin ID
SUPPORT_ID = "@SANATANI_GOJO"
DATA_FILE = "userbot_data.json"

# --- RENDER FAKE WEB SERVICE ---
app_web = Flask(__name__)
@app_web.route('/')
def home(): return "Userbot Security 10000% Online & Secure!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app_web.run(host="0.0.0.0", port=port)

# --- DATABASE HANDLING ---
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

# --- USERBOT CLIENT SETUP ---
if not SESSION_STRING:
    print("❌ Critical Error: SESSION_STRING not found in environment!")
    exit(1)

app = Client(
    "SecurityUserbot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING,
    in_memory=True
)

# --- COMMAND HANDLERS ---

# .start command (Aapki ID aur Session ID dono ke liye)
@app.on_message(filters.command("start", prefixes=".") & (filters.user(ADMIN_ID) | filters.me))
async def start_cmd(client, message):
    await message.edit("🛡️ **Userbot Security: ONLINE**\n\nAb Rose Bot ke messages nahi bachenge. A to Z deletion ready hai.")

# .gen command (License banane ke liye)
@app.on_message(filters.command("gen", prefixes=".") & (filters.user(ADMIN_ID) | filters.me))
async def gen_code(client, message):
    try:
        if len(message.command) < 2:
            return await message.edit("Usage: `.gen 30` (for 30 days)")
            
        days = int(message.command[1])
        code = str(random.randint(100000, 999999))
        db["licenses"][code] = days
        save_data(db)
        await message.edit(f"✅ **License Created!**\nCode: `{code}`\nValidity: {days} Days")
    except Exception as e:
        await message.edit(f"Error: {str(e)}")

# .redeem command (Group activate karne ke liye)
@app.on_message(filters.command("redeem", prefixes=".") & filters.group)
async def redeem_code(client, message):
    chat_id = str(message.chat.id)
    try:
        # Check permission: Admin ya Owner ya Aapki Global ID
        user_status = await client.get_chat_member(message.chat.id, message.from_user.id)
        is_admin = user_status.status in [enums.ChatMemberStatus.OWNER, enums.ChatMemberStatus.ADMINISTRATOR]
        
        if not is_admin and message.from_user.id != ADMIN_ID:
            return await message.edit("❌ Only Group Admins can use this.")

        if len(message.command) < 2:
            return await message.edit("Usage: `.redeem 123456`")

        code = message.command[1]
        if code in db["licenses"]:
            days = db["licenses"].pop(code)
            db["active_groups"][chat_id] = time.time() + (days * 86400)
            if chat_id not in db["settings"]: db["settings"][chat_id] = {"delete_time": 60}
            save_data(db)
            await message.edit("🔥 **Premium Activated!** A to Z Deletion (Users & Bots) is now ON.")
        else:
            await message.edit("❌ Invalid Code.")
    except Exception as e:
        await message.edit(f"❌ Error: Make sure this ID is Admin in this group!")

# .settime command (Delete speed control karne ke liye)
@app.on_message(filters.command("settime", prefixes=".") & filters.group)
async def set_time(client, message):
    chat_id = str(message.chat.id)
    try:
        user_status = await client.get_chat_member(message.chat.id, message.from_user.id)
        if user_status.status not in [enums.ChatMemberStatus.OWNER, enums.ChatMemberStatus.ADMINISTRATOR] and message.from_user.id != ADMIN_ID:
            return
            
        mins = int(message.command[1])
        db["settings"][chat_id]["delete_time"] = mins * 60
        save_data(db)
        await message.edit(f"⏱️ **Delete interval set to {mins} minute(s).**")
    except:
        await message.edit("Usage: `.settime 1`")

# --- 🔥 THE A TO Z DELETE ENGINE 🔥 ---

@app.on_message(filters.group & ~filters.me, group=1)
async def track_everything(client, message):
    chat_id = str(message.chat.id)
    # Check if group has active plan
    if chat_id in db["active_groups"] and db["active_groups"][chat_id] > time.time():
        # Command messages skip karein
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
                # Userbot can delete anything (including Rose bot's messages)
                await app.delete_messages(m['cid'], m['mid'])
            except FloodWait as e: await asyncio.sleep(e.value)
            except: pass
        await asyncio.sleep(1)

# --- BOOTSTRAP ---
async def start_services():
    # Start web server for Render
    threading.Thread(target=run_web, daemon=True).start()
    
    # Start the Userbot
    await app.start()
    print(">>> USERBOT STARTED SUCCESSFULLY!")
    
    # Start background task
    asyncio.create_task(delete_worker())
    
    # Keep running
    from pyrogram.methods.utilities.idle import idle
    await idle()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(start_services())
        
