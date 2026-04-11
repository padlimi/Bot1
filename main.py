import os
import io
import math
import logging
import sys
from datetime import datetime
from io import BytesIO
import pytz
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ForceReply
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter
import asyncio
import aiohttp
import numpy as np
import gc

# ======================================================
# KONFIGURASI AWAL
# ======================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)

# LOGGING
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("TELEGRAM_TOKEN")

# ======================================================
# KONFIGURASI GRUP DAN SUBTOPIK
# ======================================================
GROUP_CHAT_ID = -1002042735771
MESSAGE_THREAD_ID = 7956

# ======================================================
# KONFIGURASI UKURAN DAN WARNA UNTUK CETAK HARGA
# ======================================================
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BLUE_BG = (0, 102, 210)
RED_HEADER = (220, 0, 0)
RED_SHADOW = (160, 0, 0)
RED_LINE = (255, 0, 0)
YELLOW_BG = (255, 235, 0)

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

# ======================================================
# KONFIGURASI POP IMAGE
# ======================================================
TEMPLATE_SIZE = (720, 1018)
PRODUCT_AREA = {"x": 38, "y": 148, "width": 644, "height": 700}
PRICE_AREA = {"x": 38, "y": 848, "width": 644, "height": 139}
SCALE = 2

# ======================================================
# KEYBOARD
# ======================================================
MAIN_KEYBOARD = ReplyKeyboardMarkup([
    [KeyboardButton("/promo"), KeyboardButton("/normal")],
    [KeyboardButton("/paket"), KeyboardButton("/pop")]
], resize_keyboard=True, one_time_keyboard=False)

# ======================================================
# SISTEM REMINDER CUSTOM
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
# FUNGSI UTILITY UNTUK CETAK HARGA
# ======================================================
def get_font(size, bold=True):
    font_files = [
        "Roboto-Bold.ttf", "Roboto-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "C:\\Windows\\Fonts\\Arial.ttf",
        "C:\\Windows\\Fonts\\Arialbd.ttf",
        "Arial Black.ttf",
        "Arial Bold.ttf"
    ]
    for font_file in font_files:
        try:
            if bold and "Bold" not in font_file and "bd" not in font_file.lower() and "Black" not in font_file:
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

def format_rupiah(harga):
    """Format harga ke format rupiah dengan Rp"""
    try:
        if isinstance(harga, (int, float)):
            angka = int(harga)
        else:
            angka_str = ''.join(filter(str.isdigit, str(harga)))
            angka = int(angka_str) if angka_str else 0
        return f"Rp {angka:,}".replace(",", ".")
    except:
        return f"Rp {harga}"

def fit_text_to_width(draw, text, max_width, initial_size, bold=True):
    size = initial_size
    while size > 16:
        font = get_font(size, bold)
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        if text_width <= max_width:
            return font, size
        size -= 2
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
# FUNGSI GAMBAR KARTU UNTUK CETAK HARGA
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
    """
    Draw promo card with LARGER price font
    """
    # Background kuning promo
    draw.rectangle([x, y, x + CELL_W, y + CELL_H], fill=YELLOW_BG, outline=BLACK, width=2)
    
    # Header MERAH - diperkecil agar area harga lebih besar
    header_height = int(CELL_H * 0.16)  # dari 0.2 jadi 0.16
    draw.rectangle([x, y, x + CELL_W, y + header_height], fill=RED_HEADER)
    
    # Teks "PROMOSI"
    promo_font = get_font(44, bold=True)
    draw.text((x + CELL_W // 2, y + header_height // 2), "PROMOSI", 
              fill=YELLOW_BG, anchor="mm", font=promo_font)
    
    # Nama produk
    nama_text = nama.upper()
    max_width = CELL_W - 50
    
    # Batasi panjang nama
    if len(nama_text) > 35:
        nama_text = nama_text[:32] + "..."
    
    name_font, name_size = fit_text_to_width(draw, nama_text, max_width, 34, bold=True)
    name_y = y + header_height + int(CELL_H * 0.12)
    draw.text((x + CELL_W // 2, name_y), nama_text, fill=BLACK, anchor="mm", font=name_font)
    
    # ========== HARGA - DIPERBESAR ==========
    harga_display = format_rupiah(harga)
    
    # Font harga: LEBIH BESAR - mulai dari 100
    price_size = 100
    price_font = get_font(price_size, bold=True)
    bbox = draw.textbbox((0, 0), harga_display, font=price_font)
    
    # Kurangi ukuran jika terlalu lebar
    while (bbox[2] - bbox[0] > CELL_W - 60) and price_size > 50:
        price_size -= 4
        price_font = get_font(price_size, bold=True)
        bbox = draw.textbbox((0, 0), harga_display, font=price_font)
    
    # Posisi center sempurna
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    price_x = x + (CELL_W - text_width) // 2
    
    # Posisi Y: di tengah area yang tersisa
    available_height = CELL_H - header_height
    price_y = y + header_height + (available_height - text_height) // 2 + int(CELL_H * 0.05)
    
    # Efek bold dengan multiple layer untuk harga besar
    # Layer 1: shadow gelap (lebih tebal)
    draw.text((price_x + 3, price_y + 3), harga_display, fill=(180, 0, 0), font=price_font)
    draw.text((price_x + 2, price_y + 2), harga_display, fill=(200, 0, 0), font=price_font)
    # Layer 2: outline
    draw.text((price_x - 2, price_y - 1), harga_display, fill=(180, 0, 0), font=price_font)
    draw.text((price_x + 1, price_y - 1), harga_display, fill=(180, 0, 0), font=price_font)
    # Layer 3: teks utama
    draw.text((price_x, price_y), harga_display, fill=RED_HEADER, font=price_font)
    
    # Garis dekoratif di atas harga
    line_y = price_y - 15
    if line_y > name_y + 25:
        line_width = min(150, CELL_W - 100)
        draw.line([(x + CELL_W // 2 - line_width//2, line_y),
                   (x + CELL_W // 2 + line_width//2, line_y)], 
                  fill=RED_HEADER, width=4)

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

def parse_pop_input(line):
    """Parse input untuk POP: PLU.Harga"""
    parts = line.strip().split('.')
    if len(parts) < 2:
        return None
    plu = parts[0].strip()
    harga = '.'.join(parts[1:]).strip()
    if len(plu) != 8 or not plu.isdigit():
        return None
    return {'plu': plu, 'harga': harga}

# ======================================================
# FUNGSI POP IMAGE
# ======================================================
async def download_product_image(plu: str) -> BytesIO:
    """Download product image from Indomaret CDN"""
    url = f"https://cdn-klik.klikindomaret.com/klik-catalog/product/{plu}_meta.jpg"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                raise Exception(f"Gagal download gambar (status {response.status})")
            return BytesIO(await response.read())

def flood_fill_remove_background(image: Image.Image) -> Image.Image:
    """
    BFS flood-fill removal like TypeScript version.
    Removes connected near-white background from edges while preserving white areas inside product.
    """
    if image.mode != 'RGBA':
        image = image.convert('RGBA')
    
    img_array = np.array(image)
    h, w = img_array.shape[:2]
    
    visited = np.zeros((h, w), dtype=np.uint8)
    queue = []
    
    def is_near_white(r, g, b):
        return r >= 235 and g >= 235 and b >= 235
    
    # Add edge pixels
    for x_pos in range(w):
        r, g, b, a = img_array[0, x_pos]
        if is_near_white(r, g, b) and not visited[0, x_pos]:
            visited[0, x_pos] = 1
            queue.append((x_pos, 0))
    
    for x_pos in range(w):
        r, g, b, a = img_array[h-1, x_pos]
        if is_near_white(r, g, b) and not visited[h-1, x_pos]:
            visited[h-1, x_pos] = 1
            queue.append((x_pos, h-1))
    
    for y_pos in range(h):
        r, g, b, a = img_array[y_pos, 0]
        if is_near_white(r, g, b) and not visited[y_pos, 0]:
            visited[y_pos, 0] = 1
            queue.append((0, y_pos))
    
    for y_pos in range(h):
        r, g, b, a = img_array[y_pos, w-1]
        if is_near_white(r, g, b) and not visited[y_pos, w-1]:
            visited[y_pos, w-1] = 1
            queue.append((w-1, y_pos))
    
    # BFS flood fill
    idx = 0
    while idx < len(queue):
        x_pos, y_pos = queue[idx]
        idx += 1
        
        img_array[y_pos, x_pos, 3] = 0
        
        for nx, ny in [(x_pos+1, y_pos), (x_pos-1, y_pos), (x_pos, y_pos+1), (x_pos, y_pos-1)]:
            if 0 <= nx < w and 0 <= ny < h and not visited[ny, nx]:
                r, g, b, a = img_array[ny, nx]
                if is_near_white(r, g, b):
                    visited[ny, nx] = 1
                    queue.append((nx, ny))
    
    return Image.fromarray(img_array, 'RGBA')

def create_price_image(price: str, width: int, height: int) -> Image.Image:
    """Membuat gambar teks harga dengan format rupiah"""
    img = Image.new('RGBA', (width, height), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    
    # Format harga ke rupiah
    price_formatted = format_rupiah(price)
    
    base_size = 160
    if len(price_formatted) > 12:
        size = max(90, base_size - (len(price_formatted) - 12) * 8)
    elif len(price_formatted) > 8:
        size = max(100, base_size - (len(price_formatted) - 8) * 10)
    else:
        size = base_size
    
    try:
        font = ImageFont.truetype("Arial Black.ttf", size)
    except:
        try:
            font = ImageFont.truetype("Arial.ttf", size)
        except:
            font = get_font(size, bold=True)
    
    bbox = draw.textbbox((0, 0), price_formatted, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    x = (width - text_width) // 2
    y = (height - text_height) // 2
    
    draw.text((x, y), price_formatted, fill=(17, 17, 17), font=font)
    
    return img

async def generate_pop_image(plu: str, price: str) -> BytesIO:
    """Generate promotional image like the TypeScript bot with exact positioning"""
    scaled_w = TEMPLATE_SIZE[0] * SCALE
    scaled_h = TEMPLATE_SIZE[1] * SCALE
    scaled_product = {k: v * SCALE for k, v in PRODUCT_AREA.items()}
    scaled_price = {k: v * SCALE for k, v in PRICE_AREA.items()}
    
    try:
        template_path = "template.jpg"
        
        if not os.path.exists(template_path):
            template = Image.new('RGB', TEMPLATE_SIZE, color=(255, 255, 255))
            draw = ImageDraw.Draw(template)
            draw.rectangle([0, 0, TEMPLATE_SIZE[0]-1, TEMPLATE_SIZE[1]-1], outline=(200, 200, 200), width=2)
            draw.rectangle([PRODUCT_AREA["x"], PRODUCT_AREA["y"], 
                          PRODUCT_AREA["x"]+PRODUCT_AREA["width"], 
                          PRODUCT_AREA["y"]+PRODUCT_AREA["height"]], 
                         outline=(200, 200, 200), width=1)
            draw.rectangle([PRICE_AREA["x"], PRICE_AREA["y"], 
                          PRICE_AREA["x"]+PRICE_AREA["width"], 
                          PRICE_AREA["y"]+PRICE_AREA["height"]], 
                         outline=(200, 200, 200), width=1)
            template.save(template_path, "JPEG", quality=95)
            logger.info("Template default telah dibuat")
        
        template = Image.open(template_path)
        template = template.resize((scaled_w, scaled_h), Image.Resampling.LANCZOS)
        template = template.convert('RGBA')
        
        product_img_data = await download_product_image(plu)
        product_img = Image.open(product_img_data)
        
        product_img = flood_fill_remove_background(product_img)
        
        target_width = int(scaled_product["width"] * 0.85)
        target_height = int(scaled_product["height"] * 0.85)
        
        original_w, original_h = product_img.size
        ratio = min(target_width / original_w, target_height / original_h)
        new_w = max(int(original_w * ratio), 100)
        new_h = max(int(original_h * ratio), 100)
        
        product_img = product_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        
        paste_x = scaled_product["x"] + (scaled_product["width"] - new_w) // 2
        paste_y = scaled_product["y"] + (scaled_product["height"] - new_h) // 2
        
        template.paste(product_img, (paste_x, paste_y), product_img)
        
        price_img = create_price_image(price, scaled_price["width"], scaled_price["height"])
        template.paste(price_img, (scaled_price["x"], scaled_price["y"]), price_img)
        
        template_rgb = template.convert('RGB')
        
        enhancer = ImageEnhance.Color(template_rgb)
        template_rgb = enhancer.enhance(1.2)
        
        enhancer = ImageEnhance.Brightness(template_rgb)
        template_rgb = enhancer.enhance(1.03)
        
        template_rgb = template_rgb.filter(ImageFilter.UnsharpMask(radius=0.6, percent=100, threshold=0))
        
        output = BytesIO()
        template_rgb.save(output, format='JPEG', quality=100, optimize=True)
        output.seek(0)
        
        gc.collect()
        
        return output
        
    except Exception as e:
        logger.error(f"Error generating POP image: {e}")
        raise

# ======================================================
# REMINDER CUSTOM FUNCTIONS
# ======================================================
async def send_reminder_custom(context: CallbackContext):
    """Mengirim reminder custom yang sudah dijadwalkan"""
    try:
        wib = pytz.timezone('Asia/Jakarta')
        now = datetime.now(wib)
        hari_ini = now.strftime('%A').lower()
        tanggal_hari_ini = now.day
        
        hari_map_eng = {
            'monday': 'senin', 'tuesday': 'selasa', 'wednesday': 'rabu',
            'thursday': 'kamis', 'friday': 'jumat', 'saturday': 'sabtu', 'sunday': 'minggu'
        }
        hari_ini = hari_map_eng.get(hari_ini, hari_ini)
        
        for reminder in custom_reminders:
            if reminder.get('enabled', True):
                waktu_ok = False
                
                if reminder['schedule'].startswith('2minggu_'):
                    hari_target = reminder['schedule'].replace('2minggu_', '')
                    epoch_days = now.toordinal()
                    if (epoch_days // 14) % 2 == 0 and hari_ini == hari_target:
                        waktu_ok = True
                
                elif reminder['schedule'] == 'tanggal':
                    try:
                        if '|' in reminder['message']:
                            tgl_str, pesan_asli = reminder['message'].split('|', 1)
                            target_tanggal = int(tgl_str)
                            reminder['message'] = pesan_asli
                            if tanggal_hari_ini == target_tanggal:
                                waktu_ok = True
                    except:
                        pass
                
                elif reminder['schedule'] == 'setiaphari':
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
                        logger.info(f"✅ Reminder custom terkirim: {reminder['message'][:50]}")
                        await asyncio.sleep(60)
    except Exception as e:
        logger.error(f"❌ Gagal kirim reminder custom: {e}")

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
            f"Contoh:\n"
            f"• `09:00_senin_Rapat pagi`\n"
            f"• `08:00_2minggu_senin_Rapat 2 minggu`\n"
            f"• `10:00_tanggal_15|Bayar tagihan`\n\n"
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
            
            valid_schedules = ['setiaphari', 'weekday', 'weekend', 'tanggal',
                               '2minggu_senin', '2minggu_selasa', '2minggu_rabu', 
                               '2minggu_kamis', '2minggu_jumat', '2minggu_sabtu', '2minggu_minggu',
                               'senin', 'selasa', 'rabu', 'kamis', 'jumat', 'sabtu', 'minggu']
            
            if schedule_part not in valid_schedules:
                await update.message.reply_text(
                    f"❌ Jadwal '{schedule_part}' tidak valid!\n\n"
                    f"Jadwal yang valid:\n"
                    f"• `setiaphari` - Setiap hari\n"
                    f"• `weekday` - Senin s/d Jumat\n"
                    f"• `weekend` - Sabtu & Minggu\n"
                    f"• `2minggu_senin` hingga `2minggu_minggu` - 2 minggu sekali di hari tertentu\n"
                    f"• `tanggal` - Setiap tanggal tertentu\n"
                    f"• `senin` hingga `minggu` - Setiap minggu di hari tertentu",
                    parse_mode="Markdown"
                )
                return True
            
            if schedule_part == 'tanggal':
                if '|' not in message_part:
                    await update.message.reply_text(
                        "❌ Format untuk jadwal `tanggal` salah!\n\n"
                        "Gunakan format: `tanggal|pesan`\n"
                        "Contoh: `15|Bayar tagihan listrik`",
                        parse_mode="Markdown"
                    )
                    return True
                else:
                    try:
                        tgl_str = message_part.split('|')[0]
                        tgl = int(tgl_str)
                        if tgl < 1 or tgl > 31:
                            raise ValueError
                    except:
                        await update.message.reply_text(
                            "❌ Tanggal tidak valid! Gunakan angka 1-31.\n"
                            "Contoh: `15|Bayar tagihan`",
                            parse_mode="Markdown"
                        )
                        return True
            
            edit_id = context.user_data.get('edit_id')
            if edit_id is not None:
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
            else:
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
            await update.message.reply_text(
                f"❌ Error: {e}\n\n"
                f"Gunakan format: `HH:MM_jadwal_pesan`\n"
                f"Contoh: `15:30_setiaphari_Segera absen pulang`",
                parse_mode="Markdown"
            )
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

async def handle_reminder_menu(update: Update, context: CallbackContext):
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
            "📌 *CONTOH PENGGUNAAN:*\n"
            "• `08:00_setiaphari_Selamat pagi!`\n"
            "• `14:30_senin_Rapat tim`\n"
            "• `20:00_weekend_Istirahat`\n"
            "• `09:00_2minggu_senin_Meeting 2 minggu sekali`\n"
            "• `09:00_2minggu_jumat_Evaluasi 2 minggu sekali`\n"
            "• `10:00_tanggal_15|Bayar tagihan listrik`\n\n"
            "📋 *JADWAL YANG VALID:*\n"
            "• `setiaphari` - Setiap hari\n"
            "• `weekday` - Senin s/d Jumat\n"
            "• `weekend` - Sabtu & Minggu\n"
            "• `2minggu_senin` hingga `2minggu_minggu` - 2 minggu sekali di hari tertentu\n"
            "• `tanggal` - Setiap tanggal tertentu (format: `tanggal|pesan`)\n"
            "• `senin`, `selasa`, `rabu`, `kamis`, `jumat`, `sabtu`, `minggu`\n\n"
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
            
            valid_schedules = ['setiaphari', 'weekday', 'weekend', 'tanggal',
                               '2minggu_senin', '2minggu_selasa', '2minggu_rabu', 
                               '2minggu_kamis', '2minggu_jumat', '2minggu_sabtu', '2minggu_minggu',
                               'senin', 'selasa', 'rabu', 'kamis', 'jumat', 'sabtu', 'minggu']
            
            if schedule_part not in valid_schedules:
                await update.message.reply_text(
                    f"❌ Jadwal '{schedule_part}' tidak valid!\n\n"
                    f"Jadwal yang valid:\n"
                    f"• `setiaphari` - Setiap hari\n"
                    f"• `weekday` - Senin s/d Jumat\n"
                    f"• `weekend` - Sabtu & Minggu\n"
                    f"• `2minggu_senin` hingga `2minggu_minggu` - 2 minggu sekali di hari tertentu\n"
                    f"• `tanggal` - Setiap tanggal tertentu\n"
                    f"• `senin` hingga `minggu` - Setiap minggu di hari tertentu",
                    parse_mode="Markdown"
                )
                return True
            
            if schedule_part == 'tanggal':
                if '|' not in message_part:
                    await update.message.reply_text(
                        "❌ Format untuk jadwal `tanggal` salah!\n\n"
                        "Gunakan format: `tanggal|pesan`\n"
                        "Contoh: `15|Bayar tagihan listrik`",
                        parse_mode="Markdown"
                    )
                    return True
                else:
                    try:
                        tgl_str = message_part.split('|')[0]
                        tgl = int(tgl_str)
                        if tgl < 1 or tgl > 31:
                            raise ValueError
                    except:
                        await update.message.reply_text(
                            "❌ Tanggal tidak valid! Gunakan angka 1-31.\n"
                            "Contoh: `15|Bayar tagihan`",
                            parse_mode="Markdown"
                        )
                        return True
            
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
            await update.message.reply_text(
                f"❌ Error: {e}\n\n"
                f"Gunakan format: `HH:MM_jadwal_pesan`\n"
                f"Contoh: `15:30_setiaphari_Segera absen pulang`",
                parse_mode="Markdown"
            )
        return True
    
    return False

# ======================================================
# SCHEDULER MANUAL
# ======================================================
async def scheduler_loop(application):
    """Loop penjadwalan hanya untuk reminder custom"""
    while True:
        try:
            await send_reminder_custom(application)
            await asyncio.sleep(30)
        except Exception as e:
            logger.error(f"Error di scheduler: {e}")
            await asyncio.sleep(60)

# ======================================================
# HANDLER BOT UTAMA
# ======================================================
async def start(update: Update, context):
    await update.message.reply_text(
        "🎨 *Bot Cetak Harga Mewah + POP Maker*\n\n"
        "📦 *Mode PAKET* (2 harga)\n"
        "Format: `harga_normal.harga_promo.qty`\n"
        "Contoh: `600000.70000.3`\n\n"
        "🔥 *Mode PROMO*\n"
        "Format: `nama.harga`\n"
        "Contoh: `Indomie Goreng.3500`\n\n"
        "📄 *Mode NORMAL*\n"
        "Format: `nama.harga`\n"
        "Contoh: `Beras Premium.75000`\n\n"
        "🖼️ *Mode POP* (Point of Purchase)\n"
        "Format: `PLU.Harga`\n"
        "Contoh: `10008989.15000`\n"
        "Catatan: PLU harus 8 digit angka\n\n"
        "🔐 *Reminder:* /reminder\n\n"
        "Pilih mode dari tombol di bawah!",
        parse_mode="Markdown",
        reply_markup=MAIN_KEYBOARD
    )

async def reminder_command(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "🔐 *Akses Reminder*\n\n"
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
    
    # Handle mode
    mode = context.user_data.get('mode')
    if not mode:
        await update.message.reply_text("❌ Pilih mode dulu: /paket, /promo, /normal, atau /pop")
        return
    
    text = update.message.text.strip()
    lines = text.split('\n')
    
    # Special handling for POP mode
    if mode == 'pop':
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            pop_data = parse_pop_input(line)
            if not pop_data:
                await update.message.reply_text(
                    f"❌ Format salah untuk POP!\n"
                    f"Gunakan: `PLU.Harga`\n"
                    f"Contoh: `10008989.15000`\n\n"
                    f"PLU harus 8 digit angka", 
                    parse_mode="Markdown"
                )
                continue
            
            try:
                # Format harga untuk caption
                harga_formatted = format_rupiah(pop_data['harga'])
                
                await update.message.reply_text(f"🖼️ Membuat POP untuk PLU {pop_data['plu']}...")
                img_buffer = await generate_pop_image(pop_data['plu'], pop_data['harga'])
                await update.message.reply_photo(
                    photo=img_buffer, 
                    caption=f"🖼️ *POP*\nPLU: {pop_data['plu']}\nHarga: {harga_formatted}",
                    parse_mode="Markdown"
                )
            except Exception as e:
                await update.message.reply_text(f"❌ Gagal membuat POP: {str(e)}")
        
        context.user_data['mode'] = None
        return
    
    # Handle other modes (paket, promo, normal)
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
    
    print("=" * 60)
    print("🤖 BOT CETAK HARGA + POP MAKER + REMINDER CUSTOM")
    print("=" * 60)
    print(f"📱 Group ID: {GROUP_CHAT_ID}")
    print(f"📌 Subtopik MENU ID: {MESSAGE_THREAD_ID}")
    print(f"🔐 Reminder Custom: /reminder (password: {ADMIN_PASSWORD})")
    print(f"📐 Ukuran A4: {IMG_W}x{IMG_H} px (150 DPI)")
    print(f"🖼️ POP Template: {TEMPLATE_SIZE[0]}x{TEMPLATE_SIZE[1]} px (Scale: {SCALE}x)")
    print("=" * 60)
    print("\n📋 JADWAL REMINDER YANG TERSEDIA:")
    print("   • setiaphari      - Setiap hari")
    print("   • weekday         - Senin s/d Jumat")
    print("   • weekend         - Sabtu & Minggu")
    print("   • senin/minggu    - Setiap minggu di hari tertentu")
    print("   • 2minggu_senin   - 2 minggu sekali di hari Senin")
    print("   • 2minggu_jumat   - 2 minggu sekali di hari Jumat")
    print("   • tanggal         - Setiap tanggal tertentu")
    print("\n📋 FORMAT POP MAKER:")
    print("   • /pop lalu kirim: PLU.Harga")
    print("   • Contoh: 10008989.15000")
    print("=" * 60)
    
    application = Application.builder().token(TOKEN).build()
    
    # Handler untuk command
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("reminder", reminder_command))
    application.add_handler(CommandHandler("promo", set_mode))
    application.add_handler(CommandHandler("normal", set_mode))
    application.add_handler(CommandHandler("paket", set_mode))
    application.add_handler(CommandHandler("pop", set_mode))
    
    # Handler untuk pesan biasa
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Jalankan scheduler manual di background
    asyncio.create_task(scheduler_loop(application))
    
    print("\n✅ Bot berjalan dengan POP Maker & reminder custom...")
    print("💡 Tips: Gunakan /reminder untuk mengakses menu reminder")
    print("💡 Tips: Gunakan /pop untuk membuat gambar POP dari PLU")
    print("\n⏳ Menunggu pesan...")
    
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        print("\n❌ Bot berhenti")
        await application.updater.stop()
        await application.stop()
        await application.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
