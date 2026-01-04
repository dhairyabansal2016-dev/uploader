import os
import re
import sys
import json
import time
import asyncio
import shlex
import requests
import subprocess
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait

# Import your existing globals and vars
import globals
from vars import OWNER, CREDIT, AUTH_USERS

async def drm_handler(bot: Client, m: Message):
    globals.processing_request = True
    globals.cancel_requested = False
    
    # Settings from your globals file
    caption_type = globals.caption
    res_val = globals.res if hasattr(globals, 'res') else "720"
    quality_text = globals.quality if hasattr(globals, 'quality') else "720p"
    CR = globals.CR
    user_id = m.from_user.id

    # 1. Input Handling
    if m.document and m.document.file_name.endswith('.txt'):
        path = await m.download()
        with open(path, "r") as f:
            content = f.read()
        lines = [l.strip() for l in content.split("\n") if l.strip()]
        os.remove(path)
    elif m.text:
        lines = [m.text.strip()]
    else:
        return

    # 2. Parsing Titles and Links
    links = []
    for line in lines:
        if "://" in line:
            if ":" in line and "http" not in line.split(":")[0]:
                parts = line.split(":", 1)
                links.append([parts[0].strip(), parts[1].strip()])
            else:
                # Fallback if you only send a link
                links.append(["Video", line.strip()])

    # 3. Startup Prompts
    editable = await m.reply_text(f"✨ **Links Found:** {len(links)}\nSend Start Index (Default 1):")
    try:
        idx_msg = await bot.listen(m.chat.id, timeout=30)
        start_index = int(idx_msg.text)
        await idx_msg.delete()
    except: start_index = 1

    await editable.edit("📁 **Send Batch Name:**")
    try:
        batch_msg = await bot.listen(m.chat.id, timeout=30)
        b_name = batch_msg.text
        await batch_msg.delete()
    except: b_name = "Batch"

    await editable.delete()

    # 4. The Processing Loop
    count = start_index
    for i in range(start_index - 1, len(links)):
        if globals.cancel_requested:
            await m.reply_text("🛑 **Stopped by User**")
            break

        name1 = links[i][0]
        url = links[i][1]
        
        # --- API Extraction Logic (Classplus/Testbook) ---
        keys_string = ""
        if any(x in url for x in ["testbook", "classplus", "tpv.sr"]):
            try:
                api_url = f"https://shefu-api-final.vercel.app/shefu?url={url}@ITSGOLU_FORCE&user_id={user_id}"
                data = requests.get(api_url, timeout=15).json()
                if "KEYS" in data:
                    url = data.get("MPD")
                    keys_string = " ".join([f"--key {k}" for k in data.get("KEYS")])
            except:
                pass # Continue with original URL if API fails

        # --- FILENAME PROTECTION (FIXES THE CRASH) ---
        # 1. Clean title for the Telegram caption
        display_title = name1
        # 2. Hard-clean title for the Linux Shell (Remove spaces and special chars)
        safe_filename = re.sub(r'[^\w\-]', '_', display_title)
        if not safe_filename or safe_filename == "_":
            safe_filename = f"file_{count}"
        
        final_output = f"{safe_filename}.mp4"
        
        # shlex.quote handles any weird characters in the URL or Filename
        quoted_url = shlex.quote(url)
        quoted_out = shlex.quote(final_output)

        # 5. UI Progress
        prog_msg = await bot.send_message(m.chat.id, f"📥 **Downloading:** `{display_title}`\nIndex: {count}")

        # 6. Build Command
        if "m3u8" in url or "master" in url:
            # Generic FFMPEG (No referer needed, allowed extensions added for stability)
            cmd = f'ffmpeg -i {quoted_url} -c copy -bsf:a aac_adtstoasc -allowed_extensions ALL {quoted_out} -y'
        else:
            ytf = f"b[height<={res_val}]/bv[height<={res_val}]+ba/b"
            cmd = f'yt-dlp {keys_string} -f "{ytf}" {quoted_url} -o {quoted_out}'

        # 7. Execute and Upload
        try:
            # Run the shell command
            subprocess.run(cmd, shell=True, check=True, capture_output=True)

            if os.path.exists(final_output):
                await prog_msg.edit("📤 **Uploading...**")
                
                # Caption Templates
                if caption_type == "/cc1":
                    cap = f"🎥 **Video:** `{display_title}`\n📂 **Batch:** {b_name}"
                else:
                    cap = f"✅ **{display_title}**\n━━━━━━━━━━━━━━━\n🎬 **Quality:** {res_val}p\n🌟 **By:** {CR}"

                await bot.send_video(m.chat.id, video=final_output, caption=cap, supports_streaming=True)
                os.remove(final_output)
                await prog_msg.delete()
            else:
                raise Exception("File was not created by FFmpeg/YT-DLP")

            count += 1

        except Exception as e:
            # This captures the error so the bot doesn't crash the whole container
            await bot.send_message(m.chat.id, f"❌ **Error at {count}:** `{display_title}`\n`{str(e)[:100]}`")
            count += 1
            continue

    globals.processing_request = False
    await m.reply_text("✅ **All Done!**")
