import os
import io
import math
import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ForceReply
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from PIL import Image, ImageDraw, ImageFont

# --- KONFIGURASI LOGGING ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

TOKEN = os.environ.get("TELEGRAM_TOKEN")

# --- KONFIGURASI WARNA & UKURAN ---
YELLOW = (255, 230, 0)
RED = (230, 0, 0)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BRIGHT_BLUE = (0, 60, 150)  # Biru Cerah & Tajam
PAKET_RED = (255, 50, 50)    # Merah Terang untuk Header

COLS, ROWS = 2, 4
ITEMS_PER_IMAGE = COLS * ROWS
CELL_W, CELL_H = 600, 450
BORDER = 15
IMG_W = COLS * CELL_W + (COLS + 1) * BORDER
IMG_H = ROWS * CELL_H + (ROWS + 1) * BORDER

# Keyboard Menu Utama
MAIN_KEYBOARD = ReplyKeyboardMarkup([
    [KeyboardButton("/promo"), KeyboardButton("/normal")],
    [KeyboardButton("/paket")]
], resize_keyboard=True)

def get_font(size, bold=True):
    font_file = "Roboto-Bold.ttf" if bold else "Roboto-Regular.ttf"
    paths = [font_file, f"./{font_file}", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
    for path in paths:
        try:
            return ImageFont.truetype(path, size)
        except:
            continue
    return ImageFont.load_default()

def format_angka(harga):
    try:
        angka_str = ''.join(filter(str.isdigit, str(harga)))
        return f"{int(angka_str):,}".replace(",", ".")
    except:
        return str(harga)

def draw_text_auto_size(draw, text, x_center, y_center, max_width, initial_size, color, bold=True):
    current_size = initial_size
    font = get_font(current_size, bold)
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
    draw.rectangle([x, y, x + CELL_W, y + 100], fill=RED)
    draw.text((x + CELL_W//2, y + 50), "PROMOSI", fill=YELLOW, anchor="mm", font=get_font(65))
    draw_text_auto_size(draw, nama.upper(), x + CELL_W//2, y + 180, CELL_W - 40, 55, BLACK)
    draw_text_auto_size(draw, format_angka(harga), x + CELL_W//2, y + 330, CELL_W - 60, 180, RED)

def draw_normal(draw, x, y, nama, harga):
    draw.rectangle([x, y, x + CELL_W, y + CELL_H], fill=WHITE, outline=(220, 220, 220), width=5)
    draw_text_auto_size(draw, nama.upper(), x + CELL_W//2, y + 130, CELL_W - 40, 55, BLACK)
    draw_text_auto_size(draw, format_angka(harga), x + CELL_W//2, y + 310, CELL_W - 60, 180, BLACK)

def draw_paket(draw, x, y, h_lama, h_baru):
    # Background Biru Cerah
    draw.rectangle([x, y, x + CELL_W, y + CELL_H], fill=BRIGHT_BLUE, outline=WHITE, width=8)
    
    # Header "PAKET HEMAT"
    draw.text((x + CELL_W//2, y + 60), "PAKET HEMAT", fill=PAKET_RED, anchor="mm", font=get_font(75))
    
    # Harga Normal (Lama) - DIBUAT SANGAT BESAR & JELAS
    txt_lama = format_angka(h_lama)
    f_old = get_font(100, True) 
    bbox = draw.textbbox((0, 0), txt_lama, font=f_old)
    tw = bbox[2] - bbox[0]
    
    pos_y_lama = y + 165
    draw.text((x + CELL_W//2, pos_y_lama), txt_lama, fill=WHITE, anchor="mm", font=f_old)
    # Garis Coret Merah Sangat Tebal
    draw.line([x + (CELL_W-tw)//2 - 10, pos_y_lama, x + (CELL_W+tw)//2 + 10, pos_y_lama], fill=RED, width=12)

    # Label "HARGA SPESIAL"
    draw.text((x + CELL_W//2, y + 260), "HARGA SPESIAL", fill=YELLOW, anchor="mm", font=get_font(50))
    
    # Harga Promo (Baru) - UKURAN MAKSIMAL
    draw_text_auto_size(draw, format_angka(h_baru), x + CELL_W//2, y + 360, CELL_W - 50, 210, WHITE)

# --- BOT HANDLERS ---

async def start(update: Update, context):
    await update.message.reply_text(
        "👋 **Selamat Datang!**\n\nSilahkan pilih mode cetak di bawah ini:", 
        reply_markup=MAIN_KEYBOARD,
        parse_mode="Markdown"
    )

async def set_mode(update: Update, context):
    mode = update.message.text.replace('/', '')
    context.user_data['mode'] = mode
    await update.message.reply_text(
        f"✅ Mode {mode.upper()} Aktif.\nKirim data dengan format:\n"
        f"- Promo/Normal: `Nama.Harga` (ex: Aqua.5000)\n"
        f"- Paket: `HargaLama.HargaBaru.Qty` (ex: 15000.12000.8)", 
        reply_markup=ForceReply(selective=True)
    )

async def handle_message(update: Update, context):
    mode = context.user_data.get('mode')
    if not mode:
        await update.message.reply_text("Silahkan pilih mode terlebih dahulu:", reply_markup=MAIN_KEYBOARD)
        return

    lines = update.message.text.strip().split('\n')
    final_items = []

    for line in lines:
        parts = line.split('.')
        if len(parts) < 2: continue
        
        try:
            if mode == 'paket' and len(parts) >= 3:
                h_awal, h_promo, qty = parts[0], parts[1], int(parts[2])
                for _ in range(qty):
                    final_items.append({'h_awal': h_awal, 'h_promo': h_promo})
            elif mode == 'paket' and len(parts) == 2:
                final_items.append({'h_awal': parts[0], 'h_promo': parts[1]})
            else:
                final_items.append({'nama': parts[0], 'harga': parts[1]})
        except:
            continue

    if not final_items:
        await update.message.reply_text("⚠️ Format salah! Gunakan titik sebagai pemisah.", reply_markup=MAIN_KEYBOARD)
        return

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
                if mode == 'promo': draw_promo(draw, x_pos, y_pos, it['nama'], it['harga'])
                elif mode == 'normal': draw_normal(draw, x_pos, y_pos, it['nama'], it['harga'])
                elif mode == 'paket': draw_paket(draw, x_pos, y_pos, it['h_awal'], it['h_promo'])
            else:
                # Kotak kosong otomatis putih polos
                draw.rectangle([x_pos, y_pos, x_pos + CELL_W, y_pos + CELL_H], fill=WHITE)

        bio = io.BytesIO()
        img.save(bio, 'PNG')
        bio.seek(0)
        await update.message.reply_photo(photo=bio, reply_markup=MAIN_KEYBOARD)
    
    # Reset mode setelah selesai kirim
    context.user_data['mode'] = None

def main():
    if not TOKEN:
        print("Error: Token Telegram belum disetting!")
        return
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler(["promo", "normal", "paket"], set_mode))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

if __name__ == "__main__":
    main()
