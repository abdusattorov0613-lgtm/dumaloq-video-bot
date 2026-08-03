import asyncio
import datetime
import logging
import os
import shutil
import sqlite3
import sys
import tempfile
import uuid
from dotenv import load_dotenv
from aiohttp import web

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command, CommandStart, or_f
from aiogram.types import (
    BotCommand,
    CallbackQuery,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
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

if not BOT_TOKEN or BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
    logger.error("BOT_TOKEN topilmadi! Iltimos, .env fayliga haqiqiy Telegram Bot Tokenini kiriting.")
    sys.exit(1)

# Bot va Dispatcher obyektlarini yaratish
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

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
            "📹 <i>Videongizni yuboring!</i>"
        ),
        "help": (
            "ℹ️ <b>YORDAM VA YO'RIQNOMA</b>\n\n"
            "1️⃣ <b>Dumaloq video:</b> Videoni yuboring va 🔵 <i>Dumaloq video qilish</i> tugmasini bosing (max 60s, 1:1 format).\n"
            "2️⃣ <b>MP3 Audio:</b> Videoni yuboring va 🎵 <i>Ovozini ajratib olish</i> tugmasini bosing.\n"
            "3️⃣ <b>Tilni o'zgartirish:</b> /lang\n"
            "4️⃣ <b>Admin:</b> /admin"
        ),
        "lang_choose": "🌐 <b>Muloqot tilini tanlang:</b>",
        "lang_set": "✅ Muloqot tili <b>O'zbekcha</b>ga o'zgartirildi!",
        "video_received": (
            "📹 <b>Videongiz qabul qilindi.</b>\n"
            "Kerakli bo'limni tanlang 👇"
        ),
        "btn_note": "🔵 Dumaloq video qilish (Video Note)",
        "btn_audio": "🎵 Ovozini ajratib olish (MP3)",
        "note_processing": "⏳ <b>Dumaloq video tayyorlanmoqda...</b>",
        "audio_processing": "🎶 <b>MP3 audio ajratib olinmoqda...</b>",
        "done_note": "✅ Dumaloq videongiz tayyor, <b>{name}</b>!",
        "done_audio": "🎵 Video audiosi (MP3) tayyor, <b>{name}</b>!",
        "err_msg": "❌ Videoni qayta ishlashda xatolik yuz berdi. Iltimos, qayta urinib ko'ring.",
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
            "1️⃣ <b>Круглое видео:</b> Отправьте видео и нажмите 🔵 <i>Сделать круглое видео</i> (до 60 сек, 1:1).\n"
            "2️⃣ <b>MP3 Аудио:</b> Отправьте видео и нажмите 🎵 <i>Извлечь звук</i>.\n"
            "3️⃣ <b>Смена языка:</b> /lang\n"
            "4️⃣ <b>Администратор:</b> /admin"
        ),
        "lang_choose": "🌐 <b>Выберите язык общения:</b>",
        "lang_set": "✅ Язык успешно изменен на <b>Русский</b>!",
        "video_received": (
            "📹 <b>Видео получено.</b>\n"
            "Выберите нужное действие ниже 👇"
        ),
        "btn_note": "🔵 Сделать круглое видео (Video Note)",
        "btn_audio": "🎵 Извлечь звук (MP3)",
        "note_processing": "⏳ <b>Круглое видео обрабатывается...</b>",
        "audio_processing": "🎶 <b>Извлечение MP3 аудио...</b>",
        "done_note": "✅ Ваше круглое видео готово, <b>{name}</b>!",
        "done_audio": "🎵 MP3 аудио из видео готово, <b>{name}</b>!",
        "err_msg": "❌ Ошибка при обработке видео. Попробуйте еще раз.",
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
            "1️⃣ <b>Round Video:</b> Send video and click 🔵 <i>Make Round Video</i> (max 60s, 1:1).\n"
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
        "note_processing": "⏳ <b>Converting to round video...</b>",
        "audio_processing": "🎶 <b>Extracting MP3 audio...</b>",
        "done_note": "✅ Your round video is ready, <b>{name}</b>!",
        "done_audio": "🎵 Video audio (MP3) is ready, <b>{name}</b>!",
        "err_msg": "❌ Error processing video. Please try again.",
        "admin_info": (
            "👑 <b>BOT ADMINISTRATOR & DEVELOPER</b>\n\n"
            "For questions, suggestions, or support:\n\n"
            "👤 Admin: @ilkhomjon_abdusattorov\n"
            "💬 Telegram Link: https://t.me/ilkhomjon_abdusattorov"
        ),
        "btn_admin_contact": "💬 Contact Admin (@ilkhomjon_abdusattorov)"
    }
}


def get_main_reply_keyboard(lang: str = "uz") -> ReplyKeyboardMarkup:
    """Xabar yozish joyida (emoji tugmasi yonida) doimiy ko'rinib turuvchi asosiy menyu tugmalari"""
    if lang == "ru":
        btn_start = "🚀 Старт"
        btn_help = "ℹ️ Помощь"
        btn_lang = "🌐 Выбрать язык"
        btn_admin = "👑 Админ"
    elif lang == "en":
        btn_start = "🚀 Start"
        btn_help = "ℹ️ Help"
        btn_lang = "🌐 Change Language"
        btn_admin = "👑 Admin"
    else:
        btn_start = "🚀 Start"
        btn_help = "ℹ️ Yordam"
        btn_lang = "🌐 Tilni tanlash"
        btn_admin = "👑 Admin"

    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=btn_start), KeyboardButton(text=btn_help)],
            [KeyboardButton(text=btn_lang), KeyboardButton(text=btn_admin)]
        ],
        resize_keyboard=True,
        persistent=True
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
    """Telegram command menyusini (/start, /help, /lang, /admin) sozlash"""
    commands = [
        BotCommand(command="start", description="🚀 Botni ishga tushirish"),
        BotCommand(command="help", description="ℹ️ Yordam va yo'riqnoma"),
        BotCommand(command="lang", description="🌐 Tilni o'zgartirish / Language"),
        BotCommand(command="admin", description="👑 Admin bilan bog'lanish / Statistika"),
    ]
    await bot_obj.set_my_commands(commands)
    logger.info("Bot buyruqlar menyusi (Command Menu) muvaffaqiyatli sozlandi.")


async def set_bot_description(bot_obj: Bot):
    """Botga birinchi marta kirganda Start bosishdan oldin ko'rinadigan 'What can this bot do?' matnini o'rnatish"""
    description_text = (
        "<b>What can this bot do?</b>\n\n"
        "📹 <b>Video Note Converter & MP3 Audio Extractor</b>\n\n"
        "✨ Ushbu bot orqali siz:\n"
        "• Oddiy videolarni 1:1 kvadrat <b>Dumaloq video (Video Note)</b> formatiga o'tkazishingiz;\n"
        "• Videolardan yuqori sifatli <b>MP3 audio</b>ni ajratib olishingiz mumkin.\n\n"
        "🚀 Botni ishga tushirish uchun <b>Start</b> tugmasini bosing!"
    )
    short_desc = "📹 Dumaloq video (Video Note) va MP3 Audio yaratuvchi bot."

    try:
        await bot_obj.set_my_description(description=description_text)
        await bot_obj.set_my_short_description(short_description=short_desc)
        logger.info("Bot 'What can this bot do?' tavsifi muvaffaqiyatli o'rnatildi.")
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


async def convert_to_video_note(input_path: str, output_path: str) -> None:
    """FFmpeg yordamida videoni 1:1 kvadrat dumaloq videoga o'tkazish"""
    ffmpeg_bin = get_ffmpeg_cmd()
    vf_filter = "crop='min(iw\\,ih)':'min(iw\\,ih)',scale=640:640"

    cmd = [
        ffmpeg_bin, "-y",
        "-i", input_path,
        "-t", "60",
        "-vf", vf_filter,
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        output_path
    ]

    logger.info(f"FFmpeg dumaloq video konvertatsiyasi: {input_path} -> {output_path}")

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        error_text = stderr.decode(errors="replace")
        logger.error(f"FFmpeg xatoligi: {error_text}")
        raise RuntimeError("FFmpeg orqali videoni qayta ishlashda xatolik yuz berdi.")

    logger.info("FFmpeg dumaloq video muvaffaqiyatli tayyorlandi.")


async def extract_audio(input_path: str, output_path: str) -> None:
    """FFmpeg yordamida videodan MP3 audio ajratib olish"""
    ffmpeg_bin = get_ffmpeg_cmd()

    cmd = [
        ffmpeg_bin, "-y",
        "-i", input_path,
        "-vn",
        "-c:a", "libmp3lame",
        "-q:a", "2",
        output_path
    ]

    logger.info(f"FFmpeg audio ajratish boshlanmoqda: {input_path} -> {output_path}")

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


@dp.message(or_f(CommandStart(), F.text.in_({"🚀 Start", "🚀 Старт"})))
async def start_handler(message: Message):
    """/start va Menyudagi Start tugmasi handler'i"""
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

    text = TEXTS[lang]["start"].format(name=user.first_name) + admin_note
    await message.answer(
        text,
        reply_markup=get_main_reply_keyboard(lang),
        parse_mode="HTML"
    )


@dp.message(or_f(Command("help"), F.text.in_({"ℹ️ Yordam", "ℹ️ Помощь", "ℹ️ Help"})))
async def help_handler(message: Message):
    """/help va Menyudagi Yordam tugmasi handler'i"""
    user = message.from_user
    db_save_user(user.id, user.username, user.full_name)
    lang = db_get_user_lang(user.id)

    text = TEXTS[lang]["help"]
    await message.answer(
        text,
        reply_markup=get_main_reply_keyboard(lang),
        parse_mode="HTML"
    )


@dp.message(or_f(Command("lang"), F.text.in_({"🌐 Tilni tanlash", "🌐 Выбрать язык", "🌐 Change Language", "🌐 Язык", "🌐 Language"})))
async def lang_handler(message: Message):
    """/lang va Menyudagi Tilni tanlash tugmasi handler'i"""
    user = message.from_user
    db_save_user(user.id, user.username, user.full_name)
    lang = db_get_user_lang(user.id)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="setlang:uz"),
                InlineKeyboardButton(text="🇷🇺 Русский", callback_data="setlang:ru"),
                InlineKeyboardButton(text="🇬🇧 English", callback_data="setlang:en"),
            ]
        ]
    )

    await message.answer(
        TEXTS[lang]["lang_choose"],
        reply_markup=keyboard,
        parse_mode="HTML"
    )


@dp.callback_query(F.data.startswith("setlang:"))
async def set_language_callback(callback: CallbackQuery):
    """Til o'zgarganda ishlaydigan callback handler"""
    await callback.answer()
    new_lang = callback.data.split(":")[1]
    if new_lang in TEXTS:
        db_set_user_lang(callback.from_user.id, new_lang)
        await callback.message.edit_text(TEXTS[new_lang]["lang_set"], parse_mode="HTML")
        await callback.message.answer(
            TEXTS[new_lang]["start"].format(name=callback.from_user.first_name),
            reply_markup=get_main_reply_keyboard(new_lang),
            parse_mode="HTML"
        )


@dp.message(or_f(Command("admin", "stats"), F.text.in_({"👑 Admin", "👑 Админ"})))
async def admin_handler(message: Message):
    """/admin va Menyudagi Admin tugmasi handler'i"""
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


@dp.message(F.video | F.document)
async def video_handler(message: Message):
    """Foydalanuvchi video yuborganda ishlaydigan handler"""
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
        await message.reply(
            "😊 <b>Hurmatli foydalanuvchi!</b>\n"
            "Iltimos, menga faqat video formatidagi fayl yoki oddiy video yuboring.",
            parse_mode="HTML",
            reply_markup=get_main_reply_keyboard(lang)
        )
        return

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
    output_note_path = os.path.join(temp_dir, f"output_{unique_id}.mp4")
    output_audio_path = os.path.join(temp_dir, f"output_{unique_id}.mp3")

    try:
        # 1. Videoni yuklab olish
        file_info = await bot.get_file(file_id)
        await bot.download_file(file_info.file_path, destination=input_path)

        if action == "note":
            # Dumaloq videoga keltirish
            await convert_to_video_note(input_path, output_note_path)
            video_note_file = FSInputFile(output_note_path)

            await bot.send_video_note(
                chat_id=callback.message.chat.id,
                video_note=video_note_file,
                reply_to_message_id=target_msg.message_id
            )
            db_increment_stats(user.id, action_type="note")

            await callback.message.delete()
            await bot.send_message(
                chat_id=callback.message.chat.id,
                text=TEXTS[lang]["done_note"].format(name=user.first_name),
                reply_to_message_id=target_msg.message_id,
                parse_mode="HTML"
            )

        elif action == "audio":
            # Audioni ajratib olish
            await extract_audio(input_path, output_audio_path)
            audio_file = FSInputFile(output_audio_path, filename=f"audio_{user.first_name}.mp3")

            await bot.send_audio(
                chat_id=callback.message.chat.id,
                audio=audio_file,
                caption=TEXTS[lang]["done_audio"].format(name=user.first_name),
                reply_to_message_id=target_msg.message_id,
                parse_mode="HTML"
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
        for temp_file in (input_path, output_note_path, output_audio_path):
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception:
                    pass


async def main():
    # DB ni ishga tushirish
    init_db()
    logger.info("Database muvaffaqiyatli yaratildi/ulandi.")

    # Render uchun HTTP health serverni ishga tushirish
    await start_health_server()

    # Bot buyruqlar menyusini va 'What can this bot do?' tavsifini o'rnatish
    await set_bot_commands(bot)
    await set_bot_description(bot)

    logger.info("Bot ishga tushirilmoqda...")
    await bot.delete_webhook(drop_pending_updates=True)

    # Admin'ga xabarnoma yuborish
    if ADMIN_ID:
        try:
            await bot.send_message(
                ADMIN_ID,
                "🚀 <b>Bot muvaffaqiyatli ishga tushdi va xizmatingizda!</b>\n"
                "'What can this bot do?' tavsifi avtomatik o'rnatildi.",
                reply_markup=get_main_reply_keyboard("uz"),
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
