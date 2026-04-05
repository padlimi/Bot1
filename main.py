import os
import io
import math
import logging
from datetime import time, datetime
import pytz
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ForceReply
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from PIL import Image, ImageDraw, ImageFont
import asyncio

# --- LOGGING ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
TOKEN = os.environ.get("TELEGRAM_TOKEN")

# ======================================================
# KONFIGURASI GRUP DAN SUBTOPIK
# ======================================================
GROUP_CHAT_ID = -1002042735771
MESSAGE_THREAD_ID = 7956

# ======================================================
# KONFIGURASI UKURAN DAN WARNA
# ======================================================
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BLUE_BG = (0, 102, 210)
RED_HEADER = (220, 0, 0)
RED_SHADOW = (160, 0, 0)
RED_LINE = (255, 0, 0)

A4_W = 1240
A4_H = 1754
MARGIN = 15
PRINT_W = A4_W - (MARGIN * 2)
PRINT_H = A4_H - (MARGIN * 2)
COLS, ROWS = 2, 4
ITEMS_PER_IMAGE = COLS * ROWS
CELL_W = (PRINT_W - (COLS - 1) * 5) // COLS
CELL_H = (PRINT_H - (ROWS - 1) * 5) // ROWS
IMG_W = A4_W
IMG_H = A4_H
START_X = MARGIN
START_Y = MARGIN
GAP = 5

MAIN_KEYBOARD = ReplyKeyboardMarkup([
    [KeyboardButton("/promo"), KeyboardButton("/normal")],
    [KeyboardButton("/paket")]
], resize_keyboard=True, one_time_keyboard=False)

# ======================================================
# FUNGSI UTILITY
# ======================================================
def get_font(size, bold=True):
    font_files = [
        "Roboto-Bold.ttf", "Roboto-Regular.ttf",
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
    size = initial_size
    while size > 16:
        font = get_font(size, bold)
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        if text_width <= max_width:
            return font, size
        size -= 4
    return get_font(16, bold), 16

def get_current_date_wib():
    wib = pytz.timezone('Asia/Jakarta')
    now = datetime.now(wib)
    bulan_indonesia = {
        1: 'Januari', 2: 'Februari', 3: 'Maret', 4: 'April',
        5: 'Mei', 6: 'Juni', 7: 'Juli', 8: 'Agustus',
        9: 'September', 10: 'Oktober', 11: 'November', 12: 'Desember'
    }
    return f"{now.day} {bulan_indonesia[now.month]} {now.year}"

# ======================================================
# FUNGSI GAMBAR KARTU
# ======================================================
def draw_paket(draw, x, y, harga_normal, harga_spesial):
    draw.rectangle([x, y, x + CELL_W, y + CELL_H], fill=BLUE_BG, outline=BLACK, width=1)
    header_text = "PAKET HEMAT"
    header_center_x = x + CELL_W // 2
    header_y = y + int(CELL_H * 0.12)
    header_font = get_font(52, bold=True)
    draw.text((header_center_x + 3, header_y + 3), header_text, fill=RED_SHADOW, anchor="mm", font=header_font)
    draw.text((header_center_x, header_y), header_text, fill=RED_HEADER, anchor="mm", font=header_font)
    
    y_normal_label = y + int(CELL_H * 0.28)
    draw.text((x + 15, y_normal_label), "Harga Normal", fill=WHITE, anchor="lm", font=get_font(24, bold=False))
    
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
    draw.rectangle([box_left, box_top, box_right, box_bottom], fill=BLACK, outline=WHITE, width=1)
    text_center_x = (box_left + box_right) // 2
    text_y = y_normal_value + 4
    rp_x = text_center_x - (normal_width // 2) - spacing - (rp_width // 2)
    draw.text((rp_x, text_y), rp_text, fill=WHITE, anchor="rm", font=rp_font)
    draw.text((text_center_x + (normal_width // 2), text_y), txt_normal, fill=WHITE, anchor="rm", font=normal_font)
    line_y = text_y - 6
    draw.line([box_left + 8, line_y, box_right - 8, line_y], fill=RED_LINE, width=5)
    
    y_spesial_label = y + int(CELL_H * 0.48)
    draw.text((x + 15, y_spesial_label), "Harga Spesial", fill=WHITE, anchor="lm", font=get_font(24, bold=False))
    box_y = y + int(CELL_H * 0.57)
    box_h = CELL_H - int(CELL_H * 0.68)
    box_x1 = x + 12
    box_x2 = x + CELL_W - 12
    draw.rectangle([box_x1, box_y, box_x2, y + CELL_H - 12], fill=BLACK, outline=WHITE, width=1)
    draw.text((box_x1 + 15, box_y + box_h // 2), "Rp", fill=WHITE, anchor="lm", font=get_font(36, bold=True))
    txt_spesial = format_angka(harga_spesial)
    max_width_spesial = CELL_W - 80
    spesial_font, _ = fit_text_to_width(draw, txt_spesial, max_width_spesial, 100, bold=True)
    draw.text((box_x2 - 15, box_y + box_h // 2), txt_spesial, fill=WHITE, anchor="rm", font=spesial_font)

def draw_promo(draw, x, y, nama, harga):
    draw.rectangle([x, y, x + CELL_W, y + CELL_H], fill=(255, 240, 0), outline=BLACK, width=1)
    draw.rectangle([x, y, x + CELL_W, y + int(CELL_H * 0.2)], fill=RED_HEADER)
    draw.text((x + CELL_W // 2, y + int(CELL_H * 0.12)), "PROMOSI", fill=(255, 240, 0), anchor="mm", font=get_font(44, bold=True))
    nama_text = nama.upper()
    max_width = CELL_W - 40
    name_font, _ = fit_text_to_width(draw, nama_text, max_width, 40, bold=True)
    draw.text((x + CELL_W // 2, y + int(CELL_H * 0.42)), nama_text, fill=BLACK, anchor="mm", font=name_font)
    harga_text = format_angka(harga)
    price_font, _ = fit_text_to_width(draw, harga_text, CELL_W - 60, 100, bold=True)
    draw.text((x + CELL_W // 2, y + int(CELL_H * 0.75)), harga_text, fill=RED_HEADER, anchor="mm", font=price_font)

def draw_normal(draw, x, y, nama, harga):
    draw.rectangle([x, y, x + CELL_W, y + CELL_H], fill=WHITE, outline=BLACK, width=1)
    nama_text = nama.upper()
    max_width = CELL_W - 40
    name_font, _ = fit_text_to_width(draw, nama_text, max_width, 38, bold=True)
    draw.text((x + CELL_W // 2, y + int(CELL_H * 0.35)), nama_text, fill=BLACK, anchor="mm", font=name_font)
    harga_text = format_angka(harga)
    price_font, _ = fit_text_to_width(draw, harga_text, CELL_W - 60, 110, bold=True)
    draw.text((x + CELL_W // 2, y + int(CELL_H * 0.7)), harga_text, fill=BLACK, anchor="mm", font=price_font)

def parse_input_paket(line):
    parts = line.strip().split('.')
    if len(parts) < 2:
        return None
    harga_awal = parts[0].strip()
    harga_promo = parts[1].strip()
    qty = int(parts[2]) if len(parts) >= 3 and parts[2].strip().isdigit() else 1
    return {'harga_normal': harga_awal, 'harga_spesial': harga_promo, 'qty': min(qty, 100)}

# ======================================================
# REMINDER FUNCTIONS
# ======================================================
async def send_daily_reminder(context: CallbackContext):
    try:
        tanggal_sekarang = get_current_date_wib()
        pesan = (
            f"🔔 *Reminder Input Data Sales*\n\n"
            f"Segera input sales *{tanggal_sekarang}* di link berikut:\n"
            f"https://docs.google.com/spreadsheets/d/1-6P5CzwPQtthpYu9Pc5Q9a07nbZw06Aapmr1Xy2s6RY/edit?usp=drivesdk\n\n"
            f"Abaikan jika sudah input. Terima kasih."
        )
        await context.bot.send_message(
            chat_id=GROUP_CHAT_ID,
            message_thread_id=MESSAGE_THREAD_ID,
            text=pesan,
            parse_mode="Markdown"
        )
        logging.info(f"✅ Reminder HARIAN terkirim")
    except Exception as e:
        logging.error(f"❌ Gagal kirim reminder harian: {e}")

async def send_monthly_reminder(context: CallbackContext):
    try:
        pesan = (
            f"📋 *Reminder Cetak & Retur*\n\n"
            f"Segera cetak Tag N, R, F dan Non Category\n"
            f"dan segera lakukan retur.\n\n"
            f"📅 *Tanggal: {get_current_date_wib()}*\n"
            f"⏰ *Batas: Hari ini juga!*"
        )
        await context.bot.send_message(
            chat_id=GROUP_CHAT_ID,
            message_thread_id=MESSAGE_THREAD_ID,
            text=pesan,
            parse_mode="Markdown"
        )
        logging.info(f"✅ Reminder BULANAN terkirim")
    except Exception as e:
        logging.error(f"❌ Gagal kirim reminder bulanan: {e}")

# ======================================================
# SCHEDULER MANUAL UNTUK RAILWAY
# ======================================================
async def scheduler_loop(application):
    """Loop penjadwalan manual (tanpa job_queue)"""
    wib = pytz.timezone('Asia/Jakarta')
    last_daily = None
    last_monthly = None
    
    while True:
        try:
            now = datetime.now(wib)
            today_date = now.date()
            
            # Reminder harian: 00:02 WIB
            if now.hour == 0 and now.minute == 5:
                if last_daily != today_date:
                    logging.info(f"⏰ Mengirim reminder harian...")
                    await send_daily_reminder(application)
                    last_daily = today_date
                    await asyncio.sleep(60)
            
            # Reminder bulanan: tgl 1 atau 16 jam 08:00 WIB
            if (now.day == 1 or now.day == 16) and now.hour == 8 and now.minute == 0:
                if last_monthly != today_date:
                    logging.info(f"⏰ Mengirim reminder bulanan...")
                    await send_monthly_reminder(application)
                    last_monthly = today_date
                    await asyncio.sleep(60)
            
            await asyncio.sleep(30)
        except Exception as e:
            logging.error(f"Error di scheduler: {e}")
            await asyncio.sleep(60)

# ======================================================
# HANDLER BOT
# ======================================================
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
        "✅ *Ukuran A4 (150 DPI)* - Siap cetak!\n\n"
        "⏰ *Reminder Otomatis:*\n"
        "• 📊 Setiap hari jam 00:02 WIB (Input Sales)\n"
        "• 📋 Tanggal 1 & 16 setiap bulan jam 08:00 WIB (Cetak Tag & Retur)",
        parse_mode="Markdown",
        reply_markup=MAIN_KEYBOARD
    )

async def set_mode(update: Update, context):
    mode = update.message.text.replace('/', '')
    context.user_data['mode'] = mode
    await update.message.reply_text(
        f"✅ Mode {mode.upper()} aktif - Kirim data sekarang:",
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
        
        img = Image.new('RGB', (IMG_W, IMG_H), color=WHITE)
        draw = ImageDraw.Draw(img)
        
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
        
        bio = io.BytesIO()
        img.save(bio, format='PNG', dpi=(150, 150))
        bio.seek(0)
        
        caption = f"📸 Halaman {img_idx + 1}/{num_images} (A4 150 DPI - siap cetak)"
        await update.message.reply_photo(photo=bio, caption=caption, reply_markup=MAIN_KEYBOARD)
    
    context.user_data['mode'] = None
    await update.message.reply_text("✅ Selesai! Gambar sudah siap cetak di kertas A4.")

async def test_daily(update: Update, context):
    """Test kirim reminder harian"""
    await update.message.reply_text("🔄 Test reminder harian...")
    await send_daily_reminder(context)
    await update.message.reply_text("✅ Selesai!")

async def test_monthly(update: Update, context):
    """Test kirim reminder bulanan"""
    await update.message.reply_text("🔄 Test reminder bulanan...")
    await send_monthly_reminder(context)
    await update.message.reply_text("✅ Selesai!")

# ======================================================
# MAIN FUNCTION
# ======================================================
async def main():
    if not TOKEN:
        print("❌ ERROR: TELEGRAM_TOKEN tidak ditemukan!")
        return
    
    print("=" * 50)
    print("🤖 BOT CETAK HARGA + 2 REMINDER OTOMATIS")
    print("=" * 50)
    print(f"📱 Group ID: {GROUP_CHAT_ID}")
    print(f"📌 Subtopik MENU ID: {MESSAGE_THREAD_ID}")
    print(f"⏰ Reminder 1: Setiap hari jam 00:02 WIB (Input Sales)")
    print(f"⏰ Reminder 2: Tanggal 1 & 16 jam 08:00 WIB (Cetak Tag & Retur)")
    print(f"📐 Ukuran: A4 (150 DPI) - {IMG_W}x{IMG_H} px")
    print("=" * 50)
    
    # Buat aplikasi
    application = Application.builder().token(TOKEN).build()
    
    # Handler untuk command
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("promo", set_mode))
    application.add_handler(CommandHandler("normal", set_mode))
    application.add_handler(CommandHandler("paket", set_mode))
    application.add_handler(CommandHandler("test_daily", test_daily))
    application.add_handler(CommandHandler("test_monthly", test_monthly))
    
    # Handler untuk pesan biasa
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Jalankan scheduler manual di background
    asyncio.create_task(scheduler_loop(application))
    
    print("✅ Bot berjalan dengan 2 reminder otomatis...")
    
    # Jalankan bot
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    
    # Keep running
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        print("\n❌ Bot berhenti")
        await application.updater.stop()
        await application.stop()
        await application.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
