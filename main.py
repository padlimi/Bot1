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
    while size > 30:
        font = get_font(size, bold)
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        if text_width <= max_width:
            return font, size
        size -= 5
    return get_font(30, bold), 30


def draw_paket(draw, x, y, harga_normal, harga_spesial):
    """Gambar kartu PAKET HEMAT dengan auto-fit font"""
    
    # 1. Background biru
    draw.rectangle([x, y, x + CELL_W, y + CELL_H], fill=BLUE_BG)
    
    # 2. Header "PAKET HEMAT"
    header_text = "PAKET HEMAT"
    header_center_x = x + CELL_W // 2
    header_y = y + 50
    
    header_font = get_font(68, bold=True)
    # Bayangan
    draw.text((header_center_x + 4, header_y + 4), header_text, 
              fill=RED_SHADOW, anchor="mm", font=header_font)
    # Teks utama
    draw.text((header_center_x, header_y), header_text, 
              fill=RED_HEADER, anchor="mm", font=header_font)
    
    # 3. Label "Harga Normal"
    y_normal_label = y + 115
    draw.text((x + 20, y_normal_label), "Harga Normal", 
              fill=WHITE, anchor="lm", font=get_font(30, bold=False))
    
    # 4. Harga Normal (dengan auto-fit)
    y_normal_value = y + 120
    txt_normal = format_angka(harga_normal)
    max_width_normal = CELL_W - 180  # Ruang untuk "Rp" dan margin
    
    # Auto-fit untuk harga normal
    normal_font, _ = fit_text_to_width(draw, txt_normal, max_width_normal, 65, bold=True)
    normal_bbox = draw.textbbox((0, 0), txt_normal, font=normal_font)
    normal_width = normal_bbox[2] - normal_bbox[0]
    
    # Posisi "Rp"
    draw.text((x + 20, y_normal_value), "Rp", 
              fill=WHITE, anchor="lm", font=get_font(34, bold=True))
    
    # Posisi angka (setelah Rp + spasi)
    angka_x = x + 75
    draw.text((angka_x, y_normal_value), txt_normal, 
              fill=WHITE, anchor="lm", font=normal_font)
    
    # Coretan garis putih di atas harga normal
    line_y = y_normal_value + 8
    draw.line([angka_x - 5, line_y, angka_x + normal_width + 5, line_y], 
              fill=WHITE, width=5)
    
    # 5. Label "Harga Spesial"
    y_spesial_label = y + 185
    draw.text((x + 20, y_spesial_label), "Harga Spesial", 
              fill=WHITE, anchor="lm", font=get_font(30, bold=False))
    
    # 6. Kotak hitam untuk harga spesial
    box_y = y + 220
    box_h = CELL_H - 265
    box_x1 = x + 15
    box_x2 = x + CELL_W - 15
    draw.rectangle([box_x1, box_y, box_x2, y + CELL_H - 15], fill=BLACK)
    
    # 7. Teks "Rp" di dalam kotak
    draw.text((box_x1 + 30, box_y + box_h // 2), "Rp", 
              fill=WHITE, anchor="lm", font=get_font(48, bold=True))
    
    # 8. Harga Spesial (auto-fit besar)
    txt_spesial = format_angka(harga_spesial)
    max_width_spesial = CELL_W - 120
    
    spesial_font, _ = fit_text_to_width(draw, txt_spesial, max_width_spesial, 150, bold=True)
    draw.text((box_x2 - 20, box_y + box_h // 2), txt_spesial, 
              fill=WHITE, anchor="rm", font=spesial_font)


def draw_promo(draw, x, y, nama, harga):
    """Kartu PROMOSI"""
    draw.rectangle([x, y, x + CELL_W, y + CELL_H], fill=(255, 240, 0), outline=BLACK, width=2)
    draw.rectangle([x, y, x + CELL_W, y + 90], fill=RED_HEADER)
    draw.text((x + CELL_W // 2, y + 50), "PROMOSI", 
              fill=(255, 240, 0), anchor="mm", font=get_font(55, bold=True))
    
    # Nama produk auto-fit
    nama_text = nama.upper()
    max_width = CELL_W - 60
    name_font, _ = fit_text_to_width(draw, nama_text, max_width, 50, bold=True)
    draw.text((x + CELL_W // 2, y + 170), nama_text, 
              fill=BLACK, anchor="mm", font=name_font)
    
    # Harga auto-fit
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


# --- PARSING DENGAN QTY ---
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
        'qty': min(qty, 100)  # Maks 100
    }


def parse_input_regular(line):
    """Format: nama.harga.qty (qty opsional)"""
    parts = line.strip().split('.')
    if len(parts) < 2:
        return None
    
    nama = '.'.join(parts[:-1]).strip()
    harga = parts[-1].strip()
    qty = 1
    
    # Cek apakah ada angka qty di bagian terakhir? (opsional)
    # Untuk regular, qty tidak didukung di format ini
    
    return {'nama': nama, 'harga': harga, 'qty': 1}


# --- HANDLER BOT ---
async def start(update: Update, context):
    await update.message.reply_text(
        "🎨 *Bot Cetak Harga Mewah*\n\n"
        "📦 *Mode PAKET* (2 harga)\n"
        "Format: `harga_normal.harga_promo.qty`\n"
        "Contoh: `450000.8000.5` (cetak 5 kali)\n\n"
        "🔥 *Mode PROMO* (diskon)\n"
        "Format: `nama.harga`\n"
        "Contoh: `Indomie Goreng.3500`\n\n"
        "📄 *Mode NORMAL* (harga biasa)\n"
        "Format: `nama.harga`\n"
        "Contoh: `Beras Premium.75000`\n\n"
        "Multiple line diperbolehkan.",
        parse_mode="Markdown",
        reply_markup=MAIN_KEYBOARD
    )


async def set_mode(update: Update, context):
    mode = update.message.text.replace('/', '')
    context.user_data['mode'] = mode
    
    mode_help = {
        'paket': "📦 PAKET HEMAT\nFormat: `harga_normal.harga_promo.qty`\nContoh: `450000.8000.3`",
        'promo': "🔥 PROMO\nFormat: `nama.harga`\nContoh: `Indomie Goreng.3500`",
        'normal': "📄 NORMAL\nFormat: `nama.harga`\nContoh: `Beras Premium.75000`"
    }
    
    await update.message.reply_text(
        f"✅ Mode {mode.upper()} aktif.\n\n{mode_help.get(mode, '')}\n\nKirim data sekarang:",
        parse_mode="Markdown",
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
                    # Duplikasi sesuai qty
                    for _ in range(item['qty']):
                        all_items.append({
                            'harga_normal': item['harga_normal'],
                            'harga_spesial': item['harga_spesial']
                        })
                else:
                    errors.append(f"Baris {line_num}: format salah (contoh: 450000.8000.2)")
            else:
                # Mode promo atau normal
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
    
    # Batasi maksimal item
    if len(all_items) > 200:
        await update.message.reply_text("⚠️ Maksimal 200 item, sisanya diabaikan.")
        all_items = all_items[:200]
    
    # Buat gambar
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
