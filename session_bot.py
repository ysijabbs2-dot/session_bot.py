import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import (
    SessionPasswordNeededError,
    PhoneCodeInvalidError,
    PasswordHashInvalidError,
    PhoneNumberInvalidError
)

# Aapka Bot Token (@BotFather se naya bot bana kar token yahan daalein)
BOT_TOKEN = os.environ.get("SESSION_BOT_TOKEN", "9180219965:AAG7YG-OLeuhoT4b0fcwHccN4yn3UYtv9xE")
API_ID = int(os.environ.get("API_ID", 30417927))
API_HASH = os.environ.get("API_HASH", "a859ee736c7f07b2e2fa80159409ecc3")

# Bot Client
bot = Client("session_gen_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# In-memory storage for login states
user_sessions = {}

@bot.on_message(filters.command("start") & filters.private)
async def start_handler(client, message: Message):
    uid = message.from_user.id
    user_sessions[uid] = {}
    await message.reply(
        "👋 **Telethon String Session Generator Bot**\n\n"
        "Apna Telegram account ka phone number bhejo (country code ke sath):\n"
        "Example: `+919876543210`\n\n"
        "Process cancel karne ke liye /cancel bhejein."
    )

@bot.on_message(filters.command("cancel") & filters.private)
async def cancel_handler(client, message: Message):
    uid = message.from_user.id
    if uid in user_sessions:
        tc = user_sessions[uid].get("client")
        if tc and tc.is_connected():
            await tc.disconnect()
        del user_sessions[uid]
    await message.reply("❌ Session generation cancel kar diya gaya hai. /start karke dobara shuru karein.")

@bot.on_message(filters.text & filters.private)
async def message_handler(client, message: Message):
    uid = message.from_user.id
    text = message.text.strip()

    if uid not in user_sessions or "step" not in user_sessions[uid]:
        # Step 1: Phone number input
        phone = text.replace(" ", "")
        msg = await message.reply("⏳ Connecting to Telegram...")
        
        tc = TelegramClient(StringSession(), API_ID, API_HASH)
        await tc.connect()
        
        try:
            code_hash = await tc.send_code_request(phone)
            user_sessions[uid] = {
                "client": tc,
                "phone": phone,
                "phone_code_hash": code_hash.phone_code_hash,
                "step": "otp"
            }
            await msg.edit(
                f"✅ **Login Code bhej diya gaya hai!**\n\n"
                f"Telegram me aaya hua **OTP** yahan send karein.\n"
                f"*(Format: agar code `12345` hai, toh `1 2 3 4 5` ya `12345` likh kar bhejein)*"
            )
        except PhoneNumberInvalidError:
            await tc.disconnect()
            await msg.edit("❌ Phone number invalid hai! Sahi format me bhejein (+91...).")
        except Exception as e:
            await tc.disconnect()
            await msg.edit(f"❌ Error: {str(e)}")
        return

    step = user_sessions[uid].get("step")
    tc = user_sessions[uid].get("client")

    # Step 2: OTP Verification
    if step == "otp":
        otp = text.replace(" ", "").replace("-", "")
        phone = user_sessions[uid]["phone"]
        phone_code_hash = user_sessions[uid]["phone_code_hash"]
        
        try:
            await tc.sign_in(phone=phone, code=otp, phone_code_hash=phone_code_hash)
            # Agar bina password login ho gaya
            session_str = tc.session.save()
            await message.reply(
                f"🎉 **AAPKA TELETHON STRING SESSION READY HAI!**\n\n"
                f"`{session_str}`\n\n"
                f"⚠️ *Isko copy karke apne store bot ke stock me add kar lein.*"
            )
            await tc.disconnect()
            del user_sessions[uid]
        except SessionPasswordNeededError:
            user_sessions[uid]["step"] = "2fa"
            await message.reply("🔐 **2FA Password Detected!**\n\nIs account par Two-Step Verification laga hua hai. Apna 2FA Password yahan send karein:")
        except PhoneCodeInvalidError:
            await message.reply("❌ Galat OTP! Dobara check karke bhejein.")
        except Exception as e:
            await message.reply(f"❌ Error: {str(e)}")

    # Step 3: 2FA Password
    elif step == "2fa":
        password = text
        try:
            await tc.sign_in(password=password)
            session_str = tc.session.save()
            await message.reply(
                f"🎉 **AAPKA TELETHON STRING SESSION READY HAI!**\n\n"
                f"`{session_str}`\n\n"
                f"⚠️ *Isko copy karke apne store bot ke stock me add kar lein.*"
            )
            await tc.disconnect()
            del user_sessions[uid]
        except PasswordHashInvalidError:
            await message.reply("❌ Galat Password! Sahi 2FA Password enter karein:")
        except Exception as e:
            await message.reply(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    print("Session Generator Bot is running...")
    bot.run()
