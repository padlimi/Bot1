FROM python:3.9-slim

# Install library pendukung untuk gambar dan font
RUN apt-get update && apt-get install -y \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -r requirements.txt

# Menjalankan bot
CMD ["python", "main.py"]
