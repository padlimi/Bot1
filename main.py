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

# --- KONFIGURASI WARNA (SESUAI CONTOH GAMBAR) ---
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED_PURE = (255, 0, 0)          # Untuk coretan tipis
RED_DEEP = (180, 0, 0)          # Merah Pekat Mewah untuk header
BRIGHT_BLUE_ROYAL = (0, 100, 210) # Biru Terang Mewah (Royal Blue)
YELLOW_LABEL = (255, 240, 0)    # Kuning Mewah untuk label

# --- UKURAN GRID & CELL ---
COLS, ROWS = 2, 4
ITEMS_PER_IMAGE = COLS * ROWS
CELL_W, CELL_H = 600, 450
BORDER_GRID = 15
LINE_ULTRA_THIN = 1  # Batas gambar tipis
IMG_W = COLS * CELL_W + (COLS + 1) * BORDER_GRID
IMG_H = ROWS * CELL_H + (ROWS + 1) * BORDER_GRID

# --- KEYBOARD PERMANEN ---
MAIN_KEYBOARD = ReplyKeyboardMarkup([
    [KeyboardButton("/promo"), KeyboardButton("/normal")],
    [KeyboardButton("/paket")]
], resize_keyboard=True, one_time_keyboard=False)

def get_font(size, bold=True, italic=False):
    # Mengutamakan font Roboto, Fallback ke font sistem
    font_file = "Roboto-Bold.ttf" if bold else "Roboto-Regular.ttf"
    if italic: font_file = "Roboto-BoldItalic.ttf" if bold else "Roboto-Italic.ttf"
    
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

# --- FUNGSI DRAW UTAMA: PAKET (LAYOUT MEWAH & RAPI SESUAI CONTOH) ---
def draw_paket(draw, x, y, h_lama, h_baru):
    # 1. Background Kotak Mewah
    # Bagian Atas: Biru Terang (Royal Blue)
    header_height = CELL_H * 0.45
    draw.rectangle([x, y, x + CELL_W, y + header_height], fill=BRIGHT_BLUE_ROYAL, outline=WHITE, width=LINE_ULTRA_THIN)
    
    # Bagian Bawah: Hitam Pekat
    price_block_y = y + header_height
    draw.rectangle([x, price_block_y, x + CELL_W, y + CELL_H], fill=BLACK, outline=WHITE, width=LINE_ULTRA_THIN)
    
    # --- BAGIAN ATAS (BIRU) ---
    # Header "PAKET HEMAT" (Merah Pekat Mewah) - Posisi Y: 55
    draw.text((x + CELL_W//2, y + 55), "PAKET HEMAT", fill=RED_DEEP, anchor="mm", font=get_font(65, bold=True))
    
    # Teks Label "Harga Normal" (Kuning) - Posisi X: 20
    draw.text((x + 20, y + 115), "Harga Normal", fill=YELLOW_LABEL, anchor="lm", font=get_font(40, bold=False))
    
    # Blok Harga Normal (Lama) - Mewah
    txt_lama = format_angka(h_lama)
    f_old_price = get_font(75, bold=True)
    
    # Simbol Rp (Putih Italic) - Posisi X: 20 + Lebar "Harga Normal" + 10
    rp_lama_width = draw.textbbox((0,0), "Rp", font=get_font(40, bold=True, italic=True))[2]
    x_rp_lama = x + 20 + rp_lama_width + 10 # Penempatan rapi
    draw.text((x_rp_lama, y + 165), "Rp", fill=WHITE, anchor="rm", font=get_font(40, bold=True, italic=True))
    
    # Harga Normal Angka (Putih) - Posisi X: x_rp_lama + 10
    x_angka_lama = x_rp_lama + 10
    draw.text((x_angka_lama, y + 165), txt_lama, fill=WHITE, anchor="lm", font=f_old_price)
    
    # Coretan Mewah (Garis Coret tipis Putih di atas Harga Normal)
    bbox_old = draw.textbbox((0,0), txt_lama, font=f_old_price)
    tw_old = bbox_old[2] - bbox_old[0]
    draw.line([x_angka_lama - 5, y + 165, x_angka_lama + tw_old + 5, y + 165], fill=WHITE, width=6)
    
    
    # --- BAGIAN BAWAH (HITAM) ---
    # Teks Label "Harga Spesial" (Kuning) - Posisi X: 20, Y: 220
    draw.text((x + 20, price_block_y + 25), "Harga Spesial", fill=YELLOW_LABEL, anchor="lm", font=get_font(40, bold=False))
    
    # Blok Harga Spesial (Baru) - SANGAT BESAR & JELAS
    txt_promo = format_angka(h_baru)
    
    # Simbol Rp (Putih Italic) - Sesuai Contoh
    x_rp_baru = x + 20
    draw.text((x_rp_baru, price_block_y + 80), "Rp", fill=WHITE, anchor="lm", font=get_font(50, bold=True, italic=True))
    
    # Harga Spesial Angka (Putih) - Auto-Size Proposional
    # Koordinat Tengah Blok Hitam
    curr_size = 200 # Ukuran maksimal proposional
    font_p = get_font(curr_size, bold=True)
    
    # Auto-fit proposional agar tidak menabrak label
    while curr_size > 50:
        bw = draw.textbbox((0, 0), txt_promo, font=font_p)[2] - draw.textbbox((0, 0), txt_promo, font=font_p)[0]
        if bw <= (CELL_W - rp_lama_width - 80): break # Beri ruang dari Rp
        curr_size -= 10
        font_p = get_font(curr_size, bold=True)
        
    # Penempatan harga rapi di tengah blok hitam, sedikit bergeser dari Rp
    draw.text((x + CELL_W//2 + rp_lama_width//2 + 10, price_block_y + 160), txt_promo, fill=WHITE, anchor="mm", font=font_p)

# --- FUNGSI DRAW LAINNYA (TETAP SAMA, OUTLINE TIPIS) ---
def draw_promo(draw, x, y, nama, harga):
    draw.rectangle([x, y, x + CELL_W, y + CELL_H], fill=YELLOW_LABEL, outline=BLACK, width=LINE_ULTRA_THIN)
    draw.rectangle([x, y, x + CELL_W, y + 90], fill=RED_PURE)
    draw.text((x + CELL_W//2, y + 45), "PROMOSI", fill=YELLOW_LABEL, anchor="mm", font=get_font(55))
    draw.text((x + CELL_W//2, y + 175), nama.upper(), fill=BLACK, anchor="mm", font=get_font(50))
    draw.text((x + CELL_W//2, y + 340), format_angka(harga), fill=RED_PURE, anchor="mm", font=get_font(160))

def draw_normal(draw, x, y, nama, harga):
    draw.rectangle([x, y, x + CELL_W, y + CELL_H], fill=WHITE, outline=(200, 200, 200), width=LINE_ULTRA_THIN)
    draw.text((x + CELL_W//2, y + 130), nama.upper(), fill=BLACK, anchor="mm", font=get_font(50))
    draw.text((x + CELL_W//2, y + 310), format_angka(harga), fill=BLACK, anchor="mm", font=get_font(160))

# --- HANDLER BOT ---
async def start(update: Update, context):
    await update.message.reply_text("Silahkan pilih mode cetak Mewah di bawah:", reply_markup=MAIN_KEYBOARD)

async def set_mode(update: Update, context):
    mode = update.message.text.replace('/', '')
    context.user_data['mode'] = mode
    await update.message.reply_text(f"✅ Mode {mode.upper()} MEWAH Aktif.\nKirim data (Contoh: 100000.7000.2)", reply_markup=ForceReply())

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
                final_items.append({'nama': parts[0], 'harga': parts[Part2]})
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
