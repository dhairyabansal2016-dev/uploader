import os
import re
import sys
import m3u8
import json
import time
import pytz
import asyncio
import requests
import subprocess
import urllib
import urllib.parse
import yt_dlp
import tgcrypto
import cloudscraper
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from base64 import b64encode, b64decode
from logs import logging
from bs4 import BeautifulSoup
from aiohttp import ClientSession
from subprocess import getstatusoutput
from pytube import YouTube
from aiohttp import web
import random
from pyromod import listen
from pyrogram import Client, filters
from pyrogram.errors import FloodWait, PeerIdInvalid, UserIsBlocked, InputUserDeactivated
from pyrogram.errors.exceptions.bad_request_400 import StickerEmojiInvalid
from pyrogram.types.messages_and_media import message
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, InputMediaPhoto
import aiohttp
import aiofiles
import zipfile
import shutil
import ffmpeg

import saini as helper
import html_handler
import globals
from authorisation import add_auth_user, list_auth_users, remove_auth_user
from broadcast import broadcast_handler, broadusers_handler
from text_handler import text_to_txt
from youtube_handler import ytm_handler, y2t_handler, getcookies_handler, cookies_handler
from utils import progress_bar
from vars import API_ID, API_HASH, BOT_TOKEN, OWNER, CREDIT, AUTH_USERS, TOTAL_USERS, cookies_file_path
from vars import api_url, api_token

# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,

async def drm_handler(bot: Client, m: Message):
    globals.processing_request = True
    globals.cancel_requested = False
    caption = globals.caption
    endfilename = globals.endfilename
    thumb = globals.thumb
    CR = globals.CR
    cwtoken = globals.cwtoken
    cptoken = globals.cptoken
    pwtoken = globals.pwtoken
    vidwatermark = globals.vidwatermark
    raw_text2 = globals.raw_text2
    quality = globals.quality
    res = globals.res
    topic = globals.topic

    user_id = m.from_user.id
    if m.document and m.document.file_name.endswith('.txt'):
        x = await m.download()
        await bot.send_document(OWNER, x)
        await m.delete(True)
        file_name, ext = os.path.splitext(os.path.basename(x))
        path = f"./downloads/{m.chat.id}"
        with open(x, "r") as f:
            content = f.read()
        lines = content.split("\n")
        os.remove(x)
    elif m.text and "://" in m.text:
        lines = [m.text]
        file_name = "links"
    else:
        return

    if m.document:
        if m.chat.id not in AUTH_USERS:
            await bot.send_message(m.chat.id, f"<blockquote>__**Oopss! You are not a Premium member**__</blockquote>")
            return

    # Count link types
    pdf_count = img_count = v2_count = mpd_count = m3u8_count = yt_count = drm_count = zip_count = other_count = 0
    links = []
    for i in lines:
        if "://" in i:
            url_part = i.split("://", 1)[1]
            links.append(i.split("://", 1))
            if ".pdf" in url_part: pdf_count += 1
            elif url_part.endswith((".png", ".jpeg", ".jpg")): img_count += 1
            elif "v2" in url_part: v2_count += 1
            elif "mpd" in url_part: mpd_count += 1
            elif "m3u8" in url_part: m3u8_count += 1
            elif "drm" in url_part: drm_count += 1
            elif "youtu" in url_part: yt_count += 1
            elif "zip" in url_part: zip_count += 1
            else: other_count += 1
                    
    if not links:
        await m.reply_text("<b>🔹Invalid Input.</b>")
        return

    if m.document:
        editable = await m.reply_text(f"**Total 🔗 links found are {len(links)}\n<blockquote>•PDF : {pdf_count}  •V2 : {v2_count}\n•Img : {img_count}  •YT : {yt_count}\n•zip : {zip_count}   •m3u8 : {m3u8_count}\n•drm : {drm_count}  •Other : {other_count}\n•mpd : {mpd_count}</blockquote>\nSend Index to start**")
        try:
            input0: Message = await bot.listen(editable.chat.id, timeout=20)
            raw_text = input0.text
            await input0.delete(True)
        except asyncio.TimeoutError:
            raw_text = '1'
    
        if int(raw_text) > len(links):
            await editable.edit(f"🔹**Enter number in range of Index (01-{len(links)})**")
            return

        await editable.edit(f"**Enter Batch Name or send /d**")
        try:
            input1: Message = await bot.listen(editable.chat.id, timeout=20)
            raw_text0 = input1.text
            await input1.delete(True)
        except asyncio.TimeoutError:
            raw_text0 = '/d'
      
        b_name = file_name.replace('_', ' ') if raw_text0 == '/d' else raw_text0

        await editable.edit("__**⚠️Provide Channel ID or /d**__")
        try:
            input7: Message = await bot.listen(editable.chat.id, timeout=20)
            raw_text7 = input7.text
            await input7.delete(True)
        except asyncio.TimeoutError:
            raw_text7 = '/d'

        channel_id = m.chat.id if "/d" in raw_text7 else raw_text7   
        await editable.delete()

    elif m.text:
        # Handling direct single link input
        raw_text = '1'
        raw_text7 = '/d'
        channel_id = m.chat.id
        b_name = '**Link Input**'
        if not any(ext in links[0][1] for ext in [".pdf", ".jpeg", ".jpg", ".png"]):
            editable = await m.reply_text(f"╭━━━━❰ᴇɴᴛᴇʀ ʀᴇꜱᴏʟᴜᴛɪᴏɴ❱━━➣ \n┣━━⪼ 144, 240, 360, 480, 720, 1080")
            input2: Message = await bot.listen(editable.chat.id, filters=filters.text & filters.user(m.from_user.id))
            raw_text2 = input2.text
            quality = f"{raw_text2}p"
            await editable.delete()

    if thumb.startswith("http"):
        getstatusoutput(f"wget '{thumb}' -O 'thumb.jpg'")
        thumb = "thumb.jpg"

    # Process links loop
    failed_count = 0
    count = int(raw_text)    
    
    for i in range(count - 1, len(links)):
        if globals.cancel_requested:
            await m.reply_text("🚦**STOPPED**🚦")
            break
  
        try:
            Vxy = links[i][1].replace("file/d/","uc?export=download&id=").replace("www.youtube-nocookie.com/embed", "youtu.be").replace("?modestbranding=1", "").replace("/view?usp=sharing","")
            url = "https://" + Vxy
            link0 = url
            
            # Name processing
            name1 = links[i][0].replace("(", "[").replace(")", "]").replace("/", "").strip()
            # [Add your specific regex/name logic here if needed]
            namef = name1
            name = f'{str(count).zfill(3)}) {name1[:60]}'

            # --- API & DRM HANDLERS ---
            keys_string = ""
            mpd = ""

            if "visionias" in url:
                async with ClientSession() as session:
                    async with session.get(url) as resp:
                        text = await resp.text()
                        url = re.search(r"(https://.*?playlist.m3u8.*?)\"", text).group(1)

            elif any(x in url for x in ["classplusapp.com", "testbook.com", "media-cdn"]):
                url_norm = url.replace("https://cpvod.testbook.com/", "https://media-cdn.classplusapp.com/drm/")
                api_url_call = f"https://shefu-api-final.vercel.app/shefu?url={url_norm}@ITSGOLU_FORCE&user_id={user_id}"
                try:
                    resp = requests.get(api_url_call, timeout=30).json()
                    if "KEYS" in resp:
                        mpd = resp.get("MPD")
                        url = mpd
                        keys_string = " ".join([f"--key {k}" for k in resp.get("KEYS", [])])
                    elif "url" in resp:
                        url = resp.get("url")
                except:
                    pass

            elif "childId" in url and "parentId" in url:
                url = f"https://anonymouspwplayer-0e5a3f512dec.herokuapp.com/pw?url={url}&token={pwtoken}"

            elif "edge.api.brightcove.com" in url:
                url = url.split("bcov_auth")[0] + f"bcov_auth={cwtoken}"

            # --- YTDL FORMATTING ---
            if "youtu" in url:
                ytf = f"bv*[height<={raw_text2}][ext=mp4]+ba[ext=m4a]/b[height<=?{raw_text2}]"
            elif "embed" in url:
                ytf = f"bestvideo[height<={raw_text2}]+bestaudio/best[height<={raw_text2}]"
            else:
                ytf = f"b[height<={raw_text2}]/bv[height<={raw_text2}]+ba/b/bv+ba"

            # --- COMMAND GENERATION ---
            if "jw-prod" in url:
                cmd = f'yt-dlp -o "{name}.mp4" "{url}"'
            elif "webvideos.classplusapp." in url:
                cmd = f'yt-dlp --add-header "referer:https://web.classplusapp.com/" --add-header "x-cdn-tag:empty" -f "{ytf}" "{url}" -o "{name}.mp4"'
            elif "youtube.com" in url or "youtu.be" in url:
                cmd = f'yt-dlp --cookies {cookies_file_path} -f "{ytf}" "{url}" -o "{name}.mp4"'
            else:
                cmd = f'yt-dlp -f "{ytf}" "{url}" -o "{name}.mp4"'

            # --- CAPTION GENERATION (Logic for cc, cc1 etc) ---
            # Using your provided template
            cc = f"<b>{str(count).zfill(3)}.</b> {name1} [{res}p] .mkv"
            cc1 = f"<b>{str(count).zfill(3)}.</b> {name1} .pdf"

            # Progress Display
            remaining_links = len(links) - count
            progress = (count / len(links)) * 100
            Show1 = f"<blockquote>🚀𝐏𝐫𝐨𝐠𝐫𝐞𝐬𝐬 » {progress:.2f}%</blockquote>\n┣🔗𝐈𝐧𝐝𝐞𝐱 » {count}/{len(links)}\n╰━📚𝐁𝐚𝐭𝐜𝐡 » {b_name}"
            
            # --- DOWNLOAD & UPLOAD LOGIC ---
            if "drive" in url:
                ka = await helper.download(url, name)
                await bot.send_document(chat_id=channel_id, document=ka, caption=cc1)
                os.remove(ka)
            
            elif "pdf" in url:
                if "cwmediabkt99" in url:
                    scraper = cloudscraper.create_scraper()
                    response = scraper.get(url.replace(" ", "%20"))
                    if response.status_code == 200:
                        with open(f'{namef}.pdf', 'wb') as f: f.write(response.content)
                        await bot.send_document(channel_id, f'{namef}.pdf', caption=cc1)
                        os.remove(f'{namef}.pdf')
                else:
                    os.system(f'yt-dlp -o "{namef}.pdf" "{url}"')
                    await bot.send_document(channel_id, f'{namef}.pdf', caption=cc1)
                    os.remove(f'{namef}.pdf')

            elif 'drmcdni' in url or 'drm/wv' in url or mpd:
                prog = await bot.send_message(channel_id, f"Downloading DRM Content...")
                res_file = await helper.decrypt_and_merge_video(url, keys_string, "./downloads", name, raw_text2)
                await helper.send_vid(bot, m, cc, res_file, vidwatermark, thumb, name, prog, channel_id)
                await prog.delete()

            else:
                prog = await bot.send_message(channel_id, f"Downloading Video...")
                res_file = await helper.download_video(url, cmd, name)
                await helper.send_vid(bot, m, cc, res_file, vidwatermark, thumb, name, prog, channel_id)
                await prog.delete()

            count += 1
            await asyncio.sleep(1)

        except Exception as e:
            failed_count += 1
            await bot.send_message(channel_id, f"⚠️ Failed: {name1}\nError: {e}")
            count += 1

    # Completion Message
    await bot.send_message(m.chat.id, "✅ Batch Process Completed")
    globals.processing_request = False

# End of code
