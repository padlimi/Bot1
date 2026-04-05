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
# SISTEM REMINDER CUSTOM
# ======================================================
custom_reminders = []  # Format: {'id': 1, 'time': '08:00', 'schedule': 'senin', 'message': 'Pesan', 'enabled': True}
ADMIN_PASSWORD = "Reminder23"  # Ganti dengan password yang diinginkan

# Keyboard untuk setting reminder
REMINDER_KEYBOARD = ReplyKeyboardMarkup([
    ["📋 Lihat Reminder", "➕ Buat Reminder Baru"],
    ["✏️ Edit Reminder", "❌ Hapus Reminder"],
    ["🔘 Aktif/Nonaktifkan", "🔙 Kembali"]
], resize_keyboard=True, one_time_keyboard=False)

CANCEL_KEYBOARD = ReplyKeyboardMarkup([["❌ Batal"]], resize_keyboard=True, one_time_keyboard=False)

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
# REMINDER FUNCTIONS (BAWAAN)
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
# REMINDER CUSTOM FUNCTIONS
# ======================================================
async def send_reminder_custom(context: CallbackContext):
    """Mengirim reminder custom yang sudah dijadwalkan"""
    try:
        wib = pytz.timezone('Asia/Jakarta')
        now = datetime.now(wib)
        hari_ini = now.strftime('%A').lower()
        
        # Mapping hari Inggris ke Indonesia
        hari_map_eng = {
            'monday': 'senin', 'tuesday': 'selasa', 'wednesday': 'rabu',
            'thursday': 'kamis', 'friday': 'jumat', 'saturday': 'sabtu', 'sunday': 'minggu'
        }
        hari_ini = hari_map_eng.get(hari_ini, hari_ini)
        
        for reminder in custom_reminders:
            if reminder.get('enabled', True):
                # Cek jadwal
                if reminder['schedule'] == 'setiap_hari':
                    waktu_ok = True
                elif reminder['schedule'] == 'weekday':
                    waktu_ok = hari_ini not in ['sabtu', 'minggu']
                elif reminder['schedule'] == 'weekend':
                    waktu_ok = hari_ini in ['sabtu', 'minggu']
                else:
                    waktu_ok = reminder['schedule'] == hari_ini
                
                if waktu_ok:
                    jam, menit = map(int, reminder['time'].split(':'))
                    if now.hour == jam and now.minute == menit:
                        await context.bot.send_message(
                            chat_id=GROUP_CHAT_ID,
                            message_thread_id=MESSAGE_THREAD_ID,
                            text=f"⏰ *REMINDER*\n\n{reminder['message']}",
                            parse_mode="Markdown"
                        )
                        logging.info(f"✅ Reminder custom terkirim: {reminder['message'][:50]}")
                        await asyncio.sleep(60)
    except Exception as e:
        logging.error(f"❌ Gagal kirim reminder custom: {e}")

async def check_password(update: Update, context: CallbackContext):
    """Memeriksa password yang dimasukkan"""
    if context.user_data.get('awaiting_password'):
        password = update.message.text.strip()
        if password == ADMIN_PASSWORD:
            context.user_data['awaiting_password'] = False
            context.user_data['reminder_mode'] = True
            await update.message.reply_text(
                "✅ *Akses Diterima!*\n\nSilakan pilih menu:",
                parse_mode="Markdown",
                reply_markup=REMINDER_KEYBOARD
            )
        else:
            await update.message.reply_text("❌ *Password salah!* Akses ditolak.", parse_mode="Markdown")
            context.user_data['awaiting_password'] = False
        return True
    return False

async def list_reminders(update: Update, context: CallbackContext):
    """Menampilkan daftar reminder"""
    if not custom_reminders:
        await update.message.reply_text("📭 *Belum ada reminder custom.*\n\nGunakan 'Buat Reminder Baru' untuk menambahkan.", parse_mode="Markdown")
        return
    
    pesan = "📋 *Daftar Reminder Custom*\n\n"
    for r in custom_reminders:
        status = "✅ Aktif" if r['enabled'] else "❌ Nonaktif"
        pesan += f"*ID {r['id']}*\n"
        pesan += f"⏰ {r['time']} WIB\n"
        pesan += f"📅 {r['schedule']}\n"
        pesan += f"📝 {r['message'][:50]}\n"
        pesan += f"🔘 {status}\n\n"
    
    await update.message.reply_text(pesan, parse_mode="Markdown")

async def edit_reminder_menu(update: Update, context: CallbackContext):
    """Menu edit reminder"""
    if not custom_reminders:
        await update.message.reply_text("📭 Tidak ada reminder untuk diedit.")
        return
    
    await update.message.reply_text(
        "✏️ *Edit Reminder*\n\n"
        "Kirim ID reminder yang ingin diedit.\n\n"
        f"ID yang tersedia: {', '.join([str(r['id']) for r in custom_reminders])}\n\n"
        "Kirim `❌ Batal` untuk membatalkan.",
        parse_mode="Markdown",
        reply_markup=CANCEL_KEYBOARD
    )
    context.user_data['editing_reminder'] = True

async def delete_reminder_menu(update: Update, context: CallbackContext):
    """Menu hapus reminder"""
    if not custom_reminders:
        await update.message.reply_text("📭 Tidak ada reminder untuk dihapus.")
        return
    
    await update.message.reply_text(
        "❌ *Hapus Reminder*\n\n"
        "Kirim ID reminder yang ingin dihapus.\n\n"
        f"ID yang tersedia: {', '.join([str(r['id']) for r in custom_reminders])}\n\n"
        "Kirim `❌ Batal` untuk membatalkan.",
        parse_mode="Markdown",
        reply_markup=CANCEL_KEYBOARD
    )
    context.user_data['deleting_reminder'] = True

async def toggle_reminder_menu(update: Update, context: CallbackContext):
    """Menu aktif/nonaktifkan reminder"""
    if not custom_reminders:
        await update.message.reply_text("📭 Tidak ada reminder untuk diubah statusnya.")
        return
    
    await update.message.reply_text(
        "🔘 *Aktif/Nonaktifkan Reminder*\n\n"
        "Kirim ID reminder yang ingin diubah statusnya.\n\n"
        f"ID yang tersedia: {', '.join([str(r['id']) for r in custom_reminders])}\n\n"
        "Kirim `❌ Batal` untuk membatalkan.",
        parse_mode="Markdown",
        reply_markup=CANCEL_KEYBOARD
    )
    context.user_data['toggling_reminder'] = True

async def process_edit_reminder(update: Update, context: CallbackContext):
    """Proses edit reminder - pilih ID"""
    text = update.message.text.strip()
    
    if text == "❌ Batal":
        context.user_data['editing_reminder'] = False
        await update.message.reply_text("❌ Dibatalkan.", reply_markup=REMINDER_KEYBOARD)
        return True
    
    try:
        reminder_id = int(text)
        reminder = next((r for r in custom_reminders if r['id'] == reminder_id), None)
        
        if not reminder:
            await update.message.reply_text(f"❌ Reminder dengan ID {reminder_id} tidak ditemukan!")
            return True
        
        context.user_data['edit_id'] = reminder_id
        await update.message.reply_text(
            f"✏️ *Edit Reminder ID {reminder_id}*\n\n"
            f"Format baru: `HH:MM_jadwal_pesan`\n\n"
            f"Contoh: `09:00_senin_Rapat pagi`\n\n"
            f"Kirim `❌ Batal` untuk membatalkan.",
            parse_mode="Markdown"
        )
        context.user_data['waiting_new_reminder_data'] = True
        context.user_data['editing_reminder'] = False
        return True
        
    except ValueError:
        await update.message.reply_text("❌ Kirim angka ID yang valid!")
        return True

async def process_new_reminder_data(update: Update, context: CallbackContext):
    """Memproses data reminder baru untuk edit"""
    if context.user_data.get('waiting_new_reminder_data'):
        text = update.message.text.strip()
        
        if text == "❌ Batal":
            context.user_data['waiting_new_reminder_data'] = False
            context.user_data['edit_id'] = None
            await update.message.reply_text("❌ Dibatalkan.", reply_markup=REMINDER_KEYBOARD)
            return True
        
        try:
            parts = text.split('_')
            if len(parts) < 3:
                await update.message.reply_text("❌ Format salah! Gunakan: `HH:MM_jadwal_pesan`", parse_mode="Markdown")
                return True
            
            time_part = parts[0]
            schedule_part = parts[1]
            message_part = '_'.join(parts[2:])
            
            jam, menit = map(int, time_part.split(':'))
            if not (0 <= jam <= 23 and 0 <= menit <= 59):
                raise ValueError("Waktu tidak valid")
            
            valid_schedules = ['setiap_hari', 'weekday', 'weekend', 
                              'senin', 'selasa', 'rabu', 'kamis', 'jumat', 'sabtu', 'minggu']
            if schedule_part not in valid_schedules:
                await update.message.reply_text(f"❌ Jadwal '{schedule_part}' tidak valid!")
                return True
            
            # Update reminder
            edit_id = context.user_data['edit_id']
            for r in custom_reminders:
                if r['id'] == edit_id:
                    r['time'] = time_part
                    r['schedule'] = schedule_part
                    r['message'] = message_part
                    break
            
            context.user_data['waiting_new_reminder_data'] = False
            context.user_data['edit_id'] = None
            await update.message.reply_text(
                f"✅ *Reminder ID {edit_id} berhasil diupdate!*",
                parse_mode="Markdown",
                reply_markup=REMINDER_KEYBOARD
            )
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}", parse_mode="Markdown")
        return True
    return False

async def process_delete_reminder(update: Update, context: CallbackContext):
    """Proses hapus reminder"""
    text = update.message.text.strip()
    
    if text == "❌ Batal":
        context.user_data['deleting_reminder'] = False
        await update.message.reply_text("❌ Dibatalkan.", reply_markup=REMINDER_KEYBOARD)
        return True
    
    try:
        reminder_id = int(text)
        global custom_reminders
        reminder = next((r for r in custom_reminders if r['id'] == reminder_id), None)
        
        if not reminder:
            await update.message.reply_text(f"❌ Reminder dengan ID {reminder_id} tidak ditemukan!")
            return True
        
        custom_reminders = [r for r in custom_reminders if r['id'] != reminder_id]
        # Renumber IDs
        for i, r in enumerate(custom_reminders, 1):
            r['id'] = i
        
        context.user_data['deleting_reminder'] = False
        await update.message.reply_text(
            f"✅ *Reminder ID {reminder_id} berhasil dihapus!*",
            parse_mode="Markdown",
            reply_markup=REMINDER_KEYBOARD
        )
    except ValueError:
        await update.message.reply_text("❌ Kirim angka ID yang valid!")
    return True

async def process_toggle_reminder(update: Update, context: CallbackContext):
    """Proses aktif/nonaktifkan reminder"""
    text = update.message.text.strip()
    
    if text == "❌ Batal":
        context.user_data['toggling_reminder'] = False
        await update.message.reply_text("❌ Dibatalkan.", reply_markup=REMINDER_KEYBOARD)
        return True
    
    try:
        reminder_id = int(text)
        reminder = next((r for r in custom_reminders if r['id'] == reminder_id), None)
        
        if not reminder:
            await update.message.reply_text(f"❌ Reminder dengan ID {reminder_id} tidak ditemukan!")
            return True
        
        reminder['enabled'] = not reminder['enabled']
        status = "diaktifkan" if reminder['enabled'] else "dinonaktifkan"
        
        context.user_data['toggling_reminder'] = False
        await update.message.reply_text(
            f"✅ *Reminder ID {reminder_id} berhasil {status}!*",
            parse_mode="Markdown",
            reply_markup=REMINDER_KEYBOARD
        )
    except ValueError:
        await update.message.reply_text("❌ Kirim angka ID yang valid!")
    return True

async def handle_reminder_menu(update: Update, context: CallbackContext):
    """Handle menu reminder"""
    if not context.user_data.get('reminder_mode'):
        return False
    
    text = update.message.text
    
    if text == "🔙 Kembali":
        context.user_data['reminder_mode'] = False
        await update.message.reply_text(
            "Kembali ke menu utama.",
            reply_markup=MAIN_KEYBOARD
        )
        return True
    
    elif text == "📋 Lihat Reminder":
        await list_reminders(update, context)
        return True
    
    elif text == "➕ Buat Reminder Baru":
        context.user_data['creating_reminder'] = True
        await update.message.reply_text(
            "📝 *Buat Reminder Baru*\n\n"
            "Format: `HH:MM_jadwal_pesan`\n\n"
            "Contoh:\n"
            "• `08:00_setiap_hari_Selamat pagi!`\n"
            "• `14:30_senin_Rapat tim`\n"
            "• `20:00_weekend_Istirahat`\n\n"
            "Jadwal bisa: `setiap_hari`, `weekday`, `weekend`, atau hari:\n"
            "`senin`, `selasa`, `rabu`, `kamis`, `jumat`, `sabtu`, `minggu`\n\n"
            "Kirim `❌ Batal` untuk membatalkan.",
            parse_mode="Markdown",
            reply_markup=CANCEL_KEYBOARD
        )
        return True
    
    elif text == "✏️ Edit Reminder":
        await edit_reminder_menu(update, context)
        return True
    
    elif text == "❌ Hapus Reminder":
        await delete_reminder_menu(update, context)
        return True
    
    elif text == "🔘 Aktif/Nonaktifkan":
        await toggle_reminder_menu(update, context)
        return True
    
    elif context.user_data.get('creating_reminder'):
        if text == "❌ Batal":
            context.user_data['creating_reminder'] = False
            await update.message.reply_text("❌ Pembatalan reminder.", reply_markup=REMINDER_KEYBOARD)
            return True
        
        # Parse reminder: HH:MM_jadwal_pesan
        try:
            parts = text.split('_')
            if len(parts) < 3:
                await update.message.reply_text("❌ Format salah! Gunakan: `HH:MM_jadwal_pesan`", parse_mode="Markdown")
                return True
            
            time_part = parts[0]
            schedule_part = parts[1]
            message_part = '_'.join(parts[2:])
            
            jam, menit = map(int, time_part.split(':'))
            if not (0 <= jam <= 23 and 0 <= menit <= 59):
                raise ValueError("Waktu tidak valid")
            
            valid_schedules = ['setiap_hari', 'weekday', 'weekend', 
                              'senin', 'selasa', 'rabu', 'kamis', 'jumat', 'sabtu', 'minggu']
            if schedule_part not in valid_schedules:
                await update.message.reply_text(f"❌ Jadwal '{schedule_part}' tidak valid!")
                return True
            
            # Simpan reminder
            custom_reminders.append({
                'id': len(custom_reminders) + 1,
                'time': time_part,
                'schedule': schedule_part,
                'message': message_part,
                'enabled': True
            })
            
            context.user_data['creating_reminder'] = False
            await update.message.reply_text(
                f"✅ *Reminder berhasil dibuat!*\n\n"
                f"⏰ Waktu: {time_part} WIB\n"
                f"📅 Jadwal: {schedule_part}\n"
                f"📝 Pesan: {message_part}",
                parse_mode="Markdown",
                reply_markup=REMINDER_KEYBOARD
            )
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}\nGunakan format: `HH:MM_jadwal_pesan`", parse_mode="Markdown")
        return True
    
    return False

# ======================================================
# SCHEDULER MANUAL
# ======================================================
async def scheduler_loop(application):
    """Loop penjadwalan manual dengan semua reminder"""
    wib = pytz.timezone('Asia/Jakarta')
    last_daily = None
    last_monthly = None
    
    while True:
        try:
            now = datetime.now(wib)
            today_date = now.date()
            
            # Reminder harian: 00:02 WIB
            if now.hour == 0 and now.minute == 2:
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
            
            # Reminder custom
            await send_reminder_custom(application)
            
            await asyncio.sleep(30)
        except Exception as e:
            logging.error(f"Error di scheduler: {e}")
            await asyncio.sleep(60)

# ======================================================
# HANDLER BOT UTAMA
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
        "• 📋 Tanggal 1 & 16 setiap bulan jam 08:00 WIB (Cetak Tag & Retur)\n"
        "• 🔔 Reminder custom (ketik /reminder)\n\n"
        "🔐 *Akses Reminder Custom:* `/reminder`",
        parse_mode="Markdown",
        reply_markup=MAIN_KEYBOARD
    )

async def reminder_command(update: Update, context: CallbackContext):
    """Command /reminder - meminta password terlebih dahulu"""
    await update.message.reply_text(
        "🔐 *Akses Reminder Custom*\n\n"
        "Silakan masukkan password untuk mengakses pengaturan reminder:",
        parse_mode="Markdown"
    )
    context.user_data['awaiting_password'] = True

async def set_mode(update: Update, context):
    mode = update.message.text.replace('/', '')
    context.user_data['mode'] = mode
    await update.message.reply_text(
        f"✅ Mode {mode.upper()} aktif - Kirim data sekarang:",
        reply_markup=ForceReply()
    )

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

async def handle_message(update: Update, context: CallbackContext):
    # Cek password dulu
    if await check_password(update, context):
        return
    
    # Cek menu reminder
    if await handle_reminder_menu(update, context):
        return
    
    # Cek proses edit reminder
    if await process_new_reminder_data(update, context):
        return
    
    # Cek proses edit reminder (pilih ID)
    if context.user_data.get('editing_reminder'):
        if await process_edit_reminder(update, context):
            return
    
    # Cek proses delete reminder
    if context.user_data.get('deleting_reminder'):
        if await process_delete_reminder(update, context):
            return
    
    # Cek proses toggle reminder
    if context.user_data.get('toggling_reminder'):
        if await process_toggle_reminder(update, context):
            return
    
    # Handle mode cetak harga
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

# ======================================================
# MAIN FUNCTION
# ======================================================
async def main():
    if not TOKEN:
        print("❌ ERROR: TELEGRAM_TOKEN tidak ditemukan!")
        return
    
    print("=" * 50)
    print("🤖 BOT CETAK HARGA + REMINDER OTOMATIS")
    print("=" * 50)
    print(f"📱 Group ID: {GROUP_CHAT_ID}")
    print(f"📌 Subtopik MENU ID: {MESSAGE_THREAD_ID}")
    print(f"⏰ Reminder 1: Setiap hari jam 00:02 WIB (Input Sales)")
    print(f"⏰ Reminder 2: Tanggal 1 & 16 jam 08:00 WIB (Cetak Tag & Retur)")
    print(f"🔐 Reminder Custom: /reminder (password: {ADMIN_PASSWORD})")
    print(f"📐 Ukuran: A4 (150 DPI) - {IMG_W}x{IMG_H} px")
    print("=" * 50)
    
    # Buat aplikasi
    application = Application.builder().token(TOKEN).build()
    
    # Handler untuk command
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("reminder", reminder_command))
    application.add_handler(CommandHandler("promo", set_mode))
    application.add_handler(CommandHandler("normal", set_mode))
    application.add_handler(CommandHandler("paket", set_mode))
    application.add_handler(CommandHandler("test_daily", test_daily))
    application.add_handler(CommandHandler("test_monthly", test_monthly))
    
    # Handler untuk pesan biasa
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Jalankan scheduler manual di background
    asyncio.create_task(scheduler_loop(application))
    
    print("✅ Bot berjalan dengan semua reminder otomatis...")
    
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
