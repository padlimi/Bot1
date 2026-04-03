import os
import io
import math
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ForceReply
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from PIL import Image, ImageDraw, ImageFont

# Support both TELEGRAM_TOKEN and BOT_TOKEN environment variables
TOKEN = os.environ.get("TELEGRAM_TOKEN") or os.environ.get("BOT_TOKEN")

FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REGULAR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

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

    try:
        font_header = ImageFont.truetype(FONT_BOLD, 42)
        font_nama = ImageFont.truetype(FONT_BOLD, 34)
        font_harga = ImageFont.truetype(FONT_BOLD, 108)
    except Exception:
        font_header = ImageFont.load_default()
        font_nama = font_header
        font_harga = font_header

    header_text = "PROMOSI"
    bbox = draw.textbbox((0, 0), header_text, font=font_header)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = x + (CELL_W - tw) // 2
    ty = y + (HEADER_H - th) // 2 - (bbox[1])
    draw.text((tx, ty), header_text, fill=YELLOW, font=font_header)

    if nama:
        bbox_n = draw.textbbox((0, 0), nama, font=font_nama)
        nw = bbox_n[2] - bbox_n[0]
        nx = x + (CELL_W - nw) // 2
        ny = y + HEADER_H + 18
        draw.text((nx, ny), nama, fill=BLACK, font=font_nama)

    if harga:
        harga_fmt = format_harga(harga)
        bbox_h = draw.textbbox((0, 0), harga_fmt, font=font_harga)
        hw = bbox_h[2] - bbox_h[0]
        hx = x + (CELL_W - hw) // 2
        remaining = CELL_H - HEADER_H
        hy = y + HEADER_H + remaining // 2 - (bbox_h[3] - bbox_h[1]) // 2 + 8
        draw.text((hx, hy), harga_fmt, fill=BLACK, font=font_harga)


def draw_cell_normal(draw, x, y, nama, harga):
    draw.rectangle([x, y, x + CELL_W, y + CELL_H], fill=WHITE, outline=(200, 200, 200), width=2)

    try:
        font_nama = ImageFont.truetype(FONT_BOLD, 36)
        font_harga = ImageFont.truetype(FONT_BOLD, 108)
    except Exception:
        font_nama = ImageFont.load_default()
        font_harga = font_nama

    if nama:
        max_w = CELL_W - 20
        while True:
            bbox_n = draw.textbbox((0, 0), nama, font=font_nama)
            if (bbox_n[2] - bbox_n[0]) <= max_w or font_nama.size <= 18:
                break
            font_nama = ImageFont.truetype(FONT_BOLD, font_nama.size - 2)

        bbox_n = draw.textbbox((0, 0), nama, font=font_nama)
        nw = bbox_n[2] - bbox_n[0]
        nx = x + (CELL_W - nw) // 2
        ny = y + int(CELL_H * 0.18)
        draw.text((nx, ny), nama, fill=BLACK, font=font_nama)

    if harga:
        harga_fmt = format_harga(harga)
        font_h = font_harga
        max_w = CELL_W - 20
        while True:
            bbox_h = draw.textbbox((0, 0), harga_fmt, font=font_h)
            if (bbox_h[2] - bbox_h[0]) <= max_w or font_h.size <= 30:
                break
            font_h = ImageFont.truetype(FONT_BOLD, font_h.size - 4)

        bbox_h = draw.textbbox((0, 0), harga_fmt, font=font_h)
        hw = bbox_h[2] - bbox_h[0]
        hh = bbox_h[3] - bbox_h[1]
        hx = x + (CELL_W - hw) // 2
        hy = y + int(CELL_H * 0.52) - hh // 2
        draw.text((hx, hy), harga_fmt, fill=BLACK, font=font_h)


def buat_gambar_normal(items):
    padded = list(items)
    while len(padded) < ITEMS_PER_IMAGE:
        padded.append(("", ""))

    img = Image.new('RGB', (IMG_W, IMG_H), color=(230, 230, 230))
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


def fit_font(font_path, size, text, max_w, draw, min_size=16):
    font = ImageFont.truetype(font_path, size)
    while size > min_size:
        bbox = draw.textbbox((0, 0), text, font=font)
        if (bbox[2] - bbox[0]) <= max_w:
            break
        size -= 2
        font = ImageFont.truetype(font_path, size)
    return font


def draw_cell_paket(draw, x, y, harga_normal, harga_promo):
    draw.rectangle([x, y, x + CELL_W, y + CELL_H], fill=BLUE_BG)
    PAD = 10

    try:
        font_label = ImageFont.truetype(FONT_REGULAR, 24)
        font_rp_norm = ImageFont.truetype(FONT_BOLD, 22)
        font_rp_prom = ImageFont.truetype(FONT_BOLD, 32)
    except Exception:
        font_label = ImageFont.load_default()
        font_rp_norm = font_rp_prom = font_label

    norm_fmt = format_harga(harga_normal)
    promo_fmt = format_harga(harga_promo)

    judul = "PAKET HEMAT"
    font_judul = fit_font(FONT_BOLD, 54, judul, CELL_W - 2 * PAD, draw)
    norm_font_fit = fit_font(FONT_BOLD, 28, norm_fmt, CELL_W // 2 - 40, draw)
    prom_font_fit = fit_font(FONT_BOLD, 88, promo_fmt, CELL_W - 2 * PAD - 50, draw)

    jb = draw.textbbox((0, 0), judul, font=font_judul)
    jh = jb[3] - jb[1]
    jy = y + PAD
    for dx, dy in [(-2, -2), (2, -2), (-2, 2), (2, 2)]:
        draw.text((x + PAD + dx, jy + dy), judul, fill=BLACK, font=font_judul)
    draw.text((x + PAD, jy), judul, fill=PAKET_RED, font=font_judul)

    row1_y = jy + jh + 18
    draw.text((x + PAD, row1_y + 4), "Harga Normal", fill=WHITE, font=font_label)

    rp1b = draw.textbbox((0, 0), "Rp", font=font_rp_norm)
    norm_b = draw.textbbox((0, 0), norm_fmt, font=norm_font_fit)
    box1_h = max(rp1b[3] - rp1b[1], norm_b[3] - norm_b[1]) + 12
    box1_w = CELL_W // 2 - 5
    box1_x = x + CELL_W - box1_w - PAD
    box1_y = row1_y

    draw.rectangle([box1_x, box1_y, box1_x + box1_w, box1_y + box1_h], fill=BLACK)
    rp1_y = box1_y + (box1_h - (rp1b[3] - rp1b[1])) // 2 - rp1b[1]
    draw.text((box1_x + 6, rp1_y), "Rp", fill=WHITE, font=font_rp_norm)
    nw = norm_b[2] - norm_b[0]
    norm_x = box1_x + box1_w - nw - 6
    norm_y = box1_y + (box1_h - (norm_b[3] - norm_b[1])) // 2 - norm_b[1]
    draw_text_strikethrough(draw, (norm_x, norm_y), norm_fmt, norm_font_fit, WHITE)

    row2_y = row1_y + box1_h + 8
    draw.text((x + PAD, row2_y + 4), "Harga Spesial", fill=WHITE, font=font_label)

    lb = draw.textbbox((0, 0), "Harga Spesial", font=font_label)
    lh = lb[3] - lb[1]

    box2_y = row2_y + lh + 10
    box2_h = y + CELL_H - box2_y - PAD
    box2_x = x + PAD
    box2_w = CELL_W - 2 * PAD
    draw.rectangle([box2_x, box2_y, box2_x + box2_w, box2_y + box2_h], fill=BLACK)

    rp2b = draw.textbbox((0, 0), "Rp", font=font_rp_prom)
    rp2_x = box2_x + 10
    rp2_y = box2_y + 10 - rp2b[1]
    draw.text((rp2_x, rp2_y), "Rp", fill=WHITE, font=font_rp_prom)

    prom_b = draw.textbbox((0, 0), promo_fmt, font=prom_font_fit)
    ph = prom_b[3] - prom_b[1]
    pw = prom_b[2] - prom_b[0]
    rp_h = rp2b[3] - rp2b[1]
    remaining_h = box2_h - rp_h - 16
    prom_y = box2_y + rp_h + 12 + (remaining_h - ph) // 2 - prom_b[1]
    prom_x = box2_x + (box2_w - pw) // 2
    draw.text((prom_x, prom_y), promo_fmt, fill=WHITE, font=prom_font_fit)


def buat_gambar_paket(entries):
    img = Image.new('RGB', (IMG_W, IMG_H), color=BLUE_BG)
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, IMG_W, IMG_H], fill=(20, 70, 160))

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
        print("ERROR: TELEGRAM_TOKEN atau BOT_TOKEN tidak ditemukan di environment variables!")
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
