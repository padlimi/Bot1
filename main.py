import os
import io
import math
import logging
import sys
import asyncio
import aiohttp
import numpy as np
import gc
import pytz
from datetime import datetime
from io import BytesIO

# Telegram imports
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ForceReply
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext

# Image processing
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter

# Perbaikan import untuk Google Gemini SDK terbaru
try:
    from google import genai
    from google.genai import types
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False

# ======================================================
# KONFIGURASI AWAL & ENV
# ======================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# ======================================================
# KONFIGURASI GEMINI AI
# ======================================================
gemini_client = None
GEMINI_MODEL = "gemini-2.0-flash"
SYSTEM_PROMPT = "Kamu adalah asisten AI toko yang ramah. Bantu jawab pertanyaan user dengan singkat dan jelas."

if GOOGLE_AVAILABLE and GEMINI_API_KEY:
    try:
        gemini_client = genai.Client(api_key=GEMINI_API_KEY)
        logger.info("✅ Gemini AI berhasil dikonfigurasi")
    except Exception as e:
        logger.error(f"❌ Gagal konfigurasi Gemini AI: {e}")
        gemini_client = None

ai_chat_sessions = {}

# ======================================================
# KONFIGURASI LAYOUT (A4 150 DPI)
# ======================================================
WHITE, BLACK = (255, 255, 255), (0, 0, 0)
BLUE_BG, RED_HEADER = (0, 102, 210), (220, 0, 0)
RED_SHADOW, RED_LINE = (160, 0, 0), (255, 0, 0)

IMG_W, IMG_H = 1240, 1754 # A4
MARGIN, GAP = 15, 5
COLS, ROWS = 2, 4
ITEMS_PER_IMAGE = COLS * ROWS
CELL_W = (IMG_W - (MARGIN * 2) - (COLS - 1) * GAP) // COLS
CELL_H = (IMG_H - (MARGIN * 2) - (ROWS - 1) * GAP) // ROWS

# POP Config
TEMPLATE_SIZE = (720, 1018)
PRODUCT_AREA = {"x": 38, "y": 148, "width": 644, "height": 700}
PRICE_AREA = {"x": 38, "y": 848, "width": 644, "height": 139}
SCALE = 2

# ======================================================
# UTILITY FUNCTIONS (FONT & FORMAT)
# ======================================================
def get_font(size, bold=True):
    font_files = ["Roboto-Bold.ttf", "Roboto-Regular.ttf", "Arial.ttf", "DejaVuSans.ttf"]
    for f in font_files:
        try: return ImageFont.truetype(f, size)
        except: continue
    return ImageFont.load_default()

def format_angka(harga):
    try:
        angka = int(''.join(filter(str.isdigit, str(harga))))
        return f"{angka:,}".replace(",", ".")
    except: return str(harga)

def fit_text(draw, text, max_w, initial_size, bold=True):
    size = initial_size
    while size > 10:
        font = get_font(size, bold)
        bbox = draw.textbbox((0, 0), text, font=font)
        if (bbox[2] - bbox[0]) <= max_w: return font, size
        size -= 2
    return get_font(10, bold), 10

# ======================================================
# DRAWING FUNCTIONS
# ======================================================
def draw_paket(draw, x, y, h_normal, h_promo):
    draw.rectangle([x, y, x + CELL_W, y + CELL_H], fill=BLUE_BG, outline=BLACK)
    # Header
    draw.text((x + CELL_W//2, y + 50), "PAKET HEMAT", fill=RED_HEADER, anchor="mm", font=get_font(50))
    # Harga Normal (Coret)
    draw.text((x + 20, y + 150), "Harga Normal", fill=WHITE, font=get_font(24, False))
    txt_n = format_angka(h_normal)
    draw.rectangle([x + 180, y + 130, x + CELL_W - 20, y + 180], fill=BLACK)
    draw.text((x + 200, y + 155), f"Rp {txt_n}", fill=WHITE, anchor="lm", font=get_font(35))
    draw.line([x + 185, y + 155, x + CELL_W - 25, y + 155], fill=RED_LINE, width=4)
    # Harga Spesial
    draw.text((x + 20, y + 230), "Harga Spesial", fill=WHITE, font=get_font(24, False))
    draw.rectangle([x + 15, y + 260, x + CELL_W - 15, y + CELL_H - 15], fill=BLACK, outline=WHITE)
    draw.text((x + 40, y + 350), "Rp", fill=WHITE, font=get_font(40))
    f_sp, _ = fit_text(draw, format_angka(h_promo), CELL_W - 120, 110)
    draw.text((x + CELL_W - 30, y + 350), format_angka(h_promo), fill=WHITE, anchor="rm", font=f_sp)

def draw_promo(draw, x, y, nama, harga):
    draw.rectangle([x, y, x + CELL_W, y + CELL_H], fill=(255, 235, 0), outline=BLACK)
    draw.rectangle([x, y, x + CELL_W, y + 80], fill=RED_HEADER)
    draw.text((x + CELL_W//2, y + 40), "PROMOSI", fill=(255, 235, 0), anchor="mm", font=get_font(40))
    f_nm, _ = fit_text(draw, nama.upper(), CELL_W - 40, 35)
    draw.text((x + CELL_W//2, y + 140), nama.upper(), fill=BLACK, anchor="mm", font=f_nm)
    f_pr, _ = fit_text(draw, f"Rp {format_angka(harga)}", CELL_W - 60, 90)
    draw.text((x + CELL_W//2, y + 300), f"Rp {format_angka(harga)}", fill=RED_HEADER, anchor="mm", font=f_pr)

def draw_normal(draw, x, y, nama, harga):
    draw.rectangle([x, y, x + CELL_W, y + CELL_H], fill=WHITE, outline=BLACK)
    f_nm, _ = fit_text(draw, nama.upper(), CELL_W - 40, 35)
    draw.text((x + CELL_W//2, y + 140), nama.upper(), fill=BLACK, anchor="mm", font=f_nm)
    f_pr, _ = fit_text(draw, format_angka(harga), CELL_W - 60, 110)
    draw.text((x + CELL_W//2, y + 320), format_angka(harga), fill=BLACK, anchor="mm", font=f_pr)

# ======================================================
# AI ENGINE
# ======================================================
async def ask_gemini(user_id: int, message: str) -> str:
    if not gemini_client: return "❌ AI tidak aktif."
    try:
        if user_id not in ai_chat_sessions: ai_chat_sessions[user_id] = []
        
        # Build history with new prompt
        contents = ai_chat_sessions[user_id] + [types.Content(role="user", parts=[types.Part(text=message)])]
        
        def _call():
            return gemini_client.models.generate_content(
                model=GEMINI_MODEL, contents=contents,
                config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT, temperature=0.7)
            )
        
        res = await asyncio.to_thread(_call)
        ai_chat_sessions[user_id].append(types.Content(role="user", parts=[types.Part(text=message)]))
        ai_chat_sessions[user_id].append(types.Content(role="model", parts=[types.Part(text=res.text)]))
        
        if len(ai_chat_sessions[user_id]) > 10: ai_chat_sessions[user_id] = ai_chat_sessions[user_id][-10:]
        return res.text
    except Exception as e:
        return f"❌ Error AI: {str(e)}"

# ======================================================
# HANDLERS
# ======================================================
async def start(update: Update, context):
    kb = ReplyKeyboardMarkup([
        [KeyboardButton("/promo"), KeyboardButton("/normal")],
        [KeyboardButton("/paket"), KeyboardButton("/pop")],
        [KeyboardButton("/ai"), KeyboardButton("/stop_ai")]
    ], resize_keyboard=True)
    await update.message.reply_text("🤖 *Bot Retail Ready!*\nPilih mode di bawah:", parse_mode="Markdown", reply_markup=kb)

async def handle_msg(update: Update, context: CallbackContext):
    u_data = context.user_data
    text = update.message.text.strip()

    # Password & Reminder logic (Sesuai skrip sebelumnya)
    if u_data.get('awaiting_password'):
        if text == "Reminder23":
            u_data['awaiting_password'] = False
            u_data['reminder_mode'] = True
            await update.message.reply_text("✅ Akses Diterima!")
        return

    # AI Mode
    if u_data.get('ai_mode'):
        await update.message.chat.send_action("typing")
        resp = await ask_gemini(update.effective_user.id, text)
        await update.message.reply_text(resp)
        return

    # Printing Logic
    mode = u_data.get('mode')
    if not mode: return
    
    items = []
    for line in text.split('\n'):
        p = line.split('.')
        if mode == 'paket' and len(p) >= 2:
            qty = int(p[2]) if len(p)>2 else 1
            for _ in range(min(qty, 50)): items.append({'n': p[0], 's': p[1]})
        elif len(p) >= 2:
            items.append({'nama': p[0], 'harga': p[1]})

    if not items: return
    
    await update.message.reply_text(f"⏳ Memproses {len(items)} item...")
    
    # Generate A4
    num_imgs = math.ceil(len(items) / ITEMS_PER_IMAGE)
    for i in range(num_imgs):
        canvas = Image.new('RGB', (IMG_W, IMG_H), WHITE)
        draw = ImageDraw.Draw(canvas)
        batch = items[i*ITEMS_PER_IMAGE : (i+1)*ITEMS_PER_IMAGE]
        
        for idx, itm in enumerate(batch):
            r, c = idx // COLS, idx % COLS
            px, py = MARGIN + c*(CELL_W+GAP), MARGIN + r*(CELL_H+GAP)
            if mode == 'paket': draw_paket(draw, px, py, itm['n'], itm['s'])
            elif mode == 'promo': draw_promo(draw, px, py, itm['nama'], itm['harga'])
            else: draw_normal(draw, px, py, itm['nama'], itm['harga'])
            
        out = BytesIO()
        canvas.save(out, format='PNG')
        out.seek(0)
        await update.message.reply_photo(out, caption=f"Hal {i+1}/{num_imgs}")
    
    u_data['mode'] = None
    gc.collect()

# ======================================================
# MAIN
# ======================================================
async def main():
    # Setup status untuk print console
    g_status = "✅ Aktif" if (GOOGLE_AVAILABLE and gemini_client) else "❌ Mati"
    
    print(f"{'='*30}\nBOT RUNNING\nGemini AI: {g_status}\n{'='*30}")
    
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler(["promo", "normal", "paket", "pop"], 
        lambda u, c: (u.message.reply_text(f"Mode {u.message.text} aktif!"), c.user_data.update({'mode': u.message.text[1:]}))))
    app.add_handler(CommandHandler("ai", lambda u, c: (u.message.reply_text("🤖 Mode AI Aktif"), c.user_data.update({'ai_mode': True}))))
    app.add_handler(CommandHandler("stop_ai", lambda u, c: (u.message.reply_text("✅ Mode AI Mati"), c.user_data.update({'ai_mode': False}))))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_msg))
    
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
