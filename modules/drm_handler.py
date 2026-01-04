import os
import asyncio
import time
import cloudscraper
import re
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait
import globals
import saini as helper
from vars import AUTH_USERS, OWNER, cookies_file_path

# --- CONFIGURATION ---
MAX_CONCURRENT_TASKS = 2  # Limits concurrent downloads/uploads
semaphore = asyncio.Semaphore(MAX_CONCURRENT_TASKS)

async def process_single_link(bot, m, link_data, count, total_links, channel_id, b_name, metadata):
    """
    Handles the complete lifecycle of one link in the background.
    """
    async with semaphore:
        if globals.cancel_requested:
            return "skipped"

        try:
            # 1. Extract Metadata
            raw_text2 = metadata['raw_text2']
            pwtoken = metadata['pwtoken']
            res = metadata['res']
            thumb = metadata['thumb']
            vidwatermark = metadata['vidwatermark']
            CR = metadata['CR']
            caption_type = metadata['caption_type']

            # 2. URL & Name Formatting
            Vxy = link_data[1].replace("file/d/","uc?export=download&id=").replace("www.youtube-nocookie.com/embed", "youtu.be")
            url = "https://" + Vxy
            name1 = link_data[0].strip()
            name = f'{str(count).zfill(3)}) {name1[:60]}'

            # 3. Handler Logic (PW, Classplus, etc.)
            if "childId" in url and "parentId" in url:
                url = f"https://anonymouspwplayer-0e5a3f512dec.herokuapp.com/pw?url={url}&token={pwtoken}"
            
            # ytf format string
            ytf = f"b[height<={raw_text2}]/bv[height<={raw_text2}]+ba/b/bv+ba"

            # 4. Command Generation
            if "webvideos.classplusapp." in url:
                cmd = f'yt-dlp --add-header "referer:https://web.classplusapp.com/" --add-header "x-cdn-tag:empty" -f "{ytf}" "{url}" -o "{name}.mp4"'
            elif "youtu" in url:
                cmd = f'yt-dlp --cookies {cookies_file_path} -f "{ytf}" "{url}" -o "{name}.mp4"'
            else:
                cmd = f'yt-dlp -f "{ytf}" "{url}" -o "{name}.mp4"'

            # 5. Progress Notification
            prog = await bot.send_message(channel_id, f"📥 **Downloading ({count}/{total_links})**\n<blockquote>{name1}</blockquote>")

            # 6. Captions Logic
            if caption_type == "/cc1":
                cc = f'[🎥]Vid Id : {str(count).zfill(3)}\n**Video Title :** `{name1} [{res}p].mkv`\n<blockquote><b>Batch Name : {b_name}</b></blockquote>\n\n**Extracted by➤**{CR}'
                cc1 = f'[📕]Pdf Id : {str(count).zfill(3)}\n**File Title :** `{name1}.pdf`\n<blockquote><b>Batch Name : {b_name}</b></blockquote>'
            else:
                cc = f'<b>{str(count).zfill(3)}.</b> {name1} [{res}p] .mkv'
                cc1 = f'<b>{str(count).zfill(3)}.</b> {name1} .pdf'

            # 7. Execution (Download & Upload)
            if "pdf" in url:
                os.system(f'yt-dlp -o "{name}.pdf" "{url}"')
                await bot.send_document(channel_id, f"{name}.pdf", caption=cc1)
                if os.path.exists(f"{name}.pdf"): os.remove(f"{name}.pdf")
            else:
                res_file = await helper.download_video(url, cmd, name)
                # Helper sends the video to the channel
                await helper.send_vid(bot, m, cc, res_file, vidwatermark, thumb, name, prog, channel_id)

            await prog.delete()
            return True

        except Exception as e:
            await bot.send_message(channel_id, f"❌ **Failed {count}:** {name1}\n`{str(e)}`")
            return False

async def drm_handler(bot: Client, m: Message):
    globals.processing_request = True
    globals.cancel_requested = False
    
    # --- Input Processing ---
    if m.document and m.document.file_name.endswith('.txt'):
        x = await m.download()
        with open(x, "r") as f:
            lines = f.read().split("\n")
        os.remove(x)
        file_name = m.document.file_name.rsplit('.', 1)[0]
    elif m.text and "://" in m.text:
        lines = [m.text]
        file_name = "Link_Input"
    else: return

    links = [line.split("://", 1) for line in lines if "://" in line]
    if not links: return

    # --- Interactive Prompts ---
    editable = await m.reply_text(f"**Found {len(links)} links.**\nSend Start Index (usually 1):")
    try:
        input_idx = await bot.listen(m.chat.id, timeout=30)
        start_index = int(input_idx.text)
        await input_idx.delete()
    except: start_index = 1

    await editable.edit("**Enter Batch Name:**")
    try:
        input_bn = await bot.listen(m.chat.id, timeout=30)
        b_name = input_bn.text
        await input_bn.delete()
    except: b_name = file_name

    await editable.edit("**Send Channel ID or /d:**")
    try:
        input_ch = await bot.listen(m.chat.id, timeout=30)
        channel_id = m.chat.id if input_ch.text == "/d" else input_ch.text
        await input_ch.delete()
    except: channel_id = m.chat.id

    await editable.delete()

    # --- Metadata Package ---
    metadata = {
        'raw_text2': globals.raw_text2,
        'pwtoken': globals.pwtoken,
        'res': globals.res,
        'thumb': globals.thumb,
        'vidwatermark': globals.vidwatermark,
        'CR': globals.CR,
        'caption_type': globals.caption # /cc1 or /cc2
    }

    # --- Parallel Queue Execution ---
    tasks = []
    # Create tasks for all links from start_index to end
    for i in range(start_index - 1, len(links)):
        task = asyncio.create_task(
            process_single_link(bot, m, links[i], i + 1, len(links), channel_id, b_name, metadata)
        )
        tasks.append(task)

    

    # Run everything!
    results = await asyncio.gather(*tasks)

    # --- Final Stats ---
    success = results.count(True)
    failed = results.count(False)
    
    summary = (
        "<b>-┈━═.•°✅ Completed ✅°•.═━┈-</b>\n"
        f"<blockquote><b>🎯 Batch: {b_name}</b></blockquote>\n"
        f"🔗 Total URLs: {len(links)}\n"
        f"🟢 Success: {success}\n"
        f"🔴 Failed: {failed}"
    )
    await bot.send_message(m.chat.id, summary)
    globals.processing_request = False
