FROM python:3.12-slim

# System deps for WeasyPrint (pango, cairo, gdk-pixbuf, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libcairo2 \
    libffi-dev \
    shared-mime-info \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code will be volume-mounted for hot reload
COPY . .

EXPOSE 5000

CMD ["python", "run.py"]
