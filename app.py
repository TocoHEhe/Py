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
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Lấy cấu hình từ Environment Variables trên Render
PAGE_ACCESS_TOKEN = os.environ.get('PAGE_ACCESS_TOKEN')
VERIFY_TOKEN = os.environ.get('VERIFY_TOKEN', 'my_secret_token_123')

def send_message(recipient_id, message_text):
    if not PAGE_ACCESS_TOKEN:
        app.logger.error("LỖI: Chưa cấu hình PAGE_ACCESS_TOKEN!")
        return
    url = f"https://graph.facebook.com/v20.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"
    headers = {'Content-Type': 'application/json'}
    data = {'recipient': {'id': recipient_id}, 'message': {'text': message_text}}
    requests.post(url, headers=headers, json=data)

def perform_unlock(ff_id, recipient_id):
    driver = None
    try:
        # Cấu hình Chrome siêu nhẹ để không bị crash RAM trên Render
        options = Options()
        options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--blink-settings=imagesEnabled=false') # Tắt ảnh để nhẹ web
        
        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(30)
        driver.get('https://unlockffbeta.com/')
        
        wait = WebDriverWait(driver, 35)
        
        # Nhập UID bằng JavaScript (Tránh lỗi invalid element state)
        id_input = wait.until(EC.presence_of_element_located((By.XPATH, "//input")))
        driver.execute_script("arguments[0].value = arguments[1];", id_input, ff_id)
        
        # Click nút Unlock
        unlock_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Unlock')]")))
        driver.execute_script("arguments[0].click();", unlock_btn)
        
        try:
            # Đợi kết quả 100%
            wait.until(EC.text_to_be_present_in_element((By.XPATH, "//body"), "100%"), timeout=45)
            msg = f"✅ Unlock thành công ID {ff_id}!\nĐã mở khóa 2 giờ (Bypass Beta). 🚀"
        except TimeoutException:
            msg = f"❌ Thất bại: ID {ff_id} không tồn tại hoặc sai UID."
        
        send_message(recipient_id, msg)
        
    except Exception as e:
        app.logger.error(f"Lỗi Selenium: {str(e)}")
        send_message(recipient_id, "⚠️ Hệ thống đang bận. Vui lòng thử lại sau 1 phút!")
    finally:
        if driver:
            driver.quit()

@app.route('/', methods=['GET'])
def verify():
    if request.args.get('hub.verify_token') == VERIFY_TOKEN:
        return request.args.get('hub.challenge'), 200
    return "Bot đang chạy...", 200

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
                        send_message(sender_id, f"🔄 Đang xử lý ID: {ff_id}... Chờ khoảng 45s nhé!")
                        threading.Thread(target=perform_unlock, args=(ff_id, sender_id)).start()
                    else:
                        send_message(sender_id, "Chào bro! Gửi /unlock [ID] để mở khóa nhé.")
    return "OK", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
