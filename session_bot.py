import os
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.errors import (
    SessionPasswordNeededError,
    PhoneCodeInvalidError,
    PasswordHashInvalidError,
    PhoneNumberInvalidError
)

# ==========================================
# HEALTH SERVER (RENDER UPTIME)
# ==========================================
PORT = int(os.environ.get("PORT", 8080))

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
    def log_message(self, format, *args):
        return

def run_server():
    try:
        server = HTTPServer(("0.0.0.0", PORT), HealthHandler)
        server.serve_forever()
    except Exception as e:
        print(f"Health server port {PORT} skipped: {e}")

threading.Thread(target=run_server, daemon=True).start()

# ==========================================
# BOT CREDENTIALS
# ==========================================
BOT_TOKEN = os.environ.get("SESSION_BOT_TOKEN")
API_ID = int(os.environ.get("API_ID", 30417927))
API_HASH = os.environ.get("API_HASH", "a859ee736c7f07b2e2fa80159409ecc3")

# Main Bot Client
bot = TelegramClient("session_bot_host", API_ID, API_HASH)

# In-memory user state
user_state = {}

@bot.on(events.NewMessage(pattern="/start"))
async def start_handler(event):
    uid = event.sender_id
    user_state[uid] = {}
    await event.respond(
        "👋 **Telethon String Session Generator Bot**\n\n"
        "Apna Telegram account phone number bhejo (country code ke sath):\n"
        "Example: `+919876543210`\n\n"
        "Process cancel karne ke liye /cancel bhejein."
    )

@bot.on(events.NewMessage(pattern="/cancel"))
async def cancel_handler(event):
    uid = event.sender_id
    if uid in user_state:
        client = user_state[uid].get("client")
        if client and client.is_connected():
            await client.disconnect()
        del user_state[uid]
    await event.respond("❌ Process cancel kar diya gaya hai. Shuru karne ke liye /start dabayein.")

@bot.on(events.NewMessage)
async def message_handler(event):
    text = event.text.strip()
    if text.startswith(("/start", "/cancel")):
        return

    uid = event.sender_id
    state = user_state.get(uid, {})
    step = state.get("step")

    # Step 1: Phone number input
    if not step:
        phone = text.replace(" ", "")
        status_msg = await event.respond("⏳ Telegram se connect kiya ja raha hai...")
        
        tc = TelegramClient(StringSession(), API_ID, API_HASH)
        await tc.connect()

        try:
            res = await tc.send_code_request(phone)
            user_state[uid] = {
                "client": tc,
                "phone": phone,
                "phone_code_hash": res.phone_code_hash,
                "step": "otp"
            }
            await status_msg.edit(
                "✅ **Login Code bhej diya gaya hai!**\n\n"
                "Aapke Telegram par aaya hua **OTP** yahan send karein."
            )
        except PhoneNumberInvalidError:
            await tc.disconnect()
            await status_msg.edit("❌ Phone number invalid hai! (+91...) format me dobara bhejein.")
        except Exception as e:
            await tc.disconnect()
            await status_msg.edit(f"❌ Error: {str(e)}")
        return

    tc = state.get("client")

    # Step 2: OTP Verification
    if step == "otp":
        otp = text.replace(" ", "").replace("-", "")
        phone = state.get("phone")
        phone_code_hash = state.get("phone_code_hash")

        try:
            await tc.sign_in(phone=phone, code=otp, phone_code_hash=phone_code_hash)
            session_str = tc.session.save()
            await event.respond(
                f"🎉 **AAPKA TELETHON STRING SESSION READY HAI!**\n\n"
                f"`{session_str}`\n\n"
                f"⚠️ *Isko copy karke apne store bot ke stock me daal dein.*"
            )
            await tc.disconnect()
            del user_state[uid]
        except SessionPasswordNeededError:
            user_state[uid]["step"] = "2fa"
            await event.respond("🔐 **2FA Password Detected!**\n\nApna Telegram 2FA Password send karein:")
        except PhoneCodeInvalidError:
            await event.respond("❌ Galat OTP! Dobara check karke bhejein:")
        except Exception as e:
            await event.respond(f"❌ Error: {str(e)}")

    # Step 3: 2FA Password
    elif step == "2fa":
        password = text
        try:
            await tc.sign_in(password=password)
            session_str = tc.session.save()
            await event.respond(
                f"🎉 **AAPKA TELETHON STRING SESSION READY HAI!**\n\n"
                f"`{session_str}`\n\n"
                f"⚠️ *Isko copy karke apne store bot ke stock me daal dein.*"
            )
            await tc.disconnect()
            del user_state[uid]
        except PasswordHashInvalidError:
            await event.respond("❌ Galat Password! Sahi 2FA Password enter karein:")
        except Exception as e:
            await event.respond(f"❌ Error: {str(e)}")

def main():
    print("Telethon Session Bot starting...")
    bot.start(bot_token=BOT_TOKEN)
    bot.run_until_disconnected()

if __name__ == "__main__":
    main()
