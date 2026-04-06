import os
import io
import math
import logging
from datetime import datetime
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
# SISTEM REMINDER CUSTOM (RAHASIA)
# ======================================================
custom_reminders = []
ADMIN_PASSWORD = "Reminder23"

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
# REMINDER CUSTOM FUNCTIONS (RAHASIA)
# ======================================================
async def send_reminder_custom(context: CallbackContext):
    """Mengirim reminder custom yang sudah dijadwalkan"""
    try:
        wib = pytz.timezone('Asia/Jakarta')
        now = datetime.now(wib)
        hari_ini = now.strftime('%A').lower()
        
        hari_map_eng = {
            'monday': 'senin', 'tuesday': 'selasa', 'wednesday': 'rabu',
            'thursday': 'kamis', 'friday': 'jumat', 'saturday': 'sabtu', 'sunday': 'minggu'
        }
        hari_ini = hari_map_eng.get(hari_ini, hari_ini)
        
        for reminder in custom_reminders:
            if reminder.get('enabled', True):
                if reminder['schedule'] == 'setiaphari':
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

async def reminder_command(update: Update, context: CallbackContext):
    """Handler untuk perintah /reminder (rahasia)"""
    await update.message.reply_text("🔐 *Masukkan password:*", parse_mode="Markdown")
    context.user_data['awaiting_password'] = True

async def list_reminders(update: Update, context: CallbackContext):
    if not custom_reminders:
        await update.message.reply_text("📭 *Belum ada reminder.*\n\nGunakan 'Buat Reminder Baru' untuk menambahkan.", parse_mode="Markdown")
        return
    
    pesan = "📋 *Daftar Reminder*\n\n"
    for r in custom_reminders:
        status = "✅ Aktif" if r['enabled'] else "❌ Nonaktif"
        pesan += f"*ID {r['id']}*\n"
        pesan += f"⏰ {r['time']} WIB\n"
        pesan += f"📅 {r['schedule']}\n"
        pesan += f"📝 {r['message'][:50]}\n"
        pesan += f"🔘 {status}\n\n"
    
    await update.message.reply_text(pesan, parse_mode="Markdown")

async def edit_reminder_menu(update: Update, context: CallbackContext):
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
    if context.user_data.get('waiting_new_reminder_data'):
        text = update.message.text.strip()
        
        if text == "❌ Batal":
            context.user_data['waiting_new_reminder_data'] = False
            context.user_data['edit_id'] = None
            await update.message.reply_text("❌ Dibatalkan.", reply_markup=REMINDER_KEYBOARD)
            return True
        
        try:
            first_underscore = text.find('_')
            last_underscore = text.rfind('_')
            
            if first_underscore == -1 or last_underscore == -1 or first_underscore == last_underscore:
                await update.message.reply_text(
                    "❌ Format salah! Gunakan: `HH:MM_jadwal_pesan`\n\n"
                    "Contoh: `15:30_setiaphari_Segera absen pulang`",
                    parse_mode="Markdown"
                )
                return True
            
            time_part = text[:first_underscore]
            schedule_part = text[first_underscore + 1:last_underscore]
            message_part = text[last_underscore + 1:]
            
            jam, menit = map(int, time_part.split(':'))
            if not (0 <= jam <= 23 and 0 <= menit <= 59):
                raise ValueError("Waktu tidak valid")
            
            valid_schedules = ['setiaphari', 'weekday', 'weekend', 
                              'senin', 'selasa', 'rabu', 'kamis', 'jumat', 'sabtu', 'minggu']
            if schedule_part not in valid_schedules:
                await update.message.reply_text(
                    f"❌ Jadwal '{schedule_part}' tidak valid!\n\n"
                    f"Jadwal yang valid:\n"
                    f"• `setiaphari` - Setiap hari\n"
                    f"• `weekday` - Senin s/d Jumat\n"
                    f"• `weekend` - Sabtu & Minggu\n"
                    f"• `senin`, `selasa`, `rabu`, `kamis`, `jumat`, `sabtu`, `minggu`",
                    parse_mode="Markdown"
                )
                return True
            
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

async def process_create_reminder(update: Update, context: CallbackContext):
    if context.user_data.get('creating_reminder'):
        text = update.message.text.strip()
        
        if text == "❌ Batal":
            context.user_data['creating_reminder'] = False
            await update.message.reply_text("❌ Dibatalkan.", reply_markup=REMINDER_KEYBOARD)
            return True
        
        try:
            first_underscore = text.find('_')
            last_underscore = text.rfind('_')
            
            if first_underscore == -1 or last_underscore == -1 or first_underscore == last_underscore:
                await update.message.reply_text(
                    "❌ Format salah! Gunakan: `HH:MM_jadwal_pesan`\n\n"
                    "Contoh: `15:30_setiaphari_Segera absen pulang`",
                    parse_mode="Markdown"
                )
                return True
            
            time_part = text[:first_underscore]
            schedule_part = text[first_underscore + 1:last_underscore]
            message_part = text[last_underscore + 1:]
            
            jam, menit = map(int, time_part.split(':'))
            if not (0 <= jam <= 23 and 0 <= menit <= 59):
                raise ValueError("Waktu tidak valid")
            
            valid_schedules = ['setiaphari', 'weekday', 'weekend', 
                              'senin', 'selasa', 'rabu', 'kamis', 'jumat', 'sabtu', 'minggu']
            if schedule_part not in valid_schedules:
                await update.message.reply_text(
                    f"❌ Jadwal '{schedule_part}' tidak valid!\n\n"
                    f"Jadwal yang valid:\n"
                    f"• `setiaphari` - Setiap hari\n"
                    f"• `weekday` - Senin s/d Jumat\n"
                    f"• `weekend` - Sabtu & Minggu\n"
                    f"• `senin`, `selasa`, `rabu`, `kamis`, `jumat`, `sabtu`, `minggu`",
                    parse_mode="Markdown"
                )
                return True
            
            new_id = len(custom_reminders) + 1
            custom_reminders.append({
                'id': new_id,
                'time': time_part,
                'schedule': schedule_part,
                'message': message_part,
                'enabled': True
            })
            
            context.user_data['creating_reminder'] = False
            await update.message.reply_text(
                f"✅ *Reminder berhasil dibuat!*\n\nID: {new_id}\n⏰ {time_part} WIB\n📅 {schedule_part}\n📝 {message_part}",
                parse_mode="Markdown",
                reply_markup=REMINDER_KEYBOARD
            )
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}", parse_mode="Markdown")
        return True
    return False

async def handle_reminder_menu(update: Update, context: CallbackContext):
    if not context.user_data.get('reminder_mode'):
        return False
    
    text = update.message.text
    
    if text == "🔙 Kembali":
        context.user_data['reminder_mode'] = False
        await update.message.reply_text("Kembali ke menu utama.", reply_markup=MAIN_KEYBOARD)
        return True
    elif text == "📋 Lihat Reminder":
        await list_reminders(update, context)
        return True
    elif text == "➕ Buat Reminder Baru":
        await update.message.reply_text(
            "➕ *Buat Reminder Baru*\n\n"
            "Kirim dengan format: `HH:MM_jadwal_pesan`\n\n"
            "Contoh:\n"
            "• `09:00_setiaphari_Selamat pagi!`\n"
            "• `15:30_weekday_Segera absen pulang`\n"
            "• `08:00_senin_Rapat mingguan`\n\n"
            "Jadwal yang tersedia:\n"
            "`setiaphari`, `weekday`, `weekend`, `senin`, `selasa`, `rabu`, `kamis`, `jumat`, `sabtu`, `minggu`\n\n"
            "Kirim `❌ Batal` untuk membatalkan.",
            parse_mode="Markdown",
            reply_markup=CANCEL_KEYBOARD
        )
        context.user_data['creating_reminder'] = True
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
    
    return False

# ======================================================
# FUNGSI GENERATE GAMBAR
# ======================================================
async def generate_images(items, mode, update, context):
    try:
        await update.message.reply_text(f"🖨️ *Membuat {mode}...*\nTotal: {len(items)} item", parse_mode="Markdown")
        
        total_items = len(items)
        num_images = math.ceil(total_items / ITEMS_PER_IMAGE)
        images_data = []
        
        for img_idx in range(num_images):
            img = Image.new('RGB', (IMG_W, IMG_H), WHITE)
            draw = ImageDraw.Draw(img)
            draw.rectangle([0, 0, IMG_W-1, IMG_H-1], outline=BLACK, width=5)
            date_str = get_current_date_wib()
            draw.text((IMG_W - 30, 30), date_str, fill=BLACK, anchor="rt", font=get_font(28, bold=False))
            
            start_item = img_idx * ITEMS_PER_IMAGE
            end_item = min(start_item + ITEMS_PER_IMAGE, total_items)
            
            for idx, item in enumerate(items[start_item:end_item]):
                row = idx // COLS
                col = idx % COLS
                x = START_X + col * (CELL_W + GAP)
                y = START_Y + row * (CELL_H + GAP)
                
                if mode == "PAKET":
                    draw_paket(draw, x, y, item['harga_normal'], item['harga_spesial'])
                elif mode == "PROMO":
                    draw_promo(draw, x, y, item['nama'], item['harga'])
                else:
                    draw_normal(draw, x, y, item['nama'], item['harga'])
            
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='PNG', dpi=(150, 150))
            img_bytes.seek(0)
            images_data.append(img_bytes)
        
        for img_data in images_data:
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=img_data,
                reply_to_message_id=update.message.message_id
            )
            await asyncio.sleep(1)
        
        await update.message.reply_text(
            f"✅ *Selesai!*\n"
            f"📄 {num_images} halaman A4\n"
            f"🖼️ {len(items)} item tercetak",
            parse_mode="Markdown",
            reply_markup=MAIN_KEYBOARD
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Gagal membuat gambar: {str(e)}")

# ======================================================
# HANDLER COMMANDS
# ======================================================
async def start(update: Update, context: CallbackContext):
    welcome_text = (
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
        "✅ Ukuran A4 (150 DPI) - Siap cetak!\n\n"
        "Gunakan tombol di bawah untuk memilih mode:"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown", reply_markup=MAIN_KEYBOARD)

async def promo_mode(update: Update, context: CallbackContext):
    context.user_data['mode'] = 'promo'
    await update.message.reply_text(
        "🔥 *Mode PROMO*\n\n"
        "Kirim data dengan format:\n"
        "`nama.harga`\n\n"
        "Contoh:\n"
        "`Indomie Goreng.3500`\n"
        "`Aqua 600ml.2500`\n\n"
        "Kirim beberapa item (pisahkan dengan koma atau baris baru):\n"
        "`Indomie.3500, Aqua.2500, Pepsodent.8000`\n\n"
        "Kirim *selesai* untuk mulai mencetak.",
        parse_mode="Markdown"
    )

async def normal_mode(update: Update, context: CallbackContext):
    context.user_data['mode'] = 'normal'
    await update.message.reply_text(
        "📄 *Mode NORMAL*\n\n"
        "Kirim data dengan format:\n"
        "`nama.harga`\n\n"
        "Contoh:\n"
        "`Beras Premium.75000`\n"
        "`Minyak Goreng.15000`\n\n"
        "Kirim beberapa item (pisahkan dengan koma atau baris baru):\n"
        "`Beras.75000, Minyak.15000, Gula.13000`\n\n"
        "Kirim *selesai* untuk mulai mencetak.",
        parse_mode="Markdown"
    )

async def paket_mode(update: Update, context: CallbackContext):
    context.user_data['mode'] = 'paket'
    await update.message.reply_text(
        "📦 *Mode PAKET*\n\n"
        "Kirim data dengan format:\n"
        "`harga_normal.harga_promo.qty`\n\n"
        "Contoh:\n"
        "`600000.70000.3` (Qty 3)\n"
        "`500000.65000.1` (Qty 1)\n\n"
        "Kirim beberapa item (pisahkan dengan koma atau baris baru):\n"
        "`600000.70000.3, 500000.65000.1`\n\n"
        "Kirim *selesai* untuk mulai mencetak.",
        parse_mode="Markdown"
    )

async def process_items(update: Update, context: CallbackContext):
    if 'mode' not in context.user_data:
        await update.message.reply_text("❌ Pilih mode terlebih dahulu! Gunakan tombol di bawah.")
        return
    
    text = update.message.text.strip()
    if text.lower() == 'selesai':
        if 'items' in context.user_data and context.user_data['items']:
            await generate_images(context.user_data['items'], context.user_data['mode'], update, context)
            context.user_data['items'] = []
        else:
            await update.message.reply_text("📭 Tidak ada data untuk dicetak.")
        return
    
    mode = context.user_data['mode']
    items = []
    
    if ',' in text:
        lines = [item.strip() for item in text.split(',')]
    else:
        lines = text.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        if mode == 'paket':
            item = parse_input_paket(line)
            if item:
                items.append(item)
            else:
                await update.message.reply_text(f"❌ Format salah: `{line}`\nGunakan: `harga_normal.harga_promo.qty`", parse_mode="Markdown")
                return
        else:
            parts = line.split('.')
            if len(parts) >= 2:
                nama = '.'.join(parts[:-1]).strip()
                harga = parts[-1].strip()
                if mode == 'promo':
                    items.append({'nama': nama, 'harga': harga})
                else:
                    items.append({'nama': nama, 'harga': harga})
            else:
                await update.message.reply_text(f"❌ Format salah: `{line}`\nGunakan: `nama.harga`", parse_mode="Markdown")
                return
    
    if 'items' not in context.user_data:
        context.user_data['items'] = []
    
    context.user_data['items'].extend(items)
    total = len(context.user_data['items'])
    await update.message.reply_text(f"✅ Menambahkan {len(items)} item. Total: {total}\nKirim *selesai* untuk mencetak.", parse_mode="Markdown")

async def cancel(update: Update, context: CallbackContext):
    context.user_data.clear()
    await update.message.reply_text("❌ Dibatalkan. Gunakan tombol untuk memulai lagi.", reply_markup=MAIN_KEYBOARD)

# ======================================================
# MAIN
# ======================================================
def main():
    if not TOKEN:
        logging.error("❌ TELEGRAM_TOKEN tidak ditemukan!")
        return
    
    app = Application.builder().token(TOKEN).build()
    
    # Command untuk reminder (rahasia)
    app.add_handler(CommandHandler("reminder", reminder_command))
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("promo", promo_mode))
    app.add_handler(CommandHandler("normal", normal_mode))
    app.add_handler(CommandHandler("paket", paket_mode))
    app.add_handler(CommandHandler("cancel", cancel))
    
    # Message handlers
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, 
                                   lambda update, context: process_items(update, context) if not any([
                                       check_password(update, context),
                                       process_create_reminder(update, context),
                                       process_edit_reminder(update, context),
                                       process_delete_reminder(update, context),
                                       process_toggle_reminder(update, context),
                                       process_new_reminder_data(update, context),
                                       handle_reminder_menu(update, context)
                                   ]) else None))
    
    # Job untuk reminder
    job_queue = app.job_queue
    if job_queue:
        job_queue.run_repeating(send_reminder_custom, interval=30, first=10)
    
    logging.info("✅ Bot mulai berjalan...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
