# Telegram Video Note Bot (Dumaloq Video Bot)

Ushbu bot Telegram foydalanuvchilari tomonidan yuborilgan oddiy videolarni (MP4, MOV va h.k.) avtomatik ravishda **Video Note** (dumaloq video / video xabar) formatiga o'tkazib beradi.

---

## 🚀 Xususiyatlari
- **aiogram 3.x** frameworki asosida ishlaydi.
- **FFmpeg (asinxron)** orqali videolarni non-blocking tarzda qayta ishlaydi.
- Videoni markazdan 1:1 nisbatda (kvadrat) qirqadi (`crop`) va 640x640 o'lchamga keltiradi.
- Uzunligi 60 soniyadan oshsa, avtomatik ravishda dastlabki 60 soniyasini qirqadi.
- H.264 (video) va AAC (audio) kodeklari bilan to'liq Video Note formatiga moslaydi.
- Server xotirasini to'ldirmaslik uchun vaqtinchalik (temp) fayllarni avtomatik o'chiradi (clean-up).

---

## 🛠 Talablar
1. **Python 3.10+**
2. **FFmpeg** kompyuter/server tizimiga o'rnatilgan va PATH ga qo'shilgan bo'lishi kerak.
   - Windows uchun: [ffmpeg.org](https://ffmpeg.org/download.html) dan yuklab olib, PATH ga qo'shing.
   - Linux (Ubuntu/Debian): `sudo apt update && sudo apt install ffmpeg`
   - macOS: `brew install ffmpeg`

---

## 📦 O'rnatish va Ishga Tushirish

### 1. Repertoarni tayyorlash va virtual muhit yaratish
```bash
# Loyiha papkasiga o'ting
cd dumaloq_video

# Virtual muhit (venv) yaratish
python -m venv venv

# Virtual muhitni aktivlashtirish
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# Windows (CMD):
.\venv\Scripts\activate.bat
# Linux / macOS:
source venv/bin/activate
```

### 2. Kerakli kutubxonalarni o'rnatish
```bash
pip install -r requirements.txt
```

### 3. `.env` faylini sozlash
`.env` faylini oching va Telegram BotFather'dan olingan tokeningizni kiriting:
```env
BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyZ
```

### 4. Botni ishga tushirish
```bash
python main.py
```

---

## 📁 Loyiha Strukturasi
```text
dumaloq_video/
├── .env.example        # Env namuna fayli
├── .env                # Bot tokenini saqlash fayli
├── requirements.txt    # Kerakli Python kutubxonalari
├── main.py             # Asosiy kod va handlerlar
└── README.md           # Qo'llanma
```
