FROM python:3.11-slim

# Cài đặt Google Chrome chuẩn
RUN apt-get update && apt-get install -y \
    wget gnupg curl unzip \
    && wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update && apt-get install -y google-chrome-stable \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .
RUN pip install --no-cache-dir flask requests selenium gunicorn
CMD ["python", "app.py"]
