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

# --- KONFIGURASI WARNA PERSIS CONTOH (UPDATED) ---
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BLUE_BG_ROYAL = (0, 102, 210)  # Biru Cerah Royal (Updated)
RED_TEXT_HEADER = (220, 0, 0) # Merah Header (Updated)
RED_SHADOW_HEADER = (160, 0, 0) # Merah Tua Bayangan Header (Updated)

# --- UKURAN GRID & CELL ---
COLS, ROWS = 2, 4
ITEMS_PER_IMAGE = COLS * ROWS
CELL_W, CELL_H = 600, 450
BORDER_GRID = 10
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

# --- FUNGSI CLONE LAYOUT: PAKET (UPDATED & PERBAIKAN TOTAL) ---
def draw_paket(draw, x, y, h_lama, h_baru):
    # 1. Background Biru
    draw.rectangle([x, y, x + CELL_W, y + CELL_H], fill=BLUE_BG_ROYAL)
    
    # 2. Header "PAKET HEMAT" (Gaya Berbayang Mewah)
    txt_header = "PAKET HEMAT"
    f_header = get_font(75, True)
    # Gambar bayangan merah dulu
    draw.text((x + CELL_W//2 + 5, y + 55), txt_header, fill=RED_SHADOW_HEADER, anchor="mm", font=f_header)
    # Gambar teks utama
    draw.text((x + CELL_W//2, y + 50), txt_header, fill=RED_TEXT_HEADER, anchor="mm", font=f_header)

    # 3. Baris Harga Normal (HAPUS LATAR HITAM & BESARKAN FONT)
    draw.text((x + 15, y + 110), "Harga Normal", fill=WHITE, anchor="lm", font=get_font(32, False))
    
    # Simbol Rp Normal (Langsung di atas biru, HAPUS LATAR HITAM KECIL)
    draw.text((x + 230, y + 110), "Rp", fill=WHITE, anchor="lm", font=get_font(30, True))
    
    # Angka Harga Normal (DIBESARKAN DRASHIS)
    txt_old = format_angka(h_lama)
    f_old = get_font(70, True) # Font diperbesar signifikan (Updated)
    draw.text((x + 300, y + 110), txt_old, fill=WHITE, anchor="lm", font=f_old)
    
    # Coretan Mewah pada Harga Normal
    bbox_old = draw.textbbox((x + 300, y + 110), txt_old, font=f_old, anchor="lm")
    draw.line([bbox_old[0]-5, y+110, bbox_old[2]+5, y+110], fill=WHITE, width=6)

    # 4. Area Harga Spesial (Blok Hitam Besar & Autofit)
    draw.text((x + 15, y + 160), "Harga Spesial", fill=WHITE, anchor="lm", font=get_font(32, False))
    # Blok Hitam Utama
    draw.rectangle([x + 15, y + 185, x + CELL_W - 15, y + CELL_H - 15], fill=BLACK)
    # Label Rp di dalam blok hitam
    draw.text((x + 35, y + 225), "Rp", fill=WHITE, anchor="mm", font=get_font(40, True))
    
    # 5. Autofit Angka Harga Baru (UKURAN MAKSIMAL DITINGKATKAN)
    txt_new = format_angka(h_baru)
    curr_size = 210 # Ukuran maksimal proposional (Updated)
    font_new = get_font(curr_size, True)
    
    while curr_size > 50:
        bw = draw.textbbox((0, 0), txt_new, font=font_new)[2]
        if bw <= (CELL_W - 120): break # Beri ruang dari Rp
        curr_size -= 10
        font_new = get_font(curr_size, True)
    
    # Teks Harga Baru di Tengah Blok Hitam
    draw.text((x + CELL_W//2 + 30, y + 320), txt_new, fill=WHITE, anchor="mm", font=font_new)

# --- FUNGSI PROMO & NORMAL LAINNYA ---
def draw_promo(draw, x, y, nama, harga):
    draw.rectangle([x, y, x + CELL_W, y + CELL_H], fill=(255, 240, 0), outline=BLACK, width=1)
    draw.rectangle([x, y, x + CELL_W, y + 90], fill=RED_TEXT_HEADER)
    draw.text((x + CELL_W//2, y + 45), "PROMOSI", fill=(255, 240, 0), anchor="mm", font=get_font(55))
    draw.text((x + CELL_W//2, y + 175), nama.upper(), fill=BLACK, anchor="mm", font=get_font(50))
    draw.text((x + CELL_W//2, y + 330), format_angka(harga), fill=RED_TEXT_HEADER, anchor="mm", font=get_font(160))

def draw_normal(draw, x, y, nama, harga):
    draw.rectangle([x, y, x + CELL_W, y + CELL_H], fill=WHITE, outline=BLACK, width=1)
    draw.text((x + CELL_W//2, y + 130), nama.upper(), fill=BLACK, anchor="mm", font=get_font(50))
    draw.text((x + CELL_W//2, y + 300), format_angka(harga), fill=BLACK, anchor="mm", font=get_font(160))

# --- HANDLERS BOT ---
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
            qty = int(parts[2]) if len(parts) >= 3 else 1
            for _ in range(qty):
                if mode == 'paket': final_items.append({'h_awal': parts[0], 'h_promo': parts[1]})
                else: final_items.append({'nama': parts[Part1], 'harga': parts[Part2]}) # Fixed Index
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
