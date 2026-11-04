import os
import re
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import (
    SessionPasswordNeededError,
    PhoneCodeInvalidError,
    PasswordHashInvalidError,
    PhoneNumberInvalidError,
    FloodWaitError
)
from telethon import events, Button

# ==========================================
# CONFIGURATION
# ==========================================
# Session generator bot token
BOT_TOKEN = os.environ.get("SESSION_BOT_TOKEN", "9180219965:AAG7YG-OLeuhoT4b0fcwHccN4yn3UYtv9xE")
API_ID = int(os.environ.get("API_ID", 30417927))
API_HASH = os.environ.get("API_HASH", "a859ee736c7f07b2e2fa80159409ecc3")

# Main bot client
bot = TelegramClient('session_generator_bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# Active state cache: {user_id: {"step": "...", "client": ..., "phone": ..., "phone_code_hash": ...}}
user_sessions = {}

# ==========================================
# UI MESSAGES & TEMPLATES
# ==========================================
START_TEXT = """
<blockquote>⚡ <b>OXY SESSION ARCHITECT</b>
<i>High-Performance String Session Engine</i></blockquote>

Welcome to the <b>Telethon Session Generator</b>.

This utility creates secure, production-ready <b>Telethon String Sessions</b> for your store inventory.

<b>Security Notice:</b>
• Your session keys are generated dynamically in-memory.
• No credentials or authorization tokens are permanently stored.

<i>Click the button below to initiate generation:</i>
"""

PHONE_PROMPT = """
<blockquote>📱 <b>STEP 1 OF 3: PHONE VERIFICATION</b></blockquote>

Please enter the <b>Phone Number</b> linked to your Telegram account, including the full international country code.

<b>Format:</b> <code>+12025550143</code> or <code>+919876543210</code>

<i>Send <code>/cancel</code> or tap the button below to abort.</i>
"""

def cancel_button():
    return [Button.inline("✖ Cancel Process", b"cancel_flow")]

# ==========================================
# EVENT HANDLERS
# ==========================================
@bot.on(events.NewMessage(pattern=r"^/start"))
async def handle_start(event):
    uid = event.sender_id
    if uid in user_sessions:
        try:
            await user_sessions[uid]["client"].disconnect()
        except Exception:
            pass
        del user_sessions[uid]

    buttons = [
        [Button.inline("🚀 Generate Session", b"start_gen")],
        [Button.url("💬 Support", "https://t.me/lv_oxyg3n")]
    ]
    await event.respond(START_TEXT, parse_mode="html", buttons=buttons)

@bot.on(events.NewMessage(pattern=r"^/cancel"))
async def handle_cancel_cmd(event):
    uid = event.sender_id
    if uid in user_sessions:
        try:
            await user_sessions[uid]["client"].disconnect()
        except Exception:
            pass
        del user_sessions[uid]
        await event.respond("✖ <b>Process Terminated.</b>\nYou can restart anytime using /start.", parse_mode="html")
    else:
        await event.respond("ℹ️ No active process to cancel.", parse_mode="html")

@bot.on(events.CallbackQuery(data=b"cancel_flow"))
async def handle_cancel_callback(event):
    uid = event.sender_id
    if uid in user_sessions:
        try:
            await user_sessions[uid]["client"].disconnect()
        except Exception:
            pass
        del user_sessions[uid]
    await event.edit("✖ <b>Process Terminated.</b>\nYou can restart anytime using /start.", parse_mode="html")

@bot.on(events.CallbackQuery(data=b"start_gen"))
async def handle_start_gen(event):
    uid = event.sender_id
    user_sessions[uid] = {
        "step": "awaiting_phone",
        "client": TelegramClient(StringSession(), API_ID, API_HASH)
    }
    await event.edit(PHONE_PROMPT, parse_mode="html", buttons=cancel_button())

@bot.on(events.NewMessage)
async def handle_inputs(event):
    if event.raw_text.startswith(("/", "✖")):
        return

    uid = event.sender_id
    if uid not in user_sessions:
        return

    state = user_sessions[uid]
    step = state.get("step")
    client = state.get("client")
    text = event.raw_text.strip()

    # ------------------------------------------
    # STEP 1: PHONE NUMBER INPUT
    # ------------------------------------------
    if step == "awaiting_phone":
        phone = re.sub(r"[^\d+]", "", text)
        if not phone.startswith("+"):
            phone = "+" + phone

        status_msg = await event.respond("⏳ <b>Connecting to Telegram core servers...</b>", parse_mode="html")
        try:
            await client.connect()
            sent_code = await client.send_code_request(phone)
            
            state["phone"] = phone
            state["phone_code_hash"] = sent_code.phone_code_hash
            state["step"] = "awaiting_otp"

            otp_prompt = f"""
<blockquote>📩 <b>STEP 2 OF 3: ENTER LOGIN CODE</b></blockquote>

A 5-digit verification code has been dispatched to your official Telegram app for:
<code>{phone}</code>

<b>Instructions:</b>
• Enter the code separated by spaces if needed (e.g. <code>1 2 3 4 5</code>) to prevent Telegram auto-locking.
• Example format: <code>12345</code> or <code>1 2 3 4 5</code>
"""
            await status_msg.edit(otp_prompt, parse_mode="html", buttons=cancel_button())
        except PhoneNumberInvalidError:
            await status_msg.edit("❌ <b>Invalid Phone Number!</b>\nPlease double-check the country code and try again.", parse_mode="html", buttons=cancel_button())
        except FloodWaitError as e:
            await status_msg.edit(f"⚠️ <b>Flood Wait Triggered:</b> Please wait <code>{e.seconds}</code> seconds before retrying.", parse_mode="html")
            del user_sessions[uid]
        except Exception as e:
            await status_msg.edit(f"❌ <b>Error:</b> <code>{str(e)}</code>\nUse /start to retry.", parse_mode="html")
            del user_sessions[uid]

    # ------------------------------------------
    # STEP 2: OTP VERIFICATION
    # ------------------------------------------
    elif step == "awaiting_otp":
        otp = text.replace(" ", "").strip()
        status_msg = await event.respond("⏳ <b>Validating authorization code...</b>", parse_mode="html")

        try:
            await client.sign_in(
                phone=state["phone"],
                code=otp,
                phone_code_hash=state["phone_code_hash"]
            )
            # Login Success without 2FA
            session_str = client.session.save()
            await client.disconnect()
            del user_sessions[uid]

            done_text = f"""
<blockquote>🎉 <b>STRING SESSION GENERATED SUCCESSFULLY</b></blockquote>

<b>Phone Number:</b> <code>{state['phone']}</code>
<b>Framework:</b> Telethon (StringSession)

<b>Session String (Tap below to copy):</b>
<code>{session_str}</code>

⚠️ <b>Important:</b> Keep this session string confidential. You can now supply this key directly into your store stock.
"""
            await status_msg.edit(done_text, parse_mode="html")

        except SessionPasswordNeededError:
            # 2FA Password is required
            state["step"] = "awaiting_2fa"
            twofa_text = """
<blockquote>🔒 <b>STEP 3 OF 3: TWO-STEP VERIFICATION (2FA)</b></blockquote>

Your account is secured with a Cloud Password.

Please send your <b>Two-Step Verification Password</b> below to complete authorization:
"""
            await status_msg.edit(twofa_text, parse_mode="html", buttons=cancel_button())

        except PhoneCodeInvalidError:
            await status_msg.edit("❌ <b>Incorrect Login Code!</b>\nPlease check your Telegram messages and send the valid code again.", parse_mode="html", buttons=cancel_button())
        except Exception as e:
            await status_msg.edit(f"❌ <b>Authentication Failure:</b> <code>{str(e)}</code>", parse_mode="html")
            try:
                await client.disconnect()
            except Exception:
                pass
            del user_sessions[uid]

    # ------------------------------------------
    # STEP 3: 2FA PASSWORD INPUT
    # ------------------------------------------
    elif step == "awaiting_2fa":
        password = text
        status_msg = await event.respond("⏳ <b>Verifying Two-Step password...</b>", parse_mode="html")

        try:
            await client.sign_in(password=password)
            session_str = client.session.save()
            await client.disconnect()
            del user_sessions[uid]

            done_text = f"""
<blockquote>🎉 <b>STRING SESSION GENERATED SUCCESSFULLY</b></blockquote>

<b>Phone Number:</b> <code>{state['phone']}</code>
<b>Framework:</b> Telethon (StringSession)

<b>Session String (Tap below to copy):</b>
<code>{session_str}</code>

⚠️ <b>Important:</b> Keep this session string confidential. You can now supply this key directly into your store stock.
"""
            await status_msg.edit(done_text, parse_mode="html")

        except PasswordHashInvalidError:
            await status_msg.edit("❌ <b>Incorrect 2FA Password!</b>\nPlease verify your password and enter it again.", parse_mode="html", buttons=cancel_button())
        except Exception as e:
            await status_msg.edit(f"❌ <b>Authentication Failure:</b> <code>{str(e)}</code>", parse_mode="html")
            try:
                await client.disconnect()
            except Exception:
                pass
            del user_sessions[uid]

# ==========================================
# BOOTSTRAP
# ==========================================
print("Oxy Telethon String Session Generator Bot is running...")
bot.run_until_disconnected()
