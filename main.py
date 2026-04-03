import os
import io
import math
import logging
# Pastikan library terinstall: pip install python-telegram-bot Pillow
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ForceReply
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from PIL import Image, ImageDraw, ImageFont

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

TOKEN = os.environ.get("TELEGRAM_TOKEN")

# --- KONFIGURASI ---
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
    font_file = "Roboto-Bold.ttf" if bold else "Roboto-Regular.ttf"
    paths = [font_file, f"./{font_file}", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
    for path in paths:
        try:
            return ImageFont.truetype(path, size)
        except:
            continue
    return ImageFont.load_default()

# Ukuran Font Awal
FONT_PRICE_MAX = 180 # Diperbesar karena "Rp" dihapus
FONT_NAME_SIZE = 55
FONT_HEAD_SIZE = 65
FONT_LABEL_SIZE = 35

def format_angka(harga):
    """Format angka menjadi pemisah ribuan titik"""
    try:
        angka = int(str(harga).replace(".", "").replace(",", ""))
        return f"{angka:,}".replace(",", ".")
    except:
        return str(harga)

def draw_text_auto_size(draw, text, x_center, y_center, max_width, initial_size, color, bold=True):
    """Fungsi sakti agar teks mengecil otomatis jika kepanjangan"""
    current_size = initial_size
    font = get_font(current_size, bold)
    
    # Kecilkan font sampai muat dalam max_width
    while current_size > 20:
        bbox = draw.textbbox((0, 0), text, font=font)
        w = bbox[2] - bbox[0]
        if w <= max_width:
            break
        current_size -= 5
        font = get_font(current_size, bold)
    
    draw.text((x_center, y_center), text, fill=color, anchor="mm", font=font)

# --- FUNGSI MENGGAMBAR ---

def draw_promo(draw, x, y, nama, harga):
    draw.rectangle([x, y, x + CELL_W, y + CELL_H], fill=YELLOW, outline=BLACK, width=4)
    draw.rectangle([x, y, x + CELL_W, y + HEADER_H], fill=RED)
    draw.text((x + CELL_W//2, y + HEADER_H//2), "PROMOSI", fill=YELLOW, anchor="mm", font=get_font(FONT_HEAD_SIZE))
    
    if nama:
        draw_text_auto_size(draw, nama.upper(), x + CELL_W//2, y + 180, CELL_W - 40, FONT_NAME_SIZE, BLACK)
    
    if harga:
        harga_clean = format_angka(harga)
        # Teks Harga tanpa Rp
        draw_text_auto_size(draw, harga_clean, x + CELL_W//2, y + 330, CELL_W - 60, FONT_PRICE_MAX, RED)

def draw_normal(draw, x, y, nama, harga):
    draw.rectangle([x, y, x + CELL_W, y + CELL_H], fill=WHITE, outline=(220, 220, 220), width=5)
    
    if nama:
        draw_text_auto_size(draw, nama.upper(), x + CELL_W//2, y + 130, CELL_W - 40, FONT_NAME_SIZE, BLACK)
    
    if harga:
        harga_clean = format_angka(harga)
        draw_text_auto_size(draw, harga_clean, x + CELL_W//2, y + 310, CELL_W - 60, FONT_PRICE_MAX, BLACK)

def draw_paket(draw, x, y, h_lama, h_baru):
    draw.rectangle([x, y, x + CELL_W, y + CELL_H], fill=DARK_BLUE, outline=WHITE, width=6)
    draw.text((x + CELL_W//2, y + 60), "PAKET HEMAT", fill=PAKET_RED, anchor="mm", font=get_font(FONT_HEAD_SIZE))
    
    if h_lama:
        txt = format_angka(h_lama)
        draw_text_auto_size(draw, txt, x + CELL_W//2, y + 165, CELL_W - 100, FONT_LABEL_SIZE, WHITE, False)
        # Garis Coret manual berdasarkan lebar teks
        bbox = draw.textbbox((0, 0), txt, font=get_font(FONT_LABEL_SIZE, False))
        tw = bbox[2] - bbox[0]
        draw.line([x + (CELL_W-tw)//2, y + 165, x + (CELL_W+tw)//2, y + 165], fill=RED, width=4)

    if h_baru:
        draw.text((x + CELL_W//2, y + 240), "HARGA SPESIAL", fill=YELLOW, anchor="mm", font=get_font(FONT_LABEL_SIZE))
        draw_text_auto_size(draw, format_angka(h_baru), x + CELL_W//2, y + 340, CELL_W - 60, FONT_PRICE_MAX, WHITE)

# --- BOT HANDLERS ---

async def start(update: Update, context):
    kb = [[KeyboardButton("/promo"), KeyboardButton("/normal"), KeyboardButton("/paket")]]
    await update.message.reply_text("Pilih Mode & Kirim Daftar (Contoh: `Aqua.5000`)", 
                                   reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))

async def set_mode(update: Update, context):
    context.user_data['mode'] = update.message.text.replace('/', '')
    await update.message.reply_text(f"Mode {context.user_data['mode'].upper()} Aktif.", reply_markup=ForceReply())

async def handle_message(update: Update, context):
    mode = context.user_data.get('mode')
    if not mode: return
    
    lines = update.message.text.strip().split('\n')
    items = [l.split('.') for l in lines if '.' in l]
    if not items: return

    num_imgs = math.ceil(len(items) / ITEMS_PER_IMAGE)
    for i in range(num_imgs):
        batch = items[i * ITEMS_PER_IMAGE : (i + 1) * ITEMS_PER_IMAGE]
        img = Image.new('RGB', (IMG_W, IMG_H), color=(240, 240, 240))
        draw = ImageDraw.Draw(img)

        for idx in range(ITEMS_PER_IMAGE):
            c, r = idx % COLS, idx // COLS
            x_pos, y_pos = BORDER + c*(CELL_W+BORDER), BORDER + r*(CELL_H+BORDER)
            if idx < len(batch):
                it = batch[idx]
                if mode == 'promo': draw_promo(draw, x_pos, y_pos, it[0], it[1])
                elif mode == 'normal': draw_normal(draw, x_pos, y_pos, it[0], it[1])
                elif mode == 'paket': draw_paket(draw, x_pos, y_pos, it[0], it[1])
            else:
                draw.rectangle([x_pos, y_pos, x_pos + CELL_W, y_pos + CELL_H], fill=(235, 235, 235))

        bio = io.BytesIO()
        img.save(bio, 'PNG')
        bio.seek(0)
        await update.message.reply_photo(photo=bio)
    context.user_data['mode'] = None

def main():
    if not TOKEN: return
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler(["promo", "normal", "paket"], set_mode))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

if __name__ == "__main__":
    main()
