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

# --- WARNA (DISETTING LEBIH KONTRAS) ---
YELLOW = (255, 230, 0)
RED = (255, 0, 0)          # Merah murni untuk coretan
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BRIGHT_BLUE = (0, 80, 180) # Biru Terang (Sky/Ocean Blue)
PAKET_RED = (255, 80, 80)   # Merah Muda Terang untuk teks agar kontras di biru

COLS, ROWS = 2, 4
ITEMS_PER_IMAGE = COLS * ROWS
CELL_W, CELL_H = 600, 450
BORDER = 15
IMG_W = COLS * CELL_W + (COLS + 1) * BORDER
IMG_H = ROWS * CELL_H + (ROWS + 1) * BORDER

# Keyboard Menu
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

# --- FUNGSI UTAMA PAKET (PERBAIKAN VISUAL) ---
def draw_paket(draw, x, y, h_lama, h_baru):
    # 1. Kotak Utama (Biru Terang)
    draw.rectangle([x, y, x + CELL_W, y + CELL_H], fill=BRIGHT_BLUE, outline=WHITE, width=10)
    
    # 2. Judul (PAKET HEMAT) - Posisi Y: 60
    draw.text((x + CELL_W//2, y + 60), "PAKET HEMAT", fill=PAKET_RED, anchor="mm", font=get_font(75))
    
    # 3. Harga Normal (Lama) - DIBUAT JAUH LEBIH BESAR
    # Posisi Y diturunkan sedikit agar tidak mepet judul
    txt_lama = format_angka(h_lama)
    size_lama = 120 # Ukuran ditingkatkan ke 120
    f_old = get_font(size_lama, True)
    
    y_center_lama = y + 175
    draw.text((x + CELL_W//2, y_center_lama), txt_lama, fill=WHITE, anchor="mm", font=f_old)
    
    # Garis Coret Merah (Sangat Tebal & Lebih Lebar dari Teks)
    bbox = draw.textbbox((0, 0), txt_lama, font=f_old)
    tw = bbox[2] - bbox[0]
    draw.line([x + (CELL_W-tw)//2 - 20, y_center_lama, x + (CELL_W+tw)//2 + 20, y_center_lama], 
              fill=RED, width=15)

    # 4. Label "HARGA SPESIAL" - Posisi Y: 270
    draw.text((x + CELL_W//2, y + 270), "HARGA SPESIAL", fill=YELLOW, anchor="mm", font=get_font(55))
    
    # 5. Harga Promo (Baru) - UKURAN MAKSIMAL
    # Menggunakan auto-size agar jika angka jutaan tetap muat
    current_size = 220
    font_promo = get_font(current_size, True)
    txt_promo = format_angka(h_baru)
    
    while current_size > 50:
        bbox_p = draw.textbbox((0, 0), txt_promo, font=font_promo)
        if (bbox_p[2] - bbox_p[0]) <= (CELL_W - 60): break
        current_size -= 10
        font_promo = get_font(current_size, True)
        
    draw.text((x + CELL_W//2, y + 375), txt_promo, fill=WHITE, anchor="mm", font=font_promo)

# --- FUNGSI PROMO & NORMAL ---
def draw_promo(draw, x, y, nama, harga):
    draw.rectangle([x, y, x + CELL_W, y + CELL_H], fill=YELLOW, outline=BLACK, width=5)
    draw.rectangle([x, y, x + CELL_W, y + 100], fill=RED)
    draw.text((x + CELL_W//2, y + 50), "PROMOSI", fill=YELLOW, anchor="mm", font=get_font(65))
    draw.text((x + CELL_W//2, y + 180), nama.upper(), fill=BLACK, anchor="mm", font=get_font(55))
    draw.text((x + CELL_W//2, y + 330), format_angka(harga), fill=RED, anchor="mm", font=get_font(180))

def draw_normal(draw, x, y, nama, harga):
    draw.rectangle([x, y, x + CELL_W, y + CELL_H], fill=WHITE, outline=(200, 200, 200), width=5)
    draw.text((x + CELL_W//2, y + 130), nama.upper(), fill=BLACK, anchor="mm", font=get_font(55))
    draw.text((x + CELL_W//2, y + 310), format_angka(harga), fill=BLACK, anchor="mm", font=get_font(180))

# --- BOT HANDLERS ---
async def start(update: Update, context):
    await update.message.reply_text("Pilih mode cetak:", reply_markup=MAIN_KEYBOARD)

async def set_mode(update: Update, context):
    mode = update.message.text.replace('/', '')
    context.user_data['mode'] = mode
    await update.message.reply_text(f"Mode {mode.upper()} Aktif. Kirim data (Contoh: 15000.10000.4)", reply_markup=ForceReply())

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
