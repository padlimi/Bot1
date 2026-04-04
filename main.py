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

# --- WARNA (DIOPTIMALKAN) ---
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BRIGHT_BLUE = (0, 110, 230)  # Biru Royal Cerah
RED_TEXT = (220, 0, 0)       # Merah tajam untuk header
YELLOW_LABEL = (255, 230, 0) # Kuning untuk label kecil

# --- UKURAN GRID ---
COLS, ROWS = 2, 4
ITEMS_PER_IMAGE = COLS * ROWS
CELL_W, CELL_H = 600, 450
BORDER_GRID = 12
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

# --- FUNGSI UTAMA PAKET (PERBAIKAN TOTAL LAYOUT) ---
def draw_paket(draw, x, y, h_lama, h_baru):
    # 1. Background Split (Atas Biru, Bawah Hitam)
    split_h = int(CELL_H * 0.38)
    draw.rectangle([x, y, x + CELL_W, y + split_h], fill=BRIGHT_BLUE)
    draw.rectangle([x, y + split_h, x + CELL_W, y + CELL_H], fill=BLACK)
    # Outline tipis 1px
    draw.rectangle([x, y, x + CELL_W, y + CELL_H], outline=WHITE, width=1)

    # 2. Header "PAKET HEMAT"
    draw.text((x + CELL_W//2, y + 45), "PAKET HEMAT", fill=RED_TEXT, anchor="mm", font=get_font(60))

    # 3. Label & Harga Normal (Di bagian Biru)
    draw.text((x + 15, y + 90), "Harga Normal:", fill=WHITE, anchor="lm", font=get_font(28, False))
    
    txt_old = format_angka(h_lama)
    f_old = get_font(65, True)
    # Rp kecil untuk harga lama
    draw.text((x + 15, y + 135), "Rp", fill=WHITE, anchor="lm", font=get_font(25, True))
    # Angka harga lama
    draw.text((x + 60, y + 135), txt_old, fill=WHITE, anchor="lm", font=f_old)
    
    # Coretan Putih pada Harga Lama
    bbox_old = draw.textbbox((x + 60, y + 135), txt_old, font=f_old, anchor="lm")
    draw.line([bbox_old[0]-5, y+135, bbox_old[2]+5, y+135], fill=WHITE, width=5)

    # 4. Label & Harga Spesial (Di bagian Hitam)
    draw.text((x + 15, y + split_h + 25), "Harga Spesial:", fill=YELLOW_LABEL, anchor="lm", font=get_font(28, False))
    
    # Simbol Rp besar di kiri atas blok hitam
    draw.text((x + 20, y + split_h + 75), "Rp", fill=WHITE, anchor="lm", font=get_font(40, True))

    # 5. Autofit Harga Baru (Putih Besar di tengah Hitam)
    txt_new = format_angka(h_baru)
    curr_size = 200
    font_new = get_font(curr_size, True)
    # Cek lebar agar tidak meluap
    while curr_size > 50:
        bw = draw.textbbox((0, 0), txt_new, font=font_new)[2]
        if bw <= (CELL_W - 100): break
        curr_size -= 10
        font_new = get_font(curr_size, True)

    draw.text((x + CELL_W//2 + 20, y + split_h + 155), txt_new, fill=WHITE, anchor="mm", font=font_new)

# --- FUNGSI PROMO & NORMAL ---
def draw_promo(draw, x, y, nama, harga):
    draw.rectangle([x, y, x + CELL_W, y + CELL_H], fill=YELLOW_LABEL, outline=BLACK, width=1)
    draw.rectangle([x, y, x + CELL_W, y + 90], fill=RED_TEXT)
    draw.text((x + CELL_W//2, y + 45), "PROMOSI", fill=YELLOW_LABEL, anchor="mm", font=get_font(55))
    draw.text((x + CELL_W//2, y + 180), nama.upper(), fill=BLACK, anchor="mm", font=get_font(50))
    draw.text((x + CELL_W//2, y + 340), format_angka(harga), fill=RED_TEXT, anchor="mm", font=get_font(170))

def draw_normal(draw, x, y, nama, harga):
    draw.rectangle([x, y, x + CELL_W, y + CELL_H], fill=WHITE, outline=(200, 200, 200), width=1)
    draw.text((x + CELL_W//2, y + 130), nama.upper(), fill=BLACK, anchor="mm", font=get_font(50))
    draw.text((x + CELL_W//2, y + 310), format_angka(harga), fill=BLACK, anchor="mm", font=get_font(170))

# --- BOT HANDLER ---
async def start(update: Update, context):
    await update.message.reply_text("Pilih mode cetak:", reply_markup=MAIN_KEYBOARD)

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
