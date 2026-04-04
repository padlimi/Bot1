import os
import io
import math
import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ForceReply
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from PIL import Image, ImageDraw, ImageFont

# --- LOGGING ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
TOKEN = os.environ.get("TELEGRAM_TOKEN")

# --- KONFIGURASI WARNA PERSIS GAMBAR ---
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BLUE_BG = (10, 80, 180)    # Biru latar belakang
RED_SHADOW = (180, 0, 0)   # Merah gelap untuk "PAKET"
RED_LIGHT = (255, 40, 40)  # Merah terang untuk bayangan teks

# --- UKURAN GRID ---
COLS, ROWS = 2, 4
ITEMS_PER_IMAGE = COLS * ROWS
CELL_W, CELL_H = 600, 450
BORDER_GRID = 10
IMG_W = COLS * CELL_W + (COLS + 1) * BORDER_GRID
IMG_H = ROWS * CELL_H + (ROWS + 1) * BORDER_GRID

# --- KEYBOARD ---
MAIN_KEYBOARD = ReplyKeyboardMarkup([
    [KeyboardButton("/promo"), KeyboardButton("/normal")],
    [KeyboardButton("/paket")]
], resize_keyboard=True, one_time_keyboard=False)

def get_font(size, bold=True):
    font_file = "Roboto-Bold.ttf" if bold else "Roboto-Regular.ttf"
    paths = [font_file, f"./{font_file}", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
    for path in paths:
        try: return ImageFont.truetype(path, size)
        except: continue
    return ImageFont.load_default()

def format_angka(harga):
    try:
        angka_str = ''.join(filter(str.isdigit, str(harga)))
        return f"{int(angka_str):,}".replace(",", ".")
    except: return str(harga)

# --- FUNGSI CLONE LAYOUT GAMBAR ---
def draw_paket(draw, x, y, h_lama, h_baru):
    # 1. Background Biru
    draw.rectangle([x, y, x + CELL_W, y + CELL_H], fill=BLUE_BG)
    
    # 2. Header "PAKET HEMAT" (Gaya Berbayang/Outline)
    txt_header = "PAKET HEMAT"
    f_header = get_font(75, True)
    # Gambar bayangan merah dulu
    draw.text((x + CELL_W//2 + 4, y + 54), txt_header, fill=RED_SHADOW, anchor="mm", font=f_header)
    # Gambar teks utama
    draw.text((x + CELL_W//2, y + 50), txt_header, fill=RED_LIGHT, anchor="mm", font=f_header)

    # 3. Baris Harga Normal
    draw.text((x + 10, y + 105), "Harga Normal", fill=WHITE, anchor="lm", font=get_font(30, False))
    # Kotak Hitam Kecil untuk Rp Normal
    draw.rectangle([x + 230, y + 85, x + 310, y + 125], fill=BLACK)
    draw.text((x + 240, y + 105), "Rp", fill=WHITE, anchor="lm", font=get_font(28, True))
    # Angka Harga Normal + Coretan
    txt_old = format_angka(h_lama)
    f_old = get_font(45, True)
    draw.text((x + 330, y + 105), txt_old, fill=WHITE, anchor="lm", font=f_old)
    bbox_old = draw.textbbox((x + 330, y + 105), txt_old, font=f_old, anchor="lm")
    draw.line([bbox_old[0]-2, y+105, bbox_old[2]+2, y+105], fill=WHITE, width=4)

    # 4. Area Harga Spesial (Blok Hitam Besar)
    draw.text((x + 10, y + 150), "Harga Spesial", fill=WHITE, anchor="lm", font=get_font(30, False))
    # Blok Hitam Utama
    draw.rectangle([x + 10, y + 175, x + CELL_W - 10, y + CELL_H - 15], fill=BLACK)
    # Label Rp di dalam blok hitam
    draw.text((x + 25, y + 210), "Rp", fill=WHITE, anchor="mm", font=get_font(40, True))
    
    # 5. Autofit Angka Harga Baru
    txt_new = format_angka(h_baru)
    curr_size = 180
    font_new = get_font(curr_size, True)
    while curr_size > 50:
        bw = draw.textbbox((0, 0), txt_new, font=font_new)[2]
        if bw <= (CELL_W - 100): break
        curr_size -= 10
        font_new = get_font(curr_size, True)
    
    # Teks Harga di Tengah Blok Hitam
    draw.text((x + CELL_W//2 + 20, y + 310), txt_new, fill=WHITE, anchor="mm", font=font_new)

# --- FUNGSI PROMO & NORMAL (SEDERHANA) ---
def draw_promo(draw, x, y, nama, harga):
    draw.rectangle([x, y, x + CELL_W, y + CELL_H], fill=(255, 255, 0), outline=BLACK, width=1)
    draw.rectangle([x, y, x + CELL_W, y + 80], fill=(200, 0, 0))
    draw.text((x + CELL_W//2, y + 40), "PROMOSI", fill=WHITE, anchor="mm", font=get_font(50))
    draw.text((x + CELL_W//2, y + 180), nama.upper(), fill=BLACK, anchor="mm", font=get_font(45))
    draw.text((x + CELL_W//2, y + 330), format_angka(harga), fill=(200, 0, 0), anchor="mm", font=get_font(160))

def draw_normal(draw, x, y, nama, harga):
    draw.rectangle([x, y, x + CELL_W, y + CELL_H], fill=WHITE, outline=BLACK, width=1)
    draw.text((x + CELL_W//2, y + 130), nama.upper(), fill=BLACK, anchor="mm", font=get_font(45))
    draw.text((x + CELL_W//2, y + 310), format_angka(harga), fill=BLACK, anchor="mm", font=get_font(160))

# --- HANDLERS ---
async def start(update: Update, context):
    await update.message.reply_text("Silahkan pilih mode:", reply_markup=MAIN_KEYBOARD)

async def set_mode(update: Update, context):
    mode = update.message.text.replace('/', '')
    context.user_data['mode'] = mode
    await update.message.reply_text(f"Mode {mode.upper()} Aktif. Kirim data (ex: 50000.35000.4)", reply_markup=ForceReply())

async def handle_message(update: Update, context):
    mode = context.user_data.get('mode')
    if not mode: return

    lines = update.message.text.strip().split('\n')
    final_items = []
    for line in lines:
        parts = line.split('.')
        if len(parts) < 2: continue
        try:
            qty = int(parts[2]) if len(parts) >= 3 else 1
            for _ in range(qty):
                if mode == 'paket': final_items.append({'h_awal': parts[0], 'h_promo': parts[1]})
                else: final_items.append({'nama': parts[0], 'harga': parts[1]})
        except: continue

    if not final_items: return

    num_imgs = math.ceil(len(final_items) / ITEMS_PER_IMAGE)
    for i in range(num_imgs):
        batch = final_items[i * ITEMS_PER_IMAGE : (i + 1) * ITEMS_PER_IMAGE]
        img = Image.new('RGB', (IMG_W, IMG_H), color=WHITE)
        draw = ImageDraw.Draw(img)
        for idx in range(ITEMS_PER_IMAGE):
            c, r = idx % COLS, idx // COLS
            x_pos, y_pos = BORDER_GRID + c*(CELL_W+BORDER_GRID), BORDER_GRID + r*(CELL_H+BORDER_GRID)
            if idx < len(batch):
                it = batch[idx]
                if mode == 'paket': draw_paket(draw, x_pos, y_pos, it['h_awal'], it['h_promo'])
                elif mode == 'promo': draw_promo(draw, x_pos, y_pos, it['nama'], it['harga'])
                elif mode == 'normal': draw_normal(draw, x_pos, y_pos, it['nama'], it['harga'])
            else:
                draw.rectangle([x_pos, y_pos, x_pos + CELL_W, y_pos + CELL_H], fill=WHITE)

        bio = io.BytesIO()
        img.save(bio, 'PNG')
        bio.seek(0)
        await update.message.reply_photo(photo=bio, reply_markup=MAIN_KEYBOARD)
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
