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
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BLUE_BG = (0, 102, 210)      # Biru cerah
RED_HEADER = (220, 0, 0)     # Merah header
RED_SHADOW = (160, 0, 0)     # Bayangan header
GREEN_SPECIAL = (0, 150, 0)  # Hijau untuk harga spesial (alternatif)
YELLOW_BG = (255, 240, 0)    # Kuning promo

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
    """Mencari font yang tersedia"""
    font_files = [
        "Roboto-Bold.ttf", "Roboto-Regular.ttf",
        "./Roboto-Bold.ttf", "./Roboto-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Helvetica.ttc",  # Mac
        "C:\\Windows\\Fonts\\Arial.ttf",        # Windows
    ]
    
    for font_file in font_files:
        try:
            if bold and "Bold" not in font_file and "DejaVuSans-Bold" not in font_file:
                if "Regular" in font_file:
                    continue
            return ImageFont.truetype(font_file, size)
        except:
            continue
    return ImageFont.load_default()


def format_angka(harga):
    """Format angka dengan pemisah ribuan titik"""
    try:
        # Bersihkan input
        if isinstance(harga, (int, float)):
            angka = int(harga)
        else:
            angka_str = ''.join(filter(str.isdigit, str(harga)))
            angka = int(angka_str) if angka_str else 0
        
        return f"{angka:,}".replace(",", ".")
    except:
        return str(harga)


def draw_paket(draw, x, y, harga_normal, harga_spesial):
    """Gambar kartu PAKET HEMAT sesuai contoh"""
    
    # 1. Background biru
    draw.rectangle([x, y, x + CELL_W, y + CELL_H], fill=BLUE_BG)
    
    # 2. Header "PAKET HEMAT" dengan efek bayangan
    header_text = "PAKET HEMAT"
    header_font = get_font(68, bold=True)
    header_center_x = x + CELL_W // 2
    header_y = y + 55
    
    # Bayangan merah tua
    draw.text((header_center_x + 4, header_y + 4), header_text, 
              fill=RED_SHADOW, anchor="mm", font=header_font)
    # Teks utama merah
    draw.text((header_center_x, header_y), header_text, 
              fill=RED_HEADER, anchor="mm", font=header_font)
    
    # 3. Harga Normal
    y_normal = y + 125
    draw.text((x + 20, y_normal), "Harga Normal", 
              fill=WHITE, anchor="lm", font=get_font(32, bold=False))
    
    # Teks "Rp"
    draw.text((x + 210, y_normal), "Rp", 
              fill=WHITE, anchor="lm", font=get_font(34, bold=True))
    
    # Angka harga normal (besar)
    txt_normal = format_angka(harga_normal)
    normal_font = get_font(72, bold=True)
    draw.text((x + 270, y_normal), txt_normal, 
              fill=WHITE, anchor="lm", font=normal_font)
    
    # Coretan garis putih
    bbox = draw.textbbox((x + 270, y_normal), txt_normal, font=normal_font, anchor="lm")
    line_y = y_normal + 8
    draw.line([bbox[0] - 5, line_y, bbox[2] + 5, line_y], fill=WHITE, width=5)
    
    # 4. Harga Spesial
    y_spesial_label = y + 195
    draw.text((x + 20, y_spesial_label), "Harga Spesial", 
              fill=WHITE, anchor="lm", font=get_font(32, bold=False))
    
    # Kotak hitam untuk harga spesial
    box_y = y + 230
    box_h = CELL_H - 270
    draw.rectangle([x + 15, box_y, x + CELL_W - 15, y + CELL_H - 15], 
                   fill=BLACK)
    
    # Teks "Rp" di dalam kotak hitam
    draw.text((x + 50, box_y + box_h // 2), "Rp", 
              fill=WHITE, anchor="lm", font=get_font(48, bold=True))
    
    # Angka harga spesial (auto fit)
    txt_spesial = format_angka(harga_spesial)
    max_width = CELL_W - 130
    font_size = 160
    
    while font_size > 40:
        test_font = get_font(font_size, bold=True)
        bbox = draw.textbbox((0, 0), txt_spesial, font=test_font)
        if bbox[2] - bbox[0] <= max_width:
            break
        font_size -= 10
    
    spesial_font = get_font(min(font_size, 150), bold=True)
    draw.text((x + CELL_W - 40, box_y + box_h // 2), txt_spesial, 
              fill=WHITE, anchor="rm", font=spesial_font)


def draw_promo(draw, x, y, nama, harga):
    """Kartu PROMOSI"""
    # Background kuning
    draw.rectangle([x, y, x + CELL_W, y + CELL_H], fill=YELLOW_BG, outline=BLACK, width=2)
    
    # Header merah
    draw.rectangle([x, y, x + CELL_W, y + 90], fill=RED_HEADER)
    draw.text((x + CELL_W // 2, y + 50), "PROMOSI", 
              fill=YELLOW_BG, anchor="mm", font=get_font(55, bold=True))
    
    # Nama produk
    nama_text = nama.upper() if len(nama) < 20 else nama[:17] + "..."
    draw.text((x + CELL_W // 2, y + 170), nama_text, 
              fill=BLACK, anchor="mm", font=get_font(48, bold=True))
    
    # Harga
    harga_text = format_angka(harga)
    draw.text((x + CELL_W // 2, y + 320), harga_text, 
              fill=RED_HEADER, anchor="mm", font=get_font(140, bold=True))


def draw_normal(draw, x, y, nama, harga):
    """Kartu NORMAL"""
    # Background putih
    draw.rectangle([x, y, x + CELL_W, y + CELL_H], fill=WHITE, outline=BLACK, width=2)
    
    # Nama produk
    nama_text = nama.upper() if len(nama) < 25 else nama[:22] + "..."
    draw.text((x + CELL_W // 2, y + 140), nama_text, 
              fill=BLACK, anchor="mm", font=get_font(48, bold=True))
    
    # Harga
    draw.text((x + CELL_W // 2, y + 300), format_angka(harga), 
              fill=BLACK, anchor="mm", font=get_font(150, bold=True))


# --- HANDLER BOT ---
async def start(update: Update, context):
    await update.message.reply_text(
        "🎨 *Bot Cetak Harga Mewah*\n\n"
        "Pilih mode:\n"
        "• /paket - Format PAKET HEMAT (2 harga)\n"
        "• /promo - Format PROMOSI (1 harga)\n"
        "• /normal - Format NORMAL (1 harga)\n\n"
        "Format input:\n"
        "• Paket: `harga_normal.harga_spesial`\n"
        "• Promo: `nama.harga`\n"
        "• Normal: `nama.harga`\n\n"
        "Contoh:\n"
        "`42800.31400` (mode paket)\n"
        "`Indomie Goreng.3500` (mode promo/normal)",
        parse_mode="Markdown",
        reply_markup=MAIN_KEYBOARD
    )


async def set_mode(update: Update, context):
    mode = update.message.text.replace('/', '')
    context.user_data['mode'] = mode
    
    mode_names = {
        'paket': '📦 PAKET HEMAT (2 harga)',
        'promo': '🔥 PROMO (diskon)',
        'normal': '📄 NORMAL (harga biasa)'
    }
    
    await update.message.reply_text(
        f"✅ Mode {mode_names.get(mode, mode.upper())} aktif.\n\n"
        f"Kirim data (pisah dengan titik . ):\n"
        f"{'Contoh: 42800.31400' if mode == 'paket' else 'Contoh: Indomie Goreng.3500'}\n"
        f"Bisa multiple line, satu baris satu item.",
        reply_markup=ForceReply()
    )


async def handle_message(update: Update, context):
    mode = context.user_data.get('mode')
    if not mode:
        await update.message.reply_text("❌ Pilih mode dulu: /paket, /promo, atau /normal")
        return
    
    text = update.message.text.strip()
    lines = text.split('\n')
    
    items = []
    errors = []
    
    for line_num, line in enumerate(lines, 1):
        line = line.strip()
        if not line:
            continue
            
        parts = line.split('.')
        
        try:
            if mode == 'paket':
                if len(parts) != 2:
                    errors.append(f"Baris {line_num}: butuh 2 harga (contoh: 42800.31400)")
                    continue
                items.append({
                    'harga_normal': parts[0].strip(),
                    'harga_spesial': parts[1].strip()
                })
            else:  # promo atau normal
                if len(parts) < 2:
                    errors.append(f"Baris {line_num}: butuh nama dan harga (contoh: Indomie.3500)")
                    continue
                nama = '.'.join(parts[:-1]).strip()
                harga = parts[-1].strip()
                items.append({'nama': nama, 'harga': harga})
        except Exception as e:
            errors.append(f"Baris {line_num}: error - {str(e)}")
    
    if errors:
        await update.message.reply_text("⚠️ *Error pada data:*\n" + "\n".join(errors[:5]), parse_mode="Markdown")
        return
    
    if not items:
        await update.message.reply_text("❌ Tidak ada data valid. Kirim ulang dengan format yang benar.")
        return
    
    # Proses pembuatan gambar
    num_images = math.ceil(len(items) / ITEMS_PER_IMAGE)
    
    for img_idx in range(num_images):
        start_idx = img_idx * ITEMS_PER_IMAGE
        end_idx = min(start_idx + ITEMS_PER_IMAGE, len(items))
        batch = items[start_idx:end_idx]
        
        # Buat gambar baru
        img = Image.new('RGB', (IMG_W, IMG_H), color=WHITE)
        draw = ImageDraw.Draw(img)
        
        # Gambar setiap item
        for idx in range(ITEMS_PER_IMAGE):
            row = idx // COLS
            col = idx % COLS
            
            x_pos = BORDER_GRID + col * (CELL_W + BORDER_GRID)
            y_pos = BORDER_GRID + row * (CELL_H + BORDER_GRID)
            
            if idx < len(batch):
                item = batch[idx]
                if mode == 'paket':
                    draw_paket(draw, x_pos, y_pos, item['harga_normal'], item['harga_spesial'])
                elif mode == 'promo':
                    draw_promo(draw, x_pos, y_pos, item['nama'], item['harga'])
                elif mode == 'normal':
                    draw_normal(draw, x_pos, y_pos, item['nama'], item['harga'])
            else:
                # Cell kosong (putih)
                draw.rectangle([x_pos, y_pos, x_pos + CELL_W, y_pos + CELL_H], fill=WHITE)
        
        # Simpan ke buffer
        bio = io.BytesIO()
        img.save(bio, format='PNG')
        bio.seek(0)
        
        # Kirim gambar
        caption = f"📸 Halaman {img_idx + 1} dari {num_images}" if num_images > 1 else None
        await update.message.reply_photo(photo=bio, caption=caption, reply_markup=MAIN_KEYBOARD)
    
    # Reset mode setelah selesai
    context.user_data['mode'] = None
    await update.message.reply_text("✅ Selesai! Pilih mode lagi jika ingin cetak lebih banyak.")


def main():
    if not TOKEN:
        print("❌ ERROR: TELEGRAM_TOKEN tidak ditemukan di environment variables!")
        return
    
    print("🤖 Bot starting...")
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("promo", set_mode))
    app.add_handler(CommandHandler("normal", set_mode))
    app.add_handler(CommandHandler("paket", set_mode))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("✅ Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
