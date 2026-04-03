import os
import io
import math
import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ForceReply
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from PIL import Image, ImageDraw, ImageFont

# Setup Logging untuk memantau bot di dashboard Railway
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

TOKEN = os.environ.get("TELEGRAM_TOKEN")

# --- KONFIGURASI WARNA & UKURAN ---
YELLOW, RED, BLACK, WHITE = (255, 230, 0), (204, 0, 0), (0, 0, 0), (255, 255, 255)
DARK_BLUE, PAKET_RED = (15, 45, 90), (230, 30, 30)

COLS, ROWS = 2, 4
ITEMS_PER_IMAGE = COLS * ROWS
CELL_W, CELL_H = 600, 450
BORDER = 15
HEADER_H = 100
IMG_W = COLS * CELL_W + (COLS + 1) * BORDER
IMG_H = ROWS * CELL_H + (ROWS + 1) * BORDER

def get_font(size, bold=True):
    """Mencari font Roboto di direktori lokal atau sistem"""
    font_file = "Roboto-Bold.ttf" if bold else "Roboto-Regular.ttf"
    paths = [
        font_file, 
        f"./{font_file}",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" # Fallback Linux
    ]
    for path in paths:
        try:
            return ImageFont.truetype(path, size)
        except:
            continue
    return ImageFont.load_default()

# Inisialisasi Font Roboto
FONT_PRICE = get_font(140)  # Sangat besar untuk harga
FONT_NAME = get_font(55)    # Sedang untuk nama barang
FONT_HEAD = get_font(65)    # Untuk header "PROMOSI"
FONT_LABEL = get_font(32)   # Untuk teks keterangan kecil

def format_rp(harga):
    try:
        angka = int(str(harga).replace(".", "").replace(",", ""))
        return f"{angka:,}".replace(",", ".")
    except:
        return str(harga)

# --- FUNGSI MENGGAMBAR KARTU ---

def draw_promo(draw, x, y, nama, harga):
    draw.rectangle([x, y, x + CELL_W, y + CELL_H], fill=YELLOW, outline=BLACK, width=4)
    draw.rectangle([x, y, x + CELL_W, y + HEADER_H], fill=RED)
    draw.text((x + CELL_W//2, y + HEADER_H//2), "PROMOSI", fill=YELLOW, anchor="mm", font=FONT_HEAD)
    if nama:
        draw.text((x + CELL_W//2, y + 180), nama.upper(), fill=BLACK, anchor="mm", font=FONT_NAME)
    if harga:
        draw.text((x + CELL_W//2, y + 330), f"Rp {format_rp(harga)}", fill=RED, anchor="mm", font=FONT_PRICE)

def draw_normal(draw, x, y, nama, harga):
    draw.rectangle([x, y, x + CELL_W, y + CELL_H], fill=WHITE, outline=(220, 220, 220), width=5)
    if nama:
        draw.text((x + CELL_W//2, y + 130), nama.upper(), fill=BLACK, anchor="mm", font=FONT_NAME)
    if harga:
        draw.text((x + CELL_W//2, y + 310), f"Rp {format_rp(harga)}", fill=BLACK, anchor="mm", font=FONT_PRICE)

def draw_paket(draw, x, y, h_lama, h_baru):
    draw.rectangle([x, y, x + CELL_W, y + CELL_H], fill=DARK_BLUE, outline=WHITE, width=6)
    draw.text((x + CELL_W//2, y + 60), "PAKET HEMAT", fill=PAKET_RED, anchor="mm", font=FONT_HEAD)
    if h_lama:
        txt = f"Harga Normal: Rp {format_rp(h_lama)}"
        draw.text((x + CELL_W//2, y + 165), txt, fill=WHITE, anchor="mm", font=FONT_LABEL)
        draw.line([x+150, y+165, x+450, y+165], fill=RED, width=5) # Garis Coret
    if h_baru:
        draw.text((x + CELL_W//2, y + 240), "HARGA SPESIAL", fill=YELLOW, anchor="mm", font=FONT_LABEL)
        draw.text((x + CELL_W//2, y + 340), f"Rp {format_rp(h_baru)}", fill=WHITE, anchor="mm", font=FONT_PRICE)

# --- BOT HANDLERS ---

async def start(update: Update, context):
    kb = [[KeyboardButton("/promo"), KeyboardButton("/normal"), KeyboardButton("/paket")]]
    await update.message.reply_text(
        "👋 **Halo! Bot Label Harga Roboto Ready.**\n\nPilih mode di bawah dan kirim daftar barang.",
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True),
        parse_mode="Markdown"
    )

async def handle_message(update: Update, context):
    mode = context.user_data.get('mode')
    if not mode:
        await update.message.reply_text("⚠️ Pilih mode dulu boss: /promo, /normal, atau /paket")
        return

    lines = update.message.text.strip().split('\n')
    items = [l.split('.') for l in lines if '.' in l]

    if not items:
        await update.message.reply_text("❌ Format salah! Pakai titik. Contoh: `Beras.75000`")
        return

    num_imgs = math.ceil(len(items) / ITEMS_PER_IMAGE)
    
    for i in range(num_imgs):
        batch = items[i * ITEMS_PER_IMAGE : (i + 1) * ITEMS_PER_IMAGE]
        img = Image.new('RGB', (IMG_W, IMG_H), color=(240, 240, 240))
        draw = ImageDraw.Draw(img)

        for idx in range(ITEMS_PER_IMAGE):
            c, r = idx % COLS, idx // COLS
            x, y = BORDER + c*(CELL_W+BORDER), BORDER + r*(CELL_H+BORDER)
            
            if idx < len(batch):
                it = batch[idx]
                if mode == 'promo': draw_promo(draw, x, y, it[0], it[1])
                elif mode == 'normal': draw_normal(draw, x, y, it[0], it[1])
                elif mode == 'paket': draw_paket(draw, x, y, it[0], it[1])
            else:
                draw.rectangle([x, y, x + CELL_W, y + CELL_H], fill=(235, 235, 235))

        bio = io.BytesIO()
        img.save(bio, 'PNG')
        bio.seek(0)
        await update.message.reply_photo(photo=bio, caption=f"✨ Berhasil! Mode: {mode.upper()} ({i+1}/{num_imgs})")

    context.user_data['mode'] = None

async def set_mode(update: Update, context):
    mode = update.message.text.replace('/', '')
    context.user_data['mode'] = mode
    await update.message.reply_text(f"✅ Mode {mode.upper()} aktif. Silakan kirim daftar barangnya.", reply_markup=ForceReply())

def main():
    if not TOKEN: return
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler(["promo", "normal", "paket"], set_mode))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

if __name__ == "__main__":
    main()
