import os
import io
import math
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ForceReply
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from PIL import Image, ImageDraw, ImageFont

TOKEN = os.environ.get("TELEGRAM_TOKEN") or os.environ.get("BOT_TOKEN")

# ============ DAFTAR FONT YANG TERSEDIA ============
FONT_PATHS = [
    # Font dari Google Fonts (Roboto)
    "/usr/share/fonts/truetype/roboto/Roboto-Bold.ttf",
    "/usr/share/fonts/truetype/roboto/Roboto-Regular.ttf",
    # Font DejaVu
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    # Font Liberation
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    # Font Noto
    "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
    "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
]

def get_font(bold=True, size=20):
    """Mencari font yang tersedia di sistem"""
    for font_path in FONT_PATHS:
        if bold and "Bold" not in font_path and "bold" not in font_path:
            continue
        if not bold and ("Bold" in font_path or "bold" in font_path):
            continue
        if os.path.exists(font_path):
            try:
                return ImageFont.truetype(font_path, size)
            except:
                continue
    
    # Fallback terakhir
    return ImageFont.load_default()
# ===================================================

YELLOW = (255, 230, 0)
RED = (204, 0, 0)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)

COLS = 2
ROWS = 4
ITEMS_PER_IMAGE = COLS * ROWS

CELL_W = 420
CELL_H = 300
BORDER = 4
IMG_W = COLS * CELL_W + (COLS + 1) * BORDER
IMG_H = ROWS * CELL_H + (ROWS + 1) * BORDER

HEADER_H = 62


def format_harga(harga_str):
    try:
        angka = int(harga_str.replace(".", "").replace(",", ""))
        return f"{angka:,}".replace(",", ".")
    except ValueError:
        return harga_str


def draw_cell(draw, x, y, nama, harga):
    draw.rectangle([x, y, x + CELL_W, y + CELL_H], fill=YELLOW)
    draw.rectangle([x, y, x + CELL_W, y + HEADER_H], fill=RED)

    font_header = get_font(bold=True, size=42)
    font_nama = get_font(bold=True, size=38)
    font_harga = get_font(bold=True, size=96)

    header_text = "PROMOSI"
    bbox = draw.textbbox((0, 0), header_text, font=font_header)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = x + (CELL_W - tw) // 2
    ty = y + (HEADER_H - th) // 2
    draw.text((tx, ty), header_text, fill=YELLOW, font=font_header)

    if nama:
        # Sesuaikan ukuran font dengan panjang teks
        nama_font = get_font(bold=True, size=38)
        bbox_n = draw.textbbox((0, 0), nama, font=nama_font)
        while (bbox_n[2] - bbox_n[0]) > (CELL_W - 40) and nama_font.size > 20:
            nama_font = get_font(bold=True, size=nama_font.size - 2)
            bbox_n = draw.textbbox((0, 0), nama, font=nama_font)
        
        nw = bbox_n[2] - bbox_n[0]
        nx = x + (CELL_W - nw) // 2
        ny = y + HEADER_H + 25
        draw.text((nx, ny), nama, fill=BLACK, font=nama_font)

    if harga:
        harga_fmt = format_harga(harga)
        harga_font = get_font(bold=True, size=96)
        bbox_h = draw.textbbox((0, 0), harga_fmt, font=harga_font)
        while (bbox_h[2] - bbox_h[0]) > (CELL_W - 40) and harga_font.size > 30:
            harga_font = get_font(bold=True, size=harga_font.size - 4)
            bbox_h = draw.textbbox((0, 0), harga_fmt, font=harga_font)
        
        hw = bbox_h[2] - bbox_h[0]
        hx = x + (CELL_W - hw) // 2
        hy = y + HEADER_H + 140
        draw.text((hx, hy), harga_fmt, fill=BLACK, font=harga_font)


def draw_cell_normal(draw, x, y, nama, harga):
    draw.rectangle([x, y, x + CELL_W, y + CELL_H], fill=WHITE, outline=(200, 200, 200), width=3)

    if nama:
        nama_font = get_font(bold=True, size=42)
        bbox_n = draw.textbbox((0, 0), nama, font=nama_font)
        while (bbox_n[2] - bbox_n[0]) > (CELL_W - 40) and nama_font.size > 20:
            nama_font = get_font(bold=True, size=nama_font.size - 2)
            bbox_n = draw.textbbox((0, 0), nama, font=nama_font)
        
        nw = bbox_n[2] - bbox_n[0]
        nx = x + (CELL_W - nw) // 2
        ny = y + 50
        draw.text((nx, ny), nama, fill=BLACK, font=nama_font)

    if harga:
        harga_fmt = format_harga(harga)
        harga_font = get_font(bold=True, size=88)
        bbox_h = draw.textbbox((0, 0), harga_fmt, font=harga_font)
        while (bbox_h[2] - bbox_h[0]) > (CELL_W - 40) and harga_font.size > 30:
            harga_font = get_font(bold=True, size=harga_font.size - 4)
            bbox_h = draw.textbbox((0, 0), harga_fmt, font=harga_font)
        
        hw = bbox_h[2] - bbox_h[0]
        hx = x + (CELL_W - hw) // 2
        hy = y + 180
        draw.text((hx, hy), harga_fmt, fill=BLACK, font=harga_font)


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


BLUE_BG = (30, 90, 185)
PAKET_RED = (220, 20, 20)


def draw_text_strikethrough(draw, xy, text, font, fill):
    x, y = xy
    bbox = draw.textbbox((x, y), text, font=font)
    draw.text((x, y), text, fill=fill, font=font)
    mid_y = (bbox[1] + bbox[3]) // 2
    draw.line([(bbox[0], mid_y), (bbox[2], mid_y)], fill=fill, width=3)


def draw_cell_paket(draw, x, y, harga_normal, harga_promo):
    draw.rectangle([x, y, x + CELL_W, y + CELL_H], fill=BLUE_BG)
    PAD = 15

    font_label = get_font(bold=False, size=22)
    font_rp = get_font(bold=True, size=24)

    norm_fmt = format_harga(harga_normal)
    promo_fmt = format_harga(harga_promo)

    # Judul
    judul = "PAKET HEMAT"
    font_judul = get_font(bold=True, size=48)
    bbox_judul = draw.textbbox((0, 0), judul, font=font_judul)
    jw = bbox_judul[2] - bbox_judul[0]
    jx = x + (CELL_W - jw) // 2
    jy = y + PAD
    draw.text((jx, jy), judul, fill=PAKET_RED, font=font_judul)

    # Harga Normal
    norm_y = jy + 60
    draw.text((x + PAD, norm_y), "Harga Normal", fill=WHITE, font=font_label)
    
    norm_text = f"Rp {norm_fmt}"
    font_norm = get_font(bold=True, size=28)
    bbox_norm = draw.textbbox((0, 0), norm_text, font=font_norm)
    while (bbox_norm[2] - bbox_norm[0]) > (CELL_W // 2 - 20) and font_norm.size > 16:
        font_norm = get_font(bold=True, size=font_norm.size - 2)
        bbox_norm = draw.textbbox((0, 0), norm_text, font=font_norm)
    
    norm_x = x + CELL_W - (bbox_norm[2] - bbox_norm[0]) - PAD
    norm_y2 = norm_y + 30
    draw_text_strikethrough(draw, (norm_x, norm_y2), norm_text, font_norm, WHITE)

    # Harga Spesial
    promo_y = norm_y + 70
    draw.text((x + PAD, promo_y), "Harga Spesial", fill=WHITE, font=font_label)
    
    promo_text = f"Rp {promo_fmt}"
    font_promo = get_font(bold=True, size=56)
    bbox_promo = draw.textbbox((0, 0), promo_text, font=font_promo)
    while (bbox_promo[2] - bbox_promo[0]) > (CELL_W - 2 * PAD) and font_promo.size > 24:
        font_promo = get_font(bold=True, size=font_promo.size - 4)
        bbox_promo = draw.textbbox((0, 0), promo_text, font=font_promo)
    
    promo_x = x + (CELL_W - (bbox_promo[2] - bbox_promo[0])) // 2
    promo_y2 = promo_y + 40
    draw.text((promo_x, promo_y2), promo_text, fill=WHITE, font=font_promo)


def buat_gambar_paket(entries):
    img = Image.new('RGB', (IMG_W, IMG_H), color=BLUE_BG)
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
        parts = line.split('.')
        if len(parts) >= 3:
            harga_normal = parts[0].strip()
            harga_promo = parts[1].strip()
            try:
                jumlah = int(parts[2].strip())
            except ValueError:
                jumlah = 1
            for _ in range(jumlah):
                entries.append((harga_normal, harga_promo))
        elif len(parts) == 2:
            entries.append((parts[0].strip(), parts[1].strip()))
    return entries


KEYBOARD = ReplyKeyboardMarkup(
    [[KeyboardButton("/promo"), KeyboardButton("/normal"), KeyboardButton("/paket")]],
    resize_keyboard=True,
    is_persistent=True,
    input_field_placeholder="Pilih perintah di bawah..."
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
        "Contoh: 20000.15000.8\n\n"
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
            if nama:
                items.append((nama, harga))
    return items


async def promo(update: Update, context):
    context.user_data['mode'] = 'promo'
    await update.message.reply_text(
        "🟡 Mode PROMO dipilih.\n\n"
        "Kirim daftar barang, satu per baris:\n\n"
        "AQUA.21000\n"
        "INDOMIE.10000\n"
        "BERAS.65000",
        reply_markup=ForceReply(input_field_placeholder="Ketik daftar barang di sini...")
    )


async def normal(update: Update, context):
    context.user_data['mode'] = 'normal'
    await update.message.reply_text(
        "⬜ Mode NORMAL dipilih.\n\n"
        "Kirim daftar barang, satu per baris:\n\n"
        "AQUA.21000\n"
        "INDOMIE.10000\n"
        "BERAS.65000",
        reply_markup=ForceReply(input_field_placeholder="Ketik daftar barang di sini...")
    )


async def paket(update: Update, context):
    context.user_data['mode'] = 'paket'
    await update.message.reply_text(
        "🔵 Mode PAKET HEMAT dipilih.\n\n"
        "Kirim daftar paket, satu per baris:\n"
        "Format: HARGA_NORMAL.HARGA_PROMO.JUMLAH\n\n"
        "Contoh:\n"
        "20000.15000.8\n"
        "50000.35000.4",
        reply_markup=ForceReply(input_field_placeholder="Contoh: 20000.15000.8")
    )


async def handle_text(update: Update, context):
    mode = context.user_data.get('mode')

    if not mode:
        await update.message.reply_text(
            "Pilih perintah terlebih dahulu 👇",
            reply_markup=KEYBOARD
        )
        return

    lines = (update.message.text or "").split('\n')

    if mode == 'paket':
        entries = parse_paket(lines)
        if not entries:
            await update.message.reply_text(
                "Format salah. Contoh:\n\n20000.15000.8",
                reply_markup=KEYBOARD
            )
            return
        total_images = math.ceil(len(entries) / ITEMS_PER_IMAGE)
        await update.message.reply_text(
            f"Membuat {total_images} gambar untuk {len(entries)} kartu...",
            reply_markup=KEYBOARD
        )
        for i in range(total_images):
            batch = entries[i * ITEMS_PER_IMAGE:(i + 1) * ITEMS_PER_IMAGE]
            gambar = buat_gambar_paket(batch)
            caption = f"Gambar {i + 1}/{total_images}"
            await update.message.reply_photo(photo=gambar, caption=caption)
    else:
        items = parse_items(lines, uppercase=(mode == 'promo'))
        if not items:
            await update.message.reply_text(
                "Format salah. Contoh:\n\nAQUA.21000\nINDOMIE.10000",
                reply_markup=KEYBOARD
            )
            return
        total_images = math.ceil(len(items) / ITEMS_PER_IMAGE)
        await update.message.reply_text(
            f"Membuat {total_images} gambar untuk {len(items)} barang...",
            reply_markup=KEYBOARD
        )
        for i in range(total_images):
            batch = items[i * ITEMS_PER_IMAGE:(i + 1) * ITEMS_PER_IMAGE]
            gambar = buat_gambar_grid(batch) if mode == 'promo' else buat_gambar_normal(batch)
            caption = f"Gambar {i + 1}/{total_images}"
            await update.message.reply_photo(photo=gambar, caption=caption)

    context.user_data['mode'] = None


def main():
    if not TOKEN:
        print("ERROR: TELEGRAM_TOKEN atau BOT_TOKEN tidak ditemukan!")
        return

    print("Bot Telegram Promosi berjalan...")
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("promo", promo))
    app.add_handler(CommandHandler("normal", normal))
    app.add_handler(CommandHandler("paket", paket))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.run_polling()


if __name__ == "__main__":
    main()
