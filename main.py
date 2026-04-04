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
BLUE_BG = (0, 102, 210)
RED_HEADER = (220, 0, 0)
RED_SHADOW = (160, 0, 0)

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
        "/System/Library/Fonts/Helvetica.ttc",
        "C:\\Windows\\Fonts\\Arial.ttf",
        "C:\\Windows\\Fonts\\Arialbd.ttf",
    ]
    
    for font_file in font_files:
        try:
            if bold and "Bold" not in font_file and "bd" not in font_file.lower():
                if "Regular" in font_file or "Arial.ttf" == font_file:
                    continue
            return ImageFont.truetype(font_file, size)
        except:
            continue
    return ImageFont.load_default()


def format_angka(harga):
    """Format angka dengan pemisah ribuan titik"""
    try:
        if isinstance(harga, (int, float)):
            angka = int(harga)
        else:
            angka_str = ''.join(filter(str.isdigit, str(harga)))
            angka = int(angka_str) if angka_str else 0
        return f"{angka:,}".replace(",", ".")
    except:
        return str(harga)


def fit_text_to_width(draw, text, max_width, initial_size, bold=True):
    """Menyesuaikan ukuran font agar muat dalam lebar tertentu"""
    size = initial_size
    while size > 20:
        font = get_font(size, bold)
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        if text_width <= max_width:
            return font, size
        size -= 5
    return get_font(20, bold), 20


def draw_paket(draw, x, y, harga_normal, harga_spesial):
    """Gambar kartu PAKET HEMAT dengan latar hitam untuk harga normal"""
    
    # 1. Background biru
    draw.rectangle([x, y, x + CELL_W, y + CELL_H], fill=BLUE_BG)
    
    # 2. Header "PAKET HEMAT"
    header_text = "PAKET HEMAT"
    header_center_x = x + CELL_W // 2
    header_y = y + 55
    
    header_font = get_font(68, bold=True)
    # Bayangan
    draw.text((header_center_x + 4, header_y + 4), header_text, 
              fill=RED_SHADOW, anchor="mm", font=header_font)
    # Teks utama
    draw.text((header_center_x, header_y), header_text, 
              fill=RED_HEADER, anchor="mm", font=header_font)
    
    # 3. Label "Harga Normal" (kiri)
    y_normal_label = y + 125
    draw.text((x + 25, y_normal_label), "Harga Normal", 
              fill=WHITE, anchor="lm", font=get_font(30, bold=False))
    
    # 4. Harga Normal dengan LATAR HITAM (alignment KANAN)
    y_normal_value = y + 120
    txt_normal = format_angka(harga_normal)
    max_width_normal = CELL_W - 160
    
    # Auto-fit font
    normal_font, _ = fit_text_to_width(draw, txt_normal, max_width_normal, 55, bold=True)
    
    # Hitung dimensi teks untuk latar hitam
    rp_font = get_font(34, bold=True)
    rp_text = "Rp"
    rp_bbox = draw.textbbox((0, 0), rp_text, font=rp_font)
    rp_width = rp_bbox[2] - rp_bbox[0]
    
    normal_bbox = draw.textbbox((0, 0), txt_normal, font=normal_font)
    normal_width = normal_bbox[2] - normal_bbox[0]
    
    # Total lebar (Rp + spasi + angka)
    total_width = rp_width + 8 + normal_width
    total_height = max(rp_bbox[3] - rp_bbox[1], normal_bbox[3] - normal_bbox[1]) + 20
    
    # Posisi kanan untuk latar hitam
    margin_right = 25
    box_right = x + CELL_W - margin_right
    box_left = box_right - total_width - 10
    
    # Gambar latar hitam
    box_top = y_normal_value - 12
    box_bottom = y_normal_value + total_height - 8
    draw.rectangle([box_left, box_top, box_right, box_bottom], fill=BLACK)
    
    # Posisi teks di dalam kotak hitam (rata kanan)
    text_y = y_normal_value + 5
    
    # Gambar "Rp" (rata kanan ke angka)
    rp_x = box_right - normal_width - 8
    draw.text((rp_x, text_y), rp_text, fill=WHITE, anchor="rm", font=rp_font)
    
    # Gambar angka harga normal (rata kanan)
    draw.text((box_right, text_y), txt_normal, fill=WHITE, anchor="rm", font=normal_font)
    
    # 5. Label "Harga Spesial" (kiri)
    y_spesial_label = y + 210
    draw.text((x + 25, y_spesial_label), "Harga Spesial", 
              fill=WHITE, anchor="lm", font=get_font(30, bold=False))
    
    # 6. Kotak hitam untuk harga spesial (lebih besar)
    box_y = y + 250
    box_h = CELL_H - 295
    box_x1 = x + 20
    box_x2 = x + CELL_W - 20
    draw.rectangle([box_x1, box_y, box_x2, y + CELL_H - 18], fill=BLACK)
    
    # 7. Teks "Rp" di kiri kotak hitam
    draw.text((box_x1 + 25, box_y + box_h // 2), "Rp", 
              fill=WHITE, anchor="lm", font=get_font(48, bold=True))
    
    # 8. Harga Spesial (alignment KANAN dalam kotak hitam)
    txt_spesial = format_angka(harga_spesial)
    max_width_spesial = CELL_W - 100
    
    spesial_font, _ = fit_text_to_width(draw, txt_spesial, max_width_spesial, 140, bold=True)
    draw.text((box_x2 - 20, box_y + box_h // 2), txt_spesial, 
              fill=WHITE, anchor="rm", font=spesial_font)


def draw_promo(draw, x, y, nama, harga):
    """Kartu PROMOSI"""
    draw.rectangle([x, y, x + CELL_W, y + CELL_H], fill=(255, 240, 0), outline=BLACK, width=2)
    draw.rectangle([x, y, x + CELL_W, y + 90], fill=RED_HEADER)
    draw.text((x + CELL_W // 2, y + 50), "PROMOSI", 
              fill=(255, 240, 0), anchor="mm", font=get_font(55, bold=True))
    
    nama_text = nama.upper()
    max_width = CELL_W - 60
    name_font, _ = fit_text_to_width(draw, nama_text, max_width, 50, bold=True)
    draw.text((x + CELL_W // 2, y + 170), nama_text, 
              fill=BLACK, anchor="mm", font=name_font)
    
    harga_text = format_angka(harga)
    price_font, _ = fit_text_to_width(draw, harga_text, CELL_W - 80, 140, bold=True)
    draw.text((x + CELL_W // 2, y + 320), harga_text, 
              fill=RED_HEADER, anchor="mm", font=price_font)


def draw_normal(draw, x, y, nama, harga):
    """Kartu NORMAL"""
    draw.rectangle([x, y, x + CELL_W, y + CELL_H], fill=WHITE, outline=BLACK, width=2)
    
    nama_text = nama.upper()
    max_width = CELL_W - 60
    name_font, _ = fit_text_to_width(draw, nama_text, max_width, 48, bold=True)
    draw.text((x + CELL_W // 2, y + 140), nama_text, 
              fill=BLACK, anchor="mm", font=name_font)
    
    harga_text = format_angka(harga)
    price_font, _ = fit_text_to_width(draw, harga_text, CELL_W - 80, 150, bold=True)
    draw.text((x + CELL_W // 2, y + 300), harga_text, 
              fill=BLACK, anchor="mm", font=price_font)


def parse_input_paket(line):
    """Format: harga_awal.harga_promo.qty (qty opsional)"""
    parts = line.strip().split('.')
    if len(parts) < 2:
        return None
    
    harga_awal = parts[0].strip()
    harga_promo = parts[1].strip()
    qty = int(parts[2]) if len(parts) >= 3 and parts[2].strip().isdigit() else 1
    
    return {
        'harga_normal': harga_awal,
        'harga_spesial': harga_promo,
        'qty': min(qty, 100)
    }


async def start(update: Update, context):
    await update.message.reply_text(
        "🎨 *Bot Cetak Harga Mewah*\n\n"
        "📦 *Mode PAKET* (2 harga)\n"
        "Format: `harga_normal.harga_promo.qty`\n"
        "Contoh: `500000.60000.3`\n\n"
        "🔥 *Mode PROMO*\n"
        "Format: `nama.harga`\n"
        "Contoh: `Indomie Goreng.3500`\n\n"
        "📄 *Mode NORMAL*\n"
        "Format: `nama.harga`\n"
        "Contoh: `Beras Premium.75000`\n\n"
        "Multiple line diperbolehkan.",
        parse_mode="Markdown",
        reply_markup=MAIN_KEYBOARD
    )


async def set_mode(update: Update, context):
    mode = update.message.text.replace('/', '')
    context.user_data['mode'] = mode
    
    await update.message.reply_text(
        f"✅ Mode {mode.upper()} aktif.\n\n"
        f"Kirim data sekarang (pisah dengan titik .):",
        reply_markup=ForceReply()
    )


async def handle_message(update: Update, context):
    mode = context.user_data.get('mode')
    if not mode:
        await update.message.reply_text("❌ Pilih mode dulu: /paket, /promo, atau /normal")
        return
    
    text = update.message.text.strip()
    lines = text.split('\n')
    
    all_items = []
    errors = []
    
    for line_num, line in enumerate(lines, 1):
        line = line.strip()
        if not line:
            continue
        
        try:
            if mode == 'paket':
                item = parse_input_paket(line)
                if item:
                    for _ in range(item['qty']):
                        all_items.append({
                            'harga_normal': item['harga_normal'],
                            'harga_spesial': item['harga_spesial']
                        })
                else:
                    errors.append(f"Baris {line_num}: format salah (contoh: 500000.60000.2)")
            else:
                parts = line.split('.')
                if len(parts) < 2:
                    errors.append(f"Baris {line_num}: format salah (contoh: Nama.5000)")
                    continue
                nama = '.'.join(parts[:-1]).strip()
                harga = parts[-1].strip()
                all_items.append({'nama': nama, 'harga': harga})
        except Exception as e:
            errors.append(f"Baris {line_num}: {str(e)}")
    
    if errors:
        await update.message.reply_text("⚠️ *Error:*\n" + "\n".join(errors[:5]), parse_mode="Markdown")
        return
    
    if not all_items:
        await update.message.reply_text("❌ Tidak ada data valid.")
        return
    
    await update.message.reply_text(f"🖨️ Memproses {len(all_items)} item...")
    
    if len(all_items) > 200:
        await update.message.reply_text("⚠️ Maksimal 200 item, sisanya diabaikan.")
        all_items = all_items[:200]
    
    num_images = math.ceil(len(all_items) / ITEMS_PER_IMAGE)
    
    for img_idx in range(num_images):
        start_idx = img_idx * ITEMS_PER_IMAGE
        batch = all_items[start_idx:start_idx + ITEMS_PER_IMAGE]
        
        img = Image.new('RGB', (IMG_W, IMG_H), color=WHITE)
        draw = ImageDraw.Draw(img)
        
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
                else:
                    draw_normal(draw, x_pos, y_pos, item['nama'], item['harga'])
        
        bio = io.BytesIO()
        img.save(bio, format='PNG')
        bio.seek(0)
        
        caption = f"📸 Halaman {img_idx + 1}/{num_images}" if num_images > 1 else None
        await update.message.reply_photo(photo=bio, caption=caption, reply_markup=MAIN_KEYBOARD)
    
    context.user_data['mode'] = None
    await update.message.reply_text("✅ Selesai! Gunakan /paket, /promo, atau /normal untuk cetak lagi.")


def main():
    if not TOKEN:
        print("❌ ERROR: TELEGRAM_TOKEN tidak ditemukan!")
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
