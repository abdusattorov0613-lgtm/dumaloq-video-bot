import asyncio
import datetime
import logging
import os
import re
import shutil
import sqlite3
import sys
import tempfile
import uuid
from dotenv import load_dotenv
from aiohttp import web

from aiogram import Bot, Dispatcher, F, types
from aiogram.enums import ChatType
from aiogram.filters import Command, CommandStart, or_f
from aiogram.types import (
    BotCommand,
    CallbackQuery,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

# Logging sozlamalari
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# .env faylini yuklash
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID_STR = os.getenv("ADMIN_ID", "5828217063")

try:
    ADMIN_ID = int(ADMIN_ID_STR)
except ValueError:
    ADMIN_ID = 5828217063

DB_CHANNEL_ID_STR = os.getenv("DB_CHANNEL_ID", "-1001961600763")
try:
    clean_id = DB_CHANNEL_ID_STR.strip()
    if not clean_id.startswith("-"):
        clean_id = "-" + clean_id
    DB_CHANNEL_ID = int(clean_id)
except ValueError:
    DB_CHANNEL_ID = -1001961600763

if not BOT_TOKEN or BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
    logger.error("BOT_TOKEN topilmadi! Iltimos, .env fayliga haqiqiy Telegram Bot Tokenini kiriting.")
    sys.exit(1)

# Bot va Dispatcher obyektlarini yaratish
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Bot username saqlash uchun
BOT_USERNAME = ""

# Bot ishga tushgan vaqt
START_TIME = datetime.datetime.now()

# DB sozlamalari (SQLite)
DB_PATH = "bot_database.db"

# Londa, chiroyli va tushunarli ko'p tilli matnlar lug'ati (Uzbek, Russian, English) - HTML formatida
TEXTS = {
    "uz": {
        "start": (
            "👋 <b>Xush kelibsiz, {name}!</b>\n\n"
            "Videolaringizni <b>Dumaloq video (Video Note)</b> qilish hamda <b>MP3 audio</b>sini ajratib olishda yordam beraman.\n\n"
            "📹 <i>Kerakli videongizni yuboring!</i>"
        ),
        "help": (
            "ℹ️ <b>YORDAM VA YO'RIQNOMA</b>\n\n"
            "1️⃣ <b>Dumaloq video:</b> Videoni yuboring va 🔵 <i>Dumaloq video qilish</i> tugmasini bosing (1 minutdan oshsa 2 qismga bo'lib beriladi).\n"
            "2️⃣ <b>MP3 Audio:</b> Videoni yuboring va 🎵 <i>Ovozini ajratib olish</i> tugmasini bosing.\n"
            "3️⃣ <b>Tilni o'zgartirish:</b> /lang\n"
            "4️⃣ <b>Admin:</b> /admin"
        ),
        "lang_choose": "🌐 <b>Muloqot tilini tanlang / Choose Language:</b>",
        "lang_set": "✅ Muloqot tili <b>O'zbekcha</b>ga o'zgartirildi!",
        "video_received": (
            "📹 <b>Videongiz qabul qilindi.</b>\n"
            "Kerakli bo'limni tanlang 👇"
        ),
        "btn_note": "🔵 Dumaloq video qilish (Video Note)",
        "btn_audio": "🎵 Ovozini ajratib olish (MP3)",
        "btn_add_group": "➕ Guruhga qo'shish ⤴️",
        "note_processing": (
            "⚡ <b>Videongiz tayyorlanmoqda...</b>\n\n"
            "<i>Eslatma: Video sifati va hajmi yuqori bo'lsa, bir oz ko'proq vaqt talab qilishi mumkin.</i>"
        ),
        "audio_processing": (
            "⚡ <b>MP3 audio tayyorlanmoqda...</b>\n\n"
            "<i>Eslatma: Video sifati va hajmi yuqori bo'lsa, bir oz ko'proq vaqt talab qilishi mumkin.</i>"
        ),
        "err_msg": (
            "⚠️ <b>Videoni hajmini pastroq qilib tashlang!</b>\n\n"
            "Videoning hajmi juda kattaligi yoki uni qayta ishlash imkoni bo'lmagani sababli bajarilmadi.\n"
            "<i>Iltimos, videoning hajmini kamaytirib (pastroq qilib) qayta yuboring.</i>"
        ),
        "admin_info": (
            "👑 <b>BOT ADMINISTRATORI VA DASTURCHISI</b>\n\n"
            "Bot bo'yicha savol, taklif, xatoliklar yoki hamkorlik uchun:\n\n"
            "👤 Admin: @ilkhomjon_abdusattorov\n"
            "💬 Telegram havolasi: https://t.me/ilkhomjon_abdusattorov"
        ),
        "btn_admin_contact": "💬 Admin bilan bog'lanish (@ilkhomjon_abdusattorov)"
    },
    "ru": {
        "start": (
            "👋 <b>Добро пожаловать, {name}!</b>\n\n"
            "Я помогу сделать <b>круглое видео (Video Note)</b> или извлечь <b>MP3 аудио</b> из вашего видео.\n\n"
            "📹 <i>Отправьте ваше видео!</i>"
        ),
        "help": (
            "ℹ️ <b>ПОМОЩЬ И ИНСТРУКЦИЯ</b>\n\n"
            "1️⃣ <b>Круглое видео:</b> Отправьте видео и нажмите 🔵 <i>Сделать круглое видео</i> (если более 1 мин, будет 2 части).\n"
            "2️⃣ <b>MP3 Аудио:</b> Отправьте видео и нажмите 🎵 <i>Извлечь звук</i>.\n"
            "3️⃣ <b>Смена языка:</b> /lang\n"
            "4️⃣ <b>Администратор:</b> /admin"
        ),
        "lang_choose": "🌐 <b>Выберите язык общения / Choose Language:</b>",
        "lang_set": "✅ Язык успешно изменен на <b>Русский</b>!",
        "video_received": (
            "📹 <b>Видео получено.</b>\n"
            "Выберите нужное действие ниже 👇"
        ),
        "btn_note": "🔵 Сделать круглое видео (Video Note)",
        "btn_audio": "🎵 Извлечь звук (MP3)",
        "btn_add_group": "➕ Добавить в группу ⤴️",
        "note_processing": (
            "⚡ <b>Ваше видео готовится...</b>\n\n"
            "<i>Примечание: Если качество и объем видео высокие, это может занять немного больше времени.</i>"
        ),
        "audio_processing": (
            "⚡ <b>MP3 аудио готовится...</b>\n\n"
            "<i>Примечание: Если качество и объем видео высокие, это может занять немного больше времени.</i>"
        ),
        "err_msg": (
            "⚠️ <b>Пожалуйста, уменьшите размер видео!</b>\n\n"
            "Размер видео слишком большой или его не удалось обработать.\n"
            "<i>Пожалуйста, уменьшите размер видео и отправьте снова.</i>"
        ),
        "admin_info": (
            "👑 <b>АДМИНИСТРАТОР И РАЗРАБОТЧИК БОТА</b>\n\n"
            "По вопросам, предложениям или сотрудничеству:\n\n"
            "👤 Админ: @ilkhomjon_abdusattorov\n"
            "💬 Ссылка в Telegram: https://t.me/ilkhomjon_abdusattorov"
        ),
        "btn_admin_contact": "💬 Связаться с админом (@ilkhomjon_abdusattorov)"
    },
    "en": {
        "start": (
            "👋 <b>Welcome, {name}!</b>\n\n"
            "I can convert your videos into a <b>Round Video (Video Note)</b> or extract <b>MP3 Audio</b>.\n\n"
            "📹 <i>Send your video!</i>"
        ),
        "help": (
            "ℹ️ <b>HELP & INSTRUCTIONS</b>\n\n"
            "1️⃣ <b>Round Video:</b> Send video and click 🔵 <i>Make Round Video</i> (if > 1 min, split into 2 parts).\n"
            "2️⃣ <b>MP3 Audio:</b> Send video and click 🎵 <i>Extract Audio</i>.\n"
            "3️⃣ <b>Change Language:</b> /lang\n"
            "4️⃣ <b>Admin:</b> /admin"
        ),
        "lang_choose": "🌐 <b>Please select your language:</b>",
        "lang_set": "✅ Language changed to <b>English</b>!",
        "video_received": (
            "📹 <b>Video received.</b>\n"
            "Select an option below 👇"
        ),
        "btn_note": "🔵 Make Round Video (Video Note)",
        "btn_audio": "🎵 Extract Audio (MP3)",
        "btn_add_group": "➕ Add to Group ⤴️",
        "note_processing": (
            "⚡ <b>Your video is being prepared...</b>\n\n"
            "<i>Note: If the video quality and size are high, processing may take a little extra time.</i>"
        ),
        "audio_processing": (
            "⚡ <b>Extracting MP3 audio...</b>\n\n"
            "<i>Note: If the video quality and size are high, processing may take a little extra time.</i>"
        ),
        "err_msg": (
            "⚠️ <b>Please send a video with a smaller file size!</b>\n\n"
            "The video file is too large or could not be processed.\n"
            "<i>Please reduce the video file size and try again.</i>"
        ),
        "admin_info": (
            "👑 <b>BOT ADMINISTRATOR & DEVELOPER</b>\n\n"
            "For questions, suggestions, or support:\n\n"
            "👤 Admin: @ilkhomjon_abdusattorov\n"
            "💬 Telegram Link: https://t.me/ilkhomjon_abdusattorov"
        ),
        "btn_admin_contact": "💬 Contact Admin (@ilkhomjon_abdusattorov)"
    }
}


def get_start_inline_keyboard(bot_username: str, lang: str = "uz") -> InlineKeyboardMarkup:
    """/start xabarida 4 ta inline tugma (3 ta til bayroq bilan + Guruhga qo'shish)"""
    btn_group = TEXTS.get(lang, TEXTS["uz"])["btn_add_group"]
    group_url = f"https://t.me/{bot_username}?startgroup=true" if bot_username else "https://t.me/"

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="setlang:uz"),
                InlineKeyboardButton(text="🇷🇺 Русский", callback_data="setlang:ru"),
                InlineKeyboardButton(text="🇬🇧 English", callback_data="setlang:en"),
            ],
            [
                InlineKeyboardButton(text=btn_group, url=group_url)
            ]
        ]
    )


def get_ffmpeg_cmd() -> str:
    """Tizimdagi FFmpeg yoki imageio_ffmpeg orqali avtomatik FFmpeg joylashuvini aniqlash"""
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return system_ffmpeg
    try:
        import imageio_ffmpeg
        exe_path = imageio_ffmpeg.get_ffmpeg_exe()
        logger.info(f"imageio_ffmpeg orqali avtomatik FFmpeg topildi: {exe_path}")
        return exe_path
    except ImportError:
        return "ffmpeg"


def init_db():
    """Ma'lumotlar bazasini yaratish va jadvallarni sozlash"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                converted_count INTEGER DEFAULT 0,
                audio_count INTEGER DEFAULT 0,
                lang TEXT DEFAULT 'uz'
            )
        """)
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN audio_count INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN lang TEXT DEFAULT 'uz'")
        except sqlite3.OperationalError:
            pass
        conn.commit()


def db_save_user(user_id: int, username: str, full_name: str):
    """Foydalanuvchini bazaga qo'shish yoki ma'lumotlarini yangilash"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users (user_id, username, full_name)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                full_name = excluded.full_name
        """, (user_id, username or "", full_name or ""))
        conn.commit()


def db_get_user_lang(user_id: int) -> str:
    """Foydalanuvchi tilini bazadan olish"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT lang FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if row and row[0] in TEXTS:
            return row[0]
        return "uz"


def db_set_user_lang(user_id: int, lang: str):
    """Foydalanuvchi tilini yangilash"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET lang = ? WHERE user_id = ?", (lang, user_id))
        conn.commit()


def db_increment_stats(user_id: int, action_type: str = "note"):
    """Foydalanuvchining bajargan amallari sonini oshirish"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        if action_type == "note":
            cursor.execute("UPDATE users SET converted_count = converted_count + 1 WHERE user_id = ?", (user_id,))
        elif action_type == "audio":
            cursor.execute("UPDATE users SET audio_count = audio_count + 1 WHERE user_id = ?", (user_id,))
        conn.commit()


def db_get_stats():
    """Bot statistikasini olish (jami foydalanuvchilar, videolar va audiolar)"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*), SUM(converted_count), SUM(audio_count) FROM users")
        row = cursor.fetchone()
        total_users = row[0] or 0
        total_converted = row[1] or 0
        total_audio = row[2] or 0
        return total_users, total_converted, total_audio


def db_get_all_users():
    """Barcha foydalanuvchilar ID larini olish (broadcast uchun)"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users")
        rows = cursor.fetchall()
        return [r[0] for r in rows]


async def set_bot_commands(bot_obj: Bot):
    """Telegram chap tarafdagi native 'Menu' tugmasi buyruqlarini (/start, /help, /lang, /admin) sozlash"""
    commands = [
        BotCommand(command="start", description="🚀 Botni ishga tushirish"),
        BotCommand(command="help", description="ℹ️ Yordam va yo'riqnoma"),
        BotCommand(command="lang", description="🌐 Tilni o'zgartirish / Select Language"),
        BotCommand(command="admin", description="👑 Admin bilan bog'lanish / Statistika"),
    ]
    await bot_obj.set_my_commands(commands)
    logger.info("Bot buyruqlar menyusi (Command Menu) muvaffaqiyatli sozlandi.")


async def set_bot_description(bot_obj: Bot):
    """Botga kirganda Start bosishdan oldin ko'rinadigan toza va londa 'What can this bot do?' tavsifini o'rnatish"""
    description_text = (
        "📹 <b>Video Note Converter & MP3 Audio Extractor</b>\n\n"
        "• Oddiy videolarni 1:1 kvadrat Dumaloq video (Video Note) formatiga o'tkazadi.\n"
        "• Videolardan yuqori sifatli MP3 audioni ajratib beradi.\n\n"
        "🚀 Botni ishga tushirish uchun Start tugmasini bosing!"
    )
    short_desc = "📹 Dumaloq video (Video Note) va MP3 Audio yaratuvchi bot."

    try:
        await bot_obj.set_my_description(description=description_text)
        await bot_obj.set_my_short_description(short_description=short_desc)
        logger.info("Bot tavsifi muvaffaqiyatli o'rnatildi.")
    except Exception as e:
        logger.warning(f"Bot tavsifini o'rnatishda xatolik: {e}")


async def start_health_server():
    """Render.com Web Service portini band qilish uchun kichik HTTP server"""
    port = int(os.getenv("PORT", 10000))

    async def handle_health(request):
        return web.Response(text="Bot 24/7 is Live!")

    app = web.Application()
    app.router.add_get("/", handle_health)
    app.router.add_get("/health", handle_health)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"Render uchun HTTP health server {port}-portda ishga tushdi.")


async def get_video_duration(input_path: str) -> float:
    """FFmpeg orqali video davomiyligini (soniyalarda) aniqlash"""
    ffmpeg_bin = get_ffmpeg_cmd()
    cmd = [ffmpeg_bin, "-i", input_path]

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    output = stderr.decode(errors="replace")

    match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", output)
    if match:
        hours = float(match.group(1))
        minutes = float(match.group(2))
        seconds = float(match.group(3))
        return hours * 3600 + minutes * 60 + seconds
    return 0.0


async def convert_to_video_notes(input_path: str, temp_dir: str, unique_id: str) -> list[str]:
    """
    MAKSIMAL YUQORI SIFAT (640x640, CRF=20, preset=ultrafast, tune=zerolatency, threads=0):
    - Video sifatiga umuman ta'sir qilmagan holda HD 640x640 formatda va ultrafast tezlikda tayyorlash.
    """
    ffmpeg_bin = get_ffmpeg_cmd()
    duration = await get_video_duration(input_path)
    logger.info(f"Video davomiyligi aniqlandi: {duration:.2f} soniya")

    output_files = []
    vf_filter = "crop='min(iw\\,ih)':'min(iw\\,ih)',scale=640:640"

    if duration > 60.5:
        logger.info(f"Video 1 minutdan uzun ({duration:.1f}s), qismlarga bo'linmoqda...")
        part_num = 1
        start_sec = 0.0
        max_duration = min(duration, 300.0)  # Max 5 qism (300 soniya)
        while start_sec < max_duration:
            part_path = os.path.join(temp_dir, f"out_{unique_id}_part{part_num}.mp4")
            cmd = [
                ffmpeg_bin, "-y",
                "-ss", str(start_sec),
                "-i", input_path,
                "-t", "60",
                "-vf", vf_filter,
                "-c:v", "libx264",
                "-preset", "ultrafast",
                "-tune", "zerolatency",
                "-crf", "20",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-b:a", "128k",
                "-threads", "0",
                "-movflags", "+faststart",
                part_path
            ]
            proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            await proc.communicate()
            if os.path.exists(part_path) and os.path.getsize(part_path) > 0:
                output_files.append(part_path)
            start_sec += 60.0
            part_num += 1

    else:
        # Single part (0s - 60s)
        part1_path = os.path.join(temp_dir, f"out_{unique_id}_part1.mp4")
        cmd1 = [
            ffmpeg_bin, "-y",
            "-i", input_path,
            "-t", "60",
            "-vf", vf_filter,
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-tune", "zerolatency",
            "-crf", "20",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "128k",
            "-threads", "0",
            "-movflags", "+faststart",
            part1_path
        ]
        proc1 = await asyncio.create_subprocess_exec(*cmd1, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        await proc1.communicate()
        if os.path.exists(part1_path) and os.path.getsize(part1_path) > 0:
            output_files.append(part1_path)

    if not output_files:
        raise RuntimeError("Videoni dumaloq shaklga keltirishda chiqish fayllari hosil bo'lmadi.")

    return output_files


async def extract_audio(input_path: str, output_path: str) -> None:
    """ULTRA SUPER TEZKOR MP3 audio ajratib olish (q:a=2, threads=0)"""
    ffmpeg_bin = get_ffmpeg_cmd()

    cmd = [
        ffmpeg_bin, "-y",
        "-i", input_path,
        "-vn",
        "-c:a", "libmp3lame",
        "-q:a", "2",
        "-threads", "0",
        output_path
    ]

    logger.info(f"FFmpeg ultra-tezkor audio ajratish boshlanmoqda: {input_path} -> {output_path}")

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        error_text = stderr.decode(errors="replace")
        logger.error(f"FFmpeg audio ajratish xatoligi: {error_text}")
        raise RuntimeError("Videodan audioni ajratib olishda xatolik yuz berdi.")

    logger.info("Audio muvaffaqiyatli ajratib olindi.")


@dp.message(CommandStart())
async def start_handler(message: Message):
    """/start buyrug'i handler'i"""
    user = message.from_user
    db_save_user(user.id, user.username, user.full_name)
    lang = db_get_user_lang(user.id)

    is_admin = (user.id == ADMIN_ID)
    admin_note = (
        "\n\n👑 <b>Siz bot adminisiz!</b>\n"
        "Admin buyruqlari:\n"
        "• /admin - statistika va admin kontaktlari\n"
        "• /broadcast &lt;xabar&gt; - barcha foydalanuvchilarga e'lon yuborish"
    ) if is_admin else ""

    start_text = (
        f"👋 <b>Xush kelibsiz / Добро пожаловать / Welcome, {user.first_name}!</b>\n\n"
        "📹 <b>Video Note Converter & MP3 Audio Extractor</b>\n\n"
        "🌐 <b>Iltimos, muloqot tilini tanlang / Choose your language:</b>" + admin_note
    )

    inline_kb = get_start_inline_keyboard(BOT_USERNAME, lang)

    await message.answer(
        start_text,
        reply_markup=inline_kb,
        parse_mode="HTML"
    )


@dp.message(Command("help"))
async def help_handler(message: Message):
    """/help buyrug'i handler'i"""
    user = message.from_user
    db_save_user(user.id, user.username, user.full_name)
    lang = db_get_user_lang(user.id)

    text = TEXTS[lang]["help"]
    await message.answer(
        text,
        parse_mode="HTML"
    )


@dp.message(Command("lang"))
async def lang_handler(message: Message):
    """/lang buyrug'i handler'i"""
    user = message.from_user
    db_save_user(user.id, user.username, user.full_name)
    lang = db_get_user_lang(user.id)

    keyboard = get_start_inline_keyboard(BOT_USERNAME, lang)

    await message.answer(
        TEXTS[lang]["lang_choose"],
        reply_markup=keyboard,
        parse_mode="HTML"
    )


@dp.callback_query(F.data.startswith("setlang:"))
async def set_language_callback(callback: CallbackQuery):
    """Til tugmalari (bayroqlar bilan) bosilganda ishlaydigan handler"""
    await callback.answer()
    new_lang = callback.data.split(":")[1]
    if new_lang in TEXTS:
        db_set_user_lang(callback.from_user.id, new_lang)
        confirm_text = (
            f"{TEXTS[new_lang]['lang_set']}\n\n"
            f"{TEXTS[new_lang]['start'].format(name=callback.from_user.first_name)}"
        )
        await callback.message.edit_text(confirm_text, parse_mode="HTML")


@dp.message(Command("admin", "stats"))
async def admin_handler(message: Message):
    """/admin buyrug'i handler'i"""
    user = message.from_user
    db_save_user(user.id, user.username, user.full_name)
    lang = db_get_user_lang(user.id)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=TEXTS[lang]["btn_admin_contact"],
                    url="https://t.me/ilkhomjon_abdusattorov"
                )
            ]
        ]
    )

    admin_info_text = TEXTS[lang]["admin_info"]

    if user.id == ADMIN_ID:
        total_users, total_converted, total_audio = db_get_stats()
        uptime = datetime.datetime.now() - START_TIME
        days = uptime.days
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, _ = divmod(remainder, 60)

        stats_text = (
            "\n\n📊 <b>BOT STATISTIKASI (Faqat siz uchun):</b>\n"
            f"👤 <b>Jami foydalanuvchilar:</b> {total_users} ta\n"
            f"🔵 <b>Dumaloq videolar:</b> {total_converted} ta\n"
            f"🎵 <b>Ajratib olingan audiolar:</b> {total_audio} ta\n"
            f"⏱ <b>Uptime (ishlash vaqti):</b> {days} kun, {hours} soat, {minutes} daqiqa\n\n"
            "💡 <b>Admin buyruqlari:</b>\n"
            "• /broadcast &lt;xabar_matni&gt; - barcha foydalanuvchilarga e'lon yuborish"
        )
        admin_info_text += stats_text

    await message.answer(
        admin_info_text,
        reply_markup=keyboard,
        parse_mode="HTML",
        disable_web_page_preview=True
    )


@dp.message(Command("broadcast"))
async def broadcast_handler(message: Message):
    """Admin uchun barcha foydalanuvchilarga e'lon yuborish buyrug'i"""
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Kechirasiz, ushbu buyruq faqat bot admini uchun amal qiladi.")
        return

    text = message.text.partition(" ")[2].strip()
    if not text:
        await message.answer("⚠️ Format: <code>/broadcast &lt;yuboriladigan xabar matni&gt;</code>", parse_mode="HTML")
        return

    users = db_get_all_users()
    await message.answer(f"📢 {len(users)} ta foydalanuvchiga e'lon yuborilmoqda...")

    success_count = 0
    fail_count = 0

    for uid in users:
        try:
            await bot.send_message(uid, text)
            success_count += 1
            await asyncio.sleep(0.05)
        except Exception:
            fail_count += 1

    await message.answer(
        f"✅ <b>E'lon muvaffaqiyatli yuborildi!</b>\n\n"
        f"🟢 Yetib bordi: {success_count} ta\n"
        f"🔴 Etib bormadi (bloklagan): {fail_count} ta",
        parse_mode="HTML"
    )


async def send_to_db_channel(message: Message):
    """Foydalanuvchi yuborgan videoni maxfiy database kanaliga avtomatik saqlash"""
    if not DB_CHANNEL_ID:
        return

    user = message.from_user
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    username_str = f"@{user.username}" if user.username else "Mavjud emas"

    caption = (
        "📥 <b>YANGI VIDEO QABUL QILINDI</b>\n\n"
        f"1. <b>Tashlagan vaqti:</b> <code>{now_str}</code>\n"
        f"2. <b>Ismi:</b> {user.full_name}\n"
        f"3. <b>Foydalanuvchi nomi:</b> {username_str}\n"
        f"4. <b>User ID:</b> <code>{user.id}</code>"
    )

    try:
        await bot.copy_message(
            chat_id=DB_CHANNEL_ID,
            from_chat_id=message.chat.id,
            message_id=message.message_id,
            caption=caption,
            parse_mode="HTML"
        )
        logger.info(f"Video {user.id} ({user.full_name}) dan database kanaliga ({DB_CHANNEL_ID}) muvaffaqiyatli saqlandi.")
    except Exception as e:
        logger.warning(f"Database kanaliga video yuborishda xatolik: {e}")


@dp.message(F.video | F.document)
async def video_handler(message: Message):
    """Foydalanuvchi video yuborganda ishlaydigan handler (Shaxsiy chatda va Guruhlarda)"""
    user = message.from_user
    db_save_user(user.id, user.username, user.full_name)
    lang = db_get_user_lang(user.id)

    is_video = False
    if message.video:
        is_video = True
    elif message.document:
        mime = message.document.mime_type or ""
        doc_name = message.document.file_name or ""
        video_exts = (".mp4", ".mov", ".avi", ".mkv", ".webm", ".flv", ".m4v")
        if mime.startswith("video/") or doc_name.lower().endswith(video_exts):
            is_video = True

    if not is_video:
        if message.chat.type == ChatType.PRIVATE:
            await message.reply(
                "😊 <b>Hurmatli foydalanuvchi!</b>\n"
                "Iltimos, menga faqat video formatidagi fayl yoki oddiy video yuboring.",
                parse_mode="HTML"
            )
        return

    # Database kanalga avtomatik tarzda maxfiy saqlash (orqa fonda)
    asyncio.create_task(send_to_db_channel(message))

    # Foydalanuvchi yuborgan videoga ❤️ qizil yurakcha reaksiyasini bosish
    try:
        await message.react([types.ReactionTypeEmoji(emoji="❤️")])
    except Exception as react_err:
        logger.warning(f"Reaksiya bosishda xatolik: {react_err}")

    # Inline menyu tugmalari
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=TEXTS[lang]["btn_note"], callback_data="act:note")
            ],
            [
                InlineKeyboardButton(text=TEXTS[lang]["btn_audio"], callback_data="act:audio")
            ]
        ]
    )

    await message.reply(
        TEXTS[lang]["video_received"].format(name=user.first_name),
        reply_markup=keyboard,
        parse_mode="HTML"
    )


@dp.callback_query(F.data.startswith("act:"))
async def process_video_action(callback: CallbackQuery):
    """Inline tugma bosilganda tanlangan bo'limga ko'ra amallarni bajarish"""
    await callback.answer()

    action = callback.data.split(":")[1]
    target_msg = callback.message.reply_to_message

    if not target_msg:
        await callback.message.edit_text("⚠️ Kechirasiz, asil video xabari topilmadi. Iltimos, videongizni qayta yuboring.")
        return

    file_id = None
    if target_msg.video:
        file_id = target_msg.video.file_id
    elif target_msg.document:
        file_id = target_msg.document.file_id

    if not file_id:
        await callback.message.edit_text("⚠️ Video fayli topilmadi. Iltimos, videongizni qayta yuboring.")
        return

    user = callback.from_user
    db_save_user(user.id, user.username, user.full_name)
    lang = db_get_user_lang(user.id)

    if action == "note":
        await callback.message.edit_text(TEXTS[lang]["note_processing"], parse_mode="HTML")
    else:
        await callback.message.edit_text(TEXTS[lang]["audio_processing"], parse_mode="HTML")

    temp_dir = tempfile.gettempdir()
    unique_id = uuid.uuid4().hex
    input_path = os.path.join(temp_dir, f"input_{unique_id}.mp4")
    output_audio_path = os.path.join(temp_dir, f"output_{unique_id}.mp3")

    generated_temp_files = [input_path]

    try:
        # 1. Videoni yuklab olish
        file_info = await bot.get_file(file_id)
        await bot.download_file(file_info.file_path, destination=input_path)

        if action == "note":
            # Yuqori tiniq sifatda (640x640, CRF=20) ultra-tezkor Dumaloq videoga keltirish
            output_files = await convert_to_video_notes(input_path, temp_dir, unique_id)
            generated_temp_files.extend(output_files)

            for part_file in output_files:
                video_note_file = FSInputFile(part_file)
                await bot.send_video_note(
                    chat_id=callback.message.chat.id,
                    video_note=video_note_file,
                    reply_to_message_id=target_msg.message_id
                )
                db_increment_stats(user.id, action_type="note")
                await asyncio.sleep(0.05)

            # status xabarini o'chiramiz. Hech qanday "video tayyor" kabi ortiqcha matn yozilmaydi!
            await callback.message.delete()

        elif action == "audio":
            # Audioni ajratib olish (Foydalanuvchi so'raganidek audio tagiga va keyin hechnarsa yozilmaydi)
            generated_temp_files.append(output_audio_path)
            await extract_audio(input_path, output_audio_path)
            audio_file = FSInputFile(output_audio_path, filename=f"audio_{user.first_name}.mp3")

            await bot.send_audio(
                chat_id=callback.message.chat.id,
                audio=audio_file,
                reply_to_message_id=target_msg.message_id
            )
            db_increment_stats(user.id, action_type="audio")
            await callback.message.delete()

    except Exception as e:
        logger.error(f"Xatolik yuz berdi: {e}", exc_info=True)
        await callback.message.edit_text(TEXTS[lang]["err_msg"], parse_mode="HTML")
        if ADMIN_ID:
            try:
                await bot.send_message(
                    ADMIN_ID,
                    f"⚠️ <b>Xatolik bildirishnomasi:</b>\n"
                    f"User: {user.full_name} (<code>{user.id}</code>)\n"
                    f"Amal: <code>{action}</code>\n"
                    f"Xatolik: <code>{str(e)[:300]}</code>",
                    parse_mode="HTML"
                )
            except Exception:
                pass
    finally:
        for temp_file in generated_temp_files:
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception:
                    pass


async def main():
    global BOT_USERNAME

    # DB ni ishga tushirish
    init_db()
    logger.info("Database muvaffaqiyatli yaratildi/ulandi.")

    # Render uchun HTTP health serverni ishga tushirish
    await start_health_server()

    # Bot ma'lumotlarini olish
    bot_info = await bot.get_me()
    BOT_USERNAME = bot_info.username
    logger.info(f"Bot muvaffaqiyatli aniqlandi: @{BOT_USERNAME}")

    # Bot buyruqlar menyusini (chap tarafdagi Menu) va 'What can this bot do?' tavsifini o'rnatish
    await set_bot_commands(bot)
    await set_bot_description(bot)

    logger.info("Bot ishga tushirilmoqda...")
    await bot.delete_webhook(drop_pending_updates=True)

    # Admin'ga xabarnoma yuborish
    if ADMIN_ID:
        try:
            await bot.send_message(
                ADMIN_ID,
                "🚀 <b>YANGILANISH TAYYOR!</b>\n"
                "• 640x640 CRF=20 bilan video sifati to'liq tiniqlashtirildi!\n"
                "• Video kelganda ❤️ qizil yurakcha reaksiyasi bosiladi!\n"
                "• Video tayyor bo'lgach ortiqcha matnli xabarlar to'liq olib tashlandi.",
                parse_mode="HTML"
            )
            logger.info(f"Admin ID {ADMIN_ID} ga ishga tushganlik haqida bildirishnoma yuborildi.")
        except Exception as admin_err:
            logger.warning(f"Adminga xabarnoma yuborishda xatolik: {admin_err}")

    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot to'xtatildi.")
