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

# --- KONFIGURASI WARNA ---
YELLOW = (255, 230, 0)
RED_PURE = (255, 0, 0)      # Untuk coretan
RED_DEEP = (180, 0, 0)      # Merah Pekat untuk teks "PAKET HEMAT"
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BRIGHT_BLUE = (0, 80, 180) 

# --- UKURAN GRID & CELL ---
COLS, ROWS = 2, 4
ITEMS_PER_IMAGE = COLS * ROWS
CELL_W, CELL_H = 600, 450
BORDER_GRID = 15
LINE_ULTRA_THIN = 1  # Batas gambar dibuat 1 pixel
IMG_W = COLS * CELL_W + (COLS + 1) * BORDER_GRID
IMG_H = ROWS * CELL_H + (ROWS + 1) * BORDER_GRID

# --- KEYBOARD PERMANEN ---
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

# --- FUNGSI DRAW: PAKET ---
def draw_paket(draw, x, y, h_lama, h_baru):
    # Background & Outline 1 Pixel
    draw.rectangle([x, y, x + CELL_W, y + CELL_H], fill=BRIGHT_BLUE, outline=WHITE, width=LINE_ULTRA_THIN)
    
    # Header PAKET HEMAT (Merah Pekat)
    draw.text((x + CELL_W//2, y + 55), "PAKET HEMAT", fill=RED_DEEP, anchor="mm", font=get_font(60))
    
    # Harga Normal (Lama)
    txt_lama = format_angka(h_lama)
    f_old = get_font(80, True)
    y_lama = y + 150
    draw.text((x + CELL_W//2, y_lama), txt_lama, fill=WHITE, anchor="mm", font=f_old)
    
    # Coretan
    bbox = draw.textbbox((0, 0), txt_lama, font=f_old)
    tw = bbox[2] - bbox[0]
    draw.line([x + (CELL_W-tw)//2 - 5, y_lama, x + (CELL_W+tw)//2 + 5, y_lama], fill=RED_PURE, width=8)

    # Label & Harga Baru
    draw.text((x + CELL_W//2, y + 245), "HARGA SPESIAL", fill=YELLOW, anchor="mm", font=get_font(45))
    
    txt_promo = format_angka(h_baru)
    curr_size = 175
    font_p = get_font(curr_size, True)
    while curr_size > 50:
        bw = draw.textbbox((0, 0), txt_promo, font=font_p)[2] - draw.textbbox((0, 0), txt_promo, font=font_p)[0]
        if bw <= (CELL_W - 80): break
        curr_size -= 10
        font_p = get_font(curr_size, True)
    draw.text((x + CELL_W//2, y + 355), txt_promo, fill=WHITE, anchor="mm", font=font_p)

# --- FUNGSI DRAW: PROMO & NORMAL ---
def draw_promo(draw, x, y, nama, harga):
    draw.rectangle([x, y, x + CELL_W, y + CELL_H], fill=YELLOW, outline=BLACK, width=LINE_ULTRA_THIN)
    draw.rectangle([x, y, x + CELL_W, y + 90], fill=RED_PURE)
    draw.text((x + CELL_W//2, y + 45), "PROMOSI", fill=YELLOW, anchor="mm", font=get_font(55))
    draw.text((x + CELL_W//2, y + 175), nama.upper(), fill=BLACK, anchor="mm", font=get_font(50))
    draw.text((x + CELL_W//2, y + 340), format_angka(harga), fill=RED_PURE, anchor="mm", font=get_font(160))

def draw_normal(draw, x, y, nama, harga):
    draw.rectangle([x, y, x + CELL_W, y + CELL_H], fill=WHITE, outline=(200, 200, 200), width=LINE_ULTRA_THIN)
    draw.text((x + CELL_W//2, y + 130), nama.upper(), fill=BLACK, anchor="mm", font=get_font(50))
    draw.text((x + CELL_W//2, y + 310), format_angka(harga), fill=BLACK, anchor="mm", font=get_font(160))

# --- HANDLER BOT ---
async def start(update: Update, context):
    await update.message.reply_text("Silahkan pilih mode cetak:", reply_markup=MAIN_KEYBOARD)

async def set_mode(update: Update, context):
    mode = update.message.text.replace('/', '')
    context.user_data['mode'] = mode
    await update.message.reply_text(f"Mode {mode.upper()} Aktif.", reply_markup=ForceReply())

async def handle_message(update: Update, context):
    mode = context.user_data.get('mode')
    if not mode: return

    lines = update.message.text.strip().split('\n')
    final_items = []

    for line in lines:
        parts = line.split('.')
        if len(parts) < 2: continue
        try:
            if mode == 'paket' and len(parts) >= 3:
                for _ in range(int(parts[2])):
                    final_items.append({'h_awal': parts[0], 'h_promo': parts[1]})
            elif mode == 'paket':
                final_items.append({'h_awal': parts[0], 'h_promo': parts[1]})
            else:
                final_items.append({'nama': parts[0], 'harga': parts[1]})
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
