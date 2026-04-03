import os
import io
import math
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ForceReply
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from PIL import Image, ImageDraw, ImageFont

TOKEN = os.environ.get("TELEGRAM_TOKEN") or os.environ.get("BOT_TOKEN")

# Warna
YELLOW = (255, 230, 0)
RED = (204, 0, 0)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
DARK_BLUE = (30, 90, 185)
PAKET_RED = (220, 20, 20)

# Ukuran - DIPERBESAR LAGI
COLS = 2
ROWS = 4
ITEMS_PER_IMAGE = COLS * ROWS

CELL_W = 600      # Lebih besar
CELL_H = 400      # Lebih besar
BORDER = 10
IMG_W = COLS * CELL_W + (COLS + 1) * BORDER
IMG_H = ROWS * CELL_H + (ROWS + 1) * BORDER
HEADER_H = 100

# Ukuran font (besar!)
FONT_SIZE_HEADER = 80
FONT_SIZE_NAMA = 60
FONT_SIZE_HARGA = 140
FONT_SIZE_PAKET_JUDUL = 70
FONT_SIZE_PAKET_LABEL = 30
FONT_SIZE_PAKET_NORMAL = 40
FONT_SIZE_PAKET_PROMO = 90


def format_harga(harga_str):
    if not harga_str:
        return ""
    try:
        angka = int(str(harga_str).replace(".", "").replace(",", ""))
        return f"{angka:,}".replace(",", ".")
    except:
        return str(harga_str)


def draw_cell(draw, x, y, nama, harga):
    """Mode PROMO"""
    # Background kuning
    draw.rectangle([x, y, x + CELL_W, y + CELL_H], fill=YELLOW)
    # Header merah
    draw.rectangle([x, y, x + CELL_W, y + HEADER_H], fill=RED)

    # Teks PROMOSI - ukuran besar
    draw.text((x + CELL_W//2, y + HEADER_H//2), "PROMOSI", 
              fill=YELLOW, anchor="mm", font=None, stroke_width=0)
    
    # Untuk teks besar, kita gambar manual dengan font default yang diperbesar
    # Gunakan metode draw.text dengan ukuran yang diperbesar
    
    # Nama barang
    if nama:
        # Gambar teks dengan ukuran lebih besar (simulasi dengan spasi)
        nama_upper = nama.upper()
        y_nama = y + HEADER_H + 40
        draw.text((x + CELL_W//2, y_nama), nama_upper, fill=BLACK, anchor="mm")

    # Harga
    if harga:
        harga_fmt = format_harga(harga)
        y_harga = y + HEADER_H + 160
        draw.text((x + CELL_W//2, y_harga), harga_fmt, fill=BLACK, anchor="mm")


def draw_cell_normal(draw, x, y, nama, harga):
    """Mode NORMAL"""
    draw.rectangle([x, y, x + CELL_W, y + CELL_H], fill=WHITE, outline=(180, 180, 180), width=5)

    if nama:
        y_nama = y + 80
        draw.text((x + CELL_W//2, y_nama), nama.upper(), fill=BLACK, anchor="mm")

    if harga:
        harga_fmt = format_harga(harga)
        y_harga = y + 220
        draw.text((x + CELL_W//2, y_harga), harga_fmt, fill=BLACK, anchor="mm")


def buat_gambar_normal(items):
    padded = list(items)
    while len(padded) < ITEMS_PER_IMAGE:
        padded.append(("", ""))

    img = Image.new('RGB', (IMG_W, IMG_H), color=(240, 240, 240))
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
    draw.rectangle([0, 0, IMG_W, IMG_H], fill=(60, 60, 60))

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


def draw_cell_paket(draw, x, y, harga_normal, harga_promo):
    """Mode PAKET"""
    draw.rectangle([x, y, x + CELL_W, y + CELL_H], fill=DARK_BLUE)
    draw.rectangle([x, y, x + CELL_W, y + CELL_H], outline=WHITE, width=5)
    
    PAD = 20

    # Judul PAKET HEMAT
    y_judul = y + PAD + 10
    draw.text((x + CELL_W//2, y_judul), "PAKET HEMAT", fill=PAKET_RED, anchor="mm")

    # Harga Normal
    y_normal_label = y_judul + 80
    draw.text((x + PAD, y_normal_label), "Harga Normal", fill=WHITE, anchor="lm")
    
    norm_fmt = format_harga(harga_normal)
    if norm_fmt:
        y_normal_harga = y_normal_label + 40
        # Posisi kanan
        x_normal = x + CELL_W - PAD
        draw.text((x_normal, y_normal_harga), f"Rp {norm_fmt}", fill=WHITE, anchor="rm")

    # Harga Spesial
    y_spesial_label = y_normal_label + 100
    draw.text((x + PAD, y_spesial_label), "Harga Spesial", fill=WHITE, anchor="lm")
    
    promo_fmt = format_harga(harga_promo)
    if promo_fmt:
        y_spesial_harga = y_spesial_label + 60
        draw.text((x + CELL_W//2, y_spesial_harga), f"Rp {promo_fmt}", fill=WHITE, anchor="mm")


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
                except:
                    jumlah = 1
            for _ in range(jumlah):
                entries.append((harga_normal, harga_promo))
    return entries


KEYBOARD = ReplyKeyboardMarkup(
    [[KeyboardButton("/promo"), KeyboardButton("/normal"), KeyboardButton("/paket")]],
    resize_keyboard=True,
    is_persistent=True
)


async def start(update: Update, context):
    await update.message.reply_text(
        "👇 PILIH PERINTAH DI BAWAH 👇\n\n"
        "━━━━━━━━━━━━━━━━━\n"
        "🟡 /promo — Latar KUNING + header PROMOSI\n"
        "⬜ /normal — Latar PUTIH, nama & harga saja\n"
        "🔵 /paket — PAKET HEMAT (harga coret + promo)\n"
        "━━━━━━━━━━━━━━━━━\n\n"
        "Format /promo & /normal:\nNAMA.HARGA\n\n"
        "Format /paket:\nHARGA_NORMAL.HARGA_PROMO.JUMLAH\n"
        "Contoh: 70000.2000.4\n\n"
        "Setiap gambar memuat 8 kartu.",
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
        "🟡 Mode PROMO dipilih.\n\nKirim daftar barang, satu per baris:\n\nAQUA.21000\nINDOMIE.10000\nBERAS.65000",
        reply_markup=ForceReply(input_field_placeholder="Ketik daftar barang...")
    )


async def normal(update: Update, context):
    context.user_data['mode'] = 'normal'
    await update.message.reply_text(
        "⬜ Mode NORMAL dipilih.\n\nKirim daftar barang, satu per baris:\n\nAQUA.21000\nINDOMIE.10000\nBERAS.65000",
        reply_markup=ForceReply(input_field_placeholder="Ketik daftar barang...")
    )


async def paket(update: Update, context):
    context.user_data['mode'] = 'paket'
    await update.message.reply_text(
        "🔵 Mode PAKET HEMAT dipilih.\n\nKirim daftar paket:\nFormat: HARGA_NORMAL.HARGA_PROMO.JUMLAH\n\nContoh:\n70000.2000.4\n50000.35000.2",
        reply_markup=ForceReply(input_field_placeholder="Contoh: 70000.2000.4")
    )


async def handle_text(update: Update, context):
    mode = context.user_data.get('mode')

    if not mode:
        await update.message.reply_text(
            "Pilih perintah terlebih dahulu: /promo , /normal , atau /paket",
            reply_markup=KEYBOARD
        )
        return

    lines = (update.message.text or "").split('\n')

    if mode == 'paket':
        entries = parse_paket(lines)
        if not entries:
            await update.message.reply_text("Format salah. Contoh: 70000.2000.4", reply_markup=KEYBOARD)
            context.user_data['mode'] = None
            return
        
        total_images = math.ceil(len(entries) / ITEMS_PER_IMAGE)
        await update.message.reply_text(f"Membuat {total_images} gambar untuk {len(entries)} kartu...")
        
        for i in range(total_images):
            batch = entries[i * ITEMS_PER_IMAGE:(i + 1) * ITEMS_PER_IMAGE]
            gambar = buat_gambar_paket(batch)
            await update.message.reply_photo(photo=gambar, caption=f"Gambar {i+1}/{total_images}")
            
    else:
        items = parse_items(lines, uppercase=(mode == 'promo'))
        if not items:
            await update.message.reply_text("Format salah. Contoh: AQUA.21000", reply_markup=KEYBOARD)
            context.user_data['mode'] = None
            return
            
        total_images = math.ceil(len(items) / ITEMS_PER_IMAGE)
        await update.message.reply_text(f"Membuat {total_images} gambar untuk {len(items)} barang...")
        
        for i in range(total_images):
            batch = items[i * ITEMS_PER_IMAGE:(i + 1) * ITEMS_PER_IMAGE]
            gambar = buat_gambar_grid(batch) if mode == 'promo' else buat_gambar_normal(batch)
            await update.message.reply_photo(photo=gambar, caption=f"Gambar {i+1}/{total_images}")

    context.user_data['mode'] = None


def main():
    if not TOKEN:
        print("ERROR: TELEGRAM_TOKEN atau BOT_TOKEN tidak ditemukan!")
        return

    print("✅ Bot Telegram Promosi berjalan...")
    print(f"📐 Ukuran gambar: {IMG_W} x {IMG_H}")
    print(f"📦 Setiap gambar: {ITEMS_PER_IMAGE} kartu")
    
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("promo", promo))
    app.add_handler(CommandHandler("normal", normal))
    app.add_handler(CommandHandler("paket", paket))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.run_polling()


if __name__ == "__main__":
    main()
