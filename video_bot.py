import asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import yt_dlp
from smart_reply import FAQ_DATA, get_faq_keyboard, get_related_keyboard

API_TOKEN = '7603502976:AAFLnSmIKK2DPvuqKARRHNZ8kDGF53O665c'

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

REQUIRED_CHANNEL = ''  # e.g. '@WiamPromo'
REQUIRED_GROUP = ''    # e.g. '@WiamGrabbers'

user_links = {}
user_last_reply = {}  # For smart message deduplication

SUPPORTED_SITES = [
    'youtube.com', 'youtu.be',
    'facebook.com',
    'instagram.com',
    'tiktok.com',
    'x.com', 'twitter.com'
]

# === Join Buttons ===
def get_join_buttons():
    kb = InlineKeyboardMarkup(row_width=2)
    if REQUIRED_CHANNEL:
        kb.add(InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{REQUIRED_CHANNEL.lstrip('@')}"))
    if REQUIRED_GROUP:
        kb.add(InlineKeyboardButton("💬 Join Group", url=f"https://t.me/{REQUIRED_GROUP.lstrip('@')}"))
    return kb if REQUIRED_CHANNEL or REQUIRED_GROUP else None

# === Membership Check ===
async def is_user_verified(user_id):
    try:
        if REQUIRED_CHANNEL:
            member = await bot.get_chat_member(REQUIRED_CHANNEL, user_id)
            if member.status in ['left', 'kicked']:
                return False
        if REQUIRED_GROUP:
            member = await bot.get_chat_member(REQUIRED_GROUP, user_id)
            if member.status in ['left', 'kicked']:
                return False
        return True
    except:
        return False

# === /start ===
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    text = "👋 Welcome to WiamGrab!\n\nSend a video link to download (YouTube, Facebook, Instagram, TikTok, Twitter)."
    if REQUIRED_CHANNEL or REQUIRED_GROUP:
        text += "\n\n🔒 You must join our platform before downloading."
    await message.reply(text, reply_markup=get_join_buttons())

# === /help ===
@dp.message_handler(commands=['help'])
async def help_command(message: types.Message):
    await bot.send_chat_action(message.chat.id, action="typing")
    await asyncio.sleep(1.5)
    await message.reply("❓ Tap a question below to learn more:", reply_markup=get_faq_keyboard())

# === Smart Replies ===
@dp.callback_query_handler(lambda c: c.data.startswith("faq:"))
async def handle_faq(call: CallbackQuery):
    question = call.data.split("faq:")[1]
    if question in FAQ_DATA:
        await bot.send_chat_action(call.message.chat.id, action="typing")
        await asyncio.sleep(2)
        answer = FAQ_DATA[question]["answer"]
        await call.message.edit_text("💬 " + answer, reply_markup=get_related_keyboard(question))

# === Smart Keyword Reply System (text not containing links) ===
@dp.message_handler(lambda message: message.text and not any(site in message.text.lower() for site in SUPPORTED_SITES))
async def smart_chat(message: types.Message):
    user_id = message.from_user.id
    text = message.text.lower()
    response = None

    if "mp3" in text or "audio" in text:
        response = "🎵 Yes! After sending the link, tap '🎵 Audio' and I'll convert it to MP3."
    elif "video" in text or "how to" in text:
        response = "📥 Just paste a video link (YouTube, TikTok, etc.) and I’ll handle the download."
    elif "platform" in text or "supported" in text or "site" in text:
        response = "🌐 Supported: YouTube, Facebook, Instagram, TikTok, Twitter."
    elif "error" in text or "not working" in text or "failed" in text:
        response = "⚠️ Make sure the link is public and valid. If it keeps failing, try a different one."
    elif "group" in text or "join" in text:
        response = "🔒 Joining is required only during promotions. You'll see Join buttons if needed."
    elif "which link" in text or "what link" in text:
        response = "📎 You can send any link from YouTube, TikTok, Facebook, Instagram, or Twitter."
    elif "something" in text or "start" in text or "what can you do" in text:
        response = "🤖 Just send me a link from any video platform I support, and I’ll help you download it."
    elif "hello" in text or "hi" in text:
        response = "👋 Hey there! Just send a video link or ask me something."
    else:
        response = "🤖 I'm not sure how to help with that. Type /help or paste a video link to begin."

    # Prevent spamming same response
    if user_last_reply.get(user_id) != response:
        user_last_reply[user_id] = response
        await message.reply(response)

# === Handle Video/Audio Download ===
@dp.message_handler()
async def handle_message(message: types.Message):
    user_id = message.from_user.id
    link = message.text.strip()

    if not any(site in link for site in SUPPORTED_SITES):
        await message.reply("❌ Only YouTube, Facebook, Instagram, TikTok, or Twitter links are supported.")
        return

    if REQUIRED_CHANNEL or REQUIRED_GROUP:
        if not await is_user_verified(user_id):
            await message.reply("🚫 You must join first to use this bot.", reply_markup=get_join_buttons())
            return

    user_links[user_id] = link
    await message.reply(
        "What do you want to download?",
        reply_markup=InlineKeyboardMarkup().add(
            InlineKeyboardButton("🎥 Video", callback_data="download_video"),
            InlineKeyboardButton("🎵 Audio", callback_data="download_audio")
        )
    )

# === Process Download ===
@dp.callback_query_handler(lambda c: c.data in ["download_video", "download_audio"])
async def handle_download(call: CallbackQuery):
    user_id = call.from_user.id
    format_type = call.data.split("_")[1]
    link = user_links.get(user_id)

    if not link:
        await call.message.edit_text("❌ Please send a video link first.")
        return

    if REQUIRED_CHANNEL or REQUIRED_GROUP:
        if not await is_user_verified(user_id):
            await call.message.edit_text("🚫 You must join first to use this bot.", reply_markup=get_join_buttons())
            return

    await call.message.edit_text("⏳ Downloading...")

    ydl_opts = {
        'outtmpl': f'{user_id}_%(title).80s.%(ext)s',
        'quiet': True,
        'noplaylist': True,
        'prefer_ffmpeg': True,
    }

    if format_type == "video":
        ydl_opts.update({
            'format': 'mp4',
            'merge_output_format': 'mp4',
        })
    else:
        ydl_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
        })

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(link, download=True)
            filename = ydl.prepare_filename(info)

        if format_type == "audio":
            filename = filename.rsplit('.', 1)[0] + ".mp3"

        with open(filename, 'rb') as f:
            if format_type == "video":
                await bot.send_video(chat_id=user_id, video=f, caption="✅ Done!")
            else:
                await bot.send_audio(chat_id=user_id, audio=f, title=info.get("title", "Audio"))

        os.remove(filename)

    except Exception as e:
        await call.message.edit_text(f"❌ Error: {str(e)}")

# === Start Bot ===
if __name__ == '__main__':
    print("🚀 Bot is running...")
    executor.start_polling(dp)
