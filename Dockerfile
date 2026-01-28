FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# --- System deps for Playwright / Chromium ---
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libxshmfence1 \
    libxss1 \
    libxtst6 \
    libxkbcommon0 \
    wget \
    && rm -rf /var/lib/apt/lists/*

# --- Python deps ---
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- Install Playwright browser ---
RUN playwright install chromium

# --- Copy app ---
COPY bot.py faceit_client.py card_renderer.py ./
COPY templates ./templates
COPY static ./static

CMD ["python", "bot.py"]
