import os
import io
import math
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from PIL import Image, ImageDraw, ImageFont

# Konfigurasi Token
TOKEN = os.environ.get("TELEGRAM_TOKEN")

# Konfigurasi Warna
YELLOW, RED, BLACK, WHITE = (255, 230, 0), (204, 0, 0), (0, 0, 0), (255, 255, 255)
DARK_BLUE, PAKET_RED = (15, 45, 90), (230, 30, 30)

# Konfigurasi Ukuran
COLS, ROWS = 2, 4
ITEMS_PER_IMAGE = COLS * ROWS
CELL_W, CELL_H = 600, 450
BORDER = 15
HEADER_H = 90
IMG_W = COLS * CELL_W + (COLS + 1) * BORDER
IMG_H = ROWS * CELL_H + (ROWS + 1) * BORDER

def get_font(size):
    """Mencari font di sistem Linux (Railway) atau Lokal"""
    paths = [
        "arialbd.ttf", # Jika kamu upload file font ke Github
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", # Default Linux
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
    ]
    for path in paths:
        try:
            return ImageFont.truetype(path, size)
        except:
            continue
    return ImageFont.load_default()

# Inisialisasi Font (Besar)
FONT_BIG = get_font(130)   # Harga
FONT_MED = get_font(55)    # Nama Barang
FONT_HEAD = get_font(65)   # Tulisan PROMOSI
FONT_SMALL = get_font(30)  # Label kecil

def format_harga(harga_str):
    try:
        angka = int(str(harga_str).replace(".", "").replace(",", ""))
        return f"{angka:,}".replace(",", ".")
    except:
        return str(harga_str)

def draw_promo(draw, x, y, nama, harga):
    draw.rectangle([x, y, x + CELL_W, y + CELL_H], fill=YELLOW, outline=BLACK, width=3)
    draw.rectangle([x, y, x + CELL_W, y + HEADER_H], fill=RED)
    draw.text((x + CELL_W//2, y + HEADER_H//2), "PROMOSI", fill=YELLOW, anchor="mm", font=FONT_HEAD)
    if nama:
        draw.text((x + CELL_W//2, y + 160), nama.upper(), fill=BLACK, anchor="mm", font=FONT_MED)
    if harga:
        draw.text((x + CELL_W//2, y + 320), f"Rp {format_harga(harga)}", fill=RED, anchor="mm", font=FONT_BIG)

def draw_normal(draw, x, y, nama, harga):
    draw.rectangle([x, y, x + CELL_W, y + CELL_H], fill=WHITE, outline=(200, 200, 200), width=4)
    if nama:
        draw.text((x + CELL_W//2, y + 120), nama.upper(), fill=BLACK, anchor="mm", font=FONT_MED)
    if harga:
        draw.text((x + CELL_W//2, y + 300), f"Rp {format_harga(harga)}", fill=BLACK, anchor="mm", font=FONT_BIG)

def draw_paket(draw, x, y, h_lama, h_baru):
    draw.rectangle([x, y, x + CELL_W, y + CELL_H], fill=DARK_BLUE, outline=WHITE, width=5)
    draw.text((x + CELL_W//2, y + 60), "PAKET HEMAT", fill=PAKET_RED, anchor="mm", font=FONT_HEAD)
    
    if h_lama:
        txt = f"Harga Normal: Rp {format_harga(h_lama)}"
        draw.text((x + CELL_W//2, y + 160), txt, fill=WHITE, anchor="mm", font=FONT_SMALL)
        # Garis Coret
        draw.line([x + 150, y + 160, x + 450, y + 160], fill=RED, width=5)

    if h_baru:
        draw.text((x + CELL_W//2, y + 230), "HARGA SPESIAL", fill=YELLOW, anchor="mm", font=FONT_SMALL)
        draw.text((x + CELL_W//2, y + 330), f"Rp {format_harga(h_baru)}", fill=WHITE, anchor="mm", font=FONT_BIG)

async def start(update: Update, context):
    await update.message.reply_text(
        "Pilih Mode:",
        reply_markup=ReplyKeyboardMarkup([[KeyboardButton("/promo"), KeyboardButton("/normal"), KeyboardButton("/paket")]], resize_keyboard=True)
    )

async def handle_text(update: Update, context):
    mode = context.user_data.get('mode')
    if not mode:
        await update.message.reply_text("Klik /promo, /normal atau /paket dulu ya!")
        return

    lines = update.message.text.split('\n')
    items = [l.split('.') for l in lines if '.' in l]

    if not items:
        await update.message.reply_text("Format salah. Contoh: Sabun.5000")
        return

    img = Image.new('RGB', (IMG_W, IMG_H), color=(240, 240, 240))
    draw = ImageDraw.Draw(img)

    for i in range(ITEMS_PER_IMAGE):
        c, r = i % COLS, i // COLS
        x, y = BORDER + c*(CELL_W+BORDER), BORDER + r*(CELL_H+BORDER)
        if i < len(items):
            it = items[i]
            if mode == 'promo': draw_promo(draw, x, y, it[0], it[1])
            elif mode == 'normal': draw_normal(draw, x, y, it[0], it[1])
            elif mode == 'paket': draw_paket(draw, x, y, it[0], it[1])
        else:
            draw.rectangle([x, y, x + CELL_W, y + CELL_H], fill=(225, 225, 225))

    bio = io.BytesIO()
    img.save(bio, 'PNG')
    bio.seek(0)
    await update.message.reply_photo(photo=bio)
    context.user_data['mode'] = None

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("promo", lambda u, c: (c.user_data.update({'mode': 'promo'}), u.message.reply_text("Kirim NAMA.HARGA"))))
    app.add_handler(CommandHandler("normal", lambda u, c: (c.user_data.update({'mode': 'normal'}), u.message.reply_text("Kirim NAMA.HARGA"))))
    app.add_handler(CommandHandler("paket", lambda u, c: (c.user_data.update({'mode': 'paket'}), u.message.reply_text("Kirim H_LAMA.H_BARU"))))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.run_polling()

if __name__ == "__main__":
    main()
