import os
import re
import sys
import json
import time
import asyncio
import shlex
import requests
import cloudscraper
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait
from aiohttp import ClientSession

import globals
import helper
from vars import OWNER, CREDIT, AUTH_USERS

async def drm_handler(bot: Client, m: Message):
    globals.processing_request = True
    globals.cancel_requested = False
    
    # --- LOAD USER SETTINGS ---
    caption_type = globals.caption
    res_val = globals.res if hasattr(globals, 'res') else "720"
    quality_text = globals.quality if hasattr(globals, 'quality') else "720p"
    CR = globals.CR
    topic = globals.topic
    endfilename = globals.endfilename
    user_id = m.from_user.id

    # 1. INPUT DETECTION (Txt File or Text)
    if m.document and m.document.file_name.endswith('.txt'):
        x = await m.download()
        file_name = os.path.splitext(os.path.basename(x))[0]
        with open(x, "r") as f:
            content = f.read()
        lines = content.split("\n")
        os.remove(x)
    elif m.text and "://" in m.text:
        lines = [m.text]
        file_name = "Link_Input"
    else: return

    if m.chat.id not in AUTH_USERS:
        await m.reply_text(f"❌ **Unauthorized**\nID: `{m.chat.id}`")
        return

    # 2. LINK PARSING & CATEGORIZATION
    links = []
    pdf_count = img_count = zip_count = vid_count = 0
    
    for line in lines:
        if "://" in line:
            if ":" in line and "http" not in line.split(":", 1)[0]:
                parts = line.split(":", 1)
                title, url = parts[0].strip(), parts[1].strip()
            else:
                title, url = "File", line.strip()
            
            links.append([title, url])
            if ".pdf" in url.lower(): pdf_count += 1
            elif ".zip" in url.lower(): zip_count += 1
            elif any(ext in url.lower() for ext in [".jpg", ".png", ".jpeg"]): img_count += 1
            else: vid_count += 1

    # 3. INTERACTIVE SETUP (Same as original)
    editable = await m.reply_text(
        f"📋 **Total Links:** {len(links)}\n"
        f"<blockquote>• PDF: {pdf_count} | • Video: {vid_count}\n"
        f"• Zip: {zip_count} | • Img: {img_count}</blockquote>\n"
        f"Send **Start Index**:"
    )
    try:
        input0 = await bot.listen(editable.chat.id, timeout=30)
        start_index = int(input0.text)
        await input0.delete()
    except: start_index = 1

    await editable.edit("📂 **Enter Batch Name:**")
    try:
        input1 = await bot.listen(editable.chat.id, timeout=30)
        b_name = file_name if input1.text == "/d" else input1.text
        await input1.delete()
    except: b_name = file_name

    await editable.edit("🆔 **Channel ID (or /d):**")
    try:
        input7 = await bot.listen(editable.chat.id, timeout=30)
        channel_id = m.chat.id if input7.text == "/d" else int(input7.text)
        await input7.delete()
    except: channel_id = m.chat.id
    
    await editable.delete()

    # 4. MAIN PROCESSING LOOP
    count = start_index
    for i in range(start_index - 1, len(links)):
        if globals.cancel_requested:
            await m.reply_text("🚦 **STOPPED**")
            break

        name1 = links[i][0]
        url = links[i][1]
        
        # --- API EXTRACTION BLOCK ---
        keys_string = ""
        
        # Classplus / Testbook / Generic DRM
        if any(d in url for d in ["classplusapp", "testbook", "tpv.sr"]):
            try:
                api_url = f"https://shefu-api-final.vercel.app/shefu?url={url}@ITSGOLU_FORCE&user_id={user_id}"
                data = requests.get(api_url, timeout=20).json()
                if "KEYS" in data:
                    url = data.get("MPD")
                    keys_string = " ".join([f"--key {k}" for k in data.get("KEYS", [])])
                elif "url" in data:
                    url = data.get("url")
            except: pass

        # --- FILENAME & UI LOGIC ---
        # Fixed: Use shlex and clean names to prevent Shell Errors
        clean_title = re.sub(r'[^\w\s\-\(\)\[\]]', '', name1).strip()
        final_filename = f"{str(count).zfill(3)}_{clean_title.replace(' ', '_')}"
        
        # Progress Message (Same style as your original logs)
        progress = (count / len(links)) * 100
        status_text = (
            f"<i><b>Downloading Started</b></i>\n"
            f"<blockquote>🚀 **Progress:** {progress:.2f}%</blockquote>\n"
            f"┣ 🔗 **Index:** {count}/{len(links)}\n"
            f"┣ 📚 **Batch:** {b_name}\n"
            f"┣ 📝 **Title:** {name1}\n"
            f"┣ 🍁 **Quality:** {quality_text}\n"
            f"╰━ 🛑 /stop to cancel\n\n"
            f"✦ **Power By:** {CREDIT}"
        )
        prog_msg = await bot.send_message(m.chat.id, status_text)

        # --- DOWNLOAD & UPLOAD LOGIC ---
        try:
            # A. PDF HANDLER
            if ".pdf" in url.lower():
                scraper = cloudscraper.create_scraper()
                response = scraper.get(url)
                with open(f"{final_filename}.pdf", "wb") as f:
                    f.write(response.content)
                await bot.send_document(channel_id, f"{final_filename}.pdf", caption=f"📕 **PDF:** {name1}\n📚 **Batch:** {b_name}")
                os.remove(f"{final_filename}.pdf")

            # B. IMAGE HANDLER
            elif any(ext in url.lower() for ext in [".jpg", ".png", ".jpeg"]):
                scraper = cloudscraper.create_scraper()
                response = scraper.get(url)
                with open(f"{final_filename}.jpg", "wb") as f:
                    f.write(response.content)
                await bot.send_photo(channel_id, f"{final_filename}.jpg", caption=f"🖼 **Image:** {name1}")
                os.remove(f"{final_filename}.jpg")

            # C. VIDEO HANDLER (MPD/M3U8)
            else:
                safe_url = shlex.quote(url)
                safe_out = shlex.quote(f"{final_filename}.mp4")
                
                if ".m3u8" in url or "/hls/" in url:
                    # Generic FFMPEG (Hranker headers removed)
                    cmd = (
                        f'ffmpeg -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 '
                        f'-protocol_whitelist file,http,https,tcp,tls,crypto -i {safe_url} '
                        f'-c copy -bsf:a aac_adtstoasc {safe_out} -y'
                    )
                else:
                    ytf = f"b[height<={res_val}]/bv[height<={res_val}]+ba/b"
                    cmd = f'yt-dlp {keys_string} -f "{ytf}" {safe_url} -o {safe_out}'
                
                os.system(cmd)
                
                if not os.path.exists(f"{final_filename}.mp4"):
                    raise Exception("File not downloaded.")

                # Select Caption Template
                if caption_type == "/cc1":
                    cap = f"🎥 **Video:** `{name1}`\n📂 **Batch:** {b_name}\n✨ **By:** {CR}"
                else:
                    cap = f"✨ **{name1}**\n━━━━━━━━━━━━━━━\n🎬 **Quality:** {res_val}p\n📚 **Course:** {b_name}"

                await bot.send_video(channel_id, f"{final_filename}.mp4", caption=cap, supports_streaming=True)
                os.remove(f"{final_filename}.mp4")

            await prog_msg.delete()
            count += 1

        except Exception as e:
            await bot.send_message(m.chat.id, f"❌ **Failed:** `{name1}`\n`{str(e)[:150]}`")
            count += 1
            continue

    globals.processing_request = False
    await m.reply_text("🏁 **Batch Completed Successfully!**")
