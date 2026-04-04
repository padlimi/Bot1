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
RED_LINE = (255, 0, 0)

# --- UKURAN A4 (150 DPI - Optimal untuk cetak) ---
# A4 = 210mm x 297mm
# 150 DPI = 150 pixel per inch = 59 pixel per cm
A4_W = 1240   # 210mm * 59 = 1239 ~ 1240 px
A4_H = 1754   # 297mm * 59 = 1752 ~ 1754 px

# Margin untuk cetak (agar tidak terpotong printer)
MARGIN = 15   # pixel margin

# Ukuran area cetak efektif
PRINT_W = A4_W - (MARGIN * 2)  # 1240 - 30 = 1210 px
PRINT_H = A4_H - (MARGIN * 2)  # 1754 - 30 = 1724 px

# --- KONFIGURASI GRID ---
COLS, ROWS = 2, 4
ITEMS_PER_IMAGE = COLS * ROWS

# Hitung ukuran cell berdasarkan area cetak
CELL_W = (PRINT_W - (COLS - 1) * 5) // COLS  # 1210 - 5 = 1205 // 2 = 602 px
CELL_H = (PRINT_H - (ROWS - 1) * 5) // ROWS  # 1724 - 15 = 1709 // 4 = 427 px

# Ukuran total gambar (A4 full)
IMG_W = A4_W
IMG_H = A4_H

# Posisi awal grid (dengan margin)
START_X = MARGIN
START_Y = MARGIN
GAP = 5  # jarak antar cell

print(f"📐 Konfigurasi A4 150 DPI:")
print(f"   - Ukuran gambar: {IMG_W} x {IMG_H} px")
print(f"   - Margin: {MARGIN} px")
print(f"   - Cell size: {CELL_W} x {CELL_H} px")
print(f"   - Grid: {COLS} x {ROWS} = {ITEMS_PER_IMAGE} kartu per halaman")

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
    while size > 16:
        font = get_font(size, bold)
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        if text_width <= max_width:
            return font, size
        size -= 4
    return get_font(16, bold), 16


def draw_paket(draw, x, y, harga_normal, harga_spesial):
    """Gambar kartu PAKET HEMAT untuk cetak A4"""
    
    # 1. Background biru dengan outline 1px
    draw.rectangle([x, y, x + CELL_W, y + CELL_H], 
                   fill=BLUE_BG, outline=BLACK, width=1)
    
    # 2. Header "PAKET HEMAT" (skala lebih kecil untuk A4)
    header_text = "PAKET HEMAT"
    header_center_x = x + CELL_W // 2
    header_y = y + int(CELL_H * 0.12)  # 12% dari tinggi cell
    
    header_font = get_font(52, bold=True)  # Lebih kecil dari sebelumnya (68)
    # Bayangan
    draw.text((header_center_x + 3, header_y + 3), header_text, 
              fill=RED_SHADOW, anchor="mm", font=header_font)
    # Teks utama
    draw.text((header_center_x, header_y), header_text, 
              fill=RED_HEADER, anchor="mm", font=header_font)
    
    # 3. Label "Harga Normal"
    y_normal_label = y + int(CELL_H * 0.28)
    draw.text((x + 15, y_normal_label), "Harga Normal", 
              fill=WHITE, anchor="lm", font=get_font(24, bold=False))
    
    # 4. Harga Normal dengan LATAR HITAM
    y_normal_value = y + int(CELL_H * 0.27)
    txt_normal = format_angka(harga_normal)
    
    normal_font = get_font(38, bold=True)
    rp_font = get_font(30, bold=True)
    
    rp_text = "Rp"
    rp_bbox = draw.textbbox((0, 0), rp_text, font=rp_font)
    rp_width = rp_bbox[2] - rp_bbox[0]
    
    normal_bbox = draw.textbbox((0, 0), txt_normal, font=normal_font)
    normal_width = normal_bbox[2] - normal_bbox[0]
    
    spacing = 8
    total_width = rp_width + spacing + normal_width
    total_height = max(rp_bbox[3] - rp_bbox[1], normal_bbox[3] - normal_bbox[1]) + 16
    
    label_right = x + 140
    available_width = CELL_W - (label_right - x) - 20
    box_width = min(total_width + 30, available_width)
    
    box_center_x = x + CELL_W - 25 - (box_width // 2)
    box_left = box_center_x - (box_width // 2)
    box_right = box_left + box_width
    
    box_top = y_normal_value - 10
    box_bottom = y_normal_value + total_height - 6
    
    draw.rectangle([box_left, box_top, box_right, box_bottom], 
                   fill=BLACK, outline=WHITE, width=1)
    
    text_center_x = (box_left + box_right) // 2
    text_y = y_normal_value + 4
    
    rp_x = text_center_x - (normal_width // 2) - spacing - (rp_width // 2)
    draw.text((rp_x, text_y), rp_text, fill=WHITE, anchor="rm", font=rp_font)
    draw.text((text_center_x + (normal_width // 2), text_y), txt_normal, 
              fill=WHITE, anchor="rm", font=normal_font)
    
    # Coretan garis merah
    line_y = text_y - 6
    draw.line([box_left + 8, line_y, box_right - 8, line_y], 
              fill=RED_LINE, width=5)
    
    # 5. Label "Harga Spesial"
    y_spesial_label = y + int(CELL_H * 0.48)
    draw.text((x + 15, y_spesial_label), "Harga Spesial", 
              fill=WHITE, anchor="lm", font=get_font(24, bold=False))
    
    # 6. Kotak hitam untuk harga spesial
    box_y = y + int(CELL_H * 0.57)
    box_h = CELL_H - int(CELL_H * 0.68)
    box_x1 = x + 12
    box_x2 = x + CELL_W - 12
    draw.rectangle([box_x1, box_y, box_x2, y + CELL_H - 12], 
                   fill=BLACK, outline=WHITE, width=1)
    
    # 7. Teks "Rp" di kiri kotak hitam
    draw.text((box_x1 + 15, box_y + box_h // 2), "Rp", 
              fill=WHITE, anchor="lm", font=get_font(36, bold=True))
    
    # 8. Harga Spesial
    txt_spesial = format_angka(harga_spesial)
    max_width_spesial = CELL_W - 80
    
    spesial_font, _ = fit_text_to_width(draw, txt_spesial, max_width_spesial, 100, bold=True)
    draw.text((box_x2 - 15, box_y + box_h // 2), txt_spesial, 
              fill=WHITE, anchor="rm", font=spesial_font)


def draw_promo(draw, x, y, nama, harga):
    """Kartu PROMOSI untuk cetak A4"""
    draw.rectangle([x, y, x + CELL_W, y + CELL_H], 
                   fill=(255, 240, 0), outline=BLACK, width=1)
    draw.rectangle([x, y, x + CELL_W, y + int(CELL_H * 0.2)], fill=RED_HEADER)
    draw.text((x + CELL_W // 2, y + int(CELL_H * 0.12)), "PROMOSI", 
              fill=(255, 240, 0), anchor="mm", font=get_font(44, bold=True))
    
    nama_text = nama.upper()
    max_width = CELL_W - 40
    name_font, _ = fit_text_to_width(draw, nama_text, max_width, 40, bold=True)
    draw.text((x + CELL_W // 2, y + int(CELL_H * 0.42)), nama_text, 
              fill=BLACK, anchor="mm", font=name_font)
    
    harga_text = format_angka(harga)
    price_font, _ = fit_text_to_width(draw, harga_text, CELL_W - 60, 100, bold=True)
    draw.text((x + CELL_W // 2, y + int(CELL_H * 0.75)), harga_text, 
              fill=RED_HEADER, anchor="mm", font=price_font)


def draw_normal(draw, x, y, nama, harga):
    """Kartu NORMAL untuk cetak A4"""
    draw.rectangle([x, y, x + CELL_W, y + CELL_H], 
                   fill=WHITE, outline=BLACK, width=1)
    
    nama_text = nama.upper()
    max_width = CELL_W - 40
    name_font, _ = fit_text_to_width(draw, nama_text, max_width, 38, bold=True)
    draw.text((x + CELL_W // 2, y + int(CELL_H * 0.35)), nama_text, 
              fill=BLACK, anchor="mm", font=name_font)
    
    harga_text = format_angka(harga)
    price_font, _ = fit_text_to_width(draw, harga_text, CELL_W - 60, 110, bold=True)
    draw.text((x + CELL_W // 2, y + int(CELL_H * 0.7)), harga_text, 
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
        "🎨 *Bot Cetak Harga Mewah - Format A4*\n\n"
        "📦 *Mode PAKET* (2 harga)\n"
        "Format: `harga_normal.harga_promo.qty`\n"
        "Contoh: `600000.70000.3`\n\n"
        "🔥 *Mode PROMO*\n"
        "Format: `nama.harga`\n"
        "Contoh: `Indomie Goreng.3500`\n\n"
        "📄 *Mode NORMAL*\n"
        "Format: `nama.harga`\n"
        "Contoh: `Beras Premium.75000`\n\n"
        "✅ *Ukuran A4 (150 DPI)* - Siap cetak!\n"
        f"📐 {COLS}x{ROWS} kartu per halaman\n"
        f"📏 Margin {MARGIN}px untuk keamanan printer\n\n"
        "Multiple line diperbolehkan.",
        parse_mode="Markdown",
        reply_markup=MAIN_KEYBOARD
    )


async def set_mode(update: Update, context):
    mode = update.message.text.replace('/', '')
    context.user_data['mode'] = mode
    
    await update.message.reply_text(
        f"✅ Mode {mode.upper()} aktif - Ukuran A4 siap cetak!\n\n"
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
                    errors.append(f"Baris {line_num}: format salah (contoh: 600000.70000.2)")
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
    
    await update.message.reply_text(f"🖨️ Memproses {len(all_items)} item... (Ukuran A4 150 DPI)")
    
    if len(all_items) > 200:
        await update.message.reply_text("⚠️ Maksimal 200 item, sisanya diabaikan.")
        all_items = all_items[:200]
    
    num_images = math.ceil(len(all_items) / ITEMS_PER_IMAGE)
    
    for img_idx in range(num_images):
        start_idx = img_idx * ITEMS_PER_IMAGE
        batch = all_items[start_idx:start_idx + ITEMS_PER_IMAGE]
        
        # Buat gambar ukuran A4
        img = Image.new('RGB', (IMG_W, IMG_H), color=WHITE)
        draw = ImageDraw.Draw(img)
        
        # Gambar garis bantu margin (opsional, untuk debugging)
        # draw.rectangle([MARGIN, MARGIN, IMG_W-MARGIN, IMG_H-MARGIN], outline=(200,200,200), width=1)
        
        for idx in range(ITEMS_PER_IMAGE):
            row = idx // COLS
            col = idx % COLS
            x_pos = START_X + col * (CELL_W + GAP)
            y_pos = START_Y + row * (CELL_H + GAP)
            
            if idx < len(batch):
                item = batch[idx]
                if mode == 'paket':
                    draw_paket(draw, x_pos, y_pos, item['harga_normal'], item['harga_spesial'])
                elif mode == 'promo':
                    draw_promo(draw, x_pos, y_pos, item['nama'], item['harga'])
                else:
                    draw_normal(draw, x_pos, y_pos, item['nama'], item['harga'])
        
        # Simpan dengan kualitas tinggi untuk cetak
        bio = io.BytesIO()
        img.save(bio, format='PNG', dpi=(150, 150))
        bio.seek(0)
        
        caption = f"📸 Halaman {img_idx + 1}/{num_images} (A4 150 DPI - siap cetak)"
        await update.message.reply_photo(photo=bio, caption=caption, reply_markup=MAIN_KEYBOARD)
    
    context.user_data['mode'] = None
    await update.message.reply_text("✅ Selesai! Gambar sudah siap cetak di kertas A4.")


def main():
    if not TOKEN:
        print("❌ ERROR: TELEGRAM_TOKEN tidak ditemukan!")
        return
    
    print("🤖 Bot starting with A4 format (150 DPI)...")
    print(f"   - Image size: {IMG_W} x {IMG_H} px")
    print(f"   - Cell size: {CELL_W} x {CELL_H} px")
    
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
