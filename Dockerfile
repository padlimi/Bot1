# Gunakan Python 3.11 agar kompatibel dengan python-telegram-bot terbaru
FROM python:3.11-slim

# Install library sistem untuk pengolahan gambar (Pillow)
RUN apt-get update && apt-get install -y \
    libfreetype6-dev \
    libjpeg-dev \
    libpng-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy semua file ke dalam folder /app di server
COPY . .

# Install library dari requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Jalankan skrip utama
CMD ["python", "main.py"]
