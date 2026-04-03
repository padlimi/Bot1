import os
import io
import math
import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ForceReply
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from PIL import Image, ImageDraw, ImageFont

# Logging untuk memantau aktivitas bot
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

TOKEN = os.environ.get("TELEGRAM_TOKEN") or "YOUR_BOT_TOKEN_HERE"

# --- KONFIGURASI WARNA ---
YELLOW, RED, BLACK, WHITE = (255, 230, 0), (204, 0, 0), (0, 0, 0), (255, 255, 255)
DARK_BLUE, PAKET_RED = (20, 52, 100), (255, 50, 50)

# --- UKURAN KANVAS ---
COLS, ROWS = 2, 4
ITEMS_PER_IMAGE = COLS * ROWS
CELL_W, CELL_H = 600, 450
BORDER = 15
HEADER_H = 90
IMG_W = COLS * CELL_W + (COLS + 1) * BORDER
IMG_H = ROWS * CELL_H + (ROWS + 1) * BORDER

# --- LOAD FONT (Sistem Otomatis) ---
def get_font(size):
    paths = ["arial.ttf", "DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "C:\\Windows\\Fonts\\arialbd.ttf"]
    for path in paths:
        try:
            return ImageFont.truetype(path, size)
        except:
            continue
    return ImageFont.load_default()

FONT_HEADER = get_font(60)
FONT_NAMA = get_font(45)
FONT_HARGA = get_font(120)
FONT_PAKET_TITLE = get_font(55)
FONT_SMALL = get_font(30)

def format_harga(harga_str):
    try:
        angka = int(str(harga_str).replace(".", "").replace(",", ""))
        return f"{angka:,}".replace(",", ".")
    except:
        return str(harga_str)

# --- FUNGSI MENGGAMBAR ---

def draw_promo(draw, x, y, nama, harga):
    # Background & Header
    draw.rectangle([x, y, x + CELL_W, y + CELL_H], fill=YELLOW, outline=BLACK, width=2)
    draw.rectangle([x, y, x + CELL_W, y + HEADER_H], fill=RED)
    
    # Teks "PROMOSI"
    draw.text((x + CELL_W//2, y + HEADER_H//2), "PROMOSI", fill=YELLOW, anchor="mm", font=FONT_HEADER)
    
    # Nama & Harga
    if nama:
        draw.text((x + CELL_W//2, y + HEADER_H + 60), nama.upper(), fill=BLACK, anchor="mm", font=FONT_NAMA)
    if harga:
        draw.text((x + CELL_W//2, y + CELL_H - 120), f"Rp {format_harga(harga)}", fill=RED, anchor="mm", font=FONT_HARGA)

def draw_normal(draw, x, y, nama, harga):
    draw.rectangle([x, y, x + CELL_W, y + CELL_H], fill=WHITE, outline=(200, 200, 200), width=3)
    if nama:
        draw.text((x + CELL_W//2, y + 100), nama.upper(), fill=BLACK, anchor="mm", font=FONT_NAMA)
    if harga:
        draw.text((x + CELL_W//2, y + 280), f"Rp {format_harga(harga)}", fill=BLACK, anchor="mm", font=FONT_HARGA)

def draw_paket(draw, x, y, h_normal, h_promo):
    draw.rectangle([x, y, x + CELL_W, y + CELL_H], fill=DARK_BLUE, outline=WHITE, width=4)
    
    # Header Paket
    draw.text((x + CELL_W//2, y + 60), "PAKET HEMAT", fill=PAKET_RED, anchor="mm", font=FONT_PAKET_TITLE)
    
    # Harga Normal (Coret)
    if h_normal:
        txt = f"Harga Normal: Rp {format_harga(h_normal)}"
        tw, th = draw.textbbox((0, 0), txt, font=FONT_SMALL)[2:]
        tx, ty = x + CELL_W//2, y + 150
        draw.text((tx, ty), txt, fill=WHITE, anchor="mm", font=FONT_SMALL)
        draw.line([tx - tw//2, ty, tx + tw//2, ty], fill=RED, width=4) # Garis coret

    # Harga Promo
    if h_promo:
        draw.text((x + CELL_W//2, y + 220), "HARGA SPESIAL", fill=YELLOW, anchor="mm", font=FONT_SMALL)
        draw.text((x + CELL_W//2, y + 320), f"Rp {format_harga(h_promo)}", fill=WHITE, anchor="mm", font=FONT_HARGA)

# --- HANDLERS ---

async def start(update: Update, context):
    await update.message.reply_text(
        "✨ **Bot Pembuat Label Harga** ✨\n\n"
        "Pilih mode di bawah untuk mulai membuat gambar:",
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton("/promo"), KeyboardButton("/normal"), KeyboardButton("/paket")]],
            resize_keyboard=True
        ), parse_mode="Markdown"
    )

async def handle_logic(update: Update, context):
    mode = context.user_data.get('mode')
    if not mode:
        await update.message.reply_text("Silakan pilih mode dulu: /promo, /normal, atau /paket")
        return

    lines = update.message.text.strip().split('\n')
    data_list = []
    
    for line in lines:
        parts = line.split('.')
        if len(parts) >= 2:
            data_list.append(parts)

    if not data_list:
        await update.message.reply_text("Format salah! Gunakan titik (.) sebagai pemisah.")
        return

    # Proses Gambar
    img = Image.new('RGB', (IMG_W, IMG_H), color=(240, 240, 240))
    draw = ImageDraw.Draw(img)

    for i in range(ITEMS_PER_IMAGE):
        col, row = i % COLS, i // COLS
        x = BORDER + col * (CELL_W + BORDER)
        y = BORDER + row * (CELL_H + BORDER)
        
        if i < len(data_list):
            d = data_list[i]
            if mode == 'promo': draw_promo(draw, x, y, d[0], d[1])
            elif mode == 'normal': draw_normal(draw, x, y, d[0], d[1])
            elif mode == 'paket': draw_paket(draw, x, y, d[0], d[1])
        else:
            # Kosongkan sisa grid
            draw.rectangle([x, y, x + CELL_W, y + CELL_H], fill=(220, 220, 220))

    bio = io.BytesIO()
    img.save(bio, 'PNG')
    bio.seek(0)
    await update.message.reply_photo(photo=bio, caption=f"✅ Berhasil membuat label mode {mode.upper()}")
    context.user_data['mode'] = None

# --- MAIN ---
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("promo", lambda u, c: (c.user_data.update({'mode': 'promo'}), u.message.reply_text("Kirim daftar: NAMA.HARGA"))))
    app.add_handler(CommandHandler("normal", lambda u, c: (c.user_data.update({'mode': 'normal'}), u.message.reply_text("Kirim daftar: NAMA.HARGA"))))
    app.add_handler(CommandHandler("paket", lambda u, c: (c.user_data.update({'mode': 'paket'}), u.message.reply_text("Kirim daftar: HARGA_LAMA.HARGA_BARU"))))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_logic))
    
    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
