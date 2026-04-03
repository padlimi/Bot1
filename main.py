import os
import io
import math
import asyncio
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ForceReply
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from telegram.error import NetworkError, TimedOut

from PIL import Image, ImageDraw, ImageFont

TOKEN = os.environ.get("TELEGRAM_TOKEN") or os.environ.get("BOT_TOKEN")

# ============ FIXED FONT - PAKAI DEJAVU YANG SUDAH DIINSTALL ============
# Path font yang pasti ada setelah install di Dockerfile
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REGULAR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

def get_font(bold=True, size=20):
    """Load font dengan ukuran yang diinginkan"""
    font_path = FONT_BOLD if bold else FONT_REGULAR
    try:
        return ImageFont.truetype(font_path, size)
    except:
        return ImageFont.load_default()

# Warna
YELLOW = (255, 230, 0)
RED = (204, 0, 0)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
DARK_BLUE = (30, 90, 185)
PAKET_RED = (220, 20, 20)
GREY = (60, 60, 60)
LIGHT_GREY = (240, 240, 240)

# Ukuran grid - DIPERBESAR untuk font besar
COLS = 2
ROWS = 4
ITEMS_PER_IMAGE = COLS * ROWS

CELL_W = 500
CELL_H = 340
BORDER = 5
IMG_W = COLS * CELL_W + (COLS + 1) * BORDER
IMG_H = ROWS * CELL_H + (ROWS + 1) * BORDER
HEADER_H = 80


def format_harga(harga_str):
    if not harga_str or harga_str == "":
        return ""
    try:
        cleaned = str(harga_str).replace(".", "").replace(",", "")
        angka = int(cleaned)
        return f"{angka:,}".replace(",", ".")
    except (ValueError, AttributeError):
        return str(harga_str)


def draw_cell(draw, x, y, nama, harga):
    """Mode PROMO"""
    draw.rectangle([x, y, x + CELL_W, y + CELL_H], fill=YELLOW)
    draw.rectangle([x, y, x + CELL_W, y + HEADER_H], fill=RED)

    font_header = get_font(bold=True, size=60)
    font_nama = get_font(bold=True, size=46)
    font_harga = get_font(bold=True, size=110)

    # PROMOSI
    header_text = "PROMOSI"
    bbox = draw.textbbox((0, 0), header_text, font=font_header)
    tw = bbox[2] - bbox[0]
    tx = x + (CELL_W - tw) // 2
    ty = y + (HEADER_H - (bbox[3] - bbox[1])) // 2
    draw.text((tx, ty), header_text, fill=YELLOW, font=font_header)

    # Nama
    if nama:
        bbox_n = draw.textbbox((0, 0), nama, font=font_nama)
        nw = bbox_n[2] - bbox_n[0]
        nx = x + (CELL_W - nw) // 2
        ny = y + HEADER_H + 20
        draw.text((nx, ny), nama, fill=BLACK, font=font_nama)

    # Harga
    if harga:
        harga_fmt = format_harga(harga)
        bbox_h = draw.textbbox((0, 0), harga_fmt, font=font_harga)
        hw = bbox_h[2] - bbox_h[0]
        hx = x + (CELL_W - hw) // 2
        hy = y + HEADER_H + 120
        draw.text((hx, hy), harga_fmt, fill=BLACK, font=font_harga)


def draw_cell_normal(draw, x, y, nama, harga):
    """Mode NORMAL"""
    draw.rectangle([x, y, x + CELL_W, y + CELL_H], fill=WHITE, outline=(180, 180, 180), width=3)

    font_nama = get_font(bold=True, size=50)
    font_harga = get_font(bold=True, size=110)

    if nama:
        bbox_n = draw.textbbox((0, 0), nama, font=font_nama)
        nw = bbox_n[2] - bbox_n[0]
        nx = x + (CELL_W - nw) // 2
        ny = y + 55
        draw.text((nx, ny), nama, fill=BLACK, font=font_nama)

    if harga:
        harga_fmt = format_harga(harga)
        bbox_h = draw.textbbox((0, 0), harga_fmt, font=font_harga)
        hw = bbox_h[2] - bbox_h[0]
        hx = x + (CELL_W - hw) // 2
        hy = y + 180
        draw.text((hx, hy), harga_fmt, fill=BLACK, font=font_harga)


def buat_gambar_normal(items):
    padded = list(items)
    while len(padded) < ITEMS_PER_IMAGE:
        padded.append(("", ""))

    img = Image.new('RGB', (IMG_W, IMG_H), color=LIGHT_GREY)
    draw = ImageDraw.Draw(img)

    for row in range(ROWS):
        for col in range(COLS):
            idx = row * COLS + col
            nama, harga = padded[idx]
            x = BORDER + col * (CELL_W + BORDER)
            y = BORDER + row * (CELL_H + BORDER)
            draw_cell_normal(draw, x, y, nama, harga)

    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    return img_bytes


def buat_gambar_grid(items):
    while len(items) < ITEMS_PER_IMAGE:
        items.append(("", ""))

    img = Image.new('RGB', (IMG_W, IMG_H), color=WHITE)
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, IMG_W, IMG_H], fill=GREY)

    for row in range(ROWS):
        for col in range(COLS):
            idx = row * COLS + col
            nama, harga = items[idx]
            x = BORDER + col * (CELL_W + BORDER)
            y = BORDER + row * (CELL_H + BORDER)
            draw_cell(draw, x, y, nama, harga)

    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    return img_bytes


def draw_text_strikethrough(draw, xy, text, font, fill):
    x, y = xy
    bbox = draw.textbbox((x, y), text, font=font)
    draw.text((x, y), text, fill=fill, font=font)
    mid_y = (bbox[1] + bbox[3]) // 2
    draw.line([(bbox[0], mid_y), (bbox[2], mid_y)], fill=fill, width=4)


def draw_cell_paket(draw, x, y, harga_normal, harga_promo):
    """Mode PAKET"""
    draw.rectangle([x, y, x + CELL_W, y + CELL_H], fill=DARK_BLUE)
    draw.rectangle([x, y, x + CELL_W, y + CELL_H], outline=WHITE, width=3)
    
    PAD = 18
    
    font_label = get_font(bold=False, size=24)
    font_judul = get_font(bold=True, size=54)
    font_norm = get_font(bold=True, size=32)
    font_promo = get_font(bold=True, size=70)

    norm_fmt = format_harga(harga_normal)
    promo_fmt = format_harga(harga_promo)

    # JUDUL
    judul = "PAKET HEMAT"
    bbox_judul = draw.textbbox((0, 0), judul, font=font_judul)
    jw = bbox_judul[2] - bbox_judul[0]
    jx = x + (CELL_W - jw) // 2
    jy = y + PAD
    
    for dx, dy in [(-2, -2), (2, -2), (-2, 2), (2, 2)]:
        draw.text((jx + dx, jy + dy), judul, fill=BLACK, font=font_judul)
    draw.text((jx, jy), judul, fill=PAKET_RED, font=font_judul)

    # HARGA NORMAL
    normal_y = jy + 75
    draw.text((x + PAD, normal_y), "Harga Normal", fill=WHITE, font=font_label)
    
    if norm_fmt:
        norm_text = f"Rp {norm_fmt}"
        bbox_norm = draw.textbbox((0, 0), norm_text, font=font_norm)
        norm_width = bbox_norm[2] - bbox_norm[0]
        norm_x = x + CELL_W - norm_width - PAD
        norm_y2 = normal_y + 35
        
        bg_h = bbox_norm[3] - bbox_norm[1]
        draw.rectangle([norm_x - 8, norm_y2 - 6, norm_x + norm_width + 8, norm_y2 + bg_h + 6], fill=BLACK)
        draw_text_strikethrough(draw, (norm_x, norm_y2), norm_text, font_norm, WHITE)

    # HARGA SPESIAL
    promo_y = normal_y + 90
    draw.text((x + PAD, promo_y), "Harga Spesial", fill=WHITE, font=font_label)
    
    if promo_fmt:
        promo_text = f"Rp {promo_fmt}"
        bbox_promo = draw.textbbox((0, 0), promo_text, font=font_promo)
        promo_width = bbox_promo[2] - bbox_promo[0]
        promo_x = x + (CELL_W - promo_width) // 2
        promo_y2 = promo_y + 50
        
        bg_h = bbox_promo[3] - bbox_promo[1]
        draw.rectangle([promo_x - 10, promo_y2 - 8, promo_x + promo_width + 10, promo_y2 + bg_h + 8], fill=BLACK)
        draw.text((promo_x, promo_y2), promo_text, fill=WHITE, font=font_promo)


def buat_gambar_paket(entries):
    img = Image.new('RGB', (IMG_W, IMG_H), color=DARK_BLUE)
    draw = ImageDraw.Draw(img)

    for idx in range(ITEMS_PER_IMAGE):
        col = idx % COLS
        row = idx // COLS
        x = BORDER + col * (CELL_W + BORDER)
        y = BORDER + row * (CELL_H + BORDER)
        if idx < len(entries):
            hn, hp = entries[idx]
            draw_cell_paket(draw, x, y, hn, hp)
        else:
            draw_cell_paket(draw, x, y, "", "")

    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    return img_bytes


def parse_paket(lines):
    entries = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        parts = line.split('.')
        if len(parts) >= 2:
            harga_normal = parts[0].strip()
            harga_promo = parts[1].strip()
            jumlah = 1
            if len(parts) >= 3:
                try:
                    jumlah = int(parts[2].strip())
                except ValueError:
                    jumlah = 1
            for _ in range(jumlah):
                entries.append((harga_normal, harga_promo))
    return entries


# Keyboard
KEYBOARD = ReplyKeyboardMarkup(
    [[KeyboardButton("/promo"), KeyboardButton("/normal"), KeyboardButton("/paket")]],
    resize_keyboard=True,
    is_persistent=True,
    input_field_placeholder="Pilih perintah di bawah..."
)


async def start(update: Update, context):
    await update.message.reply_text(
        "👇 *PILIH PERINTAH DI BAWAH* 👇\n\n"
        "━━━━━━━━━━━━━━━━━\n"
        "🟡 /promo — Latar KUNING + header PROMOSI\n"
        "⬜ /normal — Latar PUTIH, nama & harga saja\n"
        "🔵 /paket — PAKET HEMAT (harga coret + promo)\n"
        "━━━━━━━━━━━━━━━━━\n\n"
        "📝 *Format Input:*\n\n"
        "▸ /promo & /normal:\n"
        "`NAMA.HARGA`\n"
        "Contoh: `AQUA.21000`\n\n"
        "▸ /paket:\n"
        "`HARGA_NORMAL.HARGA_PROMO.JUMLAH`\n"
        "Contoh: `70000.2000.4`\n\n"
        "Setiap gambar memuat 8 kartu.",
        parse_mode='Markdown',
        reply_markup=KEYBOARD
    )


def parse_items(lines, uppercase=False):
    items = []
    for line in lines:
        line = line.strip()
        if '.' in line:
            parts = line.rsplit('.', 1)
            nama = parts[0].strip()
            if uppercase:
                nama = nama.upper()
            harga = parts[1].strip()
            if nama and harga:
                items.append((nama, harga))
    return items


async def promo(update: Update, context):
    context.user_data['mode'] = 'promo'
    await update.message.reply_text(
        "🟡 *Mode PROMO* dipilih.\n\n"
        "Kirim daftar barang, satu per baris:\n\n"
        "`AQUA.21000`\n`INDOMIE.10000`\n`BERAS.65000`",
        parse_mode='Markdown',
        reply_markup=ForceReply(input_field_placeholder="Ketik daftar barang di sini...")
    )


async def normal(update: Update, context):
    context.user_data['mode'] = 'normal'
    await update.message.reply_text(
        "⬜ *Mode NORMAL* dipilih.\n\n"
        "Kirim daftar barang, satu per baris:\n\n"
        "`AQUA.21000`\n`INDOMIE.10000`\n`BERAS.65000`",
        parse_mode='Markdown',
        reply_markup=ForceReply(input_field_placeholder="Ketik daftar barang di sini...")
    )


async def paket(update: Update, context):
    context.user_data['mode'] = 'paket'
    await update.message.reply_text(
        "🔵 *Mode PAKET HEMAT* dipilih.\n\n"
        "Kirim daftar paket, satu per baris:\n"
        "Format: `HARGA_NORMAL.HARGA_PROMO.JUMLAH`\n\n"
        "Contoh:\n`70000.2000.4`\n`50000.35000.2`",
        parse_mode='Markdown',
        reply_markup=ForceReply(input_field_placeholder="Contoh: 70000.2000.4")
    )


async def handle_text(update: Update, context):
    mode = context.user_data.get('mode')

    if not mode:
        await update.message.reply_text(
            "Pilih perintah terlebih dahulu 👇\n\n/promo , /normal , atau /paket",
            reply_markup=KEYBOARD
        )
        return

    lines = (update.message.text or "").split('\n')

    if mode == 'paket':
        entries = parse_paket(lines)
        if not entries:
            await update.message.reply_text(
                "❌ *Format salah!*\n\nContoh: `70000.2000.4`",
                parse_mode='Markdown',
                reply_markup=KEYBOARD
            )
            context.user_data['mode'] = None
            return
        
        total_images = math.ceil(len(entries) / ITEMS_PER_IMAGE)
        await update.message.reply_text(
            f"📦 Membuat {total_images} gambar untuk {len(entries)} kartu...",
            reply_markup=KEYBOARD
        )
        
        for i in range(total_images):
            batch = entries[i * ITEMS_PER_IMAGE:(i + 1) * ITEMS_PER_IMAGE]
            gambar = buat_gambar_paket(batch)
            await update.message.reply_photo(photo=gambar, caption=f"📸 Gambar {i+1}/{total_images}")
            
    else:
        items = parse_items(lines, uppercase=(mode == 'promo'))
        if not items:
            await update.message.reply_text(
                "❌ *Format salah!*\n\nContoh: `AQUA.21000`",
                parse_mode='Markdown',
                reply_markup=KEYBOARD
            )
            context.user_data['mode'] = None
            return
            
        total_images = math.ceil(len(items) / ITEMS_PER_IMAGE)
        await update.message.reply_text(
            f"🖼️ Membuat {total_images} gambar untuk {len(items)} barang...",
            reply_markup=KEYBOARD
        )
        
        for i in range(total_images):
            batch = items[i * ITEMS_PER_IMAGE:(i + 1) * ITEMS_PER_IMAGE]
            gambar = buat_gambar_grid(batch) if mode == 'promo' else buat_gambar_normal(batch)
            await update.message.reply_photo(photo=gambar, caption=f"📸 Gambar {i+1}/{total_images}")

    context.user_data['mode'] = None


def main():
    if not TOKEN:
        print("ERROR: TELEGRAM_TOKEN atau BOT_TOKEN tidak ditemukan!")
        return

    print("✅ Bot Telegram Promosi berjalan...")
    print(f"📐 Ukuran gambar: {IMG_W}x{IMG_H}")
    
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("promo", promo))
    app.add_handler(CommandHandler("normal", normal))
    app.add_handler(CommandHandler("paket", paket))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    app.run_polling()


if __name__ == "__main__":
    main()
