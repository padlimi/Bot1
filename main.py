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

# --- WARNA ---
YELLOW = (255, 230, 0)
RED = (255, 0, 0)          
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BRIGHT_BLUE = (0, 80, 180) 
PAKET_RED = (255, 80, 80)   

COLS, ROWS = 2, 4
ITEMS_PER_IMAGE = COLS * ROWS
CELL_W, CELL_H = 600, 450
BORDER = 15
IMG_W = COLS * CELL_W + (COLS + 1) * BORDER
IMG_H = ROWS * CELL_H + (ROWS + 1) * BORDER

MAIN_KEYBOARD = ReplyKeyboardMarkup([
    [KeyboardButton("/promo"), KeyboardButton("/normal")],
    [KeyboardButton("/paket")]
], resize_keyboard=True)

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

# --- FUNGSI UTAMA PAKET (PENYESUAIAN UKURAN FONT) ---
def draw_paket(draw, x, y, h_lama, h_baru):
    # 1. Kotak Utama
    draw.rectangle([x, y, x + CELL_W, y + CELL_H], fill=BRIGHT_BLUE, outline=WHITE, width=10)
    
    # 2. Header "PAKET HEMAT" (Ukuran disesuaikan sedikit)
    draw.text((x + CELL_W//2, y + 55), "PAKET HEMAT", fill=PAKET_RED, anchor="mm", font=get_font(65))
    
    # 3. Harga Normal (Lama) - UKURAN DIKECILKAN AGAR RAPI
    txt_lama = format_angka(h_lama)
    size_lama = 90 # Sebelumnya 120, sekarang 90 agar tidak menabrak
    f_old = get_font(size_lama, True)
    
    y_center_lama = y + 155
    draw.text((x + CELL_W//2, y_center_lama), txt_lama, fill=WHITE, anchor="mm", font=f_old)
    
    # Garis Coret Merah (Tebal tetap 12 agar jelas)
    bbox = draw.textbbox((0, 0), txt_lama, font=f_old)
    tw = bbox[2] - bbox[0]
    draw.line([x + (CELL_W-tw)//2 - 10, y_center_lama, x + (CELL_W+tw)//2 + 10, y_center_lama], 
              fill=RED, width=12)

    # 4. Label "HARGA SPESIAL"
    draw.text((x + CELL_W//2, y + 250), "HARGA SPESIAL", fill=YELLOW, anchor="mm", font=get_font(45))
    
    # 5. Harga Promo (Baru) - UKURAN DIKECILKAN AGAR PROPORSIONAL
    max_promo_size = 170 # Sebelumnya 220, sekarang 170 agar ada ruang di bawah
    txt_promo = format_angka(h_baru)
    
    current_size = max_promo_size
    font_promo = get_font(current_size, True)
    while current_size > 50:
        bbox_p = draw.textbbox((0, 0), txt_promo, font=font_promo)
        if (bbox_p[2] - bbox_p[0]) <= (CELL_W - 80): break
        current_size -= 10
        font_promo = get_font(current_size, True)
        
    draw.text((x + CELL_W//2, y + 360), txt_promo, fill=WHITE, anchor="mm", font=font_promo)

# --- FUNGSI PROMO & NORMAL ---
def draw_promo(draw, x, y, nama, harga):
    draw.rectangle([x, y, x + CELL_W, y + CELL_H], fill=YELLOW, outline=BLACK, width=5)
    draw.rectangle([x, y, x + CELL_W, y + 90], fill=RED)
    draw.text((x + CELL_W//2, y + 45), "PROMOSI", fill=YELLOW, anchor="mm", font=get_font(60))
    draw.text((x + CELL_W//2, y + 170), nama.upper(), fill=BLACK, anchor="mm", font=get_font(50))
    draw.text((x + CELL_W//2, y + 330), format_angka(harga), fill=RED, anchor="mm", font=get_font(160))

def draw_normal(draw, x, y, nama, harga):
    draw.rectangle([x, y, x + CELL_W, y + CELL_H], fill=WHITE, outline=(200, 200, 200), width=5)
    draw.text((x + CELL_W//2, y + 120), nama.upper(), fill=BLACK, anchor="mm", font=get_font(50))
    draw.text((x + CELL_W//2, y + 300), format_angka(harga), fill=BLACK, anchor="mm", font=get_font(160))

# --- BOT HANDLERS ---
async def start(update: Update, context):
    await update.message.reply_text("Silahkan pilih mode cetak di bawah:", reply_markup=MAIN_KEYBOARD)

async def set_mode(update: Update, context):
    mode = update.message.text.replace('/', '')
    context.user_data['mode'] = mode
    await update.message.reply_text(f"Mode {mode.upper()} Aktif. Kirim data (Contoh: 100000.7000.1)", reply_markup=ForceReply())

async def handle_message(update: Update, context):
    mode = context.user_data.get('mode')
    if not mode: return

    lines = update.message.text.strip().split('\n')
    final_items = []

    for line in lines:
        parts = line.split('.')
        if len(parts) < 2: continue
        
        if mode == 'paket' and len(parts) >= 3:
            try:
                for _ in range(int(parts[2])):
                    final_items.append({'h_awal': parts[0], 'h_promo': parts[1]})
            except: final_items.append({'h_awal': parts[0], 'h_promo': parts[1]})
        elif mode != 'paket':
            final_items.append({'nama': parts[0], 'harga': parts[1]})

    if not final_items: return

    num_imgs = math.ceil(len(final_items) / ITEMS_PER_IMAGE)
    for i in range(num_imgs):
        batch = final_items[i * ITEMS_PER_IMAGE : (i + 1) * ITEMS_PER_IMAGE]
        img = Image.new('RGB', (IMG_W, IMG_H), color=WHITE)
        draw = ImageDraw.Draw(img)

        for idx in range(ITEMS_PER_IMAGE):
            c, r = idx % COLS, idx // COLS
            x_pos, y_pos = BORDER + c*(CELL_W+BORDER), BORDER + r*(CELL_H+BORDER)
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
