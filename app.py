from flask import Flask, request
import requests
import re
import threading
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
import os

app = Flask(__name__)

# Lấy Token từ Environment Variables của Koyeb
PAGE_ACCESS_TOKEN = os.environ.get('PAGE_ACCESS_TOKEN')
VERIFY_TOKEN = os.environ.get('VERIFY_TOKEN', 'my_secret_token_123')

def send_message(recipient_id, message_text):
    if not PAGE_ACCESS_TOKEN: return
    url = f"https://graph.facebook.com/v20.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"
    requests.post(url, json={'recipient': {'id': recipient_id}, 'message': {'text': message_text}})

def perform_unlock(ff_id, recipient_id):
    driver = None
    try:
        options = Options()
        options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--blink-settings=imagesEnabled=false') # Tắt ảnh để cực nhẹ
        
        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(30)
        driver.get('https://unlockffbeta.com/')
        
        wait = WebDriverWait(driver, 35)
        
        # Nhập UID bằng JS (Siêu ổn định)
        id_input = wait.until(EC.presence_of_element_located((By.XPATH, "//input")))
        driver.execute_script("arguments[0].value = arguments[1];", id_input, ff_id)
        
        # Click Unlock
        unlock_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Unlock')]")))
        driver.execute_script("arguments[0].click();", unlock_btn)
        
        try:
            wait.until(EC.text_to_be_present_in_element((By.XPATH, "//body"), "100%"), timeout=45)
            # GIAO DIỆN THÀNH CÔNG MÀU MÈ
            msg = (
                "╔══════════════╗\n"
                "       🔓 UNLOCK THÀNH CÔNG\n"
                "╚══════════════╝\n\n"
                f"👤 ID: {ff_id}\n"
                "✨ Trạng thái: Bypass Beta Thành Công\n"
                "⏰ Thời hạn: 2 Giờ Trải Nghiệm\n"
                "━━━━━━━━━━━━━━━\n"
                "🚀 Chúc bro chơi game vui vẻ nhé!"
            )
        except TimeoutException:
            msg = f"❌ Thất bại: ID {ff_id} không tồn tại hoặc hệ thống web lỗi."
        
        send_message(recipient_id, msg)
        
    except Exception as e:
        send_message(recipient_id, "⚠️ Hệ thống bận (RAM 512MB quá tải). Thử lại sau 1 phút!")
    finally:
        if driver: driver.quit()

@app.route('/', methods=['GET'])
def verify():
    if request.args.get('hub.verify_token') == VERIFY_TOKEN:
        return request.args.get('hub.challenge'), 200
    return "Bot Online!", 200

@app.route('/', methods=['POST'])
def webhook():
    data = request.get_json()
    if data.get('object') == 'page':
        for entry in data['entry']:
            for messaging in entry.get('messaging', []):
                sender_id = messaging['sender']['id']
                if 'message' in messaging and 'text' in messaging['message']:
                    text = messaging['message']['text'].strip()
                    match = re.match(r'^/unlock\s+(\d+)$', text, re.IGNORECASE)
                    if match:
                        ff_id = match.group(1)
                        # TIN NHẮN CHỜ MÀU MÈ
                        send_message(sender_id, f"🔄 Đang xử lý ID: {ff_id}\n━━━━━━━━━━━━━━━\n⌛ Vui lòng chờ server Koyeb chạy Chrome...")
                        threading.Thread(target=perform_unlock, args=(ff_id, sender_id)).start()
                    else:
                        send_message(sender_id, "👋 Gửi: /unlock [ID] để bắt đầu!")
    return "OK", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
